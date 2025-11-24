from __future__ import annotations

import builtins
import typing as t

import sqlalchemy as sa
import sqlmodel as sqlm

from audex.entity.doctor import Doctor
from audex.filters import Filter
from audex.lib.database.sqlite import SQLite
from audex.lib.repos.database.sqlite import SQLiteRepository
from audex.lib.repos.tables.doctor import DoctorTable


class DoctorRepository(SQLiteRepository[Doctor]):
    """SQLite implementation of Doctor repository.

    Provides CRUD operations for Doctor entities with additional
    specialized query methods for authentication and voiceprint
    management.
    """

    __table__ = DoctorTable
    __tablename__ = DoctorTable.__tablename__

    def __init__(self, sqlite: SQLite) -> None:
        super().__init__(sqlite)

    async def create(self, data: Doctor, /) -> str:
        """Create a new doctor in the database.

        Args:
            data: The doctor entity to create.

        Returns:
            The ID of the created doctor.
        """
        async with self.sqlite.session() as session, session.begin():
            doctor_table = DoctorTable.from_entity(data)
            session.add(doctor_table)
            await session.commit()
            await session.refresh(doctor_table)
            return doctor_table.uid

    async def read(self, id: str, /) -> Doctor | None:
        """Read a doctor by ID.

        Args:
            id: The ID (uid) of the doctor to retrieve.

        Returns:
            The doctor entity if found, None otherwise.
        """
        async with self.sqlite.session() as session:
            stmt = sqlm.select(DoctorTable).where(DoctorTable.uid == id)
            result = await session.execute(stmt)
            doctor_obj = result.scalar_one_or_none()

            if doctor_obj is None:
                return None

            return doctor_obj.to_entity()

    async def first(self, filter: Filter) -> Doctor | None:
        """Retrieve the first doctor matching the filter.

        Args:
            filter: Filter to apply when searching for the doctor.

        Returns:
            The first doctor entity matching the filter, or None if no match.
        """
        spec = self.build_query_spec(filter)

        async with self.sqlite.session() as session:
            stmt = sqlm.select(DoctorTable)

            for clause in spec.where:
                stmt = stmt.where(clause)

            for order in spec.order_by:
                stmt = stmt.order_by(order)

            stmt = stmt.limit(1)

            result = await session.execute(stmt)
            doctor_obj = result.scalar_one_or_none()

            if doctor_obj is None:
                return None

            return doctor_obj.to_entity()

    async def list(
        self,
        arg: builtins.list[str] | t.Optional[Filter] = None,  # noqa
        *,
        page_index: int = 0,
        page_size: int = 100,
    ) -> builtins.list[Doctor]:
        """List doctors by IDs or with optional filtering and
        pagination.

        Args:
            arg: Either a list of IDs to retrieve, or an optional filter.
            page_index: Zero-based page index for pagination.
            page_size: Number of items per page.

        Returns:
            List of doctor entities matching the criteria.
        """
        async with self.sqlite.session() as session:
            if isinstance(arg, list):
                if not arg:
                    return []

                stmt = sqlm.select(DoctorTable).where(sqlm.col(DoctorTable.uid).in_(arg))
                result = await session.execute(stmt)
                doctor_objs = result.scalars().all()
                return [obj.to_entity() for obj in doctor_objs]

            spec = self.build_query_spec(arg)
            stmt = sqlm.select(DoctorTable)

            for clause in spec.where:
                stmt = stmt.where(clause)

            for order in spec.order_by:
                stmt = stmt.order_by(order)

            stmt = stmt.offset(page_index * page_size).limit(page_size)

            result = await session.execute(stmt)
            doctor_objs = result.scalars().all()
            return [obj.to_entity() for obj in doctor_objs]

    async def update(self, data: Doctor, /) -> str:
        """Update an existing doctor.

        Args:
            data: The doctor entity with updated values.

        Returns:
            The ID of the updated doctor.

        Raises:
            ValueError: If the doctor with the given ID does not exist.
        """
        async with self.sqlite.session() as session, session.begin():
            stmt = sqlm.select(DoctorTable).where(DoctorTable.uid == data.id)
            result = await session.execute(stmt)
            doctor_obj = result.scalar_one_or_none()

            if doctor_obj is None:
                raise ValueError(f"Doctor with uid {data.id} not found")

            doctor_obj.update(data)
            session.add(doctor_obj)
            await session.commit()
            await session.refresh(doctor_obj)
            return doctor_obj.uid

    async def update_many(self, datas: builtins.list[Doctor]) -> builtins.list[str]:
        """Update multiple doctors in the database.

        Args:
            datas: List of doctor entities with updated values.

        Returns:
            List of IDs of the updated doctors.

        Raises:
            ValueError: If any doctor with the given ID does not exist.
        """
        if not datas:
            return []

        updated_ids: builtins.list[str] = []
        async with self.sqlite.session() as session, session.begin():
            ids = [data.id for data in datas]
            stmt = sqlm.select(DoctorTable).where(sqlm.col(DoctorTable.uid).in_(ids))
            result = await session.execute(stmt)
            table_objs = {obj.uid: obj for obj in result.scalars().all()}

            missing_ids = set(ids) - set(table_objs.keys())
            if missing_ids:
                raise ValueError(f"Doctors with IDs {missing_ids} not found")

            for data in datas:
                doctor_obj = table_objs[data.id]
                doctor_obj.update(data)
                session.add(doctor_obj)
                updated_ids.append(doctor_obj.uid)

            await session.commit()
            return updated_ids

    async def delete(self, id: str, /) -> bool:
        """Delete a doctor by ID.

        Args:
            id: The ID (uid) of the doctor to delete.

        Returns:
            True if the doctor was deleted, False if not found.
        """
        async with self.sqlite.session() as session, session.begin():
            stmt = sqlm.select(DoctorTable).where(DoctorTable.uid == id)
            result = await session.execute(stmt)
            doctor_obj = result.scalar_one_or_none()

            if doctor_obj is None:
                return False

            await session.delete(doctor_obj)
            await session.commit()
            return True

    async def delete_many(
        self,
        arg: builtins.list[str] | t.Optional[Filter] = None,  # noqa
    ) -> builtins.list[str] | int:
        """Delete multiple doctors by IDs or matching a filter.

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

                stmt = sqlm.select(DoctorTable).where(sqlm.col(DoctorTable.uid).in_(arg))
                result = await session.execute(stmt)
                doctor_objs = result.scalars().all()

                if not doctor_objs:
                    return []

                doctor_uids = [obj.uid for obj in doctor_objs]
                for obj in doctor_objs:
                    await session.delete(obj)

                await session.commit()
                return doctor_uids

            spec = self.build_query_spec(arg)
            stmt = sqlm.select(DoctorTable.uid)
            for clause in spec.where:
                stmt = stmt.where(clause)

            result = await session.execute(stmt)
            doctor_uids = [row[0] for row in result.all()]

            if not doctor_uids:
                return 0

            count = len(doctor_uids)
            delete_stmt = sa.delete(DoctorTable).where(sqlm.col(DoctorTable.uid).in_(doctor_uids))
            await session.execute(delete_stmt)
            await session.commit()
            return count

    async def count(self, filter: t.Optional[Filter] = None) -> int:  # noqa
        """Count doctors matching the filter.

        Args:
            filter: Optional filter to apply. If None, counts all doctors.

        Returns:
            Number of doctors matching the filter.
        """
        spec = self.build_query_spec(filter)

        async with self.sqlite.session() as session:
            stmt = sqlm.select(sa.func.count()).select_from(DoctorTable)

            for clause in spec.where:
                stmt = stmt.where(clause)

            result = await session.execute(stmt)
            return result.scalar_one()
