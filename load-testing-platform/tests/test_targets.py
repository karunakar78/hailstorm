import pytest
from httpx import AsyncClient

API_PREFIX = "/api/v1"


async def _register_and_login(client: AsyncClient, email: str) -> str:
    register = await client.post(f"{API_PREFIX}/auth/register", json={"email": email, "password": "supersecret1"})
    assert register.status_code == 201
    login = await client.post(f"{API_PREFIX}/auth/login", json={"email": email, "password": "supersecret1"})
    assert login.status_code == 200
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_user_can_register_target(client: AsyncClient) -> None:
    token = await _register_and_login(client, "target-reg-1@example.com")
    response = await client.post(
        f"{API_PREFIX}/targets",
        json={"hostname": "https://API.Staging.Example.com:8443/v1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["hostname"] == "api.staging.example.com"
    assert body["verification_status"] == "pending"
    assert body["owner_id"]


@pytest.mark.asyncio
async def test_unauthenticated_target_registration_rejected(client: AsyncClient) -> None:
    response = await client.post(f"{API_PREFIX}/targets", json={"hostname": "api.example.com"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_user_cannot_read_others_targets(client: AsyncClient) -> None:
    token_a = await _register_and_login(client, "target-user-a@example.com")
    token_b = await _register_and_login(client, "target-user-b@example.com")

    reg_a = await client.post(f"{API_PREFIX}/targets", json={"hostname": "a.example.com"}, headers={"Authorization": f"Bearer {token_a}"})
    reg_b = await client.post(f"{API_PREFIX}/targets", json={"hostname": "b.example.com"}, headers={"Authorization": f"Bearer {token_b}"})
    assert reg_a.status_code == 201
    assert reg_b.status_code == 201

    list_a = await client.get(f"{API_PREFIX}/targets", headers={"Authorization": f"Bearer {token_a}"})
    assert list_a.status_code == 200
    assert len(list_a.json()) == 1
    assert list_a.json()[0]["hostname"] == "a.example.com"

    list_b = await client.get(f"{API_PREFIX}/targets", headers={"Authorization": f"Bearer {token_b}"})
    assert list_b.status_code == 200
    assert len(list_b.json()) == 1
    assert list_b.json()[0]["hostname"] == "b.example.com"


@pytest.mark.asyncio
async def test_invalid_hostname_rejected(client: AsyncClient) -> None:
    token = await _register_and_login(client, "target-invalid@example.com")
    response = await client.post(f"{API_PREFIX}/targets", json={"hostname": "ht tp://bad_host"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 400

    prohibited = await client.post(f"{API_PREFIX}/targets", json={"hostname": "http://localhost:8000"}, headers={"Authorization": f"Bearer {token}"})
    assert prohibited.status_code == 400


@pytest.mark.asyncio
async def test_clients_cannot_set_verification_status(client: AsyncClient) -> None:
    token = await _register_and_login(client, "target-status@example.com")
    response = await client.post(
        f"{API_PREFIX}/targets",
        json={"hostname": "status.example.com", "verification_status": "verified"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    assert response.json()["verification_status"] == "pending"

    verify = await client.post(f"{API_PREFIX}/targets/{response.json()['id']}/verify", headers={"Authorization": f"Bearer {token}"})
    assert verify.status_code == 202


@pytest.mark.asyncio
async def test_newly_registered_target_starts_pending(client: AsyncClient) -> None:
    token = await _register_and_login(client, "target-pending@example.com")
    reg = await client.post(f"{API_PREFIX}/targets", json={"hostname": "pending.example.com"}, headers={"Authorization": f"Bearer {token}"})
    assert reg.status_code == 201
    target_id = reg.json()["id"]
    got = await client.get(f"{API_PREFIX}/targets/{target_id}", headers={"Authorization": f"Bearer {token}"})
    assert got.status_code == 200
    assert got.json()["verification_status"] == "pending"


@pytest.mark.asyncio
async def test_pending_target_cannot_be_used_for_test(client: AsyncClient) -> None:
    token = await _register_and_login(client, "target-unused@example.com")
    reg = await client.post(f"{API_PREFIX}/targets", json={"hostname": "unused.example.com"}, headers={"Authorization": f"Bearer {token}"})
    assert reg.status_code == 201
    target_id = reg.json()["id"]

    got = await client.get(f"{API_PREFIX}/targets/{target_id}", headers={"Authorization": f"Bearer {token}"})
    assert got.status_code == 200
    assert got.json()["verification_status"] == "pending"


@pytest.mark.asyncio
async def test_verification_status_changes_only_through_trusted_workflow(client: AsyncClient) -> None:
    token = await _register_and_login(client, "target-verify@example.com")
    reg = await client.post(f"{API_PREFIX}/targets", json={"hostname": "verify.example.com"}, headers={"Authorization": f"Bearer {token}"})
    assert reg.status_code == 201
    target_id = reg.json()["id"]

    verify = await client.post(f"{API_PREFIX}/targets/{target_id}/verify", headers={"Authorization": f"Bearer {token}"})
    assert verify.status_code == 202

    got = await client.get(f"{API_PREFIX}/targets/{target_id}", headers={"Authorization": f"Bearer {token}"})
    assert got.status_code == 200
    assert got.json()["verification_status"] == "pending"
