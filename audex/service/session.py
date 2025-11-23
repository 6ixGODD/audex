from __future__ import annotations

from audex.entity.session import Session
from audex.lib.database.sqlite import SQLite
from audex.lib.repos.session import SessionRepository
from audex.service import BaseService
from audex.valueobj.session import SessionStatus


class SessionService(BaseService):
    """Session service for managing doctor-patient conversation sessions.

    This service handles session lifecycle operations including creation,
    starting/stopping recordings, and session state management.

    Attributes:
        session_repo: Repository for session data persistence.
    """

    __logtag__ = "SessionService"

    def __init__(self, sqlite: SQLite) -> None:
        """Initialize the session service.

        Args:
            sqlite: SQLite database connection.
        """
        super().__init__()
        self.session_repo = SessionRepository(sqlite)

    async def create_session(
        self,
        doctor_id: str,
        patient_name: str | None = None,
        outpatient_number: str | None = None,
        medical_record_number: str | None = None,
        notes: str | None = None,
    ) -> Session:
        """Create a new conversation session.

        Args:
            doctor_id: The ID of the doctor creating the session.
            patient_name: Optional patient name.
            outpatient_number: Optional outpatient number (门诊号).
            medical_record_number: Optional medical record number (病历号).
            notes: Optional session notes.

        Returns:
            The newly created session entity.
        """
        self.logger.info(f"Creating session for doctor: {doctor_id}")

        session = Session(
            doctor_id=doctor_id,
            patient_name=patient_name,
            outpatient_number=outpatient_number,
            medical_record_number=medical_record_number,
            notes=notes,
            status=SessionStatus.DRAFT,
        )

        session_id = await self.session_repo.create(session)
        self.logger.info(f"Session created successfully with ID: {session_id}")

        # Retrieve the created session to get the actual ID from database
        created_session = await self.session_repo.read(session_id)
        if created_session is None:
            raise ValueError(f"Failed to retrieve created session with ID: {session_id}")
        
        return created_session

    async def start_session(self, session_id: str) -> Session:
        """Start a session and begin recording.

        Args:
            session_id: The ID of the session to start.

        Returns:
            The updated session entity.

        Raises:
            ValueError: If session not found or already finished.
        """
        self.logger.info(f"Starting session: {session_id}")

        session = await self.session_repo.read(session_id)
        if session is None:
            self.logger.error(f"Session not found: {session_id}")
            raise ValueError(f"Session with ID '{session_id}' not found")

        if session.is_finished:
            self.logger.error(f"Cannot start finished session: {session_id}")
            raise ValueError("Cannot start a completed or cancelled session")

        session.start()
        await self.session_repo.update(session)

        self.logger.info(f"Session started: {session_id}")
        return session

    async def complete_session(self, session_id: str) -> Session:
        """Complete a session.

        Args:
            session_id: The ID of the session to complete.

        Returns:
            The updated session entity.

        Raises:
            ValueError: If session not found.
        """
        self.logger.info(f"Completing session: {session_id}")

        session = await self.session_repo.read(session_id)
        if session is None:
            self.logger.error(f"Session not found: {session_id}")
            raise ValueError(f"Session with ID '{session_id}' not found")

        session.complete()
        await self.session_repo.update(session)

        self.logger.info(f"Session completed: {session_id}")
        return session

    async def cancel_session(self, session_id: str) -> Session:
        """Cancel a session.

        Args:
            session_id: The ID of the session to cancel.

        Returns:
            The updated session entity.

        Raises:
            ValueError: If session not found.
        """
        self.logger.info(f"Cancelling session: {session_id}")

        session = await self.session_repo.read(session_id)
        if session is None:
            self.logger.error(f"Session not found: {session_id}")
            raise ValueError(f"Session with ID '{session_id}' not found")

        session.cancel()
        await self.session_repo.update(session)

        self.logger.info(f"Session cancelled: {session_id}")
        return session

    async def get_session(self, session_id: str) -> Session | None:
        """Retrieve a session by ID.

        Args:
            session_id: The ID of the session to retrieve.

        Returns:
            The session entity if found, None otherwise.
        """
        return await self.session_repo.read(session_id)

    async def update_session_info(
        self,
        session_id: str,
        patient_name: str | None = None,
        outpatient_number: str | None = None,
        medical_record_number: str | None = None,
        notes: str | None = None,
    ) -> Session:
        """Update session clinical information.

        Args:
            session_id: The ID of the session to update.
            patient_name: Optional updated patient name.
            outpatient_number: Optional updated outpatient number.
            medical_record_number: Optional updated medical record number.
            notes: Optional updated notes.

        Returns:
            The updated session entity.

        Raises:
            ValueError: If session not found.
        """
        self.logger.info(f"Updating session info: {session_id}")

        session = await self.session_repo.read(session_id)
        if session is None:
            self.logger.error(f"Session not found: {session_id}")
            raise ValueError(f"Session with ID '{session_id}' not found")

        if patient_name is not None:
            session.patient_name = patient_name
        if outpatient_number is not None:
            session.outpatient_number = outpatient_number
        if medical_record_number is not None:
            session.medical_record_number = medical_record_number
        if notes is not None:
            session.notes = notes

        session.touch()
        await self.session_repo.update(session)

        self.logger.info(f"Session info updated: {session_id}")
        return session
