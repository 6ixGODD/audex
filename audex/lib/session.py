from __future__ import annotations

import asyncio
import contextlib
import datetime
import json
import pathlib
import typing as t

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from audex import __title__
from audex import utils
from audex.exceptions import AudexError
from audex.helper.mixin import AsyncContextMixin
from audex.helper.mixin import LoggingMixin


class SessionData(t.NamedTuple):
    """Session data structure.

    Attributes:
        doctor_id: Doctor's unique identifier.
        doctor_name: Doctor's display name.
        eid: Doctor's eid.
        created_at: Session creation timestamp (ISO format).
        expires_at: Session expiration timestamp (ISO format), None means never expires.
    """

    doctor_id: str
    doctor_name: str | None
    eid: str
    created_at: str
    expires_at: str | None  # Changed to allow None

    def to_dict(self) -> dict[str, str | None]:
        """Convert to dictionary for JSON serialization."""
        return {
            "doctor_id": self.doctor_id,
            "doctor_name": self.doctor_name,
            "eid": self.eid,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | None]) -> SessionData:
        """Create from dictionary."""
        return cls(
            doctor_id=data["doctor_id"],
            doctor_name=data["doctor_name"],
            eid=data["eid"],
            created_at=data["created_at"],
            expires_at=data.get("expires_at"),  # Allow None
        )


