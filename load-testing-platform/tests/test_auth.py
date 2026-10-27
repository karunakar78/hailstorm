import pytest
from httpx import AsyncClient
from jose import jwt

from app.core.config import settings

API_PREFIX = "/api/v1"


@pytest.mark.asyncio
async def test_user_can_register(client: AsyncClient) -> None:
    response = await client.post(
        f"{API_PREFIX}/auth/register",
        json={"email": "user1@example.com", "password": "supersecret1"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "user1@example.com"
    assert body["id"]
    assert "password_hash" not in body


@pytest.mark.asyncio
async def test_duplicate_email_registration_is_rejected(client: AsyncClient) -> None:
    payload = {"email": "dupe@example.com", "password": "supersecret1"}
    first = await client.post(f"{API_PREFIX}/auth/register", json=payload)
    assert first.status_code == 201
    second = await client.post(f"{API_PREFIX}/auth/register", json=payload)
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_incorrect_password_cannot_authenticate(client: AsyncClient) -> None:
    await client.post(f"{API_PREFIX}/auth/register", json={"email": "wrongpw@example.com", "password": "supersecret1"})
    response = await client.post(f"{API_PREFIX}/auth/login", json={"email": "wrongpw@example.com", "password": "wrongpassword"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_valid_login_returns_access_token(client: AsyncClient) -> None:
    await client.post(f"{API_PREFIX}/auth/register", json={"email": "loginuser@example.com", "password": "supersecret1"})
    response = await client.post(f"{API_PREFIX}/auth/login", json={"email": "loginuser@example.com", "password": "supersecret1"})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    decoded = jwt.decode(body["access_token"], settings.SECRET_KEY, algorithms=["HS256"])
    assert decoded["sub"]


@pytest.mark.asyncio
async def test_users_me_rejects_unauthenticated(client: AsyncClient) -> None:
    response = await client.get(f"{API_PREFIX}/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_users_me_returns_correct_user_with_valid_token(client: AsyncClient) -> None:
    await client.post(f"{API_PREFIX}/auth/register", json={"email": "meuser@example.com", "password": "supersecret1"})
    login = await client.post(f"{API_PREFIX}/auth/login", json={"email": "meuser@example.com", "password": "supersecret1"})
    token = login.json()["access_token"]
    response = await client.get(f"{API_PREFIX}/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "meuser@example.com"


@pytest.mark.asyncio
async def test_password_hashes_not_returned_to_clients(client: AsyncClient) -> None:
    response = await client.post(f"{API_PREFIX}/auth/register", json={"email": "hashuser@example.com", "password": "supersecret1"})
    assert response.status_code == 201
    assert "password_hash" not in response.json()
