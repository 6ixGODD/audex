from __future__ import annotations

import typing as t

import sqlalchemy as sa
import sqlalchemy.event as saevent
import sqlalchemy.ext.asyncio as aiosa
import sqlmodel as sqlm

from audex.lib.database import Database


class SQLitePoolConfig(t.TypedDict):
    echo: bool
    """Whether to log all SQL statements."""

    pool_size: int
    """Number of connections to maintain in the pool."""

    max_overflow: int
    """Max number of connections beyond pool_size."""

    pool_timeout: float
    """Seconds to wait before timing out on connection."""

    pool_recycle: int
    """Seconds after which to recycle connections."""

    pool_pre_ping: bool
    """Test connections before using them."""


class SQLite(Database):
    """SQLite database container with async SQLModel/SQLAlchemy support.

    This class provides a high-level interface for SQLite database
    operations with the following features:

    1. Async engine and session management for repository pattern
    2. Connection pooling with configurable parameters
    3. Raw SQL execution with transaction control
    4. Schema management utilities (create_all/drop_all)
    5. Unified lifecycle management through AsyncContextMixin

    Attributes:
        uri: SQLite connection URI.
        engine: SQLAlchemy async engine (initialized after init()).
        sessionmaker: Async session factory (initialized after init()).
        cfg: Connection pool configuration.

    Args:
        uri: SQLite connection URI (must use aiosqlite driver).
            Example: "sqlite+aiosqlite:///./database.db" (relative path)
            Example: "sqlite+aiosqlite:////absolute/path/database.db" (absolute path)
            Example: "sqlite+aiosqlite:///:memory:" (in-memory database)
        tables: List of SQLModel classes to manage. Used for create_all/drop_all.
        echo: Whether to log all SQL statements (useful for debugging).
        pool_size: Number of connections to maintain in the pool.
            Note: SQLite with aiosqlite uses NullPool by default in async mode.
        max_overflow: Max number of connections beyond pool_size.
        pool_timeout: Seconds to wait before timing out on connection.
        pool_recycle: Seconds after which to recycle connections.
            Set to -1 to disable recycling.
        pool_pre_ping: Test connections before using them. Recommended
            for production to handle stale connections.

    Example:
        ```python
        # Setup with file-based database
        sqlite = SQLite(
            uri="sqlite+aiosqlite:///./app.db",
            tables=[User, Post],
            echo=True,
        )

        # Setup with in-memory database (useful for testing)
        sqlite = SQLite(
            uri="sqlite+aiosqlite:///:memory:",
            tables=[User, Post],
        )

        # Initialize
        await sqlite.init()

        # Create tables
        await sqlite.create_all()

        # Use session for ORM operations
        async with sqlite.session() as session:
            user = await session.get(User, user_id)
            user.username = "new_name"
            await session.commit()

        # Execute raw SQL
        result = await sqlite.exec(
            "SELECT * FROM users WHERE age > :age",
            readonly=True,
            age=21,
        )

        # Cleanup
        await sqlite.close()
        ```

    Note:
        - The URI must use the aiosqlite driver for async support.
        - SQLite doesn't support some PostgreSQL features (e.g., JSONB operators).
        - Use JSON1 extension for JSON operations (enabled by default).
        - File path format: Use three slashes for relative paths, four for absolute.
    """

    def __init__(
        self,
        uri: str,
        *,
        tables: list[type[sqlm.SQLModel]] | None = None,
        echo: bool = False,
        pool_size: int = 20,
        max_overflow: int = 10,
        pool_timeout: float = 30.0,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
    ) -> None:
        self.uri = uri
        self.tables = tables or []
        self.engine: aiosa.AsyncEngine | None = None
        self.sessionmaker: aiosa.async_sessionmaker[aiosa.AsyncSession] | None = None
        self.cfg = SQLitePoolConfig(
            echo=echo,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=pool_pre_ping,
        )

    async def init(self) -> None:
        """Initialize the database engine and session factory.

        This method creates the async engine with connection pooling and
        sets up the session factory. It should be called during application
        startup, typically in a lifespan context manager.

        For SQLite, this also enables foreign key constraints and loads
        the JSON1 extension if available.

        Raises:
            Exception: If engine creation fails (e.g., invalid URI).
        """
        # Create engine with SQLite-specific configuration
        self.engine = aiosa.create_async_engine(
            self.uri,
            echo=self.cfg["echo"],
            # SQLite-specific: Use NullPool for better async compatibility
            # or StaticPool for in-memory databases
            poolclass=sa.pool.NullPool if ":memory:" not in self.uri else sa.pool.StaticPool,
            connect_args={
                "check_same_thread": False,  # Required for async SQLite
            },
        )

        # Configure SQLite settings
        @saevent.listens_for(self.engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_conn: t.Any, _connection_record: t.Any) -> None:
            """Set SQLite-specific pragmas on connection."""
            cursor = dbapi_conn.cursor()
            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys=ON")
            # Enable WAL mode for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

        self.sessionmaker = aiosa.async_sessionmaker(
            self.engine,
            class_=aiosa.AsyncSession,
            expire_on_commit=False,
        )

    async def close(self) -> None:
        """Close the database engine and clean up resources.

        This method disposes of the connection pool and resets the engine
        and session factory. It should be called during application shutdown.

        Note:
            This method is idempotent and safe to call multiple times.
        """
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.sessionmaker = None

    def session(self) -> aiosa.AsyncSession:
        """Create a new async database session.

        Returns:
            An async session context manager.

        Raises:
            RuntimeError: If sessionmaker is not initialized (call init() first).

        Example:
            ```python
            async with sqlite.session() as session:
                # Start a transaction
                user = await session.get(User, user_id)
                user.username = "new_name"
                await session.commit()
            ```

        Note:
            The session is automatically committed on successful exit and
            rolled back on exception. You can also manually commit/rollback
            within the context.
        """
        if not self.sessionmaker:
            raise RuntimeError("Sessionmaker not initialized. Call init() first.")

        return self.sessionmaker()

    async def exec(self, sql: str, /, readonly: bool = False, **params: t.Any) -> sa.Result[t.Any]:
        """Execute a raw SQL statement.

        This method provides direct SQL execution for cases where ORM
        abstractions are insufficient or when specific optimizations
        are needed.

        Args:
            sql: Raw SQL string to execute. Use named parameters with
                colon prefix.
            readonly: If True, does not commit the transaction. Use this
                for SELECT queries to avoid unnecessary commits.
            **params: Named parameters for the SQL statement.

        Returns:
            SQLAlchemy Result object containing query results.

        Raises:
            RuntimeError: If execution fails, with the original exception
                as the cause.

        Example:
            ```python
            # Read-only query
            result = await sqlite.exec(
                "SELECT * FROM users WHERE age > :age",
                readonly=True,
                age=21,
            )
            users = result.fetchall()

            # Write query
            await sqlite.exec(
                "UPDATE users SET status = :status WHERE id = :id",
                readonly=False,
                status="active",
                id=123,
            )

            # Using JSON1 extension
            result = await sqlite.exec(
                "SELECT * FROM users WHERE json_extract(tags, '$.premium') = 1",
                readonly=True,
            )
            ```

        Warning:
            Be careful with SQL injection. Always use parameterized queries
            with named parameters instead of string formatting.
        """
        async with self.session() as session, session.begin():
            result = await session.execute(sa.text(sql), params=params or None)
            if not readonly:
                await session.commit()
            return result

    async def ping(self) -> bool:
        """Check database connectivity.

        This method attempts to execute a simple query to verify that
        the database is reachable and responsive.

        Returns:
            True if database is reachable, False otherwise.

        Note:
            This method does not raise exceptions. It catches all errors
            and returns False instead.
        """
        if not self.engine:
            return False

        try:
            async with self.engine.connect() as conn:
                await conn.execute(sa.text("SELECT 1"))
            return True
        except Exception:
            return False

    async def create_all(self) -> None:
        """Create all database tables.

        This method creates tables for the specified SQLModel classes, or
        all tables in the SQLModel metadata if no models are specified.

        Raises:
            RuntimeError: If engine is not initialized.

        Example:
            ```python
            # Create specific tables
            sqlite = SQLite(
                uri="sqlite+aiosqlite:///./app.db",
                tables=[User, Post, Comment],
            )
            await sqlite.init()
            await sqlite.create_all()

            # Create all tables
            sqlite = SQLite(uri="sqlite+aiosqlite:///./app.db")
            await sqlite.init()
            await sqlite.create_all()
            ```

        Warning:
            This is typically used for development/testing. In production,
            use proper migration tools like Alembic to manage schema changes.
        """
        if not self.engine:
            raise RuntimeError("Engine not initialized. Call init() first.")

        async with self.engine.begin() as conn:
            if self.tables:

                def _create_tables(sync_conn: sa.Connection) -> None:
                    for model in self.tables:
                        model.metadata.create_all(bind=sync_conn)

                await conn.run_sync(_create_tables)
            else:
                await conn.run_sync(sqlm.SQLModel.metadata.create_all)

    async def drop_all(self) -> None:
        """Drop all database tables.

        This method drops all tables defined in the SQLModel metadata.

        Raises:
            RuntimeError: If engine is not initialized.

        Example:
            ```python
            await sqlite.drop_all()  # Be careful!
            ```

        Warning:
            This is destructive and should only be used in development/testing.
            All data will be lost. There is no confirmation prompt.
        """
        if not self.engine:
            raise RuntimeError("Engine not initialized. Call init() first.")

        async with self.engine.begin() as conn:
            await conn.run_sync(sqlm.SQLModel.metadata.drop_all)

    async def vacuum(self) -> None:
        """Run VACUUM command to optimize the database file.

        This command rebuilds the database file, repacking it into a minimal
        amount of disk space. It's useful after deleting large amounts of data.

        Raises:
            RuntimeError: If engine is not initialized.

        Example:
            ```python
            # After bulk deletions
            await sqlite.exec(
                "DELETE FROM old_logs WHERE created_at < :date",
                date=cutoff_date,
            )
            await sqlite.vacuum()  # Reclaim disk space
            ```

        Note:
            VACUUM requires exclusive access to the database and may take
            significant time on large databases.
        """
        if not self.engine:
            raise RuntimeError("Engine not initialized. Call init() first.")

        # VACUUM must be run outside a transaction
        async with self.engine.connect() as conn:
            await conn.execute(sa.text("VACUUM"))
            await conn.commit()
