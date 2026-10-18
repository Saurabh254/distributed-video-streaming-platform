import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class CatalogRepository:
    """Asynchronous PostgreSQL repository for video catalog queries using psycopg."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    async def list_videos(
        self,
        category: str | None = None,
        search: str | None = None,
        sort: str = "latest",
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Query videos joined with user/creator information."""
        conditions = ["v.status != 'pending_upload'"]
        params: list[Any] = []

        if category and category.lower() != "all":
            params.append(category)
            conditions.append("LOWER(v.category) = LOWER(%s)")

        if search and search.strip():
            term = f"%{search.strip()}%"
            params.extend([term, term, term])
            conditions.append(
                "(v.title ILIKE %s OR v.description ILIKE %s OR u.username ILIKE %s)"
            )

        where_clause = " AND ".join(conditions)

        order_by = "v.created_at DESC"
        if sort == "views":
            order_by = "v.views_count DESC, v.created_at DESC"
        elif sort == "duration":
            order_by = "v.duration_seconds DESC, v.created_at DESC"

        params.extend([limit, offset])

        query = f"""
            SELECT
                v.id,
                v.user_id,
                v.title,
                v.description,
                COALESCE(v.category, 'General') AS category,
                v.thumbnail_url,
                COALESCE(v.duration_seconds, 0) AS duration_seconds,
                v.width,
                v.height,
                COALESCE(v.views_count, 0) AS views_count,
                COALESCE(v.likes_count, 0) AS likes_count,
                v.status,
                v.hls_status,
                v.created_at,
                u.username,
                u.email
            FROM videos v
            LEFT JOIN users u ON v.user_id = u.id
            WHERE {where_clause}
            ORDER BY {order_by}
            LIMIT %s OFFSET %s
        """

        async with self._conn.cursor() as cur:
            await cur.execute(query, params)
            return await cur.fetchall()

    async def count_videos(
        self,
        category: str | None = None,
        search: str | None = None,
    ) -> int:
        """Count total videos matching filter criteria."""
        conditions = ["v.status != 'pending_upload'"]
        params: list[Any] = []

        if category and category.lower() != "all":
            params.append(category)
            conditions.append("LOWER(v.category) = LOWER(%s)")

        if search and search.strip():
            term = f"%{search.strip()}%"
            params.extend([term, term, term])
            conditions.append(
                "(v.title ILIKE %s OR v.description ILIKE %s OR u.username ILIKE %s)"
            )

        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT COUNT(*) AS total
            FROM videos v
            LEFT JOIN users u ON v.user_id = u.id
            WHERE {where_clause}
        """

        async with self._conn.cursor() as cur:
            await cur.execute(query, params)
            row = await cur.fetchone()
            return row["total"] if row else 0

    async def get_video_by_id(self, video_id: UUID | str) -> dict[str, Any] | None:
        """Retrieve a single video with creator information."""
        query = """
            SELECT
                v.id,
                v.user_id,
                v.title,
                v.description,
                COALESCE(v.category, 'General') AS category,
                v.thumbnail_url,
                COALESCE(v.duration_seconds, 0) AS duration_seconds,
                v.width,
                v.height,
                COALESCE(v.views_count, 0) AS views_count,
                COALESCE(v.likes_count, 0) AS likes_count,
                v.status,
                v.hls_status,
                v.created_at,
                u.username,
                u.email
            FROM videos v
            LEFT JOIN users u ON v.user_id = u.id
            WHERE v.id = %s
            LIMIT 1
        """
        async with self._conn.cursor() as cur:
            await cur.execute(query, (str(video_id),))
            return await cur.fetchone()

    async def get_related_videos(
        self,
        video_id: UUID | str,
        category: str | None = None,
        limit: int = 6,
    ) -> list[dict[str, Any]]:
        """Retrieve related videos (same category or latest, excluding current video)."""
        conditions = ["v.id != %s", "v.status != 'pending_upload'"]
        params: list[Any] = [str(video_id)]

        if category:
            params.append(category)
            conditions.append("LOWER(v.category) = LOWER(%s)")

        params.append(limit)
        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT
                v.id,
                v.user_id,
                v.title,
                v.description,
                COALESCE(v.category, 'General') AS category,
                v.thumbnail_url,
                COALESCE(v.duration_seconds, 0) AS duration_seconds,
                v.width,
                v.height,
                COALESCE(v.views_count, 0) AS views_count,
                COALESCE(v.likes_count, 0) AS likes_count,
                v.status,
                v.hls_status,
                v.created_at,
                u.username,
                u.email
            FROM videos v
            LEFT JOIN users u ON v.user_id = u.id
            WHERE {where_clause}
            ORDER BY v.created_at DESC
            LIMIT %s
        """
        async with self._conn.cursor() as cur:
            await cur.execute(query, params)
            return await cur.fetchall()

    async def get_categories_aggregation(self) -> list[dict[str, Any]]:
        """Retrieve distinct categories and active video counts."""
        query = """
            SELECT
                COALESCE(category, 'General') AS name,
                COUNT(*) AS video_count
            FROM videos
            WHERE status != 'pending_upload'
            GROUP BY COALESCE(category, 'General')
            ORDER BY video_count DESC
        """
        async with self._conn.cursor() as cur:
            await cur.execute(query)
            return await cur.fetchall()
