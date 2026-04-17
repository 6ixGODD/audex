from __future__ import annotations

import datetime
import typing as t
import uuid

from pydantic import BaseModel
from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema
from pydantic_core.core_schema import no_info_plain_validator_function
from pydantic_core.core_schema import plain_serializer_function_ser_schema


def gen_id(prefix: str = "", suffix: str = "", without_hyphen: bool = True, digis: int = 32) -> str:
    """Generate a unique identifier (UUID) with optional prefix and
    suffix.

    Args:
        prefix: A string to prepend to the generated UUID (default: "").
        suffix: A string to append to the generated UUID (default: "").
        without_hyphen: Whether to remove hyphens from the UUID
            (default: True).
        digis: Number of digits to include from the UUID (default: 32).

    Returns:
        A unique identifier string with the specified prefix and suffix.
    """
    uid = uuid.uuid4()
    uid_str = uid.hex if without_hyphen else str(uid)
    uid_str = uid_str[:digis]
    return f"{prefix}{uid_str}{suffix}"


def utcnow() -> datetime.datetime:
    """Get the current UTC datetime with timezone info.

    Returns:
        The current UTC datetime with timezone info.
    """
    return datetime.datetime.now(datetime.timezone.utc)


def flatten_dict(
    m: t.Mapping[str, t.Any],
    /,
    sep: str = ".",
    _parent: str = "",
) -> dict[str, t.Any]:
    """Flatten a nested dictionary into a single-level dictionary with
    dot-separated keys.

    Args:
        m: The nested dictionary to flatten.
        sep: The separator to use between keys (default: '.').
        _parent: The parent key prefix (used for recursion).

    Returns:
        A flattened dictionary with dot-separated keys.
    """
    items = []  # type: list[tuple[str, t.Any]]
    for k, v in m.items():
        key = f"{_parent}{sep}{k}" if _parent else k
        if isinstance(v, t.Mapping):
            items.extend(flatten_dict(v, _parent=key, sep=sep).items())
        else:
            items.append((key, v))
    return dict(items)


class Unset:
    """A singleton class representing an unset value, distinct from
    None.

    This class is used to indicate that a value has not been set or
    provided, allowing differentiation between an explicit None value
    and an unset state.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "<UNSET>"

    __str__ = __repr__

    def __bool__(self) -> bool:
        return False

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Unset)

    def __hash__(self) -> int:
        return hash("UNSET")

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: type[BaseModel], handler: GetCoreSchemaHandler, /
    ) -> CoreSchema:
        return no_info_plain_validator_function(
            lambda v: v if isinstance(v, Unset) else UNSET,
            serialization=plain_serializer_function_ser_schema(lambda v: str(v)),
        )


UNSET = Unset()
