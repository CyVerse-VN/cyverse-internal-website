from pydantic import BaseModel, Field


class NotebookImportConfig(BaseModel):
    match_threshold: float = Field(default=0.85, ge=0, le=1)
    max_pdf_bytes: int = Field(default=25 * 1024 * 1024, ge=1024)
    max_redirects: int = Field(default=5, ge=0, le=10)
    fetch_timeout_seconds: float = Field(default=30, ge=5, le=120)
    worker_poll_seconds: float = Field(default=2, ge=0.2, le=30)
    worker_restart_seconds: float = Field(default=5, ge=1, le=60)
    worker_lease_seconds: int = Field(default=300, ge=60, le=3600)
    worker_max_attempts: int = Field(default=2, ge=1, le=5)
    worker_advisory_lock_id: int = 724992
    processing_timeout_seconds: int = Field(default=300, ge=30, le=1800)


notebook_import_config = NotebookImportConfig()
