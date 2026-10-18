import logging

from app.core.connectors.postgres import DatabaseManager

logger = logging.getLogger(__name__)

INIT_DB_SQL = """
CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    original_filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL,
    s3_bucket VARCHAR(100) NOT NULL,
    s3_key VARCHAR(512) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending_upload',
    thumbnail_url VARCHAR(512),
    duration_seconds NUMERIC(10, 2),
    width INT,
    height INT,
    hls_master_playlist_url VARCHAR(512),
    hls_status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    uploaded_at TIMESTAMPTZ
);

ALTER TABLE videos ADD COLUMN IF NOT EXISTS thumbnail_url VARCHAR(512);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS duration_seconds NUMERIC(10, 2);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS width INT;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS height INT;
ALTER TABLE videos ADD COLUMN IF NOT EXISTS hls_master_playlist_url VARCHAR(512);
ALTER TABLE videos ADD COLUMN IF NOT EXISTS hls_status VARCHAR(50) DEFAULT 'pending';

CREATE INDEX IF NOT EXISTS idx_videos_user_id ON videos(user_id);
CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);
CREATE INDEX IF NOT EXISTS idx_videos_hls_status ON videos(hls_status);
CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(created_at DESC);
"""


async def init_db(manager: DatabaseManager) -> None:
    """Initialize required PostgreSQL tables if they do not already exist."""
    async with manager.get_connection() as conn, conn.cursor() as cur:
        await cur.execute(INIT_DB_SQL)
    logger.info(
        "Database initialized (videos table, thumbnail and HLS columns verified)"
    )
