# Quotes App — Specification

## 1. Project Overview

A self-hosted, LAN-only web app for browsing, managing, and displaying a personal quote collection. Imports an existing JSON file (~346 quotes) on first run and lets users add, edit, delete, search, tag, and annotate quotes. Includes a fullscreen rotating display mode suitable for a wall-mounted screen or kiosk.

**Hard constraints**
- 100% offline after install. No internet calls at runtime — no CDNs, web fonts from Google, analytics, telemetry, update checks, anything.
- LAN only. No authentication needed. No HTTPS needed.
- Configurable port (default `8035`). Single config file.
- Must autostart on Ubuntu boot via `systemd`.
- Installable by a non-technical person following a step-by-step guide.

**Non-goals**
- No multi-tenant deployment, no cloud, no user passwords.
- No real-time collaboration. Last-write-wins on concurrent edits is fine.
- No mobile apps. Responsive web is enough.
- No public-facing exposure. The docs should warn against port-forwarding it.

---

## 2. Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Runtime | Python 3.10+ | Ships on modern Ubuntu, no extra runtime install |
| Web framework | Flask | Minimal, well-known, easy install docs |
| Database | SQLite | Single file, zero setup, ships with Python |
| Frontend | Vanilla JS + CSS, server-rendered HTML where simple | No build step; offline-safe |
| Fonts | Self-hosted (e.g. Crimson Pro for serif, Inter for UI) | No Google Fonts |
| Icons | Inline SVG, bundled | No icon CDNs |
| Process manager | `systemd` | Standard on Ubuntu |

All Python dependencies must be installable via `pip` from a `requirements.txt`. Keep the dep list short — Flask is sufficient; avoid pulling in heavy ORMs (use `sqlite3` directly or a thin wrapper).

---

## 3. Data Model

SQLite database, single file at a configurable path (default `data/quotes.db`).

**Tables**

`quotes`
- `id` TEXT PRIMARY KEY (the slug from the JSON file)
- `text` TEXT NOT NULL
- `author` TEXT
- `source` TEXT
- `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

`tags`
- `id` INTEGER PRIMARY KEY
- `name` TEXT UNIQUE NOT NULL

`quote_tags` (join table)
- `quote_id` TEXT REFERENCES quotes(id) ON DELETE CASCADE
- `tag_id` INTEGER REFERENCES tags(id) ON DELETE CASCADE
- PRIMARY KEY (quote_id, tag_id)

`profiles`
- `id` INTEGER PRIMARY KEY
- `name` TEXT UNIQUE NOT NULL
- `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

