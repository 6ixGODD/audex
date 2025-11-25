from __future__ import annotations

import asyncio
import datetime
import enum
import io
import typing as t

import numpy as np
import pyaudio
import pydub

from audex import utils
from audex.helper.mixin import AsyncContextMixin
from audex.helper.mixin import LoggingMixin
from audex.lib.store import Store


class AudioFormat(str, enum.Enum):
    """Supported audio output formats."""

    PCM = "pcm"
    WAV = "wav"
    MP3 = "mp3"
    OPUS = "opus"


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
    """High-performance audio recorder using PyAudio with real-time
    streaming.

    This recorder captures audio from a microphone and can start/stop
    recording multiple times, creating separate audio segments for each
    recording session. Audio data is automatically uploaded to the
    configured Store.

    Features:
    - Real-time audio streaming with async generators
    - Multiple output format support (PCM, WAV, MP3, OPUS)
    - Efficient numpy-based audio processing
    - Non-blocking streaming while recording
    - Time-based segment extraction
    - Dynamic dtype handling based on AudioConfig

    Attributes:
        store: Storage backend for uploading audio files.
        config: Audio recording configuration.

    Example:
        ```python
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
        await recorder.start("session-123", "segment")

        # Stream audio chunks in real-time
        async for chunk in recorder.stream(
            chunk_size=16000,  # 1 second chunks
            format=AudioFormat.MP3,
        ):
            await send_to_api(chunk)

        segment = await recorder.stop()
        await recorder.close()
        ```
    """

    __logtag__ = "audex.lib.audio.recorder"

    # Mapping PyAudio format to numpy dtype and sample width
    _FORMAT_MAP: t.ClassVar[dict[int, tuple[np.dtype[t.Any], int]]] = {
        pyaudio.paInt8: (np.int8, 1),
        pyaudio.paInt16: (np.int16, 2),
        pyaudio.paInt24: (np.int32, 3),  # Note: 24-bit stored in 32-bit container
        pyaudio.paInt32: (np.int32, 4),
        pyaudio.paFloat32: (np.float32, 4),
    }

    def __init__(self, store: Store, config: AudioConfig | None = None):
        super().__init__()
        self.store = store
        self.config = config or AudioConfig()

        # Determine numpy dtype and sample width from config
        if self.config.format not in self._FORMAT_MAP:
            raise ValueError(f"Unsupported audio format: {self.config.format}")

        self._numpy_dtype, self._sample_width = self._FORMAT_MAP[self.config.format]

        self._audio: pyaudio.PyAudio | None = None
        self._stream: pyaudio.Stream | None = None

        # Use numpy array for efficient operations
        self._frames_data: list[np.ndarray] = []  # Store as numpy arrays
        self._frames_timestamps: list[datetime.datetime] = []  # Separate timestamps

        self._is_recording = False
        self._current_key: str | None = None
        self._started_at: datetime.datetime | None = None

        # Streaming state
        self._stream_position: int = 0  # Track streaming position in samples
        self._stream_lock = asyncio.Lock()

        self.logger.debug(
            f"Initialized with dtype={self._numpy_dtype}, sample_width={self._sample_width}"
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
        """Check if recording is currently active."""
        return self._is_recording

    @property
    def current_segment_key(self) -> str | None:
        """Get the key of the current recording segment."""
        return self._current_key

    async def start(self, *prefixes: str) -> str:
        """Start a new recording segment.

        Args:
            *prefixes: Prefix parts for the storage key.

        Returns:
            The full storage key for this segment.

        Raises:
            RuntimeError: If already recording or audio system not initialized.
        """
        if self._is_recording:
            raise RuntimeError("Already recording")

        if self._audio is None:
            raise RuntimeError("Audio system not initialized. Call init() first.")

        # Generate unique key
        segment_id = utils.gen_id(prefix="")
        self._current_key = self.store.key_builder.build(*prefixes, f"{segment_id}.wav")
        self._frames_data.clear()
        self._frames_timestamps.clear()
        self._stream_position = 0
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

        Converts to numpy array with correct dtype based on config.
        """
        if in_data and self._is_recording:
            timestamp = utils.utcnow()

            # Handle 24-bit audio specially (packed, needs unpacking)
            if self.config.format == pyaudio.paInt24:
                # Convert 24-bit packed to 32-bit
                audio_array = self._unpack_24bit(in_data)
            else:
                # Standard conversion
                audio_array = np.frombuffer(in_data, dtype=self._numpy_dtype)

            self._frames_data.append(audio_array)
            self._frames_timestamps.append(timestamp)
        return None, pyaudio.paContinue

    def _unpack_24bit(self, data: bytes) -> np.ndarray:
        """Unpack 24-bit audio data to 32-bit numpy array.

        Args:
            data: 24-bit packed audio data.

        Returns:
            32-bit numpy array.
        """
        num_samples = len(data) // 3
        samples = np.zeros(num_samples, dtype=np.int32)

        for i in range(num_samples):
            # Read 3 bytes (little-endian)
            b0 = data[i * 3]
            b1 = data[i * 3 + 1]
            b2 = data[i * 3 + 2]

            # Combine into 24-bit value
            value = b0 | (b1 << 8) | (b2 << 16)

            # Sign extension: if bit 23 is set, extend with 1s
            if value & 0x800000:  # Negative number
                value |= 0xFF000000  # Set upper 8 bits

            # Convert to signed int32
            samples[i] = np.int32(value if value < 0x80000000 else value - 0x100000000)

        return samples

    def _pack_24bit(self, data: np.ndarray) -> bytes:
        """Pack 32-bit numpy array to 24-bit audio data.

        Args:
            data: 32-bit numpy array.

        Returns:
            24-bit packed audio data.
        """
        # Clip to 24-bit range
        data = np.clip(data, -8388608, 8388607)

        packed = bytearray(len(data) * 3)
        for i, sample in enumerate(data):
            # Extract 3 bytes (little-endian)
            packed[i * 3] = sample & 0xFF  # type: ignore
            packed[i * 3 + 1] = (sample >> 8) & 0xFF  # type: ignore
            packed[i * 3 + 2] = (sample >> 16) & 0xFF  # type: ignore

        return bytes(packed)

    def _find_frame_index(self, target_time: datetime.datetime) -> int:
        """Binary search to find frame index closest to target time.

        Args:
            target_time: Target timestamp to search for.

        Returns:
            Index of the frame closest to target time (rounded down).
        """
        if not self._frames_timestamps:
            return 0

        left, right = 0, len(self._frames_timestamps) - 1

        # Handle boundary cases
        if target_time <= self._frames_timestamps[0]:
            return 0
        if target_time >= self._frames_timestamps[-1]:
            return len(self._frames_timestamps) - 1

        # Binary search
        while left <= right:
            mid = (left + right) // 2
            mid_time = self._frames_timestamps[mid]

            if mid_time == target_time:
                return mid
            if mid_time < target_time:
                left = mid + 1
            else:
                right = mid - 1

        return right if right >= 0 else 0

    def _resample_audio_numpy(
        self,
        audio_data: np.ndarray,
        src_rate: int,
        dst_rate: int,
        src_channels: int,
        dst_channels: int,
    ) -> np.ndarray:
        """Resample audio using numpy (fast linear interpolation).

        Args:
            audio_data: Input audio as numpy array.
            src_rate: Source sample rate.
            dst_rate: Destination sample rate.
            src_channels: Source number of channels.
            dst_channels: Destination number of channels.

        Returns:
            Resampled audio as numpy array.
        """
        original_dtype = audio_data.dtype

        # Convert to float for processing if integer type
        if np.issubdtype(original_dtype, np.integer):
            # Normalize to [-1.0, 1.0]
            if original_dtype == np.int8:
                audio_data = audio_data.astype(np.float32) / 128.0
            elif original_dtype == np.int16:
                audio_data = audio_data.astype(np.float32) / 32768.0
            elif original_dtype == np.int32:
                audio_data = audio_data.astype(np.float32) / 2147483648.0

        # Reshape for multi-channel processing
        if src_channels > 1:
            audio_data = audio_data.reshape(-1, src_channels)
        else:
            audio_data = audio_data.reshape(-1, 1)

        # Channel conversion
        if src_channels != dst_channels:
            if dst_channels == 1 and src_channels == 2:
                # Stereo to mono: average channels
                audio_data = audio_data.mean(axis=1, keepdims=True)
            elif dst_channels == 2 and src_channels == 1:
                # Mono to stereo: duplicate channel
                audio_data = np.repeat(audio_data, 2, axis=1)

        # Sample rate conversion using numpy interpolation
        if src_rate != dst_rate:
            num_frames = audio_data.shape[0]
            ratio = src_rate / dst_rate
            new_num_frames = int(num_frames / ratio)

            # Create interpolation indices
            src_indices = np.arange(new_num_frames) * ratio
            src_indices_low = src_indices.astype(np.int32)
            src_indices_high = np.minimum(src_indices_low + 1, num_frames - 1)
            frac = (src_indices - src_indices_low).reshape(-1, 1)

            # Linear interpolation (vectorized!)
            audio_low = audio_data[src_indices_low]
            audio_high = audio_data[src_indices_high]
            audio_data = audio_low * (1 - frac) + audio_high * frac

        # Convert back to original dtype
        if np.issubdtype(original_dtype, np.integer):
            if original_dtype == np.int8:
                audio_data = (audio_data * 128.0).clip(-128, 127).astype(np.int8)
            elif original_dtype == np.int16:
                audio_data = (audio_data * 32768.0).clip(-32768, 32767).astype(np.int16)
            elif original_dtype == np.int32:
                audio_data = (
                    (audio_data * 2147483648.0).clip(-2147483648, 2147483647).astype(np.int32)
                )

        return audio_data.flatten()

    def _to_pydub_segment(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        channels: int,
    ) -> pydub.AudioSegment:
        """Convert numpy array to pydub AudioSegment.

        Args:
            audio_data: Audio data as numpy array.
            sample_rate: Sample rate in Hz.
            channels: Number of channels.

        Returns:
            pydub AudioSegment.
        """
        # Convert numpy array to bytes
        if self.config.format == pyaudio.paInt24:
            raw_data = self._pack_24bit(audio_data)
        else:
            raw_data = audio_data.tobytes()

        # Determine sample width
        if audio_data.dtype == np.int8:
            sample_width = 1
        elif audio_data.dtype == np.int16:
            sample_width = 2
        elif audio_data.dtype == np.int32:
            sample_width = 4
        elif audio_data.dtype == np.float32:
            # Convert float32 to int16 for pydub
            audio_data = (audio_data * 32768.0).clip(-32768, 32767).astype(np.int16)
            raw_data = audio_data.tobytes()
            sample_width = 2
        else:
            raise ValueError(f"Unsupported numpy dtype: {audio_data.dtype}")

        # Create pydub AudioSegment
        return pydub.AudioSegment(
            data=raw_data,
            sample_width=sample_width,
            frame_rate=sample_rate,
            channels=channels,
        )

    def _encode_audio(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        channels: int,
        output_format: AudioFormat,
    ) -> bytes:
        """Encode audio to specified format using pydub.

        Args:
            audio_data: Audio data as numpy array.
            sample_rate: Sample rate in Hz.
            channels: Number of channels.
            output_format: Target audio format.

        Returns:
            Encoded audio data.

        Raises:
            ValueError: If unsupported format.
        """
        if output_format == AudioFormat.PCM:
            # Return raw PCM data
            if self.config.format == pyaudio.paInt24:
                return self._pack_24bit(audio_data)
            return audio_data.tobytes()

        # Convert to pydub AudioSegment
        pydub_audio = self._to_pydub_segment(audio_data, sample_rate, channels)

        if output_format == AudioFormat.WAV:
            # Export as WAV
            buffer = io.BytesIO()
            pydub_audio.export(buffer, format="wav")
            return buffer.getvalue()

        if output_format == AudioFormat.MP3:
            # Export as MP3
            buffer = io.BytesIO()
            pydub_audio.export(
                buffer,
                format="mp3",
                bitrate="128k",
                parameters=["-q:a", "2"],  # High quality
            )
            self.logger.debug(f"Encoded to MP3: {len(buffer.getvalue())} bytes")
            return buffer.getvalue()

        if output_format == AudioFormat.OPUS:
            # Export as OPUS
            buffer = io.BytesIO()
            pydub_audio.export(
                buffer,
                format="opus",
                codec="libopus",
                parameters=["-b:a", "64k"],
            )
            self.logger.debug(f"Encoded to OPUS: {len(buffer.getvalue())} bytes")
            return buffer.getvalue()

        raise ValueError(f"Unsupported format: {output_format}")

    async def stream(
        self,
        chunk_size: int | None = None,
        format: AudioFormat = AudioFormat.PCM,
        channels: int | None = None,
        rate: int | None = None,
    ) -> t.AsyncGenerator[bytes, None]:
        """Stream audio chunks in real-time while recording.

        This does NOT affect the recording buffer. You can stream and
        record simultaneously.

        Args:
            chunk_size: Number of samples per chunk. None = config.chunk.
            format: Output audio format.
            channels: Target channels. None = config.channels.
            rate: Target sample rate. None = config.rate.

        Yields:
            Audio chunks in specified format.

        Example:
            ```python
            # Stream 1-second MP3 chunks
            async for chunk in recorder.stream(
                chunk_size=16000, format=AudioFormat.MP3
            ):
                await send_to_server(chunk)
            ```
        """
        if not self._is_recording:
            self.logger.warning("Cannot stream: not recording")
            return

        chunk_size = chunk_size or self.config.chunk
        target_channels = channels or self.config.channels
        target_rate = rate or self.config.rate

        self.logger.info(
            f"Started streaming: chunk_size={chunk_size}, format={format.value}, "
            f"rate={target_rate}, channels={target_channels}"
        )

        while self._is_recording:
            async with self._stream_lock:
                # Check if we have enough new frames
                total_samples = sum(len(frame) for frame in self._frames_data)
                streamed_samples = self._stream_position

                available_samples = total_samples - streamed_samples

                if available_samples < chunk_size:
                    # Not enough data yet
                    await asyncio.sleep(0.01)  # 10ms
                    continue

                # Calculate which frames to extract
                samples_needed = chunk_size
                start_sample = streamed_samples
                end_sample = start_sample + samples_needed

                # Efficiently concatenate numpy arrays
                all_audio = np.concatenate(self._frames_data)
                chunk_audio = all_audio[start_sample:end_sample]

                # Update stream position
                self._stream_position = end_sample

            # Process audio (outside lock for performance)
            if target_rate != self.config.rate or target_channels != self.config.channels:
                chunk_audio = self._resample_audio_numpy(
                    chunk_audio,
                    src_rate=self.config.rate,
                    dst_rate=target_rate,
                    src_channels=self.config.channels,
                    dst_channels=target_channels,
                )

            # Encode to target format
            encoded_chunk = self._encode_audio(
                chunk_audio,
                sample_rate=target_rate,
                channels=target_channels,
                output_format=format,
            )

            yield encoded_chunk

        self.logger.info("Streaming ended")

    async def segment(
        self,
        started_at: datetime.datetime,
        ended_at: datetime.datetime,
        *,
        channels: int | None = None,
        rate: int | None = None,
        format: AudioFormat = AudioFormat.PCM,
    ) -> bytes:
        """Extract audio segment between two timestamps.

        Args:
            started_at: Start timestamp.
            ended_at: End timestamp.
            channels: Target channels. None = config.channels.
            rate: Target sample rate. None = config.rate.
            format: Output format (PCM, WAV, MP3, OPUS).

        Returns:
            Audio segment in specified format.

        Raises:
            RuntimeError: If audio system not initialized.
            ValueError: If invalid time range or no frames.
        """
        if self._audio is None:
            raise RuntimeError("Audio system not initialized")

        if ended_at < started_at:
            raise ValueError(
                f"End time ({ended_at.isoformat()}) must be after "
                f"start time ({started_at.isoformat()})"
            )

        if not self._frames_data:
            raise ValueError("No audio frames available")

        target_channels = channels or self.config.channels
        target_rate = rate or self.config.rate

        # Find frame indices
        start_idx = self._find_frame_index(started_at)
        end_idx = self._find_frame_index(ended_at)

        if start_idx == end_idx:
            end_idx = min(start_idx + 1, len(self._frames_data) - 1)

        self.logger.debug(
            f"Extracting frames {start_idx} to {end_idx} (total: {end_idx - start_idx + 1} frames)"
        )

        # Efficiently concatenate numpy arrays
        selected_frames = self._frames_data[start_idx : end_idx + 1]
        combined_audio = np.concatenate(selected_frames)

        # Resample if needed
        if target_rate != self.config.rate or target_channels != self.config.channels:
            combined_audio = self._resample_audio_numpy(
                combined_audio,
                src_rate=self.config.rate,
                dst_rate=target_rate,
                src_channels=self.config.channels,
                dst_channels=target_channels,
            )
            self.logger.debug(
                f"Resampled: {self.config.rate}Hz {self.config.channels}ch -> "
                f"{target_rate}Hz {target_channels}ch"
            )

        # Encode to target format
        encoded_data = self._encode_audio(
            combined_audio,
            sample_rate=target_rate,
            channels=target_channels,
            output_format=format,
        )

        self.logger.debug(
            f"Created {format.value.upper()} segment: "
            f"{len(encoded_data)} bytes, {target_rate}Hz {target_channels}ch"
        )

        return encoded_data

    async def stop(self) -> AudioSegment:
        """Stop recording and save to storage.

        Returns:
            AudioSegment containing recording information.

        Raises:
            RuntimeError: If not currently recording.
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

        # Combine all frames efficiently with numpy
        all_audio = np.concatenate(self._frames_data)

        # Convert to bytes based on format
        if self.config.format == pyaudio.paInt24:
            frames = self._pack_24bit(all_audio)
        else:
            frames = all_audio.tobytes()

        frame_count = len(self._frames_data)

        # Calculate duration
        if self._started_at is None:
            self._started_at = ended_at

        duration_ms = int((ended_at - self._started_at).total_seconds() * 1000)

        # Create WAV file using pydub
        pydub_audio = self._to_pydub_segment(
            all_audio,
            sample_rate=self.config.rate,
            channels=self.config.channels,
        )
        wav_buffer = io.BytesIO()
        pydub_audio.export(wav_buffer, format="wav")
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

        # Reset state but keep frames for potential extraction
        self._current_key = None
        self._started_at = None

        return segment

    def clear_frames(self) -> None:
        """Clear all recorded frames from memory."""
        self._frames_data.clear()
        self._frames_timestamps.clear()
        self._stream_position = 0
        self.logger.debug("Cleared all recorded frames from memory")

    def list_input_devices(self) -> list[dict[str, t.Any]]:
        """List available audio input devices."""
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
