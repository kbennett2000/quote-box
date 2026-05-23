# CLAUDE.md

## Project overview

`quote-box` is a self-hosted, LAN-only web app for browsing, managing, and displaying a personal collection of ~346 quotes. Seeded from `data/quotes.json` into SQLite on first run. Built for non-technical users; install must work without prior Python/Linux experience. Full feature spec in `SPEC.md`.

## Hard rules

- 100% offline at runtime. No CDN, no Google Fonts, no remote calls, no telemetry.
- Bind to `0.0.0.0`. Never `localhost` / `127.0.0.1`.
- Port from `config.json` only. Default `8035`. Never hardcoded elsewhere.
- No build step. No npm, no bundlers.
- `data/quotes.json` is read-only at runtime. Persistence lives in SQLite.
- Slug IDs are stable across edits.
- Service runs as user `quote-box`, never root.
- Seed only when the `quotes` table is empty. Idempotent.
- Parameterized SQL only (`?` placeholders). Never string-format SQL.

## Tech stack

- Python 3.10+
- Flask 3.x + Jinja2
- SQLite via stdlib `sqlite3` (no ORM)
- Vanilla JS (ES6+ modules), vanilla CSS
- pytest for tests; `mypy --strict` for typechecking
- black for formatting (line length 100)
- systemd for autostart

## Architecture

- App factory in `app/main.py`
- HTML page routes in `app/routes/pages.py`
- JSON API in `app/routes/{quotes,tags,profiles,notes}_api.py`
- DB schema in `app/db.py`; seed logic in `app/seed.py`; ID generation in `app/ids.py`
- Templates in `app/templates/` (Jinja2)
- Static assets in `app/static/{css,js,fonts,img}/` — all self-hosted
- Config at `config.json` (project root); template at `config.example.json`
- SQLite at `data/quotes.db`; seed at `data/quotes.json`
- Backups in `backups/` (created by `backup.sh`)
- User-facing docs in `docs/{install,user-guide,troubleshooting,admin}.md`; screenshots in `docs/screenshots/`
- ADRs in `adr/` — one Markdown file per decision (context, options, decision, consequences)
- Tests in `tests/test_*.py`; shared fixtures (in-memory SQLite, sample data) in `tests/conftest.py`
- Install/uninstall/backup scripts at project root: `install.sh`, `uninstall.sh`, `backup.sh`
- systemd unit template: `quote-box.service`

## Conventions

**File naming**
- Python: `snake_case.py`
- Templates: `snake_case.html`
- JS / CSS: `kebab-case.{js,css}`
- One JS module per page (`browse.js`, `display.js`, `quote-form.js`)

**Python**
- PEP 8, black, line length 100
- Type hints on all functions. `mypy --strict app/` must pass before a task is complete.
- Plain functions over classes unless state needs encapsulating
- Imports: stdlib → third-party → local; alphabetized within each group
- Errors: use Flask `abort(404)` etc.; never swallow exceptions silently

**JS**
- ES6+ modules: `<script type="module">`
- `fetch()` for AJAX; API returns JSON
- `data-*` attributes for behavior hooks, not CSS classes
- No frameworks, no jQuery

**CSS**
- CSS custom properties for theming (`--color-bg`, `--color-text`, …)
- One file per component or page area; single `app.css` entry imports them
- Dark theme for display mode, light for app

**HTTP**
- HTML pages: `/`, `/quotes/:id`, `/quotes/new`, `/quotes/:id/edit`, `/tags`, `/profile`, `/display`
- JSON API under `/api/*`; correct status codes (200/201/204/400/404)
- No CSRF tokens (LAN only, no auth) — document this in `admin.md`

**DB**
- Schema applied via `CREATE TABLE IF NOT EXISTS` at startup
- Schema versioning via a `schema_version` table; bump + migrate on change
- Cascade deletes for notes and tag joins

## Locked decisions

- Name: `quote-box`
- Multiple notes per profile per quote
- Free-form tag creation
- Users can edit any tag
- Display rotation duration: config default, per-session slider override, `?duration=N` URL param
- Install script auto-creates `quote-box` system user
- `backup.sh` writes timestamped copies to `backups/`
- Other profiles' notes visible read-only; only own editable
- Hard delete with confirm; cascade to notes and tag joins
- No Markdown in notes — plain text only

## Out of scope for v1

- Authentication, passwords, sessions beyond a profile cookie
- HTTPS / TLS
- Public-facing deployment
- Mobile apps (responsive web is enough)
- Real-time collaboration / websockets
- Full-text search index (SQL `LIKE` is enough at this scale)
- Tag auto-suggestion / ML-based tagging
- Quote attribution verification
- Import from other formats (CSV, RSS, …)
- Export beyond a DB file copy
- API rate limiting
- Audit log of edits
- Soft delete / undo
- Email or push notifications

## Git workflow

After any code change is complete and verified (tests pass / lint clean / feature works), do the following without being asked:

1. `git add -A` to stage all changes
2. Commit with a concise conventional-commit message
   (e.g. `feat: add user auth middleware`, `fix: handle empty cart edge case`,
   `refactor: extract validation into shared module`, `docs: update README`)
3. `git push` to push to origin/main

Commit at logical checkpoints — a complete feature, a bug fix, a refactor — not after every individual file edit. If a task spans multiple commits, make each commit independently meaningful and atomic.

If `git push` fails (auth, conflict, network), surface the full error to the user immediately. Do not retry silently or attempt destructive resolutions (no `--force`, no resetting branches).

Never commit secrets, API keys, .env files, or anything matching .gitignore.

## Engineering principles

### Tests are required, not optional
- Every new feature, bug fix, or non-trivial change ships with tests.
- For new functionality, prefer test-first: write the test from the spec, then implement until it passes.
- A task is not "done" until the relevant tests pass. Do not report completion with failing or skipped tests.
- When fixing a bug, first write a test that reproduces the bug (and fails), then fix it. This prevents regressions.
- Keep the test suite fast. If a test is slow, isolate it (mark as integration or e2e) so the default `test` command stays under 10 seconds for unit tests.

### Tight feedback loops
- Use strict typing everywhere (TypeScript strict mode / Pydantic / Zod — whatever the stack supports). Type errors should surface immediately.
- Run lint and typecheck before declaring a task complete.
- Add structured logging at module boundaries from day one. When something breaks, logs should narrow the cause in seconds, not minutes.
- If a change requires manual verification (UI, integrations), state exactly what to check and how — don't leave it implicit.

### Spec before code for non-trivial work
- For any task touching 3+ files, introducing a new module, or changing a contract between components: produce a spec FIRST in plan mode. Do not start editing until the user has approved the plan.
- For significant architectural decisions, write a short ADR (Architecture Decision Record) in `/adr/` capturing: context, options considered, decision, consequences. Reference the ADR in commit messages.
- Read `/docs/`, `/adr/`, and `SPEC.md` before starting work. Those files describe intent; the code describes implementation. Both matter.

### Taste and restraint
- Prefer the simplest solution that solves the problem. Resist adding abstraction, config options, or framework features that aren't justified by an actual requirement.
- If a diff is getting large, stop and ask whether the task should be decomposed into smaller commits.
- Reuse existing patterns in the codebase before inventing new ones.
