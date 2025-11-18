from __future__ import annotations

import abc
import datetime
import typing as t

from prototypex import utils
from prototypex.entity import BaseEntity
import sqlmodel as sqlm

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


# from prototypex.infras.repository.tables import admin
# from prototypex.infras.repository.tables import api
# from prototypex.infras.repository.tables import api_key
# from prototypex.infras.repository.tables import app
# from prototypex.infras.repository.tables import subscription
# from prototypex.infras.repository.tables import user
#
# TABLES: set[type[sqlm.SQLModel]] = (
#     admin.TABLES | api_key.TABLES | api.TABLES | app.TABLES | subscription.TABLES | user.TABLES
# )
