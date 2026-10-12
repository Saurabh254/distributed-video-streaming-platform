import pytest

from app.core.connectors.postgres import DatabaseManager


@pytest.mark.asyncio
async def test_database_manager_uninitialized():
    mgr = DatabaseManager()
    with pytest.raises(RuntimeError, match="not been initialized"):
        mgr.get_pool()

    with pytest.raises(RuntimeError, match="not been initialized"):
        async with mgr.get_connection():
            pass


@pytest.mark.asyncio
async def test_database_manager_lifecycle():
    mgr = DatabaseManager(min_size=1, max_size=3)
    await mgr.start()

    # Idempotent start
    await mgr.start()

    pool = mgr.get_pool()
    assert pool is not None
    assert pool.min_size == 1
    assert pool.max_size == 3

    # Validation
    is_valid = await mgr.validate_connection()
    assert is_valid is True

    # Legacy alias validation
    assert await mgr.validation_connection() is True

    # Borrow connection and query
    async with mgr.get_connection() as conn, conn.cursor() as cur:
        await cur.execute("SELECT 100 as val, 'fineshare' as name")
        row = await cur.fetchone()
        assert row == {"val": 100, "name": "fineshare"}

    await mgr.close()
    # Idempotent close
    await mgr.close()

    with pytest.raises(RuntimeError, match="not been initialized"):
        mgr.get_pool()


@pytest.mark.asyncio
async def test_database_manager_connect_alias():
    mgr = DatabaseManager(min_size=1, max_size=2)
    await mgr.connect()
    assert mgr.get_pool() is not None
    await mgr.close()


@pytest.mark.asyncio
async def test_database_manager_transaction_rollback():
    mgr = DatabaseManager(min_size=1, max_size=2)
    await mgr.start()

    async with mgr.get_connection() as conn, conn.cursor() as cur:
        await cur.execute("CREATE TEMPORARY TABLE test_tx (id INT)")

    # Simulate an error inside the context manager
    with pytest.raises(ValueError):
        async with mgr.get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("INSERT INTO test_tx VALUES (1)")
            raise ValueError("Forced error to test rollback")

    # Verify that the value was rolled back
    async with mgr.get_connection() as conn, conn.cursor() as cur:
        await cur.execute("SELECT count(*) as cnt FROM test_tx")
        res = await cur.fetchone()
        assert res["cnt"] == 0

    await mgr.close()


def test_fastapi_dependencies():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.core.dependencies import DbDep, DbPoolDep
    from app.core.lifespan import lifespan

    test_app = FastAPI(lifespan=lifespan)

    @test_app.get("/test-conn")
    async def endpoint_conn(conn: DbDep):
        async with conn.cursor() as cur:
            await cur.execute("SELECT 777 as lucky")
            row = await cur.fetchone()
            return row

    @test_app.get("/test-pool")
    async def endpoint_pool(pool: DbPoolDep):
        stats = pool.get_stats()
        return {"pool_size": stats["pool_size"]}

    with TestClient(test_app) as client:
        res = client.get("/test-conn")
        assert res.status_code == 200
        assert res.json() == {"lucky": 777}

        res_pool = client.get("/test-pool")
        assert res_pool.status_code == 200
        assert res_pool.json()["pool_size"] > 0
