# Frontend Instructions

- Follow the repository-level `AGENTS.md`.
- Use Next.js App Router conventions.
- Prefer Server Components by default.
- Add `"use client"` only when browser APIs, client state, effects, or event handlers require it.
- Keep components focused on rendering and interaction.
- Put feature business logic in `src/features`.
- Put reusable hooks in `src/hooks`, API clients in `src/lib/api`, and shared UI in `src/components`.
- Reuse shared components before creating duplicate implementations.
- Keep environment access centralized and never expose secrets through `NEXT_PUBLIC_*` variables.
- Use semantic HTML and preserve keyboard and screen-reader accessibility.
- Represent loading, empty, error, and success states explicitly.
- Avoid fetching or transforming the same data independently in multiple components.
- Add Vitest tests for frontend logic and component behavior.
- Add Playwright tests for critical user flows.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
