"""Authentication flow integration tests."""

from __future__ import annotations

from httpx import AsyncClient

OWNER = {"email": "owner@example.com", "password": "supersecret12345"}


async def test_bootstrap_registration_then_closes(client: AsyncClient, reset_users: None) -> None:
    open_state = await client.get("/api/v1/auth/registration-open")
    assert open_state.json() == {"open": True}

    created = await client.post("/api/v1/auth/register", json=OWNER)
    assert created.status_code == 201, created.text
    assert created.json()["user"]["email"] == OWNER["email"]
    assert created.json()["user"]["is_superuser"] is True

    closed = await client.get("/api/v1/auth/registration-open")
    assert closed.json() == {"open": False}

    second = await client.post(
        "/api/v1/auth/register",
        json={"email": "intruder@example.com", "password": "anothersecret12345"},
    )
    assert second.status_code == 403
    assert second.json()["error"]["code"] == "authorization_error"


async def test_login_refresh_logout_lifecycle(client: AsyncClient, reset_users: None) -> None:
    await client.post("/api/v1/auth/register", json=OWNER)

    bad = await client.post(
        "/api/v1/auth/login", json={"email": OWNER["email"], "password": "wrong-password"}
    )
    assert bad.status_code == 401

    login = await client.post("/api/v1/auth/login", json=OWNER)
    assert login.status_code == 200, login.text
    tokens = login.json()["tokens"]
    access, refresh = tokens["access_token"], tokens["refresh_token"]

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert me.status_code == 200
    assert me.json()["email"] == OWNER["email"]

    rotated = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert rotated.status_code == 200, rotated.text
    new_refresh = rotated.json()["refresh_token"]

    # The old refresh token was revoked by rotation.
    reused = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert reused.status_code == 401

    logged_out = await client.post("/api/v1/auth/logout", json={"refresh_token": new_refresh})
    assert logged_out.status_code == 200

    after_logout = await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert after_logout.status_code == 401


async def test_protected_route_requires_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_error"


async def test_password_too_short_rejected(client: AsyncClient, reset_users: None) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "tiny"},
    )
    # Pydantic enforces min_length=12 before it reaches the service.
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
