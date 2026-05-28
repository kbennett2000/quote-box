# quote-box

*Self-hosted, offline-first quote manager with a fullscreen kiosk slideshow — Flask + SQLite, no build step, runs on a Raspberry Pi.*

A small home for the quotes you've collected — the lines you've copied
out of books, the half-remembered passages from talks, the bits of
conversation you didn't want to lose. Search and annotate them from
any device on your home network. Put them on a slideshow on a TV in
the kitchen.

![A quote on display mode](docs/screenshots/display-mode.png)

quote-box runs on a Raspberry Pi, a mini PC, or a laptop you're not
using anymore. It doesn't talk to the internet, doesn't have an
account to log into, doesn't update itself. It just sits there with
your quotes, ready when you want them.

![Browsing the collection](docs/screenshots/browse.png)

## Get started

New install? Start with the [install guide](docs/install.md). It
walks through every command, with what to expect at each step, and
assumes no prior terminal experience.

## Documentation

| Guide | What it covers |
| --- | --- |
| [Install guide](docs/install.md) | Setting up quote-box on an Ubuntu server |
| [User guide](docs/user-guide.md) | Using the app from any device on your network |
| [Troubleshooting](docs/troubleshooting.md) | Common problems and how to fix them |
| [Admin guide](docs/admin.md) | Backup, restore, database access, security |

## Features

- **Browse & search** your whole collection — full-text search across quote, author, and source, with tag and author filters.
- **Free-form tags** and per-quote organization, plus a tags page to rename and tidy.
- **Per-profile notes** — annotate quotes; everyone on the network sees each other's notes, but you only edit your own.
- **Fullscreen kiosk display mode** for a TV or wall screen: a gentle rotating slideshow with curly typography, a dark theme, and screen wake-lock so the display never sleeps. Tune it from the URL — `?duration=30`, `?tags=irish,wisdom`, `?author=Voltaire`, `?nocontrols=1`.
- **No accounts, no internet, no fuss** — bind it to your LAN and forget it.

## Built with

Python · Flask · Jinja2 · SQLite · vanilla JS & CSS · systemd — *no npm, no build step, no internet calls at runtime.*

---

<sub>Curious about the design? The feature spec lives in [SPEC.md](SPEC.md).</sub>
