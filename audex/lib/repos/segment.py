from __future__ import annotations

import builtins
import typing as t

import sqlalchemy as sa
import sqlmodel as sqlm

from audex.entity.segment import Segment
from audex.filters import Filter
from audex.lib.database.sqlite import SQLite
from audex.lib.repos.database.sqlite import SQLiteRepository
from audex.lib.repos.tables.segment import SegmentTable


class SegmentRepository(SQLiteRepository[Segment]):
    """SQLite implementation of Segment repository.

    Provides CRUD operations for Segment entities with additional
    specialized query methods for segment management by session.
    """

    __table__ = SegmentTable
    __tablename__ = SegmentTable.__tablename__

    def __init__(self, sqlite: SQLite) -> None:
        super().__init__(sqlite)

    async def create(self, data: Segment, /) -> str:
        """Create a new segment in the database.

        Args:
            data: The segment entity to create.

        Returns:
            The ID of the created segment.
        """
        async with self.sqlite.session() as session:
            segment_table = SegmentTable.from_entity(data)
            session.add(segment_table)
            await session.commit()
            await session.refresh(segment_table)
            return segment_table.id

    async def read(self, id: str, /) -> Segment | None:
        """Read a segment by ID.

        Args:
            id: The ID (id) of the segment to retrieve.

        Returns:
            The segment entity if found, None otherwise.
        """
        async with self.sqlite.session() as session:
            stmt = sqlm.select(SegmentTable).where(SegmentTable.id == id)
            result = await session.execute(stmt)
            segment_obj = result.scalar_one_or_none()

            if segment_obj is None:
                return None

            return segment_obj.to_entity()

    async def first(self, filter: Filter) -> Segment | None:
        """Retrieve the first segment matching the filter.

        Args:
            filter: Filter to apply when searching for the segment.

        Returns:
            The first segment entity matching the filter, or None if no match.
        """
        spec = self.build_query_spec(filter)

        async with self.sqlite.session() as session:
            stmt = sqlm.select(SegmentTable)

            for clause in spec.where:
                stmt = stmt.where(clause)

            for order in spec.order_by:
                stmt = stmt.order_by(order)

            stmt = stmt.limit(1)

            result = await session.execute(stmt)
            segment_obj = result.scalar_one_or_none()

            if segment_obj is None:
                return None

            return segment_obj.to_entity()

    async def list(
        self,
        arg: builtins.list[str] | t.Optional[Filter] = None,  # noqa
        *,
        page_index: int = 0,
        page_size: int = 100,
    ) -> builtins.list[Segment]:
        """List segments by IDs or with optional filtering and
        pagination.

        Args:
            arg: Either a list of IDs to retrieve, or an optional filter.
            page_index: Zero-based page index for pagination.
            page_size: Number of items per page.

        Returns:
            List of segment entities matching the criteria.
        """
        async with self.sqlite.session() as session:
            if isinstance(arg, list):
                if not arg:
                    return []

                stmt = sqlm.select(SegmentTable).where(sqlm.col(SegmentTable.id).in_(arg))
                result = await session.execute(stmt)
                segment_objs = result.scalars().all()
                return [obj.to_entity() for obj in segment_objs]

            spec = self.build_query_spec(arg)
            stmt = sqlm.select(SegmentTable)

            for clause in spec.where:
                stmt = stmt.where(clause)

            for order in spec.order_by:
                stmt = stmt.order_by(order)

            stmt = stmt.offset(page_index * page_size).limit(page_size)

            result = await session.execute(stmt)
            segment_objs = result.scalars().all()
            return [obj.to_entity() for obj in segment_objs]

    async def update(self, data: Segment, /) -> str:
        """Update an existing segment.

        Args:
            data: The segment entity with updated values.

        Returns:
            The ID of the updated segment.

        Raises:
            ValueError: If the segment with the given ID does not exist.
        """
        async with self.sqlite.session() as session:
            stmt = sqlm.select(SegmentTable).where(SegmentTable.id == data.id)
            result = await session.execute(stmt)
            segment_obj = result.scalar_one_or_none()

            if segment_obj is None:
                raise ValueError(f"Segment with id {data.id} not found")

            segment_obj.update(data)
            session.add(segment_obj)
            await session.commit()
            await session.refresh(segment_obj)
            return segment_obj.id

    async def update_many(self, datas: builtins.list[Segment]) -> builtins.list[str]:
        """Update multiple segments in the database.

        Args:
            datas: List of segment entities with updated values.

        Returns:
            List of IDs of the updated segments.

        Raises:
            ValueError: If any segment with the given ID does not exist.
        """
        if not datas:
            return []

        updated_ids: builtins.list[str] = []
        async with self.sqlite.session() as session:
            ids = [data.id for data in datas]
            stmt = sqlm.select(SegmentTable).where(sqlm.col(SegmentTable.id).in_(ids))
            result = await session.execute(stmt)
            table_objs = {obj.id: obj for obj in result.scalars().all()}

            missing_ids = set(ids) - set(table_objs.keys())
            if missing_ids:
                raise ValueError(f"Segments with IDs {missing_ids} not found")

            for data in datas:
                segment_obj = table_objs[data.id]
                segment_obj.update(data)
                session.add(segment_obj)
                updated_ids.append(segment_obj.id)

            await session.commit()
            return updated_ids

    async def delete(self, id: str, /) -> bool:
        """Delete a segment by ID.

        Args:
            id: The ID (id) of the segment to delete.

        Returns:
            True if the segment was deleted, False if not found.
        """
        async with self.sqlite.session() as session:
            stmt = sqlm.select(SegmentTable).where(SegmentTable.id == id)
            result = await session.execute(stmt)
            segment_obj = result.scalar_one_or_none()

            if segment_obj is None:
                return False

            await session.delete(segment_obj)
            await session.commit()
            return True

    async def delete_many(
        self,
        arg: builtins.list[str] | t.Optional[Filter] = None,  # noqa
    ) -> builtins.list[str] | int:
        """Delete multiple segments by IDs or matching a filter.

        Args:
            arg: Either a list of IDs to delete, or an optional filter.

        Returns:
            If deleting by IDs, returns list of deleted IDs.
            If deleting by filter, returns count of deleted records.
        """
        async with self.sqlite.session() as session:
            if isinstance(arg, list):
                if not arg:
                    return []

                stmt = sqlm.select(SegmentTable).where(sqlm.col(SegmentTable.id).in_(arg))
                result = await session.execute(stmt)
                segment_objs = result.scalars().all()

                if not segment_objs:
                    return []

                segment_ids = [obj.id for obj in segment_objs]
                for obj in segment_objs:
                    await session.delete(obj)

                await session.commit()
                return segment_ids

            spec = self.build_query_spec(arg)
            stmt = sqlm.select(SegmentTable.id)
            for clause in spec.where:
                stmt = stmt.where(clause)

            result = await session.execute(stmt)
            segment_ids = [row[0] for row in result.all()]

            if not segment_ids:
                return 0

            count = len(segment_ids)
            delete_stmt = sa.delete(SegmentTable).where(sqlm.col(SegmentTable.id).in_(segment_ids))
            await session.execute(delete_stmt)
            await session.commit()
            return count

    async def count(self, filter: t.Optional[Filter] = None) -> int:  # noqa
        """Count segments matching the filter.

        Args:
            filter: Optional filter to apply. If None, counts all segments.

        Returns:
            Number of segments matching the filter.
        """
        spec = self.build_query_spec(filter)

        async with self.sqlite.session() as session:
            stmt = sqlm.select(sa.func.count()).select_from(SegmentTable)

            for clause in spec.where:
                stmt = stmt.where(clause)

            result = await session.execute(stmt)
            return result.scalar_one()
