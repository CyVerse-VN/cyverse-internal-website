from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1.notebooklm import get_notebook_import_service
from app.auth.dependencies import get_current_user
from app.main import create_app
from app.tools.notebooklm.schemas import (
    ImportResponse,
    NotebookAccount,
    NotebookItem,
    NotebookListResponse,
    PaperSeed,
)


def test_notebook_routes_require_login() -> None:
    client = TestClient(create_app())
    assert client.post("/api/v1/tools/notebooklm/accounts/discover", json={}).status_code == 401
    assert client.post("/api/v1/tools/notebooklm/notebooks", json={}).status_code == 401
    assert client.post("/api/v1/tools/notebooklm/imports", json={
        "notebook_id": "notebook-1", "source": "google_scholar",
        "paper": {"title": "Paper"},
    }).status_code == 401
    assert client.get(f"/api/v1/tools/notebooklm/imports/{uuid4()}").status_code == 401


def test_browser_session_cannot_be_replaced_via_api() -> None:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4(), role="member")
    client = TestClient(app)
    assert client.post("/api/v1/tools/notebooklm/auth/login-window").status_code == 404
    assert client.post("/api/v1/tools/notebooklm/auth/cookies", json={"cookies": []}).status_code == 404


def test_notebook_routes_accept_member_and_return_queued_job() -> None:
    user = SimpleNamespace(id=uuid4(), role="member")
    now = datetime.now(UTC)
    response = ImportResponse(
        id=uuid4(), notebook_id="notebook-1",
        account_email="alice@gmail.com",
        paper=PaperSeed(title="Paper", authors=["Alice"], year=2025),
        status="queued", current_stage="queued", source_id=None,
        error=None, created_at=now, updated_at=now,
    )
    service = SimpleNamespace(
        discover=AsyncMock(return_value=[NotebookAccount(email="alice@gmail.com", authuser=0)]),
        list_notebooks=AsyncMock(return_value=NotebookListResponse(account_email="alice@gmail.com", items=[
            NotebookItem(id="notebook-1", title="Shared")
        ])),
        create=AsyncMock(return_value=response),
        get=AsyncMock(return_value=response),
    )
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_notebook_import_service] = lambda: service
    client = TestClient(app)

    cookies = [{"name": "SID", "value": "example", "domain": ".google.com", "path": "/"}]
    accounts = client.post("/api/v1/tools/notebooklm/accounts/discover", json={"cookies": cookies})
    notebooks = client.post("/api/v1/tools/notebooklm/notebooks", json={
        "cookies": cookies, "account_email": "alice@gmail.com",
    })
    created = client.post(
        "/api/v1/tools/notebooklm/imports",
        headers={"Idempotency-Key": "paper-import-1"},
        json={
            "notebook_id": "notebook-1", "source": "google_scholar",
            "cookies": cookies, "account_email": "alice@gmail.com",
            "paper": {"title": "Paper", "authors": ["Alice"], "year": 2025},
        },
    )
    fetched = client.get(f"/api/v1/tools/notebooklm/imports/{response.id}")

    assert accounts.status_code == 200
    assert accounts.json()["items"] == [{"email": "alice@gmail.com", "authuser": 0}]
    assert notebooks.status_code == 200
    assert notebooks.json()["account_email"] == "alice@gmail.com"
    assert notebooks.json()["items"] == [{"id": "notebook-1", "title": "Shared"}]
    assert created.status_code == 202
    assert created.json()["id"] == str(response.id)
    assert fetched.status_code == 200
    assert service.create.await_args.args[0] is user
    assert service.create.await_args.args[2] == "paper-import-1"
    assert service.get.await_args.args == (user, response.id)
