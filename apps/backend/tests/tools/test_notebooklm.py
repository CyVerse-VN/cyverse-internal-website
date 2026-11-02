from contextlib import asynccontextmanager
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.notebook_import import NotebookImport
from app.tools.notebooklm.errors import NotebookImportError
from app.tools.notebooklm.pdf import download_pdf, resolve_public_addresses, validate_url
from app.tools.notebooklm.provider import NotebookLMPyProvider, storage_json, temporary_storage
from app.tools.notebooklm.repository import NotebookImportRepository
from app.tools.notebooklm.resolver import PaperResolver, match_score
from app.tools.notebooklm.schemas import (
    BrowserCookie,
    CreateImportRequest,
    NotebookAccount,
    NotebookItem,
    PaperSeed,
)
from app.tools.notebooklm.service import NotebookImportService
from app.tools.notebooklm.session import decrypt_session, encrypt_session
from app.tools.research.domain import PaperCandidate


def seed(**values: object) -> PaperSeed:
    return PaperSeed.model_validate({
        "title": "Reliable Academic Paper",
        "authors": ["Alice Researcher"],
        "year": 2025,
        **values,
    })


def candidate(**values: object) -> PaperCandidate:
    return PaperCandidate.model_validate({
        "source": "semantic_scholar",
        "source_rank": 1,
        "title": "Reliable Academic Paper",
        "authors": ["Alice Researcher"],
        "year": 2025,
        "pdf_url": "https://example.org/paper.pdf",
        **values,
    })


def session_cookies() -> list[BrowserCookie]:
    return [BrowserCookie(name="SID", value="test", domain=".google.com", path="/")]


def import_request(notebook_id: str = "notebook-1") -> CreateImportRequest:
    return CreateImportRequest(
        notebook_id=notebook_id, source="google_scholar", paper=seed(),
        account_email="alice@gmail.com", cookies=session_cookies(),
    )


def test_browser_session_rejects_non_google_cookie_domains() -> None:
    with pytest.raises(ValueError, match="Only Google cookies"):
        BrowserCookie(name="SID", value="secret", domain="attacker.example", path="/")
    with pytest.raises(ValueError, match="Only NotebookLM authentication cookies"):
        BrowserCookie(name="NID", value="tracking", domain=".google.com", path="/")


def test_matching_rejects_conflicting_identifier_and_weak_metadata() -> None:
    assert match_score(seed(doi="10.1/a"), candidate(doi="10.1/b")) == 0
    assert match_score(seed(doi="10.1/a"), candidate(doi="10.1/a", year=2010)) == 0
    assert match_score(seed(doi="10.1/a"), candidate(doi="10.1/a", authors=["Other Person"])) == 0
    assert match_score(seed(), candidate(title="Unrelated Work")) == 0
    assert match_score(seed(), candidate()) >= 0.85
    assert match_score(seed(authors=[], year=None), candidate()) == 0


@pytest.mark.asyncio
async def test_direct_pdf_skips_search() -> None:
    assert await PaperResolver().resolve(seed(pdf_url="https://example.org/a.pdf")) == (
        "https://example.org/a.pdf"
    )


@pytest.mark.asyncio
async def test_arxiv_identifier_precedes_search() -> None:
    assert await PaperResolver().resolve(seed(arxiv_id="2501.12345")) == (
        "https://arxiv.org/pdf/2501.12345"
    )


