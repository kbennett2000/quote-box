# Administration guide

This is the reference for running quote-box long-term — backups,
restores, occasional direct database edits, updates, and security
notes. It assumes you're the person who installed the app and are
comfortable in a terminal.

For day-to-day use, see the [user guide](user-guide.md). For things
gone wrong, see the [troubleshooting guide](troubleshooting.md).

In the examples below, replace `/path/to/quote-box` with the actual
project folder on your server (often `/home/youruser/quote-box`).

## Backing up <a id="backing-up"></a>

The included `backup.sh` script writes a timestamped SQLite snapshot
to the `backups/` folder next to the install. It uses SQLite's
online backup feature, so it's safe to run while the service is up.

Run it manually:

```bash
sudo -u quote-box /path/to/quote-box/backup.sh
```

The script prints the path of the new file on success:

```
/path/to/quote-box/backups/quotes-2026-05-23_0300.db
```

The filename encodes the date and time, so listings sort
chronologically.

### Daily automatic backups via cron

Edit `quote-box`'s crontab (the service user has a crontab even
though it can't log in):

```bash
sudo crontab -e -u quote-box
```

Add this line and save:

```
0 3 * * * /path/to/quote-box/backup.sh
```

That runs the script every day at 3:00 AM. The five fields are
**minute hour day-of-month month day-of-week** — `0 3 * * *` reads
as "minute zero of hour three, every day, every month, every weekday."

Verify it's installed:

```bash
sudo crontab -l -u quote-box
```

After the first night, check the `backups/` folder for the new file.

## Restoring from backup <a id="restoring"></a>

Stop the service, copy the backup file over the live database, fix
ownership, and start the service:

```bash
sudo systemctl stop quote-box
sudo cp /path/to/quote-box/backups/quotes-2026-05-23_0300.db \
        /path/to/quote-box/data/quotes.db
sudo chown quote-box:quote-box /path/to/quote-box/data/quotes.db
sudo systemctl start quote-box
```

Open the app in a browser and confirm the restored state.

**Always check the timestamp of the backup before restoring.** If
you delete a quote at 4 PM and restore from a 3 AM backup, you'll
lose anything anyone added or changed during the day.

## Editing the database directly

For batch cleanups, schema spelunking, or the rare situation where
the UI doesn't expose what you need, you can talk to the SQLite
database directly with the `sqlite3` command-line tool.

