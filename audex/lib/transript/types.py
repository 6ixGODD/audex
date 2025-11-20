from __future__ import annotations


class Start:
    __slots__ = ("at",)

    def __init__(self, at: float) -> None:
        self.at = at


class Delta:
    __slots__ = ("from_at", "interim", "text", "to_at")

    def __init__(self, from_at: float, to_at: float, text: str, interim: bool) -> None:
        self.from_at = from_at
        self.to_at = to_at
        self.text = text
        self.interim = interim


class Done:
    __slots__ = ()