@pytest.mark.asyncio
async def test_doi_search_ignores_first_unrelated_result(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.tools.notebooklm.resolver as resolver_module

    semantic = SimpleNamespace(search=AsyncMock(return_value=[
        candidate(title="Another Research Topic", doi="10.1234/right"),
        candidate(doi="10.1234/right", pdf_url="https://example.org/right.pdf"),
    ]))
    openalex = SimpleNamespace(search=AsyncMock(return_value=[]))
    arxiv = SimpleNamespace(search=AsyncMock(return_value=[]))
    monkeypatch.setattr(resolver_module, "SemanticScholarSource", lambda _client: semantic)
    monkeypatch.setattr(resolver_module, "OpenAlexSource", lambda _client: openalex)
    monkeypatch.setattr(resolver_module, "ArxivSource", lambda _client: arxiv)
    assert await PaperResolver().resolve(seed(doi="10.1234/right")) == (
        "https://example.org/right.pdf"
    )
    semantic.search.assert_awaited_once()
    openalex.search.assert_not_awaited()


def test_pdf_url_rejects_unsafe_schemes_and_private_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(NotebookImportError, match="allowed public HTTP"):
        validate_url("file:///etc/passwd")
    monkeypatch.setattr(
        "app.tools.notebooklm.pdf.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(2, 1, 0, "", ("127.0.0.1", 80))],
    )
    with pytest.raises(NotebookImportError) as caught:
        resolve_public_addresses("internal.example", 80)
    assert caught.value.code == "UNSAFE_PDF_URL"


@pytest.mark.parametrize(
    ("content_type", "body", "expected"),
    [
        ("text/html", b"<html>login</html>", "INVALID_PDF"),
        ("application/pdf", b"<html>login</html>", "INVALID_PDF"),
        (None, b"%PDF-1.7\n", "INVALID_PDF"),
    ],
)
def test_pdf_download_rejects_html(
    monkeypatch: pytest.MonkeyPatch, tmp_path, content_type: str | None, body: bytes,
    expected: str,
) -> None:
    import app.tools.notebooklm.pdf as pdf_module

    class FakeResponse:
        status = 200

        def __init__(self) -> None:
            self.stream = BytesIO(body)

        def getheader(self, name: str):
            return content_type if name == "Content-Type" else None

        def read(self, amount: int) -> bytes:
            return self.stream.read(amount)

    monkeypatch.setattr(pdf_module, "_request_pinned", lambda *_args: (
        SimpleNamespace(sock=None, close=lambda: None), FakeResponse()
    ))
    monkeypatch.setattr(pdf_module.tempfile, "tempdir", str(tmp_path))
    with pytest.raises(NotebookImportError) as caught:
        download_pdf("https://example.org/paper.pdf")
    assert caught.value.code == expected
    assert not list(tmp_path.iterdir())


def test_pdf_download_accepts_valid_pdf(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    import app.tools.notebooklm.pdf as pdf_module

    payload = b"%PDF-1.7\nvalid test data"

    class FakeResponse:
        status = 200

        def __init__(self) -> None:
            self.stream = BytesIO(payload)

        def getheader(self, name: str):
            return "application/pdf" if name == "Content-Type" else None

        def read(self, amount: int) -> bytes:
            return self.stream.read(amount)

    monkeypatch.setattr(pdf_module, "_request_pinned", lambda *_args: (
        SimpleNamespace(sock=None, close=lambda: None), FakeResponse()
    ))
    monkeypatch.setattr(pdf_module.tempfile, "tempdir", str(tmp_path))
    path = download_pdf("https://example.org/paper.pdf")
    try:
        assert path.read_bytes() == payload
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.parametrize(
    ("status", "headers", "body", "expected"),
    [
        (403, {}, b"", "PDF_UNAVAILABLE"),
        (200, {"Content-Type": "application/pdf", "Content-Length": "100"}, b"", "PDF_TOO_LARGE"),
        (200, {"Content-Type": "application/pdf"}, b"%PDF-" + b"x" * 100, "PDF_TOO_LARGE"),
    ],
)
def test_pdf_rejects_denied_and_oversized_downloads(
    monkeypatch: pytest.MonkeyPatch, tmp_path, status: int,
    headers: dict[str, str], body: bytes, expected: str,
) -> None:
    import app.tools.notebooklm.pdf as pdf_module

    class FakeResponse:
        def __init__(self) -> None:
            self.status = status
            self.stream = BytesIO(body)

        def getheader(self, name: str):
            return headers.get(name)

        def read(self, amount: int) -> bytes:
            return self.stream.read(amount)

    monkeypatch.setattr(pdf_module, "_request_pinned", lambda *_args: (
        SimpleNamespace(sock=None, close=lambda: None), FakeResponse()
    ))
    monkeypatch.setattr(pdf_module.tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(pdf_module.notebook_import_config, "max_pdf_bytes", 50)
    with pytest.raises(NotebookImportError) as caught:
        download_pdf("https://example.org/paper.pdf")
    assert caught.value.code == expected
    assert not list(tmp_path.iterdir())


def test_redirect_rechecks_private_target(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.tools.notebooklm.pdf as pdf_module

    class Redirect:
        status = 302

        def getheader(self, name: str):
            return "http://internal.example/paper.pdf" if name == "Location" else None

    calls = []

    def request(url: str, _deadline: float):
        calls.append(url)
        if len(calls) == 1:
            return SimpleNamespace(close=lambda: None), Redirect()
        pdf_module.resolve_public_addresses("internal.example", 80)
        raise AssertionError("Private address must be rejected")

    monkeypatch.setattr(pdf_module, "_request_pinned", request)
    monkeypatch.setattr(pdf_module.socket, "getaddrinfo", lambda *_a, **_k: [
        (2, 1, 0, "", ("127.0.0.1", 80))
    ])
    with pytest.raises(NotebookImportError) as caught:
        download_pdf("https://example.org/paper.pdf")
    assert caught.value.code == "UNSAFE_PDF_URL"
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_invalid_notebook_id_is_rejected_before_job_creation() -> None:
    repository = SimpleNamespace(create=AsyncMock())
    provider = SimpleNamespace(discover=AsyncMock(return_value=[
        NotebookAccount(email="alice@gmail.com", authuser=0)
    ]), list_notebooks=AsyncMock(return_value=[
        NotebookItem(id="valid", title="Shared")
    ]))
    service = NotebookImportService(repository, provider)
    request = import_request("missing")
    with pytest.raises(NotebookImportError) as caught:
        await service.create(SimpleNamespace(id=uuid4()), request, "a-valid-key")
    assert caught.value.code == "NOTEBOOK_NOT_FOUND"
    repository.create.assert_not_called()


@pytest.mark.asyncio
async def test_idempotency_reuses_identical_job_and_rejects_changed_input() -> None:
    user = SimpleNamespace(id=uuid4())
    request = import_request()
    run = SimpleNamespace(id=uuid4(), tool_name="notebooklm")
    item = SimpleNamespace(notebook_id="notebook-1", account_email="alice@gmail.com", paper=seed().model_dump(mode="json"))
    session = AsyncMock()
    session.scalar.side_effect = [run, item, run, item]
    repository = NotebookImportRepository(session)
    assert await repository._existing(user, request, "repeat-key") is item
    changed = request.model_copy(update={"notebook_id": "notebook-2"})
    with pytest.raises(NotebookImportError) as caught:
        await repository._existing(user, changed, "repeat-key")
    assert caught.value.code == "IDEMPOTENCY_CONFLICT"


@pytest.mark.asyncio
async def test_member_import_lookup_is_scoped_to_owner() -> None:
    session = AsyncMock()
    session.scalar.return_value = None
    repository = NotebookImportRepository(session)
    with pytest.raises(NotebookImportError) as caught:
        await repository.get(uuid4(), SimpleNamespace(id=uuid4(), role="member"))
    query = str(session.scalar.await_args.args[0])
    assert "tool_runs.owner_id" in query
    assert caught.value.code == "IMPORT_NOT_FOUND"

    with pytest.raises(NotebookImportError):
        await repository.get(uuid4(), SimpleNamespace(id=uuid4(), role="admin"))
    admin_query = str(session.scalar.await_args.args[0])
    assert "tool_runs.owner_id" not in admin_query


def test_selected_session_is_scoped_and_encrypted() -> None:
    from notebooklm.auth import get_account_email_for_storage, get_authuser_for_storage

    content = storage_json(session_cookies(), NotebookAccount(email="alice@gmail.com", authuser=1))
    ciphertext = encrypt_session(content)
    assert "alice@gmail.com" not in ciphertext
    assert decrypt_session(ciphertext) == content
    with temporary_storage(content) as path:
        assert path.is_file()
        assert path.read_text(encoding="utf-8") == content
        assert get_authuser_for_storage(path) == 1
        assert get_account_email_for_storage(path) == "alice@gmail.com"
    assert not path.exists()


@pytest.mark.asyncio
async def test_email_must_match_verified_browser_account() -> None:
    provider = SimpleNamespace(discover=AsyncMock(return_value=[
        NotebookAccount(email="alice@gmail.com", authuser=0)
    ]), list_notebooks=AsyncMock())
    service = NotebookImportService(SimpleNamespace(), provider)
    with pytest.raises(NotebookImportError) as caught:
        await service.list_notebooks(session_cookies(), "bob@gmail.com")
    assert caught.value.code == "NOTEBOOKLM_ACCOUNT_MISMATCH"
    provider.list_notebooks.assert_not_awaited()


@pytest.mark.asyncio
async def test_expired_notebooklm_sdk_session_has_explicit_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from notebooklm import AuthError, NotebookLMClient

    def expired(*_args, **_kwargs):
        raise AuthError("expired")

    monkeypatch.setattr(NotebookLMClient, "from_storage", staticmethod(expired))
    with pytest.raises(NotebookImportError) as caught:
        await NotebookLMPyProvider().list_notebooks("{}")
    assert caught.value.code == "NOTEBOOKLM_AUTH_EXPIRED"


@pytest.mark.asyncio
async def test_stale_upload_without_source_is_never_requeued() -> None:
    run = SimpleNamespace(current_stage="uploading", source_id=None, attempt_count=1)
    item = SimpleNamespace(run=run, source_id=None)
    session = AsyncMock()
    session.scalars.return_value = SimpleNamespace(all=lambda: [item])
    repository = NotebookImportRepository(session)
    repository.fail = AsyncMock()
    await repository.recover_stale(300, 2)
    assert repository.fail.await_args.args[1].code == "UPLOAD_OUTCOME_UNKNOWN"
    assert NotebookImport.__tablename__ == "notebooklm_imports"


@pytest.mark.asyncio
async def test_worker_records_stages_and_removes_temporary_pdf(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    import app.workers.notebooklm as worker_module

    path = tmp_path / "paper.pdf"
    path.write_bytes(b"%PDF-1.7\n")
    run = SimpleNamespace(current_stage="resolving")
    item = SimpleNamespace(
        paper=seed().model_dump(mode="json"), notebook_id="nb-1", source_id=None,
        run=run, run_id=uuid4(), session_ciphertext=encrypt_session("{}"),
    )
    stages: list[str] = []
    repository = SimpleNamespace(
        recover_stale=AsyncMock(), claim_next=AsyncMock(return_value=item),
        complete=AsyncMock(), fail=AsyncMock(),
    )

    async def transition(_item, stage, _progress, _message, **values):
        stages.append(stage)
        run.current_stage = stage
        if "source_id" in values:
            item.source_id = values["source_id"]

    repository.transition = transition

    @asynccontextmanager
    async def session_factory():
        yield SimpleNamespace(rollback=AsyncMock(), get=AsyncMock(return_value=item.run))

    monkeypatch.setattr(worker_module, "async_session_factory", session_factory)
    monkeypatch.setattr(worker_module, "NotebookImportRepository", lambda _session: repository)
    monkeypatch.setattr(worker_module, "download_pdf", lambda _url: path)

    async def ready(_storage: str, _notebook_id: str, _source_id: str) -> None:
        assert not path.exists()

    provider = SimpleNamespace(
        add_file=AsyncMock(return_value="source-1"), wait_ready=AsyncMock(side_effect=ready)
    )
    worker = worker_module.NotebookImportWorker(provider)
    worker.resolver = SimpleNamespace(resolve=AsyncMock(return_value="https://example.org/paper.pdf"))
    assert await worker.run_once() is True
    assert stages == ["downloading", "uploading", "processing"]
    provider.wait_ready.assert_awaited_once_with("{}", "nb-1", "source-1")
    repository.complete.assert_awaited_once_with(item)
    assert not path.exists()


@pytest.mark.asyncio
async def test_worker_marks_unknown_if_source_id_cannot_be_persisted(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    import app.workers.notebooklm as worker_module

    path = tmp_path / "paper.pdf"
    path.write_bytes(b"%PDF-1.7\n")
    item = SimpleNamespace(
        paper=seed().model_dump(mode="json"), notebook_id="nb-1", source_id=None,
        run=SimpleNamespace(current_stage="resolving"), run_id=uuid4(), session_ciphertext=encrypt_session("{}"),
    )
    repository = SimpleNamespace(
        recover_stale=AsyncMock(), claim_next=AsyncMock(return_value=item),
        complete=AsyncMock(), fail=AsyncMock(),
    )

    async def transition(_item, stage, _progress, _message, **_values):
        item.run.current_stage = stage
        if stage == "processing":
            raise RuntimeError("Database write failed after upload")

    repository.transition = transition

    @asynccontextmanager
    async def session_factory():
        yield SimpleNamespace(rollback=AsyncMock(), get=AsyncMock(return_value=item.run))

    monkeypatch.setattr(worker_module, "async_session_factory", session_factory)
    monkeypatch.setattr(worker_module, "NotebookImportRepository", lambda _session: repository)
    monkeypatch.setattr(worker_module, "download_pdf", lambda _url: path)
    provider = SimpleNamespace(
        add_file=AsyncMock(return_value="source-1"), wait_ready=AsyncMock()
    )
    worker = worker_module.NotebookImportWorker(provider)
    worker.resolver = SimpleNamespace(resolve=AsyncMock(return_value="https://example.org/paper.pdf"))
    assert await worker.run_once() is True
    assert repository.fail.await_args.args[1].code == "UPLOAD_OUTCOME_UNKNOWN"
    provider.wait_ready.assert_not_awaited()
    assert not path.exists()


@pytest.mark.asyncio
async def test_worker_keeps_upload_auth_failure_ambiguous(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    import app.workers.notebooklm as worker_module

    path = tmp_path / "paper.pdf"
    path.write_bytes(b"%PDF-1.7\n")
    item = SimpleNamespace(
        paper=seed().model_dump(mode="json"), notebook_id="nb-1", source_id=None,
        run=SimpleNamespace(current_stage="resolving"), run_id=uuid4(), session_ciphertext=encrypt_session("{}"),
    )
    repository = SimpleNamespace(
        recover_stale=AsyncMock(), claim_next=AsyncMock(return_value=item),
        transition=AsyncMock(), complete=AsyncMock(), fail=AsyncMock(),
    )

    @asynccontextmanager
    async def session_factory():
        yield SimpleNamespace(rollback=AsyncMock())

    monkeypatch.setattr(worker_module, "async_session_factory", session_factory)
    monkeypatch.setattr(worker_module, "NotebookImportRepository", lambda _session: repository)
    monkeypatch.setattr(worker_module, "download_pdf", lambda _url: path)
    provider = SimpleNamespace(add_file=AsyncMock(side_effect=NotebookImportError(
        "NOTEBOOKLM_AUTH_EXPIRED", "Session expired."
    )), wait_ready=AsyncMock())
    worker = worker_module.NotebookImportWorker(provider)
    worker.resolver = SimpleNamespace(resolve=AsyncMock(return_value="https://example.org/paper.pdf"))
    assert await worker.run_once() is True
    assert repository.fail.await_args.args[1].code == "UPLOAD_OUTCOME_UNKNOWN"
    assert not path.exists()
