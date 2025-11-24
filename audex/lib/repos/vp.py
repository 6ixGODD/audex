from __future__ import annotations

import builtins
import typing as t

import sqlalchemy as sa
import sqlmodel as sqlm

from audex.entity.vp import VP
from audex.filters import Filter
from audex.lib.database.sqlite import SQLite
from audex.lib.repos.database.sqlite import SQLiteRepository
from audex.lib.repos.tables.vp import VPTable


class VPRepository(SQLiteRepository[VP]):
    """SQLite implementation of VP repository.

    Provides CRUD operations for VP entities with additional specialized
    query methods for utterance management by session and segment.
    """

    __table__ = VPTable
    __tablename__ = VPTable.__tablename__

    def __init__(self, sqlite: SQLite) -> None:
        super().__init__(sqlite)

    async def create(self, data: VP, /) -> str:
        """Create a new utterance in the database.

        Args:
            data: The utterance entity to create.

        Returns:
            The ID of the created utterance.
        """
        async with self.sqlite.session() as session, session.begin():
            utterance_table = VPTable.from_entity(data)
            session.add(utterance_table)
            await session.commit()
            await session.refresh(utterance_table)
            return utterance_table.uid

    async def read(self, id: str, /) -> VP | None:
        """Read an utterance by ID.

        Args:
            id: The ID (uid) of the utterance to retrieve.

        Returns:
            The utterance entity if found, None otherwise.
        """
        async with self.sqlite.session() as session:
            stmt = sqlm.select(VPTable).where(VPTable.uid == id)
            result = await session.execute(stmt)
            utterance_obj = result.scalar_one_or_none()

            if utterance_obj is None:
                return None

            return utterance_obj.to_entity()

    async def first(self, filter: Filter) -> VP | None:
        """Retrieve the first utterance matching the filter.

        Args:
            filter: Filter to apply when searching for the utterance.

        Returns:
            The first utterance entity matching the filter, or None if no match.
        """
        spec = self.build_query_spec(filter)

        async with self.sqlite.session() as session:
            stmt = sqlm.select(VPTable)

            for clause in spec.where:
                stmt = stmt.where(clause)

            for order in spec.order_by:
                stmt = stmt.order_by(order)

            stmt = stmt.limit(1)

            result = await session.execute(stmt)
            utterance_obj = result.scalar_one_or_none()

            if utterance_obj is None:
                return None

            return utterance_obj.to_entity()

    async def list(
        self,
        arg: builtins.list[str] | t.Optional[Filter] = None,  # noqa
        *,
        page_index: int = 0,
        page_size: int = 100,
    ) -> builtins.list[VP]:
        """List utterances by IDs or with optional filtering and
        pagination.

        Args:
            arg: Either a list of IDs to retrieve, or an optional filter.
            page_index: Zero-based page index for pagination.
            page_size: Number of items per page.

        Returns:
            List of utterance entities matching the criteria.
        """
        async with self.sqlite.session() as session:
            if isinstance(arg, list):
                if not arg:
                    return []

                stmt = sqlm.select(VPTable).where(sqlm.col(VPTable.uid).in_(arg))
                result = await session.execute(stmt)
                utterance_objs = result.scalars().all()
                return [obj.to_entity() for obj in utterance_objs]

            spec = self.build_query_spec(arg)
            stmt = sqlm.select(VPTable)

            for clause in spec.where:
                stmt = stmt.where(clause)

            for order in spec.order_by:
                stmt = stmt.order_by(order)

            stmt = stmt.offset(page_index * page_size).limit(page_size)

            result = await session.execute(stmt)
            utterance_objs = result.scalars().all()
            return [obj.to_entity() for obj in utterance_objs]

    async def update(self, data: VP, /) -> str:
        """Update an existing utterance.

        Args:
            data: The utterance entity with updated values.

        Returns:
            The ID of the updated utterance.

        Raises:
            ValueError: If the utterance with the given ID does not exist.
        """
        async with self.sqlite.session() as session, session.begin():
            stmt = sqlm.select(VPTable).where(VPTable.uid == data.id)
            result = await session.execute(stmt)
            utterance_obj = result.scalar_one_or_none()

            if utterance_obj is None:
                raise ValueError(f"VP with uid {data.id} not found")

            utterance_obj.update(data)
            session.add(utterance_obj)
            await session.commit()
            await session.refresh(utterance_obj)
            return utterance_obj.uid

    async def update_many(self, datas: builtins.list[VP]) -> builtins.list[str]:
        """Update multiple utterances in the database.

        Args:
            datas: List of utterance entities with updated values.

        Returns:
            List of IDs of the updated utterances.

        Raises:
            ValueError: If any utterance with the given ID does not exist.
        """
        if not datas:
            return []

        updated_ids: builtins.list[str] = []
        async with self.sqlite.session() as session, session.begin():
            ids = [data.id for data in datas]
            stmt = sqlm.select(VPTable).where(sqlm.col(VPTable.uid).in_(ids))
            result = await session.execute(stmt)
            table_objs = {obj.uid: obj for obj in result.scalars().all()}

            missing_ids = set(ids) - set(table_objs.keys())
            if missing_ids:
                raise ValueError(f"VPs with IDs {missing_ids} not found")

            for data in datas:
                utterance_obj = table_objs[data.id]
                utterance_obj.update(data)
                session.add(utterance_obj)
                updated_ids.append(utterance_obj.uid)

            await session.commit()
            return updated_ids

    async def delete(self, id: str, /) -> bool:
        """Delete an utterance by ID.

        Args:
            id: The ID (uid) of the utterance to delete.

        Returns:
            True if the utterance was deleted, False if not found.
        """
        async with self.sqlite.session() as session, session.begin():
            stmt = sqlm.select(VPTable).where(VPTable.uid == id)
            result = await session.execute(stmt)
            utterance_obj = result.scalar_one_or_none()

            if utterance_obj is None:
                return False

            await session.delete(utterance_obj)
            await session.commit()
            return True

    async def delete_many(
        self,
        arg: builtins.list[str] | t.Optional[Filter] = None,  # noqa
    ) -> builtins.list[str] | int:
        """Delete multiple utterances by IDs or matching a filter.

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

                stmt = sqlm.select(VPTable).where(sqlm.col(VPTable.uid).in_(arg))
                result = await session.execute(stmt)
                utterance_objs = result.scalars().all()

                if not utterance_objs:
                    return []

                utterance_uids = [obj.uid for obj in utterance_objs]
                for obj in utterance_objs:
                    await session.delete(obj)

                await session.commit()
                return utterance_uids

            spec = self.build_query_spec(arg)
            stmt = sqlm.select(VPTable.uid)
            for clause in spec.where:
                stmt = stmt.where(clause)

            result = await session.execute(stmt)
            utterance_uids = [row[0] for row in result.all()]

            if not utterance_uids:
                return 0

            count = len(utterance_uids)
            delete_stmt = sa.delete(VPTable).where(sqlm.col(VPTable.uid).in_(utterance_uids))
            await session.execute(delete_stmt)
            await session.commit()
            return count

    async def count(self, filter: t.Optional[Filter] = None) -> int:  # noqa
        """Count utterances matching the filter.

        Args:
            filter: Optional filter to apply. If None, counts all utterances.

        Returns:
            Number of utterances matching the filter.
        """
        spec = self.build_query_spec(filter)

        async with self.sqlite.session() as session:
            stmt = sqlm.select(sa.func.count()).select_from(VPTable)

            for clause in spec.where:
                stmt = stmt.where(clause)

            result = await session.execute(stmt)
            return result.scalar_one()
