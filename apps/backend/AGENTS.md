# Backend Instructions

- Follow the repository-level `AGENTS.md`.
- Keep FastAPI route handlers limited to validation, authorization, orchestration, and response mapping.
- Put business logic in services or domain modules.
- Put database access in repositories or the database layer.
- Do not import FastAPI request or response objects into business services.
- Use Pydantic schemas at API and external-integration boundaries.
- Use type annotations for public functions and methods.
- Use async I/O in async request paths and avoid blocking operations.
- Raise domain-specific exceptions and map them centrally.
- Use timezone-aware UTC timestamps.
- Never log access tokens, API keys, passwords, or complete sensitive payloads.
- Add an Alembic migration for every database schema change.
- Keep external providers behind interfaces or adapters.
- Mock external APIs in unit tests.
- Add pytest tests for changed backend behavior.
