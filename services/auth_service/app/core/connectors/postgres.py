from contextlib import contextmanager

from app.core.config import settings


class DatabaseManager:
    def __init__(self) -> None:
        self._connection = None

    def connect(self) -> None:
        self._pool.open(wait=True)

    @contextmanager
    def get_connection(self):
        with self._pool.connection() as conn:
            yield conn

    def validation_connection(self) -> bool:
        try:
            with self._pool.connection() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    def close(self) -> None:
        self._pool.close()


db_manager = DatabaseManager()
