from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection, Connection


class VideoRepository:
    def __init__(self, conn: AsyncConnection) -> None:
        self.conn = conn

    async def create_video(
        self,
        video_id: UUID | str,
        user_id: UUID | str,
        title: str,
        description: str | None,
        category: str | None,
        original_filename: str,
        content_type: str,
        file_size: int,
        s3_bucket: str,
        s3_key: str,
        status: str = "pending_upload",
    ) -> dict[str, Any]:
        query = """
        INSERT INTO videos (
            id, user_id, title, description, category,
            original_filename, content_type, file_size,
            s3_bucket, s3_key, status
        )
        VALUES (
            %(id)s, %(user_id)s, %(title)s, %(description)s, %(category)s,
            %(original_filename)s, %(content_type)s, %(file_size)s,
            %(s3_bucket)s, %(s3_key)s, %(status)s
        )
        RETURNING *;
        """
        async with self.conn.cursor() as cur:
            await cur.execute(
                query,
                {
                    "id": str(video_id),
                    "user_id": str(user_id),
                    "title": title,
                    "description": description,
                    "category": category,
                    "original_filename": original_filename,
                    "content_type": content_type,
                    "file_size": file_size,
                    "s3_bucket": s3_bucket,
                    "s3_key": s3_key,
                    "status": status,
                },
            )
            row = await cur.fetchone()
            return dict(row)  # type: ignore

    async def get_video_by_id(self, video_id: UUID | str) -> dict[str, Any] | None:
        query = "SELECT * FROM videos WHERE id = %(id)s;"
        async with self.conn.cursor() as cur:
            await cur.execute(query, {"id": str(video_id)})
            row = await cur.fetchone()
            return dict(row) if row else None

    async def update_status(
        self,
        video_id: UUID | str,
        status: str,
        uploaded_at: datetime | None = None,
    ) -> dict[str, Any] | None:
        query = """
        UPDATE videos
        SET status = %(status)s,
            updated_at = NOW(),
            uploaded_at = COALESCE(%(uploaded_at)s, uploaded_at)
        WHERE id = %(id)s
        RETURNING *;
        """
        async with self.conn.cursor() as cur:
            await cur.execute(
                query,
                {
                    "id": str(video_id),
                    "status": status,
                    "uploaded_at": uploaded_at,
                },
            )
            row = await cur.fetchone()
            return dict(row) if row else None

    async def update_processing_results(
        self,
        video_id: UUID | str,
        status: str,
        thumbnail_url: str | None = None,
        duration_seconds: float | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> dict[str, Any] | None:
        query = """
        UPDATE videos
        SET status = %(status)s,
            thumbnail_url = COALESCE(%(thumbnail_url)s, thumbnail_url),
            duration_seconds = COALESCE(%(duration_seconds)s, duration_seconds),
            width = COALESCE(%(width)s, width),
            height = COALESCE(%(height)s, height),
            updated_at = NOW()
        WHERE id = %(id)s
        RETURNING *;
        """
        async with self.conn.cursor() as cur:
            await cur.execute(
                query,
                {
                    "id": str(video_id),
                    "status": status,
                    "thumbnail_url": thumbnail_url,
                    "duration_seconds": duration_seconds,
                    "width": width,
                    "height": height,
                },
            )
            row = await cur.fetchone()
            return dict(row) if row else None

    async def update_hls_results(
        self,
        video_id: UUID | str,
        hls_status: str,
        hls_master_playlist_url: str | None = None,
    ) -> dict[str, Any] | None:
        query = """
        UPDATE videos
        SET hls_status = %(hls_status)s,
            hls_master_playlist_url = COALESCE(%(hls_master_playlist_url)s, hls_master_playlist_url),
            updated_at = NOW()
        WHERE id = %(id)s
        RETURNING *;
        """
        async with self.conn.cursor() as cur:
            await cur.execute(
                query,
                {
                    "id": str(video_id),
                    "hls_status": hls_status,
                    "hls_master_playlist_url": hls_master_playlist_url,
                },
            )
            row = await cur.fetchone()
            return dict(row) if row else None

    async def list_by_user(
        self, user_id: UUID | str, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        query = """
        SELECT * FROM videos
        WHERE user_id = %(user_id)s
        ORDER BY created_at DESC
        LIMIT %(limit)s OFFSET %(offset)s;
        """
        async with self.conn.cursor() as cur:
            await cur.execute(
                query,
                {
                    "user_id": str(user_id),
                    "limit": limit,
                    "offset": offset,
                },
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def count_by_user(self, user_id: UUID | str) -> int:
        query = "SELECT COUNT(*) as cnt FROM videos WHERE user_id = %(user_id)s;"
        async with self.conn.cursor() as cur:
            await cur.execute(query, {"user_id": str(user_id)})
            row = await cur.fetchone()
            return int(row["cnt"]) if row else 0


class SyncVideoRepository:
    """Synchronous repository for Dramatiq worker execution."""

    def __init__(self, conn: Connection) -> None:
        self.conn = conn

    def update_processing_results(
        self,
        video_id: UUID | str,
        status: str,
        thumbnail_url: str | None = None,
        duration_seconds: float | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> dict[str, Any] | None:
        query = """
        UPDATE videos
        SET status = %(status)s,
            thumbnail_url = COALESCE(%(thumbnail_url)s, thumbnail_url),
            duration_seconds = COALESCE(%(duration_seconds)s, duration_seconds),
            width = COALESCE(%(width)s, width),
            height = COALESCE(%(height)s, height),
            updated_at = NOW()
        WHERE id = %(id)s
        RETURNING *;
        """
        with self.conn.cursor() as cur:
            cur.execute(
                query,
                {
                    "id": str(video_id),
                    "status": status,
                    "thumbnail_url": thumbnail_url,
                    "duration_seconds": duration_seconds,
                    "width": width,
                    "height": height,
                },
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def update_hls_results(
        self,
        video_id: UUID | str,
        hls_status: str,
        hls_master_playlist_url: str | None = None,
    ) -> dict[str, Any] | None:
        query = """
        UPDATE videos
        SET hls_status = %(hls_status)s,
            hls_master_playlist_url = COALESCE(%(hls_master_playlist_url)s, hls_master_playlist_url),
            updated_at = NOW()
        WHERE id = %(id)s
        RETURNING *;
        """
        with self.conn.cursor() as cur:
            cur.execute(
                query,
                {
                    "id": str(video_id),
                    "hls_status": hls_status,
                    "hls_master_playlist_url": hls_master_playlist_url,
                },
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def update_status(
        self,
        video_id: UUID | str,
        status: str,
    ) -> dict[str, Any] | None:
        query = """
        UPDATE videos
        SET status = %(status)s,
            updated_at = NOW()
        WHERE id = %(id)s
        RETURNING *;
        """
        with self.conn.cursor() as cur:
            cur.execute(query, {"id": str(video_id), "status": status})
            row = cur.fetchone()
            return dict(row) if row else None
