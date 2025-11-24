from __future__ import annotations

import asyncio
import collections
import datetime
import io
import pathlib
import typing as t
import wave

import pyaudio

from audex import utils
from audex.helper.mixin import AsyncContextMixin
from audex.helper.mixin import LoggingMixin
from audex.lib.store import Store


class AudioConfig(t.TypedDict):
    """Audio recording configuration.

    Attributes:
        format: Audio format (pyaudio constant).
        channels: Number of audio channels (1=mono, 2=stereo).
        rate: Sample rate in Hz (e.g., 16000, 44100, 48000).
        chunk: Number of frames per buffer.
        input_device_index: Index of input device, None for default.
    """

    format: int
    channels: int
    rate: int
    chunk: int
    input_device_index: int | None


class AudioSegment(t.NamedTuple):
    """Represents a recorded audio segment.

    Attributes:
        key: Storage key where the audio is saved.
        duration_ms: Duration of the segment in milliseconds.
        started_at: Timestamp when recording started.
        ended_at: Timestamp when recording ended.
        frames: Raw audio frames (bytes).
    """

    key: str
    duration_ms: int
    started_at: datetime.datetime
    ended_at: datetime.datetime
    frames: bytes


class AudioRecorder(LoggingMixin, AsyncContextMixin):
    """Audio recorder using PyAudio for continuous recording.

    This recorder captures audio from a microphone and can start/stop
    recording multiple times, creating separate audio segments for each
    recording session. Audio data is automatically uploaded to the
    configured Store.

    Attributes:
        store: Storage backend for uploading audio files.
        config: Audio recording configuration.

    Example:
        ```python
        # Create recorder
        recorder = AudioRecorder(
            store=local_store,
            config={
                "format": pyaudio.paInt16,
                "channels": 1,
                "rate": 16000,
                "chunk": 1024,
                "input_device_index": None,
            },
        )

        await recorder.init()

        # Start recording
        await recorder.start_recording(
            key_prefix="session-123/segment"
        )

        # Record for some time...
        await asyncio.sleep(5)

        # Stop and get the segment
        segment = await recorder.stop_recording()
        print(f"Recorded {segment.duration_ms}ms to {segment.key}")

        # Start another segment
        await recorder.start_recording(
            key_prefix="session-123/segment"
        )
        await asyncio.sleep(3)
        segment2 = await recorder.stop_recording()

        # Cleanup
        await recorder.close()
        ```
    """

    __logtag__ = "audex.lib.audio.recorder"

    def __init__(
        self,
        store: Store,
        config: AudioConfig | None = None,
    ) -> None:
        super().__init__()
        self.store = store
        self.config = config or self._default_config()

        self._audio: pyaudio.PyAudio | None = None
        self._stream: pyaudio.Stream | None = None
        self._frames: collections.deque[bytes] = collections.deque()
        self._is_recording = False
        self._recording_task: asyncio.Task[None] | None = None
        self._current_key: str | None = None
        self._started_at: datetime.datetime | None = None

    @staticmethod
    def _default_config() -> AudioConfig:
        """Get default audio configuration.

        Returns:
            Default AudioConfig with 16kHz mono recording.
        """
        return AudioConfig(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            chunk=1024,
            input_device_index=None,
        )

    async def init(self) -> None:
        """Initialize the audio system.

        Creates the PyAudio instance and validates the audio configuration.

        Raises:
            Exception: If audio initialization fails.
        """
        self._audio = pyaudio.PyAudio()
        self.logger.info("Audio system initialized")

        # Log available devices
        device_count = self._audio.get_device_count()
        self.logger.debug(f"Found {device_count} audio devices")

        for i in range(device_count):
            device_info = self._audio.get_device_info_by_index(i)
            if device_info["maxInputChannels"] > 0:
                self.logger.debug(
                    f"Input device {i}: {device_info['name']} "
                    f"(channels: {device_info['maxInputChannels']}, "
                    f"rate: {device_info['defaultSampleRate']})"
                )

    async def close(self) -> None:
        """Close the audio system and release resources.

        Stops any active recording and cleans up PyAudio resources.
        """
        if self._is_recording:
            await self.stop_recording()

        if self._stream is not None:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

        if self._audio is not None:
            self._audio.terminate()
            self._audio = None

        self.logger.info("Audio system closed")

    @property
    def is_recording(self) -> bool:
        """Check if recording is currently active.

        Returns:
            True if recording, False otherwise.
        """
        return self._is_recording

    @property
    def current_segment_key(self) -> str | None:
        """Get the key of the current recording segment.

        Returns:
            The storage key for the current segment, or None if not recording.
        """
        return self._current_key

    async def start_recording(self, key_prefix: str) -> str:
        """Start a new recording segment.

        Args:
            key_prefix: Prefix for the storage key (e.g., "session-123/segment").
                A unique ID and .wav extension will be appended.

        Returns:
            The full storage key for this segment.

        Raises:
            RuntimeError: If already recording or audio system not initialized.

        Example:
            ```python
            key = await recorder.start_recording("session-abc/segment")
            # key might be: "audex/session-abc/segment-xyz123.wav"
            ```
        """
        if self._is_recording:
            raise RuntimeError("Already recording")

        if self._audio is None:
            raise RuntimeError("Audio system not initialized. Call init() first.")

        # Generate unique key
        segment_id = utils.gen_id(prefix="")
        self._current_key = self.store.key_builder.build(f"{key_prefix}-{segment_id}.wav")
        self._frames.clear()
        self._started_at = utils.utcnow()

        # Open audio stream
        self._stream = self._audio.open(
            format=self.config["format"],
            channels=self.config["channels"],
            rate=self.config["rate"],
            input=True,
            frames_per_buffer=self.config["chunk"],
            input_device_index=self.config["input_device_index"],
            stream_callback=self._audio_callback,
        )

        self._is_recording = True
        self._stream.start_stream()

        self.logger.info(f"Started recording to {self._current_key}")
        return self._current_key

    def _audio_callback(
        self,
        in_data: bytes | None,
        _frame_count: int,
        _time_info: t.Mapping[str, float],
        _status_flags: int,
    ) -> tuple[None, int]:
        """PyAudio callback for capturing audio frames.

        This is called automatically by PyAudio on a separate thread.

        Args:
            in_data: Input audio data.
            _frame_count: Number of frames.
            _time_info: Timing information.
            _status_flags: Status flags.

        Returns:
            Tuple of (None, pyaudio.paContinue).
        """
        if in_data and self._is_recording:
            self._frames.append(in_data)
        return None, pyaudio.paContinue

    async def stop_recording(self) -> AudioSegment:
        """Stop the current recording and save to storage.

        Returns:
            AudioSegment containing recording information and data.

        Raises:
            RuntimeError: If not currently recording.

        Example:
            ```python
            segment = await recorder.stop_recording()
            print(f"Duration: {segment.duration_ms}ms")
            print(f"Saved to: {segment.key}")
            ```
        """
        if not self._is_recording:
            raise RuntimeError("Not currently recording")

        self._is_recording = False

        # Stop stream
        if self._stream is not None:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

        ended_at = utils.utcnow()

        # Collect frames
        frames = b"".join(self._frames)
        self._frames.clear()

        # Calculate duration
        if self._started_at is None:
            self._started_at = ended_at  # Fallback

        duration_ms = int((ended_at - self._started_at).total_seconds() * 1000)

        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(self.config["channels"])
            wf.setsampwidth(self._audio.get_sample_size(self.config["format"]))
            wf.setframerate(self.config["rate"])
            wf.writeframes(frames)

        wav_data = wav_buffer.getvalue()

        # Upload to store
        key = self._current_key
        if key is None:
            raise RuntimeError("No current segment key")

        await self.store.upload(
            data=wav_data,
            key=key,
            metadata={
                "content_type": "audio/wav",
                "duration_ms": duration_ms,
                "sample_rate": self.config["rate"],
                "channels": self.config["channels"],
                "started_at": self._started_at.isoformat(),
                "ended_at": ended_at.isoformat(),
            },
        )

        self.logger.info(
            f"Stopped recording. Duration: {duration_ms}ms, Size: {len(wav_data)} bytes"
        )

        segment = AudioSegment(
            key=key,
            duration_ms=duration_ms,
            started_at=self._started_at,
            ended_at=ended_at,
            frames=frames,
        )

        # Reset state
        self._current_key = None
        self._started_at = None

        return segment

    async def export_segment(
        self,
        key: str,
        output_path: str | pathlib.Path,
    ) -> None:
        """Export a recorded segment to a local file.

        Args:
            key: Storage key of the segment to export.
            output_path: Local file path to save the audio.

        Raises:
            Exception: If download or file write fails.

        Example:
            ```python
            await recorder.export_segment(
                key="audex/session-123/segment-001.wav",
                output_path="/tmp/recording.wav",
            )
            ```
        """
        output_path = pathlib.Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = await self.store.download(key)
        if isinstance(data, bytes):
            output_path.write_bytes(data)
        else:
            # Handle streaming case
            with output_path.open("wb") as f:
                async for chunk in data:
                    f.write(chunk)

        self.logger.info(f"Exported segment {key} to {output_path}")

    async def list_segments(self, prefix: str) -> list[str]:
        """List all audio segments with a given prefix.

        Args:
            prefix: Key prefix to filter segments (e.g., "session-123").

        Returns:
            List of storage keys for matching segments.

        Example:
            ```python
            segments = await recorder.list_segments("session-123")
            # Returns: [
            #     "audex/session-123/segment-001.wav",
            #     "audex/session-123/segment-002.wav",
            # ]
            ```
        """
        full_prefix = self.store.key_builder.build(prefix)
        keys: list[str] = []

        async for batch in await self.store.list(prefix=full_prefix):
            keys.extend(batch)

        self.logger.debug(f"Found {len(keys)} segments with prefix {prefix}")
        return keys

    async def delete_segment(self, key: str) -> None:
        """Delete a recorded segment from storage.

        Args:
            key: Storage key of the segment to delete.

        Example:
            ```python
            await recorder.delete_segment(
                "audex/session-123/segment-001.wav"
            )
            ```
        """
        await self.store.delete(key)
        self.logger.info(f"Deleted segment {key}")

    def list_input_devices(self) -> list[dict[str, t.Any]]:
        """List available audio input devices.

        Returns:
            List of device information dictionaries.

        Example:
            ```python
            devices = recorder.list_input_devices()
            for dev in devices:
                print(f"{dev['index']}: {dev['name']}")
            ```
        """
        if self._audio is None:
            raise RuntimeError("Audio system not initialized")

        devices: list[dict[str, t.Any]] = []
        for i in range(self._audio.get_device_count()):
            info = self._audio.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0:
                devices.append({
                    "index": i,
                    "name": info["name"],
                    "channels": info["maxInputChannels"],
                    "default_rate": info["defaultSampleRate"],
                })

        return devices
