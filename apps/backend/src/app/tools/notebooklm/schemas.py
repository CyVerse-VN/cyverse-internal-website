from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class PaperSeed(BaseModel):
    title: str = Field(min_length=1, max_length=1000)
    authors: list[str] = Field(default_factory=list, max_length=50)
    year: int | None = Field(default=None, ge=1800, le=2100)
    doi: str | None = Field(default=None, max_length=300)
    arxiv_id: str | None = Field(default=None, max_length=100)
    landing_url: str | None = Field(default=None, max_length=2048)
    pdf_url: str | None = Field(default=None, max_length=2048)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        result = " ".join(value.split())
        if not result:
            raise ValueError("Title cannot be blank")
        return result

    @field_validator("authors")
    @classmethod
    def clean_authors(cls, value: list[str]) -> list[str]:
        return [name for author in value if (name := " ".join(author.split()))][:50]


class BrowserCookie(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    value: str = Field(min_length=1, max_length=8192)
    domain: str = Field(min_length=1, max_length=256)
    path: str = Field(default="/", max_length=256)

    @field_validator("name")
    @classmethod
    def auth_cookie_name(cls, value: str) -> str:
        if value not in {
            "APISID", "LSID", "OSID", "SAPISID", "SID",
            "__Secure-1PSIDTS", "__Secure-3PSIDTS",
        }:
            raise ValueError("Only NotebookLM authentication cookies are accepted")
        return value

    @field_validator("domain")
    @classmethod
    def google_domain(cls, value: str) -> str:
        domain = value.lower().lstrip(".")
        if domain != "google.com" and not domain.endswith(".google.com"):
            raise ValueError("Only Google cookies are accepted")
        return value.lower()


class BrowserSessionRequest(BaseModel):
    cookies: list[BrowserCookie] = Field(min_length=1, max_length=80)

    @model_validator(mode="after")
    def limit_cookie_payload(self) -> "BrowserSessionRequest":
        if (
            sum(
                len(cookie.name) + len(cookie.domain) + len(cookie.path) + len(cookie.value)
                for cookie in self.cookies
            )
            > 65536
        ):
            raise ValueError("Google session payload is too large")
        return self


class SelectedSessionRequest(BrowserSessionRequest):
    account_email: str = Field(max_length=320, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class NotebookAccount(BaseModel):
    email: str
    authuser: int


class NotebookAccountsResponse(BaseModel):
    items: list[NotebookAccount]


class CreateImportRequest(SelectedSessionRequest):
    notebook_id: str = Field(min_length=1, max_length=200)
    paper: PaperSeed
    source: Literal["google_scholar"]


class NotebookItem(BaseModel):
    id: str
    title: str


class NotebookListResponse(BaseModel):
    account_email: str
    items: list[NotebookItem]


class ImportResponse(BaseModel):
    id: UUID
    notebook_id: str
    account_email: str | None
    paper: PaperSeed
    status: str
    current_stage: str
    source_id: str | None
    error: dict[str, str] | None
    created_at: datetime
    updated_at: datetime