`notes`
- `id` INTEGER PRIMARY KEY
- `quote_id` TEXT REFERENCES quotes(id) ON DELETE CASCADE
- `profile_id` INTEGER REFERENCES profiles(id) ON DELETE CASCADE
- `body` TEXT NOT NULL
- `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP

A profile can have multiple notes per quote (e.g., notes added over time). Display them in created order.

**Initial seed**: On first run, if the `quotes` table is empty, import from `data/quotes.json` (the file we built). Idempotent — second run is a no-op.

---

## 4. Configuration

Single config file: `config.json` in the project root.

```json
{
  "port": 8035,
  "bind_host": "0.0.0.0",
  "db_path": "data/quotes.db",
  "seed_json_path": "data/quotes.json",
  "display_rotation_seconds": 20,
  "display_transition_ms": 800
}
```

All values have sane defaults if the file is missing. The install script writes a default `config.json`. Config changes require a restart — no need for hot-reload.

---

## 5. Features

### 5.1 Quote management (CRUD)

- **List**: paginated grid or list view of all quotes (50 per page is fine). Each card shows the quote text (truncated if very long, with "expand"), author, source if present, tags as small chips.
- **Add**: form with text (required), author (optional, free-text or autocomplete from existing authors), source (optional), tags (multi-select existing tags + free-text new tags). On submit, generates an ID slug from author+first-words like the seed data.
- **Edit**: same form, prefilled. Updates `updated_at`. ID stays stable even if author/text changes (so links/notes don't break).
- **Delete**: requires a confirm dialog. Hard delete; cascades to notes and tag joins.

### 5.2 Search and filter

A single page with:
- **Search box**: full-text match across `text`, `author`, and `source` fields. Case-insensitive substring; one box for all three. (Source IS included in search — yes, per your question. Worth having.)
- **Tag filter**: multi-select. Combined with search via AND. "Show me quotes tagged `death` AND `humor` containing the word `Twain`."
- **Author filter**: dropdown of all authors with counts. Selecting one shows only their quotes.
- **Result count** displayed.
- **Clear filters** button.

Performance note: with 346 quotes (likely <2000 long-term), do filtering in SQL with `LIKE` queries. No need for a search index.

### 5.3 Profiles

- **Profile picker on first visit**: a screen asking "Who are you?" with existing profiles as buttons + a "create new" option.
- Profile name is just a label. No password. Name persists in a cookie (`profile_id`) so they're not re-prompted on the same device.
- A "switch profile" link in the top nav.
- No "delete profile" in the UI v1 — if needed, delete in the DB directly. (Documented in admin section.)
- Profiles exist solely to scope notes. A quote's text/tags/author are shared across all profiles.

### 5.4 Notes

- On any quote's detail page, the current profile sees their own notes (and can add/edit/delete them).
- Other profiles' notes are visible but read-only and labeled with the profile name. (LAN, no privacy — collaborative annotation is the model.)
- Markdown is **not** supported in v1. Plain text only, line breaks preserved. Keep it simple.

### 5.5 Rotating display mode

A dedicated URL: `/display`. Designed for fullscreen on a TV or monitor.

- **Layout**: one quote centered on the screen. Large, readable text. Author below, smaller. Source smaller still and italicized if present. Tags optional, off by default (toggleable via URL param `?tags=1`).
- **Rotation**: every N seconds (from config, default 20), advance to a new random quote. Avoid repeating until all quotes shown (shuffled queue, not pure random — prevents back-to-back repeats).
- **Transition**: configurable. Default: fade out (300ms) + fade in (500ms) = `display_transition_ms` total budget. Implementation: CSS opacity transition.
- **Visually pleasing** means:
  - Serif font, generous line-height (1.5+), comfortable max-width (~700px).
  - Dark mode by default for the display (easier on the eyes on a wall screen). Light text on dark background.
  - Subtle animation only — no zooms, slides, or motion effects that distract from the text.
  - Quote marks rendered as proper typographic quotes (curly), not the straight quotes that are in the data.
- **Controls** (hidden until mouse moves, fade after 3s of inactivity):
  - Pause/resume
  - Next / previous
  - Toggle fullscreen
  - Link back to main app
- **URL params for kiosk use**:
  - `?duration=30` — override rotation seconds
  - `?tags=irish,wisdom` — restrict to quotes matching any of these tags
  - `?author=Voltaire` — restrict to one author
  - `?nocontrols=1` — hide controls completely (true kiosk mode)
- **Wake-lock**: use the [Screen Wake Lock API](https://developer.mozilla.org/en-US/docs/Web/API/Screen_Wake_Lock_API) so the display doesn't sleep. Where unsupported, the docs should note to disable screen sleep in the OS.

### 5.6 Tags page

A simple page listing all tags with counts, sorted by count descending. Clicking a tag filters the main list to that tag. Allows renaming and deleting tags (with confirm). Deleting a tag removes it from all quotes; quote text is untouched.

---

## 6. API

REST-style JSON API. All endpoints return JSON unless noted. All return appropriate status codes (200, 201, 204, 400, 404).

```
GET    /api/quotes                         # list, supports ?q=, ?tags=, ?author=, ?limit=, ?offset=
POST   /api/quotes                         # create
GET    /api/quotes/:id                     # detail
PUT    /api/quotes/:id                     # update
DELETE /api/quotes/:id                     # delete

GET    /api/quotes/random                  # one random quote (for display mode); supports same filters
GET    /api/quotes/shuffle                 # returns a shuffled ordering of IDs (for display mode queue)

GET    /api/tags                           # list with counts
PUT    /api/tags/:id                       # rename
DELETE /api/tags/:id                       # delete

GET    /api/authors                        # list with counts

GET    /api/profiles                       # list
POST   /api/profiles                       # create {name}
DELETE /api/profiles/:id                   # delete

GET    /api/quotes/:id/notes               # all notes for a quote (across all profiles)
POST   /api/quotes/:id/notes               # add a note; body: {profile_id, body}
PUT    /api/notes/:id                      # edit (only if matches current profile)
DELETE /api/notes/:id                      # delete (only if matches current profile)

