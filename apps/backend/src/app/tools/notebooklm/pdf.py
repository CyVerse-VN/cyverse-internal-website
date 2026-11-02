from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
import tempfile
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from app.tools.notebooklm.config import notebook_import_config
from app.tools.notebooklm.errors import NotebookImportError


def resolve_public_addresses(host: str, port: int) -> list[tuple[int, tuple]]:
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise NotebookImportError("PDF_UNAVAILABLE", "The PDF host could not be resolved.") from exc
    if not addresses:
        raise NotebookImportError("PDF_UNAVAILABLE", "The PDF host has no address.")
    result: list[tuple[int, tuple]] = []
    for family, _, _, _, sockaddr in addresses:
        address = ipaddress.ip_address(sockaddr[0])
        if not address.is_global:
            raise NotebookImportError("UNSAFE_PDF_URL", "The PDF URL resolves to a non-public address.")
        result.append((family, sockaddr))
    return result


def validate_url(url: str) -> tuple[str, int, str]:
    try:
        parsed = urlsplit(url)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise NotebookImportError("UNSAFE_PDF_URL", "The PDF URL is invalid.") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or not 1 <= port <= 65535
    ):
        raise NotebookImportError("UNSAFE_PDF_URL", "The PDF URL is not an allowed public HTTP URL.")
    return parsed.hostname, port, parsed.scheme


def _request_pinned(url: str, deadline: float) -> tuple[http.client.HTTPConnection, http.client.HTTPResponse]:
    parsed = urlsplit(url)
    host, port, scheme = validate_url(url)
    addresses = resolve_public_addresses(host, port)
    timeout = max(0.1, min(10.0, deadline - time.monotonic()))
    if timeout <= 0.1:
        raise TimeoutError
    last_error: OSError | None = None
    for family, sockaddr in addresses:
        raw = socket.socket(family, socket.SOCK_STREAM)
        raw.settimeout(timeout)
        try:
            raw.connect(sockaddr)
            connection: http.client.HTTPConnection
            if scheme == "https":
                connection = http.client.HTTPSConnection(host, port, timeout=timeout)
                connection.sock = ssl.create_default_context().wrap_socket(raw, server_hostname=host)
            else:
                connection = http.client.HTTPConnection(host, port, timeout=timeout)
                connection.sock = raw
            path = parsed.path or "/"
            if parsed.query:
                path += f"?{parsed.query}"
            connection.request("GET", path, headers={"Accept": "application/pdf"})
            return connection, connection.getresponse()
        except (OSError, ssl.SSLError) as exc:
            raw.close()
            last_error = exc
    raise NotebookImportError("PDF_UNAVAILABLE", "The PDF host did not respond.") from last_error


def download_pdf(url: str) -> Path:
    deadline = time.monotonic() + notebook_import_config.fetch_timeout_seconds
    current_url = url
    for redirect_count in range(notebook_import_config.max_redirects + 1):
        connection: http.client.HTTPConnection | None = None
        path: Path | None = None
        completed = False
        try:
            connection, response = _request_pinned(current_url, deadline)
            if response.status in {301, 302, 303, 307, 308}:
                if redirect_count >= notebook_import_config.max_redirects:
                    raise NotebookImportError("PDF_REDIRECT_LIMIT", "The PDF redirected too many times.")
                location = response.getheader("Location")
                if not location:
                    raise NotebookImportError("PDF_UNAVAILABLE", "The PDF redirect is incomplete.")
                current_url = urljoin(current_url, location)
                validate_url(current_url)
                continue
            if response.status != 200:
                raise NotebookImportError("PDF_UNAVAILABLE", "The PDF server rejected the download.")
            content_type = (response.getheader("Content-Type") or "").split(";", 1)[0].strip().lower()
            if content_type not in {"application/pdf", "application/octet-stream"}:
                raise NotebookImportError("INVALID_PDF", "The download is not a PDF response.")
            declared_size = response.getheader("Content-Length")
            if declared_size and int(declared_size) > notebook_import_config.max_pdf_bytes:
                raise NotebookImportError("PDF_TOO_LARGE", "The PDF exceeds the size limit.")
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as output:
                path = Path(output.name)
                size = 0
                first = True
                while True:
                    if time.monotonic() >= deadline:
                        raise NotebookImportError("PDF_UNAVAILABLE", "The PDF download timed out.")
                    if connection.sock:
                        connection.sock.settimeout(max(0.1, min(5.0, deadline - time.monotonic())))
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    if first and not chunk.startswith(b"%PDF-"):
                        raise NotebookImportError("INVALID_PDF", "The download does not contain PDF data.")
                    first = False
                    size += len(chunk)
                    if size > notebook_import_config.max_pdf_bytes:
                        raise NotebookImportError("PDF_TOO_LARGE", "The PDF exceeds the size limit.")
                    output.write(chunk)
                if first:
                    raise NotebookImportError("INVALID_PDF", "The PDF is empty.")
            completed = True
            return path
        except (OSError, TimeoutError, ValueError) as exc:
            raise NotebookImportError("PDF_UNAVAILABLE", "The PDF could not be downloaded.") from exc
        finally:
            if connection is not None:
                connection.close()
            if path is not None and not completed:
                path.unlink(missing_ok=True)
    raise NotebookImportError("PDF_REDIRECT_LIMIT", "The PDF redirected too many times.")
