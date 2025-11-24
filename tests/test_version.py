from __future__ import annotations

import audex


async def test_version() -> None:
    assert hasattr(audex, "__version__")
    assert isinstance(audex.__version__, str)
    assert audex.__version__ != ""


async def test_title() -> None:
    assert hasattr(audex, "__title__")
    assert isinstance(audex.__title__, str)
    assert audex.__title__ == "Audex"
