import logging

from app.core.connectors.postgres import DatabaseManager

logger = logging.getLogger(__name__)

INIT_CATALOG_DB_SQL = """
-- Ensure views_count and likes_count columns exist on videos table
ALTER TABLE videos ADD COLUMN IF NOT EXISTS views_count BIGINT DEFAULT 0;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS likes_count BIGINT DEFAULT 0;

-- Ensure playback_history table exists for watch progress and history tracking
CREATE TABLE IF NOT EXISTS playback_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    session_id UUID NOT NULL,
    last_position_seconds NUMERIC(10, 2) DEFAULT 0,
    duration_seconds NUMERIC(10, 2) DEFAULT 0,
    completed BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_playback_history_user_video ON playback_history(user_id, video_id);
CREATE INDEX IF NOT EXISTS idx_playback_history_video ON playback_history(video_id);
"""


async def init_db(manager: DatabaseManager) -> None:
    """Ensure catalog-related schema extensions and tables exist."""
    async with manager.get_connection() as conn, conn.cursor() as cur:
        await cur.execute(INIT_CATALOG_DB_SQL)
    logger.info(
        "Catalog database verified (views_count, likes_count, playback_history)"
    )