GET    /api/health                         # returns {"ok": true}; for systemd healthchecks
```

Server-rendered HTML pages (Flask routes that return HTML):
```
GET  /                  # main browse / search page
GET  /quotes/:id        # quote detail with notes
GET  /quotes/new        # add quote form
GET  /quotes/:id/edit   # edit quote form
GET  /tags              # tags page
GET  /profile           # profile picker / switcher
GET  /display           # rotating display
```

---

## 7. Frontend Design Notes

- Two visual modes:
  - **App mode** (main pages): clean, neutral, content-first. Light background, readable text. Comfortable for desk use.
  - **Display mode**: dark, dramatic, large. Designed to be seen across a room.
- Both modes use the same font family for consistency. Serif for the quote text itself, sans-serif for UI chrome (buttons, nav, labels).
- Mobile-friendly enough to use on a phone for adding quotes (a common use case: you read something good, want to add it immediately). Add-quote form should be one column, touch-friendly.
- No JS framework, but feel free to use small standalone libs IF they can be bundled and have no runtime network deps. Suggestions: none required, but Alpine.js (~15KB) is fine if it simplifies. Skip if vanilla JS works.

---

## 8. Deployment

The install needs to be doable by following a numbered list with copy-paste commands. No assumed knowledge of Python, pip, systemd, etc.

**Install steps** the docs should walk through:
1. Open a terminal on the Ubuntu server.
2. Install Python (likely already installed; doc the verification command).
3. Clone or copy the project directory to `/opt/quotes` (or wherever; document the choice).
4. Run an install script (`./install.sh`) that:
   - Creates a Python virtualenv at `/opt/quotes/.venv`
   - Installs deps from `requirements.txt`
   - Creates default `config.json` if missing
   - Creates `data/` directory if missing
   - Copies `quotes.json` (the seed) into `data/`
   - Installs the `systemd` unit file at `/etc/systemd/system/quotes.service`
   - Runs `systemctl daemon-reload`, `systemctl enable quotes`, `systemctl start quotes`
   - Prints the URL to visit (e.g. `http://<server-ip>:8035`)
5. The script is idempotent — re-running upgrades cleanly without losing data.

**systemd unit** should:
- Run as a non-root user (create `quotes` user during install, or document creating one)
- Restart on failure
- Log to journal (`journalctl -u quotes`)
- Set `WorkingDirectory` correctly
- Use the venv's Python

**Uninstall** script: stops the service, disables it, removes the unit file, leaves data in place by default with a `--purge` flag to wipe it.

---

## 9. Documentation Deliverables

Write all docs as Markdown in a `docs/` directory.

**`docs/install.md`** — the install guide. Tone: assume zero technical background. Every command is shown verbatim with copy-paste. Explain what each command does in plain language. Include expected output samples. Cover:
- Verifying Ubuntu version
- Verifying Python is present
- Downloading the app (with both git clone and "download zip" paths)
- Running the install script
- Finding the server's IP address
- Visiting the app in a browser from another device on the LAN
- Setting up autostart (already done by the install script, but verify)
- Changing the port

**`docs/user-guide.md`** — the user guide with screenshots. Cover:
- First-visit profile creation
- Browsing and searching
- Adding a quote
- Editing/deleting a quote
- Adding notes
- Using display mode (and the URL parameters)
- Switching profiles

**`docs/troubleshooting.md`** — common problems:
- "I can't reach it from my phone" → check IP, check that port isn't blocked
- "Service won't start" → `journalctl` instructions
- "I want to reset everything" → how to wipe and re-seed
- "Port 8035 is already in use" → how to change it

**`docs/admin.md`** — administrator tasks:
- Backing up the database (just copy the SQLite file)
- Editing quotes directly in the DB (with `sqlite3` CLI examples)
- Deleting a profile
- Restoring from backup
- Updating the app

**Screenshots**: I can't generate these from the spec. The implementer should produce placeholder paths in the user guide (`![Profile picker](screenshots/profile-picker.png)`) and a `screenshots/` directory. Real screenshots get added after the UI is built.

---

## 10. Acceptance Criteria

The app is "done" when:
- A non-technical person can install it on a fresh Ubuntu server using only the docs in `docs/install.md`.
- The app autostarts after reboot.
- Browsing, search, add, edit, delete, tag, and notes all work from any device on the LAN.
- Display mode runs continuously on a wall-mounted screen without intervention.
- Disconnecting the server from the internet (or putting it on an air-gapped LAN) changes nothing about the user experience.
- Changing the port in `config.json` and restarting the service works.

---

## 11. Open Questions

These I want your call on before Claude Code starts:

1. **Project/repo name?** I've been calling it "Quotes App" but it deserves a name. Suggestions: `quotebox`, `wellspring`, `commonplace` (the old name for a quote book), or your pick.
2. **Multiple notes per quote per profile** (I assumed yes) — or one editable note per profile per quote? Multiple is more flexible; single is simpler UX.
3. **Can users add new tags freely**, or only pick from existing ones? I assumed free-add — easier for growth, slight risk of tag sprawl. Tags page provides cleanup.
4. **Can users edit the `irish` (and similar) tags** on existing quotes? I assumed yes — your collection, you decide.
5. **Display mode duration in the UI**: I made it config-file only. Want a UI toggle on the display page (slider in the controls) that overrides per-session?
6. **Should the install script create the `quotes` system user**, or should the docs walk through creating it manually? Auto-create is friendlier; manual is more explicit.
7. **Backup**: just document "copy the SQLite file" — or include a `backup.sh` script that timestamps and saves to `backups/`?
