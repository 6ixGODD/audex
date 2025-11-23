from __future__ import annotations

import builtins
import typing as t

import sqlalchemy as sa
import sqlmodel as sqlm

from audex.entity.session import Session
from audex.filters import Filter
from audex.lib.database.sqlite import SQLite
from audex.lib.repos.database.sqlite import SQLiteRepository
from audex.lib.repos.tables.session import SessionTable


class SessionRepository(SQLiteRepository[Session]):
    """SQLite implementation of Session repository.

    Provides CRUD operations for Session entities with additional
    specialized query methods for session management by doctor.
    """

    __table__ = SessionTable
    __tablename__ = SessionTable.__tablename__

    def __init__(self, sqlite: SQLite) -> None:
        super().__init__(sqlite)

    async def create(self, data: Session, /) -> str:
        """Create a new session in the database.

        Args:
            data: The session entity to create.

        Returns:
            The ID of the created session.
        """
        async with self.sqlite.session() as session, session.begin():
            session_table = SessionTable.from_entity(data)
            session.add(session_table)
            await session.commit()
            await session.refresh(session_table)
            return session_table.uid

    async def read(self, id: str, /) -> Session | None:
        """Read a session by ID.

        Args:
            id: The ID (uid) of the session to retrieve.

        Returns:
            The session entity if found, None otherwise.
        """
        async with self.sqlite.session() as session:
            stmt = sqlm.select(SessionTable).where(SessionTable.uid == id)
            result = await session.execute(stmt)
            session_obj = result.scalar_one_or_none()

            if session_obj is None:
                return None

            return session_obj.to_entity()

    async def first(self, filter: Filter) -> Session | None:
        """Retrieve the first session matching the filter.

        Args:
            filter: Filter to apply when searching for the session.

        Returns:
            The first session entity matching the filter, or None if no match.
        """
        spec = self.build_query_spec(filter)

        async with self.sqlite.session() as session:
            stmt = sqlm.select(SessionTable)

            for clause in spec.where:
                stmt = stmt.where(clause)

            for order in spec.order_by:
                stmt = stmt.order_by(order)

            stmt = stmt.limit(1)

            result = await session.execute(stmt)
            session_obj = result.scalar_one_or_none()

            if session_obj is None:
                return None

            return session_obj.to_entity()

    async def list(
        self,
        arg: builtins.list[str] | t.Optional[Filter] = None,  # noqa
        *,
        page_index: int = 0,
        page_size: int = 100,
    ) -> builtins.list[Session]:
        """List sessions by IDs or with optional filtering and
        pagination.

        Args:
            arg: Either a list of IDs to retrieve, or an optional filter.
            page_index: Zero-based page index for pagination.
            page_size: Number of items per page.

        Returns:
            List of session entities matching the criteria.
        """
        async with self.sqlite.session() as session:
            if isinstance(arg, list):
                if not arg:
                    return []

                stmt = sqlm.select(SessionTable).where(sqlm.col(SessionTable.uid).in_(arg))
                result = await session.execute(stmt)
                session_objs = result.scalars().all()
                return [obj.to_entity() for obj in session_objs]

            spec = self.build_query_spec(arg)
            stmt = sqlm.select(SessionTable)

            for clause in spec.where:
                stmt = stmt.where(clause)

            for order in spec.order_by:
                stmt = stmt.order_by(order)

            stmt = stmt.offset(page_index * page_size).limit(page_size)

            result = await session.execute(stmt)
            session_objs = result.scalars().all()
            return [obj.to_entity() for obj in session_objs]

    async def update(self, data: Session, /) -> str:
        """Update an existing session.

        Args:
            data: The session entity with updated values.

        Returns:
            The ID of the updated session.

        Raises:
            ValueError: If the session with the given ID does not exist.
        """
        async with self.sqlite.session() as session, session.begin():
            stmt = sqlm.select(SessionTable).where(SessionTable.uid == data.id)
            result = await session.execute(stmt)
            session_obj = result.scalar_one_or_none()

            if session_obj is None:
                raise ValueError(f"Session with uid {data.id} not found")

            session_obj.doctor_id = data.doctor_id
            session_obj.patient_name = data.patient_name
            session_obj.status = data.status.value
            session_obj.started_at = data.started_at
            session_obj.ended_at = data.ended_at
            session_obj.notes = data.notes
            session_obj.updated_at = data.updated_at

            session.add(session_obj)
            await session.commit()
            await session.refresh(session_obj)
            return session_obj.uid

    async def update_many(self, datas: builtins.list[Session]) -> builtins.list[str]:
        """Update multiple sessions in the database.

        Args:
            datas: List of session entities with updated values.

        Returns:
            List of IDs of the updated sessions.

        Raises:
            ValueError: If any session with the given ID does not exist.
        """
        if not datas:
            return []

        updated_ids: builtins.list[str] = []
        async with self.sqlite.session() as session, session.begin():
            ids = [data.id for data in datas]
            stmt = sqlm.select(SessionTable).where(sqlm.col(SessionTable.uid).in_(ids))
            result = await session.execute(stmt)
            table_objs = {obj.uid: obj for obj in result.scalars().all()}

            missing_ids = set(ids) - set(table_objs.keys())
            if missing_ids:
                raise ValueError(f"Sessions with IDs {missing_ids} not found")

            for data in datas:
                session_obj = table_objs[data.id]
                session_obj.doctor_id = data.doctor_id
                session_obj.patient_name = data.patient_name
                session_obj.status = data.status.value
                session_obj.started_at = data.started_at
                session_obj.ended_at = data.ended_at
                session_obj.notes = data.notes
                session_obj.updated_at = data.updated_at
                session.add(session_obj)
                updated_ids.append(session_obj.uid)

            await session.commit()
            return updated_ids

    async def delete(self, id: str, /) -> bool:
        """Delete a session by ID.

        Args:
            id: The ID (uid) of the session to delete.

        Returns:
            True if the session was deleted, False if not found.
        """
        async with self.sqlite.session() as session, session.begin():
            stmt = sqlm.select(SessionTable).where(SessionTable.uid == id)
            result = await session.execute(stmt)
            session_obj = result.scalar_one_or_none()

            if session_obj is None:
                return False

            await session.delete(session_obj)
            await session.commit()
            return True

    async def delete_many(
        self,
        arg: builtins.list[str] | t.Optional[Filter] = None,  # noqa
    ) -> builtins.list[str] | int:
        """Delete multiple sessions by IDs or matching a filter.

        Args:
            arg: Either a list of IDs to delete, or an optional filter.

        Returns:
            If deleting by IDs, returns list of deleted IDs.
            If deleting by filter, returns count of deleted records.
        """
        async with self.sqlite.session() as session, session.begin():
            if isinstance(arg, list):
                if not arg:
                    return []

                stmt = sqlm.select(SessionTable).where(sqlm.col(SessionTable.uid).in_(arg))
                result = await session.execute(stmt)
                session_objs = result.scalars().all()

                if not session_objs:
                    return []

                session_uids = [obj.uid for obj in session_objs]
                for obj in session_objs:
                    await session.delete(obj)

                await session.commit()
                return session_uids

            spec = self.build_query_spec(arg)
            stmt = sqlm.select(SessionTable.uid)
            for clause in spec.where:
                stmt = stmt.where(clause)

            result = await session.execute(stmt)
            session_uids = [row[0] for row in result.all()]

            if not session_uids:
                return 0

            count = len(session_uids)
            delete_stmt = sa.delete(SessionTable).where(
                sqlm.col(SessionTable.uid).in_(session_uids)
            )
            await session.execute(delete_stmt)
            await session.commit()
            return count

    async def count(self, filter: t.Optional[Filter] = None) -> int:  # noqa
        """Count sessions matching the filter.

        Args:
            filter: Optional filter to apply. If None, counts all sessions.

        Returns:
            Number of sessions matching the filter.
        """
        spec = self.build_query_spec(filter)

        async with self.sqlite.session() as session:
            stmt = sqlm.select(sa.func.count()).select_from(SessionTable)

            for clause in spec.where:
                stmt = stmt.where(clause)

            result = await session.execute(stmt)
            return result.scalar_one()
