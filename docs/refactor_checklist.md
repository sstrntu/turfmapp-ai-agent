## Refactor Compliance Checklist

Aligned with `code.md`, `PLANNING.md` (absent; using project defaults), and `TASK.md`.

### Global
- [ ] Directory layout matches documented structure (backend/app/{models,routes,services,utils}, frontend/src/{components,lib,types}).
- [ ] No source file exceeds 500 lines; large modules split logically.
- [ ] Imports are package-relative inside packages.
- [ ] Environment variables loaded via `python_dotenv` utilities; no hard-coded secrets.
- [ ] Logging handled via `rich` logger; no stray `print`.
- [ ] Tests mirror code layout; coverage includes happy path, edge, failure.
- [ ] Docs (`README.md`, `SETUP.md`, `CHANGELOG.md`) updated for structural changes.

### Backend (Python/FastAPI)
- [ ] Python 3.11 features & typing (all functions annotated).
- [ ] Google-style docstrings present on all functions/methods.
- [ ] FastAPI routes isolated under `app/routes/`; services encapsulate business logic.
- [ ] Database access via Supabase proxy utilities; no direct frontend credentials.
- [ ] Error handling uses specific exception classes; user-safe messages returned.
- [ ] Tool-processing helpers broken out of `chat_service.py` to keep modules manageable.
- [ ] Tests in `backend/tests/` cover services, routes, utilities; external calls mocked.

### Frontend (React/TypeScript/Tailwind)
- [ ] All code authored in TypeScript (`.ts`/`.tsx`); legacy `.js` migrated or isolated.
- [ ] Strict typing (no `any`); interfaces in `src/types`.
- [ ] Component hierarchy: `components/{features,ui}`, hooks in `lib`, runtime adapters typed.
- [ ] Styling via Tailwind utility classes; bespoke CSS minimized/migrated.
- [ ] API calls routed through backend endpoints; no Supabase direct access.
- [ ] Tests (Jest/Vitest) cover key adapters, components, helpers.

### Operations & Tooling
- [ ] Linting/formatting scripts configured (black, isort, eslint, prettier).
- [ ] Docker workflows documented; compose up/down instructions verified.
- [ ] Secrets scrubbed from `.env` in repo (placeholders with instructions).

### Tasks & Documentation
- [ ] `TASK.md` updated with in-progress/completed refactor items.
- [ ] Newly discovered follow-ups logged under “Discovered During Work”.
- [ ] Developer onboarding docs refreshed (folder layout, tooling commands, testing).

Use this checklist to track progress as refactors proceed; update boxes when items are verified.
