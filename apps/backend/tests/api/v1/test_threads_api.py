from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.threads import get_threads_service
from app.auth.dependencies import get_current_user
from app.main import create_app
from app.tools.threads.errors import ThreadsError
from app.tools.threads.schemas import ThreadsRequest, ThreadsResult, ThreadsRunResponse


def test_all_threads_routes_require_authentication() -> None:
    client = TestClient(create_app())
    run_id = uuid4()
    assert client.get("/api/v1/tools/threads/config").status_code == 401
    assert client.post("/api/v1/tools/threads/runs", json={"query": "travel"}).status_code == 401
    assert client.get("/api/v1/tools/threads/runs").status_code == 401
    assert client.get(f"/api/v1/tools/threads/runs/{run_id}").status_code == 401
    assert client.post(f"/api/v1/tools/threads/runs/{run_id}/cancel").status_code == 401
    assert (
        client.patch(
            f"/api/v1/tools/threads/runs/{run_id}", json={"visibility": "private"}
        ).status_code
        == 401
    )
    assert client.delete(f"/api/v1/tools/threads/runs/{run_id}").status_code == 401
    assert client.get(f"/api/v1/tools/threads/runs/{run_id}/export").status_code == 401


def setup_client() -> tuple[TestClient, SimpleNamespace, ThreadsRunResponse]:
    run = ThreadsRunResponse(
        id=uuid4(),
        status="queued",
        stage="queued",
        progress=0,
        request=ThreadsRequest(query="travel tips"),
        created_at=datetime.now(UTC),
    )
    service = SimpleNamespace(
        create=AsyncMock(return_value=run),
        get=AsyncMock(return_value=run),
        list=AsyncMock(return_value=[run]),
        cancel=AsyncMock(return_value=run),
        export=AsyncMock(return_value=run),
        update=AsyncMock(return_value=run),
        delete=AsyncMock(return_value=run),
    )
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4(), role="member")
    app.dependency_overrides[get_threads_service] = lambda: service
    return TestClient(app), service, run


def test_member_can_queue_poll_list_and_cancel_job() -> None:
    client, service, run = setup_client()
    created = client.post(
        "/api/v1/tools/threads/runs",
        json={"query": "travel tips"},
        headers={"Idempotency-Key": "threads-run-1"},
    )
    assert created.status_code == 202
    assert created.json()["status"] == "queued"
    assert service.create.await_args.args[2] == "threads-run-1"
    assert client.get(f"/api/v1/tools/threads/runs/{run.id}").json()["id"] == str(run.id)
    assert len(client.get("/api/v1/tools/threads/runs").json()) == 1
    assert client.post(f"/api/v1/tools/threads/runs/{run.id}/cancel").status_code == 200


@pytest.mark.parametrize(
    "payload",
    [
        {"query": " "},
        {"query": "travel", "max_posts_per_keyword": 10000},
        {"query": "travel", "keywords": [""]},
        {"query": "travel", "proxy": "http://localhost"},
        {"query": "travel", "sessions_dir": "../"},
    ],
)
def test_requests_reject_invalid_limits_and_server_configuration(
    payload: dict[str, object],
) -> None:
    client, service, _ = setup_client()
    response = client.post("/api/v1/tools/threads/runs", json=payload)
    assert response.status_code == 422
    service.create.assert_not_awaited()


def test_safe_domain_errors_and_result_exports() -> None:
    client, service, run = setup_client()
    service.get.side_effect = ThreadsError("RUN_NOT_FOUND", "Threads run not found.", 404)
    denied = client.get(f"/api/v1/tools/threads/runs/{run.id}")
    assert denied.status_code == 404
    assert denied.json() == {"code": "RUN_NOT_FOUND", "detail": "Threads run not found."}
    run.status, run.stage = "completed", "completed"
    run.result = ThreadsResult(
        query="travel tips", keywords=["travel"], posts=[], duration_seconds=1
    )
    exported = client.get(f"/api/v1/tools/threads/runs/{run.id}/export?format=json")
    assert exported.status_code == 200
    assert exported.json()["keywords"] == ["travel"]
    assert "attachment" in exported.headers["content-disposition"]
    text = client.get(f"/api/v1/tools/threads/runs/{run.id}/export?format=txt")
    assert text.status_code == 200
    assert '"query": "travel tips"' in text.text
    assert "Format: threads-text-v2" in text.text
    assert client.get(f"/api/v1/tools/threads/runs/{run.id}/export?format=md").status_code == 422
    assert client.get(f"/api/v1/tools/threads/runs/{run.id}/export?format=html").status_code == 422


def test_visibility_updates_and_deletion_are_dispatched_and_validated() -> None:
    client, service, run = setup_client()
    assert (
        client.patch(
            f"/api/v1/tools/threads/runs/{run.id}", json={"visibility": "private"}
        ).status_code
        == 200
    )
    assert service.update.await_args.args[2] == "private"
    assert (
        client.patch(
            f"/api/v1/tools/threads/runs/{run.id}", json={"visibility": "unlisted"}
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f"/api/v1/tools/threads/runs/{run.id}",
            json={"visibility": "public", "owner_id": str(uuid4())},
        ).status_code
        == 422
    )
    assert client.delete(f"/api/v1/tools/threads/runs/{run.id}").status_code == 202
    service.delete.assert_awaited_once()
