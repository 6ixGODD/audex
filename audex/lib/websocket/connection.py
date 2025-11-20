from __future__ import annotations

import asyncio as aio
import contextlib
import time
import typing as t
import uuid

from websockets import ClientConnection
from websockets import ConnectionClosed
from websockets import connect
from websockets import protocol

from audex.helper.mixin import LoggingMixin
from audex.lib.websocket import WebsocketError


class ConnectionBusyError(WebsocketError):
    """Raised when attempting to use a connection that is already
    busy."""

    code = 1100


class ConnectionUnavailableError(WebsocketError):
    """Raised when a connection is unavailable or cannot be
    established."""

    code = 1101


class ConnectionClosedError(WebsocketError):
    """Raised when attempting to use a closed connection."""

    code = 1102


class ConnectionDrainTimeoutError(WebsocketError):
    """Raised when connection draining exceeds the timeout."""

    code = 1103


# Type alias for drain condition callback
DrainConditionCallback: t.TypeAlias = t.Callable[[str | bytes], bool]


class WebsocketConnection(LoggingMixin, t.Hashable, t.AsyncContextManager):
    """Manages a single WebSocket connection with lifecycle management.

    This class provides automatic idle timeout monitoring, connection health
    checks, and proper resource cleanup for WebSocket connections.

    Attributes:
        uri: The WebSocket URI to connect to.
        headers: Optional HTTP headers for the connection.
        idle_timeout: Maximum idle time before auto-close in seconds.
        check_server_data_on_release: Whether to check for server data on release.
        drain_timeout: Timeout for draining server data in seconds.
        drain_condition: Callback to determine if data should be drained.
    """

    __logtag__ = "websocket.connection"

    def __init__(
        self,
        *,
        uri: str,
        headers: dict[str, str] | None = None,
        idle_timeout: float = 30.0,
        check_server_data_on_release: bool = False,
        drain_timeout: float = 5.0,
        drain_condition: DrainConditionCallback | None = None,
        **kwargs: t.Any,
    ):
        """Initialize a WebSocket connection.

        Args:
            uri: The WebSocket URI to connect to.
            headers: Optional HTTP headers to include in connection requests.
            idle_timeout: Maximum time in seconds before idle connection closes.
                Defaults to 30.0.
            check_server_data_on_release: Whether to check for server data
                during release. Defaults to False.
            drain_timeout: Maximum time in seconds to drain server data.
                Defaults to 5.0.
            drain_condition: Function to determine what constitutes server data
                that should be drained. Defaults to None (uses default condition).
            **kwargs: Additional parameters to pass to websockets.connect().
        """
        super().__init__()
        self.uri = uri
        self.headers = headers
        self.idle_timeout = idle_timeout
        self.check_server_data_on_release = check_server_data_on_release
        self.drain_timeout = drain_timeout
        self.drain_condition = drain_condition or self._default_drain_condition
        self._params = kwargs

        self.websocket: ClientConnection | None = None
        self._is_busy = False
        self._is_draining = False
        self._last_activity = time.time()
        self._monitor_task: aio.Task | None = None
        self._closed = False
        self._lock = aio.Lock()
        self._connection_id = uuid.uuid4().hex  # For hashing

    @staticmethod
    def _default_drain_condition(message: str | bytes) -> bool:
        """Default condition to determine if incoming data should be
        drained.

        Args:
            message: The incoming message from the server.

        Returns:
            True if the message should be drained (considered as server data).
        """
        # By default, consider any non-empty message as server data
        return len(message) > 0

    @property
    def is_busy(self) -> bool:
        """Check if the connection is currently busy.

        Returns:
            True if the connection is busy, False otherwise.
        """
        return self._is_busy

    @property
    def is_draining(self) -> bool:
        """Check if the connection is currently draining.

        Returns:
            True if the connection is draining, False otherwise.
        """
        return self._is_draining

    @property
    def is_connected(self) -> bool:
        """Check if the connection is currently active.

        Returns:
            True if the connection is open and not closed, False otherwise.
        """
        return (
            self.websocket is not None
            and not self._closed
            and self.websocket.state == protocol.OPEN
        )

    @property
    def last_activity(self) -> float:
        """Get the timestamp of the last activity.

        Returns:
            Unix timestamp of the last activity.
        """
        return self._last_activity

    def _update_activity(self) -> None:
        """Update the last activity timestamp to current time."""
        self._last_activity = time.time()

    async def _monitor_idle(self) -> None:
        """Background task to monitor and close idle connections.

        This task runs continuously and checks if the connection has
        been idle for longer than idle_timeout. If so, it automatically
        closes the connection.
        """
        try:
            while not self._closed:
                should_close = False
                async with self._lock:
                    if (
                        self.is_connected
                        and not self.is_busy
                        and not self.is_draining
                        and (time.time() - self._last_activity) > self.idle_timeout
                    ):
                        should_close = True

                if should_close:
                    self.logger.debug(f"Closing idle connection to {self.uri}")
                    await self.close()
                    break
                await aio.sleep(1)
        except aio.CancelledError:
            pass

    async def connect(self) -> None:
        """Establish the WebSocket connection.

        If already connected, this method does nothing. Otherwise, it attempts
        to establish a new connection and starts the idle monitor task.

        Raises:
            ConnectionUnavailableError: If the connection has been closed or
                if connection establishment fails.
        """
        async with self._lock:
            if self.is_connected:
                return

            if self._closed:
                raise ConnectionUnavailableError("Connection has been closed")

            # Clean up old monitor task if done
            if self._monitor_task is not None and self._monitor_task.done():
                try:
                    await self._monitor_task
                finally:
                    self._monitor_task = None

        # Establish connection outside the lock to avoid blocking
        try:
            websocket = await connect(self.uri, additional_headers=self.headers, **self._params)

            async with self._lock:
                self.websocket = websocket
                self._update_activity()

                # Start monitor task if not already running
                if self._monitor_task is None or self._monitor_task.done():
                    self._monitor_task = aio.create_task(self._monitor_idle())

            self.logger.debug(f"Connected to {self.uri}")
        except Exception as e:
            self.logger.error(f"Failed to connect to {self.uri}: {e}")
            raise ConnectionUnavailableError(f"Failed to connect: {e}") from e

    async def close(self) -> None:
        """Close the WebSocket connection and clean up resources.

        This method cancels the idle monitor task, closes the WebSocket
        connection, and resets all internal state flags.
        """
        async with self._lock:
            if self._closed:
                return

            self._closed = True

            # Cancel monitor task
            if self._monitor_task is not None:
                if not self._monitor_task.done():
                    self._monitor_task.cancel()

                try:
                    await self._monitor_task
                except aio.CancelledError:
                    self.logger.debug(f"Monitor task for {self.uri} cancelled")
                finally:
                    self._monitor_task = None

            # Close websocket
            if self.websocket is not None:
                try:
                    await self.websocket.close()
                finally:
                    self.websocket = None

            self._is_busy = False
            self._is_draining = False
            self.logger.debug(f"Closed connection to {self.uri}")

    async def acquire(self) -> None:
        """Acquire the connection for exclusive use.

        This method marks the connection as busy and ensures it is connected.

        Raises:
            ConnectionUnavailableError: If the connection has been closed or
                if connection establishment fails.
            ConnectionBusyError: If the connection is already busy or draining.
        """
        async with self._lock:
            if self._closed:
                raise ConnectionUnavailableError("Connection has been closed")
            if self._is_busy:
                raise ConnectionBusyError("Connection is already busy")
            if self._is_draining:
                raise ConnectionBusyError("Connection is currently draining")

        try:
            await self.connect()
            async with self._lock:
                self._is_busy = True
                self._update_activity()
        except Exception as e:
            self.logger.error(f"Failed to acquire connection to {self.uri}: {e}")
            raise ConnectionUnavailableError(f"Failed to acquire connection: {e}") from e

    async def release(self) -> None:
        """Release the connection back to the pool.

        This method marks the connection as no longer busy and updates
        the activity timestamp.
        """
        async with self._lock:
            if not self._is_busy:
                return

            self._is_busy = False
            self._update_activity()

    async def ping(self) -> None:
        """Send a ping to the WebSocket server to check connection
        health.

        This method performs a health check by sending a ping frame to the
        server. The connection must be open for this to succeed.

        Raises:
            ConnectionUnavailableError: If the websocket is not connected.
            ConnectionClosedError: If the connection closes during the ping.
        """
        # Check connection state outside lock (quick check)
        if not (
            self.websocket is not None
            and not self._closed
            and self.websocket.state == protocol.OPEN
        ):
            raise ConnectionUnavailableError("Websocket is not connected")

        # Get websocket reference under lock
        async with self._lock:
            if not self.is_connected:
                raise ConnectionUnavailableError("Websocket is not connected")
            websocket = self.websocket

        # Perform ping outside lock to avoid blocking other operations
        connection_closed = False
        connection_closed_error = None
        try:
            await websocket.ping()
            async with self._lock:
                self._update_activity()
        except ConnectionClosed as e:
            self.logger.error(f"Connection closed during ping: {e}")
            connection_closed = True
            connection_closed_error = e

        if connection_closed:
            await self.close()
            raise ConnectionClosedError(
                f"Connection closed during ping: {connection_closed_error}"
            ) from connection_closed_error

    @contextlib.asynccontextmanager
    async def session(self) -> t.AsyncGenerator[WebsocketConnection, None]:
        """Create a context manager session for the connection.

        The connection is automatically acquired on entry and released on exit.

        Yields:
            The WebsocketConnection instance.

        Example:
            async with connection.session():
                await connection.send("Hello")
                response = await connection.recv()
        """
        await self.acquire()
        try:
            yield self
        finally:
            await self.release()

    async def send(self, message: str | bytes) -> None:
        """Send a message through the WebSocket connection.

        Args:
            message: The message to send (string or bytes).

        Raises:
            ConnectionBusyError: If the connection has not been acquired.
            ConnectionUnavailableError: If the websocket is not connected.
            ConnectionClosedError: If the connection closes during sending.
        """
        if not self.is_busy:
            raise ConnectionBusyError("Connection must be acquired before sending messages")

        # Check connection state outside lock
        if not (
            self.websocket is not None
            and not self._closed
            and self.websocket.state == protocol.OPEN
        ):
            raise ConnectionUnavailableError("Websocket is not connected")

        # Get websocket reference under lock
        async with self._lock:
            websocket = self.websocket
            if websocket is None:
                raise ConnectionUnavailableError("Websocket is not connected")

        # Perform send outside lock
        try:
            await websocket.send(message)
            async with self._lock:
                self._update_activity()
        except ConnectionClosed as e:
            await self.close()
            self.logger.error(f"Connection closed while sending message: {e}")
            raise ConnectionClosedError(f"Connection closed while sending message: {e}") from e

    async def recv(self) -> str | bytes:
        """Receive a message from the WebSocket connection.

        Returns:
            The received message (string or bytes).

        Raises:
            ConnectionBusyError: If the connection has not been acquired.
            ConnectionUnavailableError: If the websocket is not connected.
            ConnectionClosedError: If the connection closes during receiving.
        """
        if not self._is_busy:
            raise ConnectionBusyError("Connection must be acquired before receiving messages")

        # Check connection state outside lock
        if not (
            self.websocket is not None
            and not self._closed
            and self.websocket.state == protocol.OPEN
        ):
            raise ConnectionUnavailableError("Websocket is not connected")

        # Get websocket reference under lock
        async with self._lock:
            websocket = self.websocket
            if websocket is None:
                raise ConnectionUnavailableError("Websocket is not connected")

        # Perform recv outside lock
        try:
            message = await websocket.recv()
            async with self._lock:
                self._update_activity()
            return message
        except ConnectionClosed as e:
            await self.close()
            self.logger.error(f"Connection closed while receiving message: {e}")
            raise ConnectionClosedError(f"Connection closed while receiving message: {e}") from e

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"connection_id={self._connection_id}, "
            f"uri={self.uri}, "
            f"busy={self._is_busy}, "
            f"draining={self._is_draining}, "
            f"connected={self.is_connected}, "
            f"closed={self._closed})"
        )

    def __str__(self) -> str:
        return f"WebsocketConnection({self._connection_id})"

    def __hash__(self) -> int:
        return hash(self._connection_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WebsocketConnection):
            return NotImplemented
        return self._connection_id == other._connection_id

    async def __aenter__(self) -> t.Self:
        await self.connect()
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> t.Literal[False]:
        await self.release()
        return False
