from __future__ import annotations

import abc
import datetime
import typing as t

import sqlmodel as sqlm

from audex import utils
from audex.entity import BaseEntity

E = t.TypeVar("E", bound=BaseEntity)


class BaseTable(sqlm.SQLModel, abc.ABC, t.Generic[E], table=False):
    """Base __table__ model with common fields for entities.

    All entity __table__ models should inherit from this class to ensure
    consistent structure across the database schema.
    """

    __tablename__: t.ClassVar[str]

    id: int | None = sqlm.Field(
        default=None,
        primary_key=True,
        description="Auto-increment primary key",
    )
    uid: str = sqlm.Field(
        index=True,
        unique=True,
        max_length=50,
        default_factory=utils.gen_id,
        description="Business identifier (UUID/ULID)",
    )
    created_at: datetime.datetime = sqlm.Field(
        default_factory=utils.utcnow,
        nullable=False,
        description="Creation timestamp",
    )
    updated_at: datetime.datetime | None = sqlm.Field(
        default=None,
        nullable=True,
        sa_column_kwargs={"onupdate": utils.utcnow},
        description="Last update timestamp",
    )

    def __repr__(self) -> str:
        return f"TABLE <{self.__class__.__name__}(uid={self.uid!r})>"

    @classmethod
    @abc.abstractmethod
    def from_entity(cls, entity: E) -> t.Self: ...

    @abc.abstractmethod
    def to_entity(self) -> E: ...


from audex.lib.repos.tables import doctor  # noqa: E402
from audex.lib.repos.tables import segment  # noqa: E402
from audex.lib.repos.tables import session  # noqa: E402
from audex.lib.repos.tables import utterance  # noqa: E402

TABLES: set[type[sqlm.SQLModel]] = (
    doctor.TABLES | segment.TABLES | session.TABLES | utterance.TABLES
)
