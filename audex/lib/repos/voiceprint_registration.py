from __future__ import annotations

import builtins
import typing as t

import sqlalchemy as sa
import sqlmodel as sqlm

from audex.entity.voiceprint_registration import VoiceprintRegistration
from audex.filters import Filter
from audex.lib.database.sqlite import SQLite
from audex.lib.repos.database.sqlite import SQLiteRepository
from audex.lib.repos.tables.voiceprint_registration import VoiceprintRegistrationTable


class VoiceprintRegistrationRepository(SQLiteRepository[VoiceprintRegistration]):
    """SQLite implementation of VoiceprintRegistration repository.

    Provides CRUD operations for VoiceprintRegistration entities with
    specialized query methods for VPR system integration.
    """

    __table__ = VoiceprintRegistrationTable
    __tablename__ = VoiceprintRegistrationTable.__tablename__

    def __init__(self, sqlite: SQLite) -> None:
        super().__init__(sqlite)

    async def create(self, data: VoiceprintRegistration, /) -> str:
        """Create a new voiceprint registration in the database.

        Args:
            data: The voiceprint registration entity to create.

        Returns:
            The ID of the created registration.
        """
        async with self.sqlite.session() as session, session.begin():
            vpr_table = VoiceprintRegistrationTable.from_entity(data)
            session.add(vpr_table)
            await session.commit()
            await session.refresh(vpr_table)
            return vpr_table.uid

    async def read(self, id: str, /) -> VoiceprintRegistration | None:
        """Read a voiceprint registration by ID.

        Args:
            id: The ID (uid) of the registration to retrieve.

        Returns:
            The voiceprint registration entity if found, None otherwise.
        """
        async with self.sqlite.session() as session:
            stmt = sqlm.select(VoiceprintRegistrationTable).where(
                VoiceprintRegistrationTable.uid == id
            )
            result = await session.execute(stmt)
            vpr_obj = result.scalar_one_or_none()

            if vpr_obj is None:
                return None

            return vpr_obj.to_entity()

    async def read_by_doctor_id(self, doctor_id: str, /) -> VoiceprintRegistration | None:
        """Read a voiceprint registration by doctor ID.

        Args:
            doctor_id: The doctor ID to retrieve registration for.

        Returns:
            The voiceprint registration entity if found, None otherwise.
        """
        async with self.sqlite.session() as session:
            stmt = sqlm.select(VoiceprintRegistrationTable).where(
                VoiceprintRegistrationTable.doctor_id == doctor_id
            )
            result = await session.execute(stmt)
            vpr_obj = result.scalar_one_or_none()

            if vpr_obj is None:
                return None

            return vpr_obj.to_entity()

    async def first(self, filter: Filter) -> VoiceprintRegistration | None:
        """Retrieve the first voiceprint registration matching the filter.

        Args:
            filter: Filter to apply when searching.

        Returns:
            The first registration entity matching the filter, or None.
        """
        spec = self.build_query_spec(filter)

        async with self.sqlite.session() as session:
            stmt = sqlm.select(VoiceprintRegistrationTable)

            for clause in spec.where:
                stmt = stmt.where(clause)

            for order in spec.order_by:
                stmt = stmt.order_by(order)

            stmt = stmt.limit(1)

            result = await session.execute(stmt)
            vpr_obj = result.scalar_one_or_none()

            if vpr_obj is None:
                return None

            return vpr_obj.to_entity()

    async def list(
        self,
        arg: builtins.list[str] | t.Optional[Filter] = None,  # noqa
        *,
        page_index: int = 0,
        page_size: int = 100,
    ) -> builtins.list[VoiceprintRegistration]:
        """List voiceprint registrations by IDs or with optional filtering.

        Args:
            arg: Either a list of IDs to retrieve, or an optional filter.
            page_index: Zero-based page index for pagination.
            page_size: Number of items per page.

        Returns:
            List of voiceprint registration entities matching the criteria.
        """
        async with self.sqlite.session() as session:
            if isinstance(arg, list):
                if not arg:
                    return []

                stmt = sqlm.select(VoiceprintRegistrationTable).where(
                    sqlm.col(VoiceprintRegistrationTable.uid).in_(arg)
                )
                result = await session.execute(stmt)
                vpr_objs = result.scalars().all()
                return [obj.to_entity() for obj in vpr_objs]

            spec = self.build_query_spec(arg)
            stmt = sqlm.select(VoiceprintRegistrationTable)

            for clause in spec.where:
                stmt = stmt.where(clause)

            for order in spec.order_by:
                stmt = stmt.order_by(order)

            stmt = stmt.offset(page_index * page_size).limit(page_size)

            result = await session.execute(stmt)
            vpr_objs = result.scalars().all()
            return [obj.to_entity() for obj in vpr_objs]

    async def update(self, data: VoiceprintRegistration, /) -> str:
        """Update an existing voiceprint registration.

        Args:
            data: The registration entity with updated values.

        Returns:
            The ID of the updated registration.

        Raises:
            ValueError: If the registration with the given ID does not exist.
        """
        async with self.sqlite.session() as session, session.begin():
            stmt = sqlm.select(VoiceprintRegistrationTable).where(
                VoiceprintRegistrationTable.uid == data.id
            )
            result = await session.execute(stmt)
            vpr_obj = result.scalar_one_or_none()

            if vpr_obj is None:
                raise ValueError(f"VoiceprintRegistration with uid {data.id} not found")

            vpr_obj.doctor_id = data.doctor_id
            vpr_obj.vp_id = data.vp_id
            vpr_obj.vpr_group_id = data.vpr_group_id
            vpr_obj.vpr_system = data.vpr_system
            vpr_obj.registration_address = data.registration_address
            vpr_obj.updated_at = data.updated_at

            session.add(vpr_obj)
            await session.commit()
            await session.refresh(vpr_obj)
            return vpr_obj.uid

    async def update_many(
        self, datas: builtins.list[VoiceprintRegistration]
    ) -> builtins.list[str]:
        """Update multiple voiceprint registrations in the database.

        Args:
            datas: List of registration entities with updated values.

        Returns:
            List of IDs of the updated registrations.

        Raises:
            ValueError: If any registration with the given ID does not exist.
        """
        if not datas:
            return []

        updated_ids: builtins.list[str] = []
        async with self.sqlite.session() as session, session.begin():
            ids = [data.id for data in datas]
            stmt = sqlm.select(VoiceprintRegistrationTable).where(
                sqlm.col(VoiceprintRegistrationTable.uid).in_(ids)
            )
            result = await session.execute(stmt)
            table_objs = {obj.uid: obj for obj in result.scalars().all()}

            missing_ids = set(ids) - set(table_objs.keys())
            if missing_ids:
                raise ValueError(f"VoiceprintRegistrations with IDs {missing_ids} not found")

            for data in datas:
                vpr_obj = table_objs[data.id]
                vpr_obj.doctor_id = data.doctor_id
                vpr_obj.vp_id = data.vp_id
                vpr_obj.vpr_group_id = data.vpr_group_id
                vpr_obj.vpr_system = data.vpr_system
                vpr_obj.registration_address = data.registration_address
                vpr_obj.updated_at = data.updated_at
                session.add(vpr_obj)
                updated_ids.append(vpr_obj.uid)

            await session.commit()
            return updated_ids

    async def delete(self, id: str, /) -> bool:
        """Delete a voiceprint registration by ID.

        Args:
            id: The ID (uid) of the registration to delete.

        Returns:
            True if the registration was deleted, False if not found.
        """
        async with self.sqlite.session() as session, session.begin():
            stmt = sqlm.select(VoiceprintRegistrationTable).where(
                VoiceprintRegistrationTable.uid == id
            )
            result = await session.execute(stmt)
            vpr_obj = result.scalar_one_or_none()

            if vpr_obj is None:
                return False

            await session.delete(vpr_obj)
            await session.commit()
            return True

    async def delete_many(
        self,
        arg: builtins.list[str] | t.Optional[Filter] = None,  # noqa
    ) -> builtins.list[str] | int:
        """Delete multiple voiceprint registrations by IDs or matching a filter.

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

                stmt = sqlm.select(VoiceprintRegistrationTable).where(
                    sqlm.col(VoiceprintRegistrationTable.uid).in_(arg)
                )
                result = await session.execute(stmt)
                vpr_objs = result.scalars().all()

                if not vpr_objs:
                    return []

                vpr_uids = [obj.uid for obj in vpr_objs]
                for obj in vpr_objs:
                    await session.delete(obj)

                await session.commit()
                return vpr_uids

            spec = self.build_query_spec(arg)
            stmt = sqlm.select(VoiceprintRegistrationTable.uid)
            for clause in spec.where:
                stmt = stmt.where(clause)

            result = await session.execute(stmt)
            vpr_uids = [row[0] for row in result.all()]

            if not vpr_uids:
                return 0

            count = len(vpr_uids)
            delete_stmt = sa.delete(VoiceprintRegistrationTable).where(
                sqlm.col(VoiceprintRegistrationTable.uid).in_(vpr_uids)
            )
            await session.execute(delete_stmt)
            await session.commit()
            return count

    async def count(self, filter: t.Optional[Filter] = None) -> int:  # noqa
        """Count voiceprint registrations matching the filter.

        Args:
            filter: Optional filter to apply. If None, counts all registrations.

        Returns:
            Number of registrations matching the filter.
        """
        spec = self.build_query_spec(filter)

        async with self.sqlite.session() as session:
            stmt = sqlm.select(sa.func.count()).select_from(VoiceprintRegistrationTable)

            for clause in spec.where:
                stmt = stmt.where(clause)

            result = await session.execute(stmt)
            return result.scalar_one()
