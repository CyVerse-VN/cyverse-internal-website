# Repository Instructions

## Scope and instruction priority

- These instructions apply to the entire repository.
- More specific `AGENTS.md` files may add rules for their directory scope.
- Follow explicit task requirements while preserving the security requirements in this file.
- Read the relevant files in `docs` before changing architecture, module boundaries, or data flows.
- Preserve existing user changes and avoid modifying unrelated files.

## Language

- Use English for source code, identifiers, filenames, directory names, comments, docstrings, configuration comments, test names, logs, API messages, and user-interface text.
- Vietnamese is allowed only in files under `docs/**` and in `README` files so that users can understand the project more easily.
- Keep technical names, commands, paths, environment variables, and code examples unchanged when writing Vietnamese documentation.
- Write commit messages in English when the user explicitly asks for commits.

## Architecture and design

- Keep frontend code in `apps/web` and backend code in `apps/backend`.
- Keep API handlers and UI components thin.
- Put business logic in services, features, domain modules, or focused reusable utilities.
- Prefer small, cohesive functions and modules with one clear responsibility.
- Reuse existing utilities and abstractions before creating new ones.
- Extract shared logic only when it represents a stable concept or has a clear second use case.
- Avoid speculative abstractions, unnecessary design patterns, and unrelated refactors.
- Keep business logic independent from frameworks where practical.
- Use explicit types at public APIs and module boundaries.
- Avoid `any`, broad exception handling, and silent error suppression.
- Do not add `eslint-disable`, `noqa`, or type-ignore directives without a brief justification.
- Prefer clear, maintainable code over clever or overly compressed code.

## Comments and documentation

- Write code comments and docstrings in concise English.
- Explain intent, constraints, or non-obvious tradeoffs rather than restating the code.
- Do not comment obvious assignments, control flow, or function calls.
- Remove or update stale comments when behavior changes.
- Update the relevant `.env.example` whenever an environment variable is added, renamed, or removed.
- Update architecture documentation when module boundaries or data flows change.

## Dependencies and runtime versions

- Use Node.js 24.21.0, pnpm 12.4.0, and Python 3.13.15.
- Use pnpm for JavaScript dependencies and uv for Python dependencies.
- Do not use npm, yarn, pip, Poetry, or another package manager for project dependencies.
- Do not manually edit `pnpm-lock.yaml` or `uv.lock`.
- Do not change runtime versions or approved framework version lines unless explicitly requested.
- Add dependencies only when the standard library, platform APIs, or installed packages cannot reasonably solve the task.
- Update the relevant manifest and generated lockfile together.

## Security and safe operations

- Never commit, print, expose, or log secrets, credentials, tokens, private keys, or personal data.
- Never place server-side secrets in `NEXT_PUBLIC_*` variables.
- Validate untrusted input at API, database, file, and external-service boundaries.
- Enforce authentication and authorization on the server.
- Use parameterized database queries and avoid dynamic code execution such as `eval`.
- Do not weaken security controls to make a command pass.
- Do not perform destructive database, Git, deployment, or infrastructure operations unless explicitly requested.
- Do not contact production services or mutate production data during development or testing.
- Review new dependencies for necessity, maintenance status, license, and known security concerns.

## Testing and verification

- Add or update meaningful tests for changed behavior.
- Test observable behavior instead of implementation details.
- Do not add trivial tests solely to increase coverage.
- Run checks relevant to the changed area before completing a task.
- Report which checks were run and clearly state any checks that could not be run.

Frontend checks:

- `pnpm lint:web`
- `pnpm test:web`
- `pnpm build:web`

Backend checks:

- `pnpm lint:backend`
- `pnpm test:backend`

On Windows PowerShell, use `pnpm.cmd` when script execution is restricted.

## Git discipline

- Do not commit generated files, local environment files, dependency directories, or build output.
- Do not create commits, rewrite history, force-push, or delete branches unless explicitly requested.
- Keep changes focused on the requested task.
- Do not discard or overwrite unrelated user changes.
