from typing import Any
from uuid import UUID

from psycopg import AsyncConnection


class AuthRepository:
    """Repository handling database queries for users and separate password salt credentials."""

    def __init__(self, conn: AsyncConnection) -> None:
        self._conn = conn

    async def create_user_with_password(
        self,
        username: str,
        email: str,
        password_hash: str,
        salt: str,
        iterations: int = 600_000,
        algorithm: str = "pbkdf2_sha256",
    ) -> dict[str, Any]:
        """Atomically create user and user_passwords rows."""
        async with self._conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO users (username, email)
                VALUES (%s, %s)
                RETURNING id, username, email, is_active, created_at, updated_at
                """,
                (username, email),
            )
            user_row = await cur.fetchone()
            if user_row is None:
                raise RuntimeError("Failed to create user record")

            user_id = user_row["id"]  # type: ignore

            await cur.execute(
                """
                INSERT INTO user_passwords (user_id, password_hash, salt, iterations, algorithm)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, password_hash, salt, iterations, algorithm),
            )

            return dict(user_row)

    async def get_user_by_identifier(self, identifier: str) -> dict[str, Any] | None:
        """Find user by username or email."""
        async with self._conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, username, email, is_active, created_at, updated_at
                FROM users
                WHERE username = %s OR email = %s
                LIMIT 1
                """,
                (identifier, identifier),
            )
            row = await cur.fetchone()
            return dict(row) if row else None

    async def get_user_by_id(self, user_id: UUID | str) -> dict[str, Any] | None:
        """Find user by unique ID."""
        async with self._conn.cursor() as cur:
            await cur.execute(
                """
                SELECT id, username, email, is_active, created_at, updated_at
                FROM users
                WHERE id = %s
                LIMIT 1
                """,
                (str(user_id),),
            )
            row = await cur.fetchone()
            return dict(row) if row else None

    async def get_password_credentials(
        self, user_id: UUID | str
    ) -> dict[str, Any] | None:
        """Find stored password salt and hash credentials from the user_passwords table."""
        async with self._conn.cursor() as cur:
            await cur.execute(
                """
                SELECT user_id, password_hash, salt, algorithm, iterations, created_at, updated_at
                FROM user_passwords
                WHERE user_id = %s
                LIMIT 1
                """,
                (str(user_id),),
            )
            row = await cur.fetchone()
            return dict(row) if row else None

    async def is_username_taken(self, username: str) -> bool:
        """Check if username is already in use."""
        async with self._conn.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM users WHERE username = %s LIMIT 1",
                (username,),
            )
            return (await cur.fetchone()) is not None

    async def is_email_taken(self, email: str) -> bool:
        """Check if email is already in use."""
        async with self._conn.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM users WHERE email = %s LIMIT 1",
                (email,),
            )
            return (await cur.fetchone()) is not None
