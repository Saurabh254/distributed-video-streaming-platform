import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def unique_user_data():
    uid = uuid.uuid4().hex[:8]
    return {
        "username": f"user_{uid}",
        "email": f"user_{uid}@example.com",
        "password": "StrongPassword123!",
    }


def test_auth_full_flow(unique_user_data):
    with TestClient(app) as client:
        # 1. Register
        reg_res = client.post("/api/v1/auth/register", json=unique_user_data)
        assert reg_res.status_code == 201
        reg_data = reg_res.json()
        assert "user" in reg_data
        assert "access_token" in reg_data
        assert "refresh_token" in reg_data
        assert reg_data["user"]["username"] == unique_user_data["username"]
        assert reg_data["user"]["email"] == unique_user_data["email"]
        user_id = reg_data["user"]["id"]

        # 2. Duplicate registration fails
        dup_res = client.post("/api/v1/auth/register", json=unique_user_data)
        assert dup_res.status_code == 409

        # 3. Login with JSON identifier
        login_res = client.post(
            "/api/v1/auth/login",
            json={
                "identifier": unique_user_data["username"],
                "password": unique_user_data["password"],
            },
        )
        assert login_res.status_code == 200
        tokens = login_res.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        assert tokens["user"]["id"] == user_id

        # 4. Login with JSON username field alias
        login_username_res = client.post(
            "/api/v1/auth/login",
            json={
                "username": unique_user_data["username"],
                "password": unique_user_data["password"],
            },
        )
        assert login_username_res.status_code == 200
        assert "access_token" in login_username_res.json()

        # 5. Login with JSON email field alias
        login_email_res = client.post(
            "/api/v1/auth/login",
            json={
                "email": unique_user_data["email"],
                "password": unique_user_data["password"],
            },
        )
        assert login_email_res.status_code == 200
        assert "access_token" in login_email_res.json()

        # 6. Login with OAuth2 Form data (used by Swagger UI "Authorize" dialog)
        oauth_form_res = client.post(
            "/api/v1/auth/login",
            data={
                "username": unique_user_data["username"],
                "password": unique_user_data["password"],
            },
        )
        assert oauth_form_res.status_code == 200
        oauth_data = oauth_form_res.json()
        assert oauth_data["token_type"] == "bearer"
        assert "access_token" in oauth_data

        # 7. Login with invalid password fails
        bad_pass_res = client.post(
            "/api/v1/auth/login",
            json={
                "identifier": unique_user_data["username"],
                "password": "WrongPassword123!",
            },
        )
        assert bad_pass_res.status_code == 401

        # 8. Access protected /me endpoint
        headers = {"Authorization": f"Bearer {access_token}"}
        me_res = client.get("/api/v1/auth/me", headers=headers)
        assert me_res.status_code == 200
        assert me_res.json()["id"] == user_id

        # 9. Unauthenticated request to /me fails
        unauth_me = client.get("/api/v1/auth/me")
        assert unauth_me.status_code == 401

        # 10. Refresh token rotation
        ref_res = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert ref_res.status_code == 200
        new_tokens = ref_res.json()
        new_access_token = new_tokens["access_token"]
        new_refresh_token = new_tokens["refresh_token"]
        assert new_refresh_token != refresh_token

        # 11. Reusing old refresh token fails (rotation protection)
        reused_ref = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert reused_ref.status_code == 401

        # 12. Logout with access token & refresh token
        logout_headers = {"Authorization": f"Bearer {new_access_token}"}
        logout_res = client.post(
            "/api/v1/auth/logout",
            headers=logout_headers,
            json={"refresh_token": new_refresh_token},
        )
        assert logout_res.status_code == 200

        # 13. Logged-out access token is blacklisted in Redis
        revoked_me = client.get("/api/v1/auth/me", headers=logout_headers)
        assert revoked_me.status_code == 401
        assert "revoked" in revoked_me.json()["detail"].lower()

        # 14. Logged-out refresh token is revoked in Redis
        revoked_ref = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": new_refresh_token},
        )
        assert revoked_ref.status_code == 401


@pytest.mark.asyncio
async def test_two_separate_tables_verification(unique_user_data):
    from app.core.connectors.postgres import db_manager
    from app.core.connectors.redis import redis_manager
    from app.repository.auth import AuthRepository
    from app.schemas.auth import UserRegisterRequest
    from app.services.auth_service import AuthService

    await redis_manager.start()
    await db_manager.start()

    async with db_manager.get_connection() as conn:
        repo = AuthRepository(conn)
        service = AuthService(repo=repo, redis=redis_manager.get_client())

        req = UserRegisterRequest(**unique_user_data)
        user, _ = await service.register(req)
        user_id = user["id"]

        # Check users table
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, username, email FROM users WHERE id = %s",
                (user_id,),
            )
            user_row = await cur.fetchone()
            assert user_row is not None
            assert user_row["username"] == unique_user_data["username"]
            assert "password" not in user_row
            assert "salt" not in user_row

            # Check user_passwords table
            await cur.execute(
                "SELECT user_id, password_hash, salt, algorithm, iterations FROM user_passwords WHERE user_id = %s",
                (user_id,),
            )
            cred_row = await cur.fetchone()
            assert cred_row is not None
            assert cred_row["user_id"] == user_id
            assert len(cred_row["salt"]) == 32  # 16 bytes hex
            assert len(cred_row["password_hash"]) == 64  # sha256 hex
            assert cred_row["algorithm"] == "pbkdf2_sha256"
            assert cred_row["iterations"] == 600000

    await db_manager.close()
    await redis_manager.close()
