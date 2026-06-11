# Canned interview answers — ts-monorepo fixture

1. **Project description:** acme is an npm-workspaces monorepo of TypeScript
   utility libraries. The first package, `@acme/slugify`, exports `slugify`,
   which turns a title into a URL slug. Consumed as source-level library
   imports by other packages.
2. **Domain terms:** Slug (the normalized URL token), Title (the raw input
   string), Package (one workspace under `packages/`), Workspace (the npm
   workspaces root), Separator (the `-` joining slug words). No recurring
   wrong names yet — leave the debt column empty.
3. **Vocabulary polarity:** embrace — it is a product; use domain terms freely.
4. **API surface:** no external API contract to manage — the exported functions
   are plain library imports; no HTTP, no RPC, no Contracts section needed.
5. **Gate commands:** `npx tsc --noEmit` and `npx vitest run` (the configured
   tools; no eslint config exists).
6. **Parallel agents:** no — solo development on this machine.
7. **Unit of work:** not applicable — a library, no Logging section.
8. **First epic:** Epic 0 — Ship slugify (the first workspace package builds,
   tests, and is gated).
