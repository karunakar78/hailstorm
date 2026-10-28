import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.target import RegisteredTarget
from app.models.test import Test as TestModel
from app.models.configuration import TestConfiguration as TestConfigurationModel
from app.schemas.test import TestConfigurationCreate, TestCreate
from app.services import tests as tests_service

API_PREFIX = "/api/v1"


async def _register_and_login(client: AsyncClient, email: str) -> str:
    register = await client.post(f"{API_PREFIX}/auth/register", json={"email": email, "password": "supersecret1"})
    assert register.status_code == 201
    login = await client.post(f"{API_PREFIX}/auth/login", json={"email": email, "password": "supersecret1"})
    assert login.status_code == 200
    return login.json()["access_token"]


async def _get_user_id_by_email(async_session: AsyncSession, email: str) -> uuid.UUID:
    result = await async_session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    assert user is not None
    return user.id


async def _insert_target(async_session: AsyncSession, owner_id: uuid.UUID, hostname: str = "tests.example.com", status: str = "verified") -> uuid.UUID:
    target = RegisteredTarget(owner_id=owner_id, hostname=hostname, verification_status=status)
    async_session.add(target)
    await async_session.commit()
    await async_session.refresh(target)
    return target.id


@pytest.mark.asyncio
async def test_create_test_with_authorized_target_returns_201(client: AsyncClient, async_session: AsyncSession) -> None:
    token = await _register_and_login(client, "test-create-1@example.com")
    owner_id = await _get_user_id_by_email(async_session, "test-create-1@example.com")
    target_id = await _insert_target(async_session, owner_id)

    response = await client.post(
        f"{API_PREFIX}/tests",
        json={
            "name": "Checkout load test",
            "description": "Smoke checkout flow",
            "configuration": {
                "target_id": str(target_id),
                "target_url": "https://tests.example.com/api/v1/checkout",
                "request_rate": 10.5,
                "duration_seconds": 60,
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Checkout load test"
    assert body["description"] == "Smoke checkout flow"
    assert body["status"] == "active"
    assert body["owner_id"]
    assert body["id"]
    assert body["configuration"]["target_id"] == str(target_id)
    assert body["configuration"]["target_url"] == "https://tests.example.com/api/v1/checkout"
    assert body["configuration"]["request_rate"] == 10.5
    assert body["configuration"]["duration_seconds"] == 60


@pytest.mark.asyncio
async def test_create_test_missing_auth_returns_401(client: AsyncClient) -> None:
    response = await client.post(
        f"{API_PREFIX}/tests",
        json={
            "name": "Checkout load test",
            "configuration": {"target_id": str(uuid.uuid4()), "target_url": "https://tests.example.com", "request_rate": 10, "duration_seconds": 60},
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_test_missing_fields_returns_422(client: AsyncClient, async_session: AsyncSession) -> None:
    token = await _register_and_login(client, "test-missing-fields@example.com")

    response = await client.post(f"{API_PREFIX}/tests", json={}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 422

    response = await client.post(f"{API_PREFIX}/tests", json={"name": "Checkout load test"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 422

    response = await client.post(
        f"{API_PREFIX}/tests",
        json={"name": "Checkout load test", "configuration": {"target_id": str(uuid.uuid4()), "target_url": "https://tests.example.com", "duration_seconds": 60}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_test_zero_or_negative_request_rate_rejected(client: AsyncClient, async_session: AsyncSession) -> None:
    token = await _register_and_login(client, "test-rate-1@example.com")
    owner_id = await _get_user_id_by_email(async_session, "test-rate-1@example.com")
    target_id = await _insert_target(async_session, owner_id)

    response = await client.post(
        f"{API_PREFIX}/tests",
        json={
            "name": "Checkout load test",
            "configuration": {"target_id": str(target_id), "target_url": "https://tests.example.com", "request_rate": 0, "duration_seconds": 60},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422

    response = await client.post(
        f"{API_PREFIX}/tests",
        json={
            "name": "Checkout load test",
            "configuration": {"target_id": str(target_id), "target_url": "https://tests.example.com", "request_rate": -1, "duration_seconds": 60},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_test_invalid_duration_rejected(client: AsyncClient, async_session: AsyncSession) -> None:
    token = await _register_and_login(client, "test-duration-1@example.com")
    owner_id = await _get_user_id_by_email(async_session, "test-duration-1@example.com")
    target_id = await _insert_target(async_session, owner_id)

    response = await client.post(
        f"{API_PREFIX}/tests",
        json={
            "name": "Checkout load test",
            "configuration": {"target_id": str(target_id), "target_url": "https://tests.example.com", "request_rate": 10, "duration_seconds": 0},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_test_target_belongs_to_other_user_returns_404(client: AsyncClient, async_session: AsyncSession) -> None:
    token_a = await _register_and_login(client, "test-owner-a@example.com")
    token_b = await _register_and_login(client, "test-owner-b@example.com")
    owner_b_id = await _get_user_id_by_email(async_session, "test-owner-b@example.com")
    target_id_b = await _insert_target(async_session, owner_b_id)

    response = await client.post(
        f"{API_PREFIX}/tests",
        json={
            "name": "Checkout load test",
            "configuration": {"target_id": str(target_id_b), "target_url": "https://tests.example.com", "request_rate": 10, "duration_seconds": 60},
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_test_unverified_target_rejected(client: AsyncClient, async_session: AsyncSession) -> None:
    token = await _register_and_login(client, "test-unverified@example.com")
    owner_id = await _get_user_id_by_email(async_session, "test-unverified@example.com")
    target_id = await _insert_target(async_session, owner_id, status="pending")

    response = await client.post(
        f"{API_PREFIX}/tests",
        json={
            "name": "Checkout load test",
            "configuration": {"target_id": str(target_id), "target_url": "https://tests.example.com", "request_rate": 10, "duration_seconds": 60},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_test_target_url_outside_scope_rejected(client: AsyncClient, async_session: AsyncSession) -> None:
    token = await _register_and_login(client, "test-scope@example.com")
    owner_id = await _get_user_id_by_email(async_session, "test-scope@example.com")
    target_id = await _insert_target(async_session, owner_id)

    response = await client.post(
        f"{API_PREFIX}/tests",
        json={
            "name": "Checkout load test",
            "configuration": {"target_id": str(target_id), "target_url": "https://evil.example.com/api/v1/checkout", "request_rate": 10, "duration_seconds": 60},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_test_configuration_insertion_failure_rolls_back_test(client: AsyncClient, async_session: AsyncSession) -> None:
    token = await _register_and_login(client, "test-rollback@example.com")
    owner_id = await _get_user_id_by_email(async_session, "test-rollback@example.com")
    target_id = await _insert_target(async_session, owner_id)

    test_data = TestCreate(
        name="Rollback load test",
        configuration=TestConfigurationCreate(target_id=target_id, target_url="https://tests.example.com", request_rate=10, duration_seconds=60),
    )

    with patch("app.services.tests.TestConfiguration", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            await tests_service.create_test(async_session, owner_id, test_data)

    await async_session.rollback()

    result = await async_session.execute(select(TestModel).where(TestModel.owner_id == owner_id))
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_create_test_successful_creation_persists_one_test_and_one_config(client: AsyncClient, async_session: AsyncSession) -> None:
    token = await _register_and_login(client, "test-success@example.com")
    owner_id = await _get_user_id_by_email(async_session, "test-success@example.com")
    target_id = await _insert_target(async_session, owner_id)

    response = await client.post(
        f"{API_PREFIX}/tests",
        json={
            "name": "Successful load test",
            "configuration": {"target_id": str(target_id), "target_url": "https://tests.example.com", "request_rate": 10, "duration_seconds": 60},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201

    test_id = response.json()["id"]
    test_count = (await async_session.execute(select(func.count()).select_from(TestModel).where(TestModel.owner_id == owner_id))).scalar_one()
    config_select = select(func.count()).select_from(TestConfigurationModel).where(TestConfigurationModel.test_id == uuid.UUID(str(test_id)))
    config_count = (await async_session.execute(config_select)).scalar_one()
    assert test_count == 1
    assert config_count == 1


@pytest.mark.asyncio
async def test_create_test_response_does_not_expose_internal_fields(client: AsyncClient, async_session: AsyncSession) -> None:
    token = await _register_and_login(client, "test-response@example.com")
    owner_id = await _get_user_id_by_email(async_session, "test-response@example.com")
    target_id = await _insert_target(async_session, owner_id)

    response = await client.post(
        f"{API_PREFIX}/tests",
        json={
            "name": "Response shape load test",
            "configuration": {"target_id": str(target_id), "target_url": "https://tests.example.com", "request_rate": 10, "duration_seconds": 60},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert set(body.keys()) == {"id", "owner_id", "name", "description", "status", "created_at", "updated_at", "configuration"}
    assert set(body["configuration"].keys()) == {"id", "test_id", "target_id", "target_url", "request_rate", "duration_seconds", "updated_at"}
    assert "password_hash" not in body


@pytest.mark.asyncio
async def test_list_tests_returns_only_own_tests(client: AsyncClient, async_session: AsyncSession) -> None:
    token_a = await _register_and_login(client, "list-user-a@example.com")
    token_b = await _register_and_login(client, "list-user-b@example.com")
    owner_a = await _get_user_id_by_email(async_session, "list-user-a@example.com")
    owner_b = await _get_user_id_by_email(async_session, "list-user-b@example.com")
    target_a = await _insert_target(async_session, owner_a)
    target_b = await _insert_target(async_session, owner_b)

    for i in range(2):
        await tests_service.create_test(async_session, owner_a, TestCreate(name=f"A test {i}", configuration=TestConfigurationCreate(target_id=target_a, target_url="https://tests.example.com", request_rate=10, duration_seconds=60)))
    await tests_service.create_test(async_session, owner_b, TestCreate(name="B test", configuration=TestConfigurationCreate(target_id=target_b, target_url="https://tests.example.com", request_rate=10, duration_seconds=60)))

    resp_a = await client.get(f"{API_PREFIX}/tests", headers={"Authorization": f"Bearer {token_a}"})
    assert resp_a.status_code == 200
    assert len(resp_a.json()) == 2

    resp_b = await client.get(f"{API_PREFIX}/tests", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b.status_code == 200
    assert len(resp_b.json()) == 1


@pytest.mark.asyncio
async def test_list_tests_empty_for_user_without_tests(client: AsyncClient) -> None:
    token = await _register_and_login(client, "list-empty@example.com")
    response = await client.get(f"{API_PREFIX}/tests", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_test_valid_returns_test_and_config(client: AsyncClient, async_session: AsyncSession) -> None:
    token = await _register_and_login(client, "test-get-1@example.com")
    owner_id = await _get_user_id_by_email(async_session, "test-get-1@example.com")
    target_id = await _insert_target(async_session, owner_id)
    test, config = await tests_service.create_test(
        async_session,
        owner_id,
        TestCreate(name="Get test", configuration=TestConfigurationCreate(target_id=target_id, target_url="https://tests.example.com", request_rate=10, duration_seconds=60)),
    )

    response = await client.get(f"{API_PREFIX}/tests/{test.id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(test.id)
    assert body["name"] == "Get test"
    assert body["configuration"]["test_id"] == str(test.id)
    assert body["configuration"]["target_id"] == str(target_id)


@pytest.mark.asyncio
async def test_get_test_not_found_for_other_user(client: AsyncClient, async_session: AsyncSession) -> None:
    token_a = await _register_and_login(client, "test-get-a@example.com")
    token_b = await _register_and_login(client, "test-get-b@example.com")
    owner_b_id = await _get_user_id_by_email(async_session, "test-get-b@example.com")
    target_b = await _insert_target(async_session, owner_b_id)
    test_b, _ = await tests_service.create_test(
        async_session,
        owner_b_id,
        TestCreate(name="B test", configuration=TestConfigurationCreate(target_id=target_b, target_url="https://tests.example.com", request_rate=10, duration_seconds=60)),
    )

    response = await client.get(f"{API_PREFIX}/tests/{test_b.id}", headers={"Authorization": f"Bearer {token_a}"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_test_not_found_when_missing(client: AsyncClient) -> None:
    token = await _register_and_login(client, "test-get-missing@example.com")
    response = await client.get(f"{API_PREFIX}/tests/{uuid.uuid4()}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_negative_skip_returns_422(client: AsyncClient) -> None:
    token = await _register_and_login(client, "test-skip@example.com")
    response = await client.get(f"{API_PREFIX}/tests", params={"skip": -1}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_limit_exceeds_100_returns_422(client: AsyncClient) -> None:
    token = await _register_and_login(client, "test-limit@example.com")
    response = await client.get(f"{API_PREFIX}/tests", params={"limit": 101}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_matches_no_test_returns_empty(client: AsyncClient) -> None:
    token = await _register_and_login(client, "test-search@example.com")
    response = await client.get(f"{API_PREFIX}/tests", params={"search": "no-such-test"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_status_filter_valid_returns_only_matching(client: AsyncClient, async_session: AsyncSession) -> None:
    token = await _register_and_login(client, "test-status@example.com")
    owner_id = await _get_user_id_by_email(async_session, "test-status@example.com")

    active, _ = await tests_service.create_test(async_session, owner_id, TestCreate(name="Status active", configuration=TestConfigurationCreate(target_id=(await _insert_target(async_session, owner_id)), target_url="https://tests.example.com", request_rate=10, duration_seconds=60)))
    archived_test = TestModel(owner_id=owner_id, name="Status archived", description=None, status="archived", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    async_session.add(archived_test)
    await async_session.commit()

    response = await client.get(f"{API_PREFIX}/tests", params={"status": "archived"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Status archived"
    assert active is not None


@pytest.mark.asyncio
async def test_archived_test_retrievable_by_id(client: AsyncClient, async_session: AsyncSession) -> None:
    token = await _register_and_login(client, "test-archived@example.com")
    owner_id = await _get_user_id_by_email(async_session, "test-archived@example.com")
    target_id = await _insert_target(async_session, owner_id)
    archived_test = TestModel(owner_id=owner_id, name="Archived test", description=None, status="archived", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    async_session.add(archived_test)
    await async_session.commit()
    await async_session.refresh(archived_test)

    response = await client.get(f"{API_PREFIX}/tests/{archived_test.id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_list_requires_auth(client: AsyncClient) -> None:
    response = await client.get(f"{API_PREFIX}/tests")
    assert response.status_code == 401

