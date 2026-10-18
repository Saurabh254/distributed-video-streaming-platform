import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class PlaybackRepository:
    """PostgreSQL repository for playback metadata, view counting, and watch history."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    async def get_video(self, video_id: UUID | str) -> dict[str, Any] | None:
        """Fetch video stream details and status."""
        query = """
            SELECT
                id,
                user_id,
                title,
                description,
                s3_bucket,
                s3_key,
                status,
                COALESCE(hls_status, 'pending') AS hls_status,
                hls_master_playlist_url,
                COALESCE(duration_seconds, 0) AS duration_seconds,
                width,
                height,
                thumbnail_url,
                COALESCE(views_count, 0) AS views_count
            FROM videos
            WHERE id = $1
            LIMIT 1
        """
        async with self._conn.cursor() as cur:
            await cur.execute(query, (str(video_id),))
            return await cur.fetchone()

    async def increment_views(self, video_id: UUID | str) -> int:
        """Atomically increment views_count in database."""
        query = """
            UPDATE videos
            SET views_count = COALESCE(views_count, 0) + 1,
                updated_at = NOW()
            WHERE id = $1
            RETURNING views_count
        """
        async with self._conn.cursor() as cur:
            await cur.execute(query, (str(video_id),))
            row = await cur.fetchone()
            return row["views_count"] if row else 0

    async def upsert_playback_history(
        self,
        user_id: UUID | str,
        video_id: UUID | str,
        session_id: UUID | str,
        position_seconds: float,
        duration_seconds: float,
        completed: bool = False,
    ) -> None:
        """Save user watch progress to playback_history."""
        query = """
            INSERT INTO playback_history (
                id, user_id, video_id, session_id, last_position_seconds,
                duration_seconds, completed, updated_at, created_at
            )
            VALUES (
                gen_random_uuid(), $1, $2, $3, $4, $5, $6, NOW(), NOW()
            )
            ON CONFLICT DO NOTHING
        """
        async with self._conn.cursor() as cur:
            await cur.execute(
                query,
                (
                    str(user_id),
                    str(video_id),
                    str(session_id),
                    position_seconds,
                    duration_seconds,
                    completed,
                ),
            )

    async def get_resume_position(
        self,
        user_id: UUID | str,
        video_id: UUID | str,
    ) -> dict[str, Any] | None:
        """Retrieve most recent watch progress for user."""
        query = """
            SELECT last_position_seconds, completed
            FROM playback_history
            WHERE user_id = $1 AND video_id = $2
            ORDER BY updated_at DESC
            LIMIT 1
        """
        async with self._conn.cursor() as cur:
            await cur.execute(query, (str(user_id), str(video_id)))
            return await cur.fetchone()
