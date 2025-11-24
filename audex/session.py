from __future__ import annotations

import abc
import asyncio
import contextlib
import datetime
import json
import os
import pathlib
import typing as t

from audex import utils
from audex.exceptions import AudexError
from audex.helper.mixin import LoggingMixin


class SessionData(t.TypedDict):
    """Session data structure.

    Attributes:
        session_id: Unique session identifier.
        doctor_id: Doctor's unique identifier.
        doctor_name: Doctor's display name.
        eid: Doctor's eid.
        created_at: Session creation timestamp (ISO format).
        last_active_at: Last activity timestamp (ISO format).
        expires_at: Session expiration timestamp (ISO format).
        metadata: Additional session metadata.
    """

    session_id: str
    doctor_id: str
    doctor_name: str
    eid: str
    created_at: str
    last_active_at: str
    expires_at: str
    metadata: dict[str, t.Any]


class Session:
    """Represents an active login session.

    Attributes:
        session_id: Unique session identifier.
        doctor_id: Doctor's unique identifier.
        doctor_name: Doctor's display name.
        eid: Doctor's eid.
        created_at: Session creation timestamp.
        last_active_at: Last activity timestamp.
        expires_at: Session expiration timestamp.
        metadata: Additional session metadata.

    Example:
        ```python
        session = Session(
            session_id="sess-abc123",
            doctor_id="doctor-xyz789",
            doctor_name="张医生",
            eid="dr_zhang",
            created_at=utils.utcnow(),
            expires_at=utils.utcnow() + timedelta(hours=24),
            metadata={"vpr_uid": "vpr_user_123"},
        )

        # Check if expired
        if session.is_expired:
            print("Session expired")

        # Check if active (not expired and recently used)
        if session.is_active:
            print("Session is active")

        # Update activity
        session.touch()
        ```
    """

    __slots__ = (
        "created_at",
        "doctor_id",
        "doctor_name",
        "eid",
        "expires_at",
        "last_active_at",
        "metadata",
        "session_id",
    )

    def __init__(
        self,
        session_id: str,
        doctor_id: str,
        doctor_name: str,
        eid: str,
        created_at: datetime.datetime,
        expires_at: datetime.datetime,
        *,
        last_active_at: datetime.datetime | None = None,
        metadata: dict[str, t.Any] | None = None,
    ) -> None:
        self.session_id = session_id
        self.doctor_id = doctor_id
        self.doctor_name = doctor_name
        self.eid = eid
        self.created_at = created_at
        self.last_active_at = last_active_at or created_at
        self.expires_at = expires_at
        self.metadata = metadata or {}

    @property
    def is_expired(self) -> bool:
        """Check if session has expired.

        Returns:
            True if session is expired, False otherwise.
        """
        return utils.utcnow() >= self.expires_at

    @property
    def is_active(self) -> bool:
        """Check if session is active (not expired and recently used).

        A session is considered active if:
        1. Not expired
        2. Last activity was within 30 minutes

        Returns:
            True if session is active, False otherwise.
        """
        if self.is_expired:
            return False

        # Check if last activity was within 30 minutes
        inactive_threshold = datetime.timedelta(minutes=30)
        return utils.utcnow() - self.last_active_at < inactive_threshold

    @property
    def remaining_time(self) -> datetime.timedelta:
        """Get remaining time until session expires.

        Returns:
            Timedelta representing remaining time. Negative if expired.
        """
        return self.expires_at - utils.utcnow()

    def touch(self) -> None:
        """Update last activity timestamp to current time."""
        self.last_active_at = utils.utcnow()

    def to_dict(self) -> SessionData:
        """Convert session to dictionary.

        Returns:
            SessionData dictionary.
        """
        return SessionData(
            session_id=self.session_id,
            doctor_id=self.doctor_id,
            doctor_name=self.doctor_name,
            eid=self.eid,
            created_at=self.created_at.isoformat(),
            last_active_at=self.last_active_at.isoformat(),
            expires_at=self.expires_at.isoformat(),
            metadata=self.metadata,
        )

    @classmethod
    def from_dict(cls, data: SessionData) -> t.Self:
        """Create session from dictionary.

        Args:
            data: SessionData dictionary.

        Returns:
            Session instance.
        """
        return cls(
            session_id=data["session_id"],
            doctor_id=data["doctor_id"],
            doctor_name=data["doctor_name"],
            eid=data["eid"],
            created_at=datetime.datetime.fromisoformat(data["created_at"]),
            last_active_at=datetime.datetime.fromisoformat(data["last_active_at"]),
            expires_at=datetime.datetime.fromisoformat(data["expires_at"]),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        return (
            f"SESSION <{self.session_id}("
            f"doctor={self.doctor_name}, "
            f"expires_in={self.remaining_time.total_seconds():.0f}s)>"
        )


class SessionManager(LoggingMixin, abc.ABC):
    """Abstract base class for session management.

    Provides interface for creating, retrieving, updating, and removing
    login sessions.
    """

    __logtag__ = "audex.lib.session"

    @abc.abstractmethod
    async def create(
        self,
        doctor_id: str,
        doctor_name: str,
        eid: str,
        *,
        ttl: datetime.timedelta | None = None,
        metadata: dict[str, t.Any] | None = None,
    ) -> Session:
        """Create a new session.

        Args:
            doctor_id: Doctor's unique identifier.
            doctor_name: Doctor's display name.
            eid: Doctor's eid.
            ttl: Time-to-live for the session. If None, uses default.
            metadata: Additional session metadata.

        Returns:
            Created Session instance.
        """

    @abc.abstractmethod
    async def get(self, session_id: str) -> Session | None:
        """Get session by ID.

        Args:
            session_id: Unique session identifier.

        Returns:
            Session instance if found and not expired, None otherwise.
        """

    @abc.abstractmethod
    async def get_by_doctor(self, doctor_id: str) -> Session | None:
        """Get active session for a doctor.

        Args:
            doctor_id: Doctor's unique identifier.

        Returns:
            Session instance if found and not expired, None otherwise.
        """

    @abc.abstractmethod
    async def update(self, session: Session) -> None:
        """Update an existing session.

        Args:
            session: Session instance to update.
        """

    @abc.abstractmethod
    async def delete(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Unique session identifier.

        Returns:
            True if session was deleted, False if not found.
        """

    @abc.abstractmethod
    async def delete_by_doctor(self, doctor_id: str) -> bool:
        """Delete all sessions for a doctor.

        Args:
            doctor_id: Doctor's unique identifier.

        Returns:
            True if any sessions were deleted, False otherwise.
        """

    @abc.abstractmethod
    async def cleanup_expired(self) -> int:
        """Remove all expired sessions.

        Returns:
            Number of sessions removed.
        """

    @abc.abstractmethod
    async def list_active(self) -> list[Session]:
        """List all active (non-expired) sessions.

        Returns:
            List of active Session instances.
        """


class LocalSessionManager(SessionManager):
    """Local file-based session manager.

    Stores sessions in a JSON file on the local filesystem. Suitable for
    single-user desktop applications.

    Attributes:
        storage_path: Path to the session storage file.
        default_ttl: Default time-to-live for sessions.
        auto_cleanup_interval: Interval for automatic cleanup of expired
            sessions.

    Example:
        ```python
        # Initialize manager
        manager = LocalSessionManager(
            storage_path=Path("/var/lib/audex/sessions.json"),
            default_ttl=timedelta(hours=24),
            auto_cleanup_interval=timedelta(minutes=10),
        )

        await manager.init()

        # Create session
        session = await manager.create(
            doctor_id="doctor-abc123",
            doctor_name="张医生",
            eid="dr_zhang",
            metadata={"vpr_uid": "vpr_user_123"},
        )

        # Get session
        retrieved = await manager.get(session.session_id)
        if retrieved and retrieved.is_active:
            print(f"Welcome back, {retrieved.doctor_name}")
            retrieved.touch()
            await manager.update(retrieved)

        # Get by doctor
        doctor_session = await manager.get_by_doctor(
            "doctor-abc123"
        )

        # Delete session (logout)
        await manager.delete(session.session_id)

        # Cleanup
        await manager.close()
        ```
    """

    def __init__(
        self,
        storage_path: str | pathlib.Path | os.PathLike[str],
        *,
        default_ttl: datetime.timedelta = datetime.timedelta(hours=24),
        auto_cleanup_interval: datetime.timedelta = datetime.timedelta(minutes=10),
    ) -> None:
        super().__init__()
        self.storage_path = pathlib.Path(storage_path)
        self.default_ttl = default_ttl
        self.auto_cleanup_interval = auto_cleanup_interval

        self._sessions: dict[str, Session] = {}
        self._doctor_index: dict[str, str] = {}  # doctor_id -> session_id
        self._cleanup_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    async def init(self) -> None:
        """Initialize the session manager.

        Loads existing sessions from storage and starts automatic
        cleanup.
        """
        # Ensure storage directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing sessions
        await self._load()

        # Start automatic cleanup
        self._cleanup_task = asyncio.create_task(self._auto_cleanup_loop())

        self.logger.info(
            f"Session manager initialized with {len(self._sessions)} sessions",
            storage_path=str(self.storage_path),
        )

    async def close(self) -> None:
        """Close the session manager.

        Saves sessions to storage and stops automatic cleanup.
        """
        # Stop cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None

        # Save sessions
        await self._save()

        self.logger.info("Session manager closed")

    async def create(
        self,
        doctor_id: str,
        doctor_name: str,
        eid: str,
        *,
        ttl: datetime.timedelta | None = None,
        metadata: dict[str, t.Any] | None = None,
    ) -> Session:
        """Create a new session.

        If a session already exists for this doctor, it will be replaced.

        Args:
            doctor_id: Doctor's unique identifier.
            doctor_name: Doctor's display name.
            eid: Doctor's eid.
            ttl: Time-to-live for the session. If None, uses default.
            metadata: Additional session metadata.

        Returns:
            Created Session instance.
        """
        async with self._lock:
            # Delete existing session for this doctor
            await self._delete_by_doctor_unsafe(doctor_id)

            # Create new session
            session_id = utils.gen_id(prefix="sess-")
            ttl = ttl or self.default_ttl
            now = utils.utcnow()

            session = Session(
                session_id=session_id,
                doctor_id=doctor_id,
                doctor_name=doctor_name,
                eid=eid,
                created_at=now,
                expires_at=now + ttl,
                metadata=metadata or {},
            )

            self._sessions[session_id] = session
            self._doctor_index[doctor_id] = session_id

            await self._save()

            self.logger.info(
                f"Created session for doctor {doctor_name}",
                session_id=session_id,
                doctor_id=doctor_id,
                expires_at=session.expires_at.isoformat(),
            )

            return session

    async def get(self, session_id: str) -> Session | None:
        """Get session by ID.

        Args:
            session_id: Unique session identifier.

        Returns:
            Session instance if found and not expired, None otherwise.
        """
        async with self._lock:
            session = self._sessions.get(session_id)

            if session is None:
                return None

            if session.is_expired:
                # Auto-remove expired session
                await self._delete_unsafe(session_id)
                return None

            return session

    async def get_by_doctor(self, doctor_id: str) -> Session | None:
        """Get active session for a doctor.

        Args:
            doctor_id: Doctor's unique identifier.

        Returns:
            Session instance if found and not expired, None otherwise.
        """
        async with self._lock:
            session_id = self._doctor_index.get(doctor_id)

            if session_id is None:
                return None

            session = self._sessions.get(session_id)

            if session is None:
                # Clean up stale index
                del self._doctor_index[doctor_id]
                return None

            if session.is_expired:
                # Auto-remove expired session
                await self._delete_unsafe(session_id)
                return None

            return session

    async def update(self, session: Session) -> None:
        """Update an existing session.

        Args:
            session: Session instance to update.

        Raises:
            SessionNotFoundError: If session doesn't exist.
        """
        async with self._lock:
            if session.session_id not in self._sessions:
                raise SessionNotFoundError(f"Session {session.session_id} not found")

            self._sessions[session.session_id] = session
            await self._save()

            self.logger.debug(
                f"Updated session {session.session_id}",
                last_active_at=session.last_active_at.isoformat(),
            )

    async def delete(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Unique session identifier.

        Returns:
            True if session was deleted, False if not found.
        """
        async with self._lock:
            return await self._delete_unsafe(session_id)

    async def delete_by_doctor(self, doctor_id: str) -> bool:
        """Delete all sessions for a doctor.

        Args:
            doctor_id: Doctor's unique identifier.

        Returns:
            True if any sessions were deleted, False otherwise.
        """
        async with self._lock:
            return await self._delete_by_doctor_unsafe(doctor_id)

    async def cleanup_expired(self) -> int:
        """Remove all expired sessions.

        Returns:
            Number of sessions removed.
        """
        async with self._lock:
            expired_ids = [
                session_id for session_id, session in self._sessions.items() if session.is_expired
            ]

            for session_id in expired_ids:
                await self._delete_unsafe(session_id)

            if expired_ids:
                await self._save()
                self.logger.info(f"Cleaned up {len(expired_ids)} expired sessions")

            return len(expired_ids)

    async def list_active(self) -> list[Session]:
        """List all active (non-expired) sessions.

        Returns:
            List of active Session instances.
        """
        async with self._lock:
            return [session for session in self._sessions.values() if not session.is_expired]

    async def _delete_unsafe(self, session_id: str) -> bool:
        """Delete a session without acquiring lock.

        Args:
            session_id: Unique session identifier.

        Returns:
            True if session was deleted, False if not found.
        """
        session = self._sessions.pop(session_id, None)

        if session is None:
            return False

        # Clean up doctor index
        if (
            session.doctor_id in self._doctor_index
            and self._doctor_index[session.doctor_id] == session_id
        ):
            del self._doctor_index[session.doctor_id]

        await self._save()

        self.logger.info(f"Deleted session {session_id}", doctor_id=session.doctor_id)

        return True

    async def _delete_by_doctor_unsafe(self, doctor_id: str) -> bool:
        """Delete all sessions for a doctor without acquiring lock.

        Args:
            doctor_id: Doctor's unique identifier.

        Returns:
            True if any sessions were deleted, False otherwise.
        """
        session_id = self._doctor_index.get(doctor_id)

        if session_id is None:
            return False

        return await self._delete_unsafe(session_id)

    async def _load(self) -> None:
        """Load sessions from storage file."""
        if not self.storage_path.exists():
            self.logger.debug("No existing session storage found")
            return

        try:
            data = json.loads(self.storage_path.read_text())

            sessions_data: list[SessionData] = data.get("sessions", [])

            for session_data in sessions_data:
                try:
                    session = Session.from_dict(session_data)

                    # Skip expired sessions
                    if session.is_expired:
                        continue

                    self._sessions[session.session_id] = session
                    self._doctor_index[session.doctor_id] = session.session_id

                except Exception as e:
                    self.logger.warning(
                        f"Failed to load session: {e}",
                        session_id=session_data.get("session_id"),
                    )

            self.logger.info(f"Loaded {len(self._sessions)} sessions from storage")

        except Exception as e:
            self.logger.error(f"Failed to load sessions: {e}", exc_info=True)

    async def _save(self) -> None:
        """Save sessions to storage file."""
        try:
            data = {
                "sessions": [
                    session.to_dict()
                    for session in self._sessions.values()
                    if not session.is_expired
                ],
                "saved_at": utils.utcnow().isoformat(),
            }

            # Write to temporary file first
            temp_path = self.storage_path.with_suffix(".tmp")
            temp_path.write_text(json.dumps(data, indent=2))

            # Atomic rename
            temp_path.replace(self.storage_path)

            self.logger.debug(f"Saved {len(data['sessions'])} sessions to storage")

        except Exception as e:
            self.logger.error(f"Failed to save sessions: {e}", exc_info=True)

    async def _auto_cleanup_loop(self) -> None:
        """Automatic cleanup loop for expired sessions."""
        while True:
            try:
                await asyncio.sleep(self.auto_cleanup_interval.total_seconds())
                cleaned = await self.cleanup_expired()
                if cleaned > 0:
                    self.logger.debug(f"Auto-cleanup removed {cleaned} sessions")
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in auto-cleanup: {e}", exc_info=True)


class SessionNotFoundError(AudexError):
    """Raised when session is not found."""

    default_message = "Session not found"


class SessionExpiredError(AudexError):
    """Raised when session has expired."""

    default_message = "Session has expired"
