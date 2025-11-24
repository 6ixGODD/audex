from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:
    from audex.config import Config
    from audex.lib.recorder import AudioRecorder
    from audex.lib.store import Store


def make_recorder(config: Config, store: Store) -> AudioRecorder:
    import pyaudio

    from audex.lib.recorder import AudioConfig
    from audex.lib.recorder import AudioRecorder

    fmt = {
        "float32": pyaudio.paFloat32,
        "int32": pyaudio.paInt32,
        "int16": pyaudio.paInt16,
        "int8": pyaudio.paInt8,
        "uint8": pyaudio.paUInt8,
    }
    return AudioRecorder(
        store=store,
        config=AudioConfig(
            format=fmt[config.infrastructure.recorder.format],
            channels=config.infrastructure.recorder.channels,
            rate=config.infrastructure.recorder.rate,
            chunk=config.infrastructure.recorder.chunk,
            input_device_index=config.infrastructure.recorder.input_device_index,
        ),
    )
