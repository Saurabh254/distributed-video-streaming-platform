import logging

from app.core.connectors.postgres import DatabaseManager

logger = logging.getLogger(__name__)

INIT_DB_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE TABLE IF NOT EXISTS user_passwords (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    password_hash VARCHAR(255) NOT NULL,
    salt VARCHAR(64) NOT NULL,
    algorithm VARCHAR(32) DEFAULT 'pbkdf2_sha256' NOT NULL,
    iterations INTEGER DEFAULT 600000 NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
"""


async def init_db(manager: DatabaseManager) -> None:
    """Initialize required PostgreSQL tables if they do not already exist."""
    async with manager.get_connection() as conn, conn.cursor() as cur:
        await cur.execute(INIT_DB_SQL)
    logger.info("Database initialized (users, user_passwords verified)")