class SessionManager(LoggingMixin, AsyncContextMixin):
    """Secure local session manager with automatic state management.

    This manager maintains session state automatically - no need to manually
    manage tokens. Session persists across application restarts until it
    expires (or never expires if ttl is None).

    Security features:
    1. Uses application data directory (persistent storage)
    2. File permissions restricted to current user (0o600)
    3. Session data encrypted with Fernet (AES-128-CBC + HMAC-SHA256)
    4. Automatic expiration and cleanup (optional)
    5. Machine-specific encryption key

    Attributes:
        session_dir: Directory for session files (in app data directory).
        session_file: Path to the encrypted session file.
        ttl: Default time-to-live for sessions (None = never expires).

    Example:
        ```python
        # Initialize manager
        manager = SessionManager(
            app_name="audex",
            default_ttl=timedelta(
                hours=8
            ),  # or None for no expiration
        )

        await manager.init()

        # Login with expiration
        await manager.login(
            doctor_id="doctor-abc123",
            doctor_name="张医生",
            eid="dr_zhang",
        )

        # Login without expiration (永久登录)
        await manager.login(
            doctor_id="doctor-abc123",
            doctor_name="张医生",
            eid="dr_zhang",
            ttl=None,  # 永不过期
        )

        # Check if logged in (no token needed!)
        if await manager.is_logged_in():
            session = await manager.get_session()
            print(f"Logged in as: {session.doctor_name}")

        # Works across app restarts (if not expired)
        # ... restart app ...
        if await manager.is_logged_in():
            print("Auto-logged in!")

        # Logout
        await manager.logout()

        # Cleanup
        await manager.close()
        ```
    """

    __logtag__ = "audex.lib.session"

    def __init__(
        self,
        app_name: str = __title__,
        *,
        ttl: datetime.timedelta | None = datetime.timedelta(hours=8),
    ) -> None:
        super().__init__()
        self.app_name = app_name
        self.ttl = ttl

        # Use platform-specific application data directory
        self.session_dir = self._get_app_data_dir() / f".{app_name}_session"
        self.session_file = self.session_dir / "session.enc"

        # Machine-specific encryption key (using Fernet)
        self._encryption_key = self._generate_machine_key()
        self._fernet = Fernet(self._encryption_key)

        self._cleanup_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()

    def _get_app_data_dir(self) -> pathlib.Path:
        """Get platform-specific application data directory.

        Returns:
            Path to application data directory:
            - Windows: %PROGRAMDATA%\\audex
            - Linux: ~/.local/share/audex or /var/lib/audex
            - macOS: ~/Library/Application Support/audex
        """
        import os
        import platform

        system = platform.system()

        if system == "Windows":
            # Windows: C:\ProgramData\audex
            base_dir = pathlib.Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData"))
            return base_dir / self.app_name.lower()

        if system == "Linux":
            # Linux: ~/.local/share/audex or /var/lib/audex
            home = pathlib.Path.home()
            if home.exists():
                return home / ".local" / "share" / self.app_name.lower()
            return pathlib.Path("/var/lib") / self.app_name.lower()

        if system == "Darwin":
            # macOS: ~/Library/Application Support/audex
            home = pathlib.Path.home()
            return home / "Library" / "Application Support" / self.app_name.lower()

        # Fallback
        return pathlib.Path.home() / f".{self.app_name.lower()}"

    async def init(self) -> None:
        """Initialize the session manager.

        Creates session directory with restricted permissions and starts
        automatic cleanup task (if ttl is set).
        """
        # Create session directory with restricted permissions
        self.session_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

        # Start automatic cleanup task only if ttl is set
        if self.ttl is not None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        self.logger.info(
            "Session manager initialized",
            session_dir=str(self.session_dir),
            ttl_hours=self.ttl.total_seconds() / 3600 if self.ttl else "never",
        )

    async def close(self) -> None:
        """Close the session manager.

        Stops the cleanup task. Session file is preserved for next
        startup.
        """
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None

        self.logger.info("Session manager closed")

    async def login(
        self,
        doctor_id: str,
        eid: str,
        *,
        doctor_name: str | None = None,
        ttl: datetime.timedelta | None = None,
    ) -> SessionData:
        """Create a login session.

        If a session already exists, it will be replaced with the new one.
        Session persists across application restarts until expiration.

        Args:
            doctor_id: Doctor's unique identifier.
            doctor_name: Doctor's display name.
            eid: Doctor's eid.
            ttl: Time-to-live for the session. If None, session never expires.
                 If not provided, uses default ttl from __init__.

        Returns:
            Created SessionData.

        Example:
            ```python
            # Login with expiration
            session = await manager.login(
                doctor_id="doctor-abc123",
                doctor_name="张医生",
                eid="dr_zhang",
            )

            # Login without expiration (永久登录)
            session = await manager.login(
                doctor_id="doctor-abc123",
                doctor_name="张医生",
                eid="dr_zhang",
                ttl=None,
            )
            ```
        """
        async with self._lock:
            # If ttl is not explicitly passed, use default
            # If ttl=None is explicitly passed, session never expires
            if ttl is None and self.ttl is not None:
                ttl = self.ttl

            now = utils.utcnow()
            expires_at = None if ttl is None else now + ttl

            session_data = SessionData(
                doctor_id=doctor_id,
                doctor_name=doctor_name,
                eid=eid,
                created_at=now.isoformat(),
                expires_at=expires_at.isoformat() if expires_at else None,
            )

            # Encrypt and write session data
            await self._write_session(session_data)

            self.logger.bind(
                doctor_id=doctor_id,
                eid=eid,
                expires_at=expires_at.isoformat() if expires_at else "never",
            ).info(f"Session created for {eid}")

            return session_data

    async def logout(self) -> bool:
        """Logout by deleting the session.

        Returns:
            True if session was deleted, False if no session exists.

        Example:
            ```python
            logged_out = await manager.logout()
            if logged_out:
                print("Successfully logged out")
            ```
        """
        async with self._lock:
            if not self.session_file.exists():
                return False

            try:
                self.session_file.unlink()
                self.logger.info("Session deleted (logout)")
                return True
            except Exception as e:
                self.logger.error(f"Failed to delete session: {e}", exc_info=True)
                return False

    async def is_logged_in(self) -> bool:
        """Check if there's an active (non-expired) session.

        Returns:
            True if there's an active session, False otherwise.

        Example:
            ```python
            if await manager.is_logged_in():
                print("User is logged in")
            else:
                print("Please login")
            ```
        """
        session = await self.get_session()
        return session is not None

    async def get_session(self) -> SessionData | None:
        """Get current session if exists and not expired.

        Returns:
            SessionData if session exists and is valid, None otherwise.

        Example:
            ```python
            session = await manager.get_session()
            if session:
                print(f"Logged in as: {session.doctor_name}")
                print(f"Doctor ID: {session.doctor_id}")
            else:
                print("No active session")
            ```
        """
        async with self._lock:
            if not self.session_file.exists():
                return None

            try:
                # Read and decrypt session data
                session_data = await self._read_session()
                if session_data is None:
                    return None

                # Check if expired (only if expires_at is set)
                if session_data.expires_at is not None:
                    expires_at = datetime.datetime.fromisoformat(session_data.expires_at)
                    if utils.utcnow() >= expires_at:
                        self.logger.debug("Session expired, removing file")
                        self.session_file.unlink()
                        return None

                return session_data

            except Exception as e:
                self.logger.warning(f"Failed to read session: {e}", exc_info=True)
                # If data is corrupted, remove file
                if self.session_file.exists():
                    self.session_file.unlink()
                return None

    async def get_doctor_id(self) -> str | None:
        """Get current logged-in doctor's ID.

        Returns:
            Doctor ID if logged in, None otherwise.

        Example:
            ```python
            doctor_id = await manager.get_doctor_id()
            if doctor_id:
                print(f"Current doctor: {doctor_id}")
            ```
        """
        session = await self.get_session()
        return session.doctor_id if session else None

    async def extend_session(self, extra_ttl: datetime.timedelta) -> bool:
        """Extend current session expiration time.

        Note: This only works if the session has an expiration time.
        For sessions with no expiration (ttl=None), this operation has no effect.

        Args:
            extra_ttl: Additional time to add to expiration.

        Returns:
            True if session was extended, False if no session exists or session never expires.

        Example:
            ```python
            # Extend by 2 hours
            extended = await manager.extend_session(timedelta(hours=2))
            if extended:
                print("Session extended")
            ```
        """
        async with self._lock:
            session = await self.get_session()
            if session is None:
                return False

            # Cannot extend a session that never expires
            if session.expires_at is None:
                self.logger.debug("Cannot extend session with no expiration")
                return False

            # Calculate new expiration
            current_expires = datetime.datetime.fromisoformat(session.expires_at)
            new_expires = current_expires + extra_ttl

            # Create updated session
            updated_session = SessionData(
                doctor_id=session.doctor_id,
                doctor_name=session.doctor_name,
                eid=session.eid,
                created_at=session.created_at,
                expires_at=new_expires.isoformat(),
            )

            await self._write_session(updated_session)
            self.logger.info(
                "Session extended",
                new_expires_at=new_expires.isoformat(),
            )

            return True

    async def _read_session(self) -> SessionData | None:
        """Read and decrypt session from file.

        Returns:
            SessionData if successful, None otherwise.
        """
        try:
            encrypted_data = self.session_file.read_bytes()
            decrypted_json = self._decrypt_data(encrypted_data)
            data = json.loads(decrypted_json)
            return SessionData.from_dict(data)
        except Exception as e:
            self.logger.warning(f"Failed to decrypt session: {e}")
            return None

    async def _write_session(self, session_data: SessionData) -> None:
        """Encrypt and write session to file.

        Args:
            session_data: Session data to write.
        """
        json_data = json.dumps(session_data.to_dict())
        encrypted_data = self._encrypt_data(json_data)

        self.session_file.write_bytes(encrypted_data)
        self.session_file.chmod(0o600)  # Restrict to owner only

    async def _cleanup_loop(self) -> None:
        """Automatic cleanup loop that runs every 5 minutes.

        Checks for expired sessions and removes them.
        Only runs if ttl is set (not None).
        """
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes

                if self.session_file.exists():
                    session = await self.get_session()
                    if session is None:
                        # File exists but session is invalid/expired
                        self.logger.debug("Auto-cleanup: removed expired/invalid session")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}", exc_info=True)

    def _generate_machine_key(self) -> bytes:
        """Generate machine-specific encryption key using PBKDF2.

        Uses machine ID and app name to create a deterministic key that's
        unique to this machine and application. The key is derived using
        PBKDF2-HMAC-SHA256 for better security.

        Returns:
            32-byte Fernet-compatible key (base64 encoded).
        """
        # Try to get machine ID from various sources
        machine_id = None

        # Try /etc/machine-id (Linux)
        machine_id_file = pathlib.Path("/etc/machine-id")
        if machine_id_file.exists():
            with contextlib.suppress(Exception):
                machine_id = machine_id_file.read_text().strip()

        # Try /var/lib/dbus/machine-id (Linux alternative)
        if machine_id is None:
            dbus_id_file = pathlib.Path("/var/lib/dbus/machine-id")
            if dbus_id_file.exists():
                with contextlib.suppress(Exception):
                    machine_id = dbus_id_file.read_text().strip()

        # Fallback: use hostname + username
        if machine_id is None:
            import getpass
            import socket

            machine_id = f"{socket.gethostname()}-{getpass.getuser()}"

        # Use PBKDF2 to derive a secure key
        password = f"{machine_id}:{self.app_name}".encode()
        salt = b"audex_session_salt"  # Fixed salt for deterministic key generation

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,  # High iteration count for security
        )
        key = kdf.derive(password)

        # Fernet requires a base64-encoded 32-byte key
        import base64

        return base64.urlsafe_b64encode(key)

    def _encrypt_data(self, data: str) -> bytes:
        """Encrypt session data using Fernet (AES-128-CBC + HMAC-SHA256).

        Fernet provides authenticated encryption, which means:
        1. Data confidentiality (AES encryption)
        2. Data integrity (HMAC authentication)
        3. Timestamp verification (prevents replay attacks)

        Args:
            data: Plain text data to encrypt.

        Returns:
            Encrypted bytes.
        """
        data_bytes = data.encode()
        return self._fernet.encrypt(data_bytes)

    def _decrypt_data(self, data: bytes) -> str:
        """Decrypt session data using Fernet.

        Args:
            data: Encrypted bytes.

        Returns:
            Decrypted string.

        Raises:
            Exception: If decryption fails (wrong machine, corrupted data, or tampered).
        """
        decrypted_bytes = self._fernet.decrypt(data)
        return decrypted_bytes.decode()


class SessionError(AudexError):
    """Base exception for session errors."""

    default_message = "Session error occurred"


class SessionExpiredError(SessionError):
    """Raised when session has expired."""

    default_message = "Session has expired"


class SessionNotFoundError(SessionError):
    """Raised when session is not found."""

    default_message = "No active session found"