Install it (the app itself doesn't need it):

```bash
sudo apt install sqlite3
```

**Always back up first.**

```bash
sudo -u quote-box /path/to/quote-box/backup.sh
sudo -u quote-box sqlite3 /path/to/quote-box/data/quotes.db
```

You'll get a `sqlite>` prompt. Type `.tables` to see the table
list; `.schema quotes` (or any other table) to see its columns.
`.quit` exits.

### Example queries

List all quotes by a single author:

```sql
SELECT id, text FROM quotes WHERE author = 'Voltaire';
```

Find quotes containing a word (case-insensitive):

```sql
SELECT id, author FROM quotes WHERE LOWER(text) LIKE '%wisdom%';
```

Rename a tag everywhere (the UI also does this — easier there,
but for SQL purists):

```sql
UPDATE tags SET name = 'philosophy' WHERE name = 'philosophical';
```

Delete a profile and its notes (the cascade is automatic via the
schema):

```sql
DELETE FROM profiles WHERE name = 'alice';
```

Touch a quote's updated_at without changing anything else:

```sql
UPDATE quotes SET updated_at = CURRENT_TIMESTAMP WHERE id = 'some-quote-id';
```

Count quotes per tag:

```sql
SELECT t.name, COUNT(qt.quote_id) AS n
FROM tags t LEFT JOIN quote_tags qt ON qt.tag_id = t.id
GROUP BY t.id, t.name ORDER BY n DESC;
```

After making changes, the running app picks them up immediately —
SQLite is fine with concurrent readers and a writer, and the app
re-reads on every request.

## Schema reference

quote-box uses six tables. The full canonical definitions live in
[SPEC.md §3](../SPEC.md), but a quick reference:

| Table | Columns | Notes |
| --- | --- | --- |
| `schema_version` | `version` | Single row tracking the schema generation |
| `quotes` | `id`, `text`, `author`, `source`, `created_at`, `updated_at` | `id` is a slug like `voltaire-it-is-dangerous-to-be-right`, stable across edits |
| `tags` | `id`, `name` | Tag names are stored lowercased; `name` is unique |
| `quote_tags` | `quote_id`, `tag_id` | Many-to-many join; cascades on delete |
| `profiles` | `id`, `name`, `created_at` | `name` is unique; cookie holds `id` |
| `notes` | `id`, `quote_id`, `profile_id`, `body`, `created_at`, `updated_at` | Cascades on delete of either parent |

## Updating quote-box

When a new version drops:

```bash
cd /path/to/quote-box
sudo git pull
sudo ./install.sh
```

`install.sh` is idempotent — it skips whatever's already in place,
upgrades the Python dependencies, re-renders the systemd unit if it
changed, and restarts the service. **The database and `config.json`
are never touched by the installer.**

Watch the script's final health check. If it reports `service
responding on port 8035`, you're done. If it doesn't, see
[Troubleshooting → The service won't start](troubleshooting.md#wont-start).

If you downloaded the ZIP instead of using git, replace the project
files with the new ZIP's contents (preserving `data/`, `backups/`,
and `config.json`) and then run `sudo ./install.sh` from the
project folder.

## Disk space

Backups accumulate. A reasonable retention policy is "keep the last
thirty days, delete older." Add this line to `quote-box`'s crontab
to run nightly cleanup:

```
30 3 * * * find /path/to/quote-box/backups -name 'quotes-*.db' -mtime +30 -delete
```

That's the 3:30 AM slot — half an hour after the daily backup. The
`find` command deletes any `quotes-*.db` file older than 30 days.

The app's database itself stays small as long as the quote count
stays in the low thousands. Disk pressure is almost always from
backups.

## Security notes

quote-box is **LAN-only by design**. Specifically:

- **No HTTPS.** Traffic on your network is unencrypted. Don't put
  passwords or sensitive content in quote text, source, or notes.
- **No login passwords.** Anyone who can reach the server's address
  can use the app. Profiles are just labels for note attribution.
- **No CSRF protection.** A malicious page on a device on your
  network could trigger write operations. This is acceptable when
  "your network" is your home.
- **No encryption at rest.** Anyone with file access to the server
  can read `data/quotes.db`.
- **The profile cookie is unsigned.** Anyone on your LAN can spoof
  any profile by setting the cookie manually. This is fine for
  collaborative annotation on a home network and would be a problem
  in any adversarial setting.

**Do not port-forward quote-box to the public internet.** If you
want internet-facing access to your quote collection, you want a
different application — this one is not designed or hardened for
that.

The systemd unit `install.sh` writes does apply a small amount of
process hardening: `NoNewPrivileges`, `PrivateTmp`,
`ProtectSystem=strict`, and `ReadWritePaths` scoped to the data and
backup directories. (`ProtectHome` is deliberately not set —
installing under `/home/<user>/...` is common, and that flag would
make the service unable to see its own venv.) That's defense in
depth against a compromised app process, not protection against a
hostile network.

## Migrating to a new server

You don't need to do anything special. Install quote-box on the new
server normally, restore your most recent backup over the freshly
seeded `data/quotes.db`, and you're done:

```bash
# On the old server:
sudo -u quote-box /path/to/quote-box/backup.sh
# Copy the printed file to the new server somehow (scp, USB stick, etc.).

# On the new server:
cd /path/to/quote-box
sudo ./install.sh                       # if not already installed
sudo systemctl stop quote-box
sudo cp /path/to/quotes-YYYY-MM-DD_HHMM.db data/quotes.db
sudo chown quote-box:quote-box data/quotes.db
sudo systemctl start quote-box
```

Quote IDs are stable strings, so any links anyone has to specific
quotes still work after a migration. Profiles, notes, tags — all of
it survives intact.

If you're moving to a different IP address, the only thing that
breaks is browser shortcuts on devices that pointed at the old IP.
Update those bookmarks and you're done.
