from __future__ import annotations

import array
import datetime
import io
import typing as t
import wave

import pyaudio

from audex import utils
from audex.helper.mixin import AsyncContextMixin
from audex.helper.mixin import LoggingMixin
from audex.lib.store import Store


class AudioConfig(t.NamedTuple):
    """Audio recording configuration.

    Attributes:
        format: Audio format (pyaudio constant).
        channels: Number of audio channels (1=mono, 2=stereo).
        rate: Sample rate in Hz (e.g., 16000, 44100, 48000).
        chunk: Number of frames per buffer.
        input_device_index: Index of input device, None for default.
    """

    format: int = pyaudio.paInt16
    channels: int = 1
    rate: int = 16000
    chunk: int = 1024
    input_device_index: int | None = None


class AudioFrame:
    """Single audio frame with timestamp.

    Uses __slots__ to minimize memory footprint.

    Attributes:
        timestamp: When this frame was captured.
        data: Raw audio bytes.
    """

    __slots__ = ("data", "timestamp")

    def __init__(self, timestamp: datetime.datetime, data: bytes) -> None:
        self.timestamp = timestamp
        self.data = data


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

    All recorded frames are kept in memory with timestamps, allowing
    efficient extraction of arbitrary time ranges after recording.

    Attributes:
        store: Storage backend for uploading audio files.
        config: Audio recording configuration.

    Example:
        ```python
        # Create recorder
        recorder = AudioRecorder(
            store=local_store,
            config=AudioConfig(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                chunk=1024,
            ),
        )

        await recorder.init()

        # Start recording
        await recorder.start("session-123", "segment")

        # Record for some time...
        await asyncio.sleep(5)

        # Extract segment by time range
        start_time = (
            datetime.datetime.utcnow()
            - datetime.timedelta(seconds=3)
        )
        end_time = datetime.datetime.utcnow()
        audio_data = await recorder.segment(
            started_at=start_time,
            ended_at=end_time,
            channels=1,
            rate=8000,  # Resample to 8kHz
        )

        # Stop and get the full segment
        segment = await recorder.stop()
        print(f"Recorded {segment.duration_ms}ms to {segment.key}")

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
        self.config = config or AudioConfig()

        self._audio: pyaudio.PyAudio | None = None
        self._stream: pyaudio.Stream | None = None
        self._frames: list[AudioFrame] = []  # Use list for efficient indexing
        self._is_recording = False
        self._current_key: str | None = None
        self._started_at: datetime.datetime | None = None

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
            await self.stop()

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

    async def start(self, *prefixes: str) -> str:
        """Start a new recording segment.

        Args:
            *prefixes: Prefix parts for the storage key (e.g., "session-123", "segment").
                A unique ID and .wav extension will be appended.

        Returns:
            The full storage key for this segment.

        Raises:
            RuntimeError: If already recording or audio system not initialized.

        Example:
            ```python
            key = await recorder.start("session-abc", "segment")
            # key might be: "audex/session-abc/segment/xyz123.wav"
            ```
        """
        if self._is_recording:
            raise RuntimeError("Already recording")

        if self._audio is None:
            raise RuntimeError("Audio system not initialized. Call init() first.")

        # Generate unique key
        segment_id = utils.gen_id(prefix="")
        self._current_key = self.store.key_builder.build(*prefixes, f"{segment_id}.wav")
        self._frames.clear()
        self._started_at = utils.utcnow()

        # Open audio stream
        self._stream = self._audio.open(
            format=self.config.format,
            channels=self.config.channels,
            rate=self.config.rate,
            input=True,
            frames_per_buffer=self.config.chunk,
            input_device_index=self.config.input_device_index,
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
        Stores frames with timestamps for later extraction.

        Args:
            in_data: Input audio data.
            _frame_count: Number of frames.
            _time_info: Timing information.
            _status_flags: Status flags.

        Returns:
            Tuple of (None, pyaudio.paContinue).
        """
        if in_data and self._is_recording:
            timestamp = utils.utcnow()
            self._frames.append(AudioFrame(timestamp, in_data))
        return None, pyaudio.paContinue

    def _find_frame_index(self, target_time: datetime.datetime) -> int:
        """Binary search to find frame index closest to target time.

        Args:
            target_time: Target timestamp to search for.

        Returns:
            Index of the frame closest to target time (rounded down).
        """
        if not self._frames:
            return 0

        left, right = 0, len(self._frames) - 1

        # Handle boundary cases
        if target_time <= self._frames[0].timestamp:
            return 0
        if target_time >= self._frames[-1].timestamp:
            return len(self._frames) - 1

        # Binary search
        while left <= right:
            mid = (left + right) // 2
            mid_time = self._frames[mid].timestamp

            if mid_time == target_time:
                return mid
            if mid_time < target_time:
                left = mid + 1
            else:
                right = mid - 1

        # Return the index just before target time
        return right if right >= 0 else 0

    def _resample_audio(
        self,
        audio_data: bytes,
        src_rate: int,
        dst_rate: int,
        src_channels: int,
        dst_channels: int,
        sample_width: int,
    ) -> bytes:
        """Resample audio data to different rate and/or channel
        configuration.

        Uses simple linear interpolation for resampling and channel mixing/splitting.

        Args:
            audio_data: Input audio data as bytes.
            src_rate: Source sample rate.
            dst_rate: Destination sample rate.
            src_channels: Source number of channels.
            dst_channels: Destination number of channels.
            sample_width: Bytes per sample (e.g., 2 for int16).

        Returns:
            Resampled audio data as bytes.
        """
        # Convert bytes to array of samples
        format_char = {1: "b", 2: "h", 4: "i"}[sample_width]
        samples = array.array(format_char, audio_data)

        # Reshape into frames (interleaved channels)
        num_frames = len(samples) // src_channels
        frames = [samples[i * src_channels : (i + 1) * src_channels] for i in range(num_frames)]

        # Channel conversion
        if src_channels != dst_channels:
            new_frames = []
            for frame in frames:
                if dst_channels == 1 and src_channels == 2:
                    # Stereo to mono: average channels
                    new_frames.append([sum(frame) // len(frame)])
                elif dst_channels == 2 and src_channels == 1:
                    # Mono to stereo: duplicate channel
                    new_frames.append([frame[0], frame[0]])
                else:
                    # For other cases, just take first dst_channels
                    new_frames.append(frame[:dst_channels])
            frames = new_frames

        # Sample rate conversion
        if src_rate != dst_rate:
            ratio = src_rate / dst_rate
            new_num_frames = int(num_frames / ratio)
            new_frames = []

            for i in range(new_num_frames):
                # Linear interpolation
                src_idx = i * ratio
                idx_low = int(src_idx)
                idx_high = min(idx_low + 1, num_frames - 1)
                frac = src_idx - idx_low

                frame_low = frames[idx_low]
                frame_high = frames[idx_high]

                # Interpolate each channel
                new_frame = [
                    int(frame_low[ch] * (1 - frac) + frame_high[ch] * frac)
                    for ch in range(dst_channels)
                ]
                new_frames.append(new_frame)

            frames = new_frames

        # Flatten frames back to samples
        result_samples = array.array(format_char)
        for frame in frames:
            result_samples.extend(frame)

        return result_samples.tobytes()

    async def segment(
        self,
        started_at: datetime.datetime,
        ended_at: datetime.datetime,
        *,
        channels: int | None = None,
        rate: int | None = None,
        format: int | None = None,
    ) -> bytes:
        """Extract audio segment data between two timestamps.

        Efficiently extracts frames recorded between the specified timestamps
        using binary search, then optionally resamples/reformats them. The
        segment is returned as a complete WAV file in bytes.

        Args:
            started_at: Start timestamp of the segment.
            ended_at: End timestamp of the segment.
            channels: Target number of channels. If None, uses recording config.
            rate: Target sample rate. If None, uses recording config.
            format: Target audio format. If None, uses recording config.

        Returns:
            Bytes of the audio segment in WAV format with specified config.

        Raises:
            RuntimeError: If audio system not initialized.
            ValueError: If end time is before start time, or no frames available.

        Example:
            ```python
            # Extract last 3 seconds at 8kHz mono
            start = datetime.datetime.utcnow() - datetime.timedelta(
                seconds=3
            )
            end = datetime.datetime.utcnow()
            data = await recorder.segment(
                started_at=start,
                ended_at=end,
                channels=1,
                rate=8000,
            )

            # Save to file
            with open("/tmp/segment.wav", "wb") as f:
                f.write(data)
            ```
        """
        if self._audio is None:
            raise RuntimeError("Audio system not initialized")

        # Validate time range
        if ended_at < started_at:
            raise ValueError(
                f"End time ({ended_at.isoformat()}) must be after "
                f"start time ({started_at.isoformat()})"
            )

        if not self._frames:
            raise ValueError("No audio frames available")

        # Use recording config as defaults
        target_channels = channels if channels is not None else self.config.channels
        target_rate = rate if rate is not None else self.config.rate
        target_format = format if format is not None else self.config.format

        # Find frame indices using binary search (efficient!)
        start_idx = self._find_frame_index(started_at)
        end_idx = self._find_frame_index(ended_at)

        # Ensure we have at least one frame
        if start_idx == end_idx:
            end_idx = min(start_idx + 1, len(self._frames) - 1)

        # Extract frames efficiently with slice (no iteration!)
        selected_frames = self._frames[start_idx : end_idx + 1]

        self.logger.debug(
            f"Extracted frames {start_idx} to {end_idx} (total: {len(selected_frames)} frames)"
        )

        # Combine frame data
        combined_frames = b"".join(frame.data for frame in selected_frames)

        # Resample/reformat if needed
        needs_conversion = (
            target_channels != self.config.channels
            or target_rate != self.config.rate
            or target_format != self.config.format
        )

        if needs_conversion:
            sample_width = self._audio.get_sample_size(self.config.format)
            combined_frames = self._resample_audio(
                audio_data=combined_frames,
                src_rate=self.config.rate,
                dst_rate=target_rate,
                src_channels=self.config.channels,
                dst_channels=target_channels,
                sample_width=sample_width,
            )
            self.logger.debug(
                f"Resampled: {self.config.rate}Hz {self.config.channels}ch -> "
                f"{target_rate}Hz {target_channels}ch"
            )

        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(target_channels)
            wf.setsampwidth(self._audio.get_sample_size(target_format))
            wf.setframerate(target_rate)
            wf.writeframes(combined_frames)

        wav_data = wav_buffer.getvalue()

        self.logger.debug(
            f"Created WAV segment: {len(selected_frames)} frames, "
            f"{len(wav_data)} bytes, {target_rate}Hz {target_channels}ch"
        )

        return wav_data

    async def stop(self) -> AudioSegment:
        """Stop the current recording and save to storage.

        Returns:
            AudioSegment containing recording information and data.

        Raises:
            RuntimeError: If not currently recording.

        Example:
            ```python
            segment = await recorder.stop()
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
        frames = b"".join(frame.data for frame in self._frames)
        frame_count = len(self._frames)

        # Calculate duration
        if self._started_at is None:
            self._started_at = ended_at  # Fallback

        duration_ms = int((ended_at - self._started_at).total_seconds() * 1000)

        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(self.config.channels)
            wf.setsampwidth(self._audio.get_sample_size(self.config.format))
            wf.setframerate(self.config.rate)
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
                "sample_rate": self.config.rate,
                "channels": self.config.channels,
                "started_at": self._started_at.isoformat(),
                "ended_at": ended_at.isoformat(),
                "frame_count": frame_count,
            },
        )

        self.logger.info(
            f"Stopped recording. Duration: {duration_ms}ms, "
            f"Frames: {frame_count}, Size: {len(wav_data)} bytes"
        )

        segment = AudioSegment(
            key=key,
            duration_ms=duration_ms,
            started_at=self._started_at,
            ended_at=ended_at,
            frames=frames,
        )

        # Reset state but keep frames in memory for potential segment extraction
        self._current_key = None
        self._started_at = None

        return segment

    def clear_frames(self) -> None:
        """Clear all recorded frames from memory.

        Use this to free memory after you're done extracting segments.

        Example:
            ```python
            # After recording and extracting all needed segments
            recorder.clear_frames()
            ```
        """
        self._frames.clear()
        self.logger.debug("Cleared all recorded frames from memory")

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
