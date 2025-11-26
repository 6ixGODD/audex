from __future__ import annotations

import socket
import typing as t


def getaddr() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return t.cast(str, s.getsockname()[0])
    finally:
        s.close()


def getfreeport() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return t.cast(int, s.getsockname()[1])
