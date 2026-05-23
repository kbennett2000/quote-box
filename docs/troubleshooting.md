# Troubleshooting

When something isn't working, walk through the relevant section
below. Each one assumes you're comfortable opening a terminal on the
server (or SSHing into it) and copy-pasting commands.

If a command needs `sudo`, you'll be prompted for the password the
first time per session.

## I can't reach quote-box from another device <a id="cant-reach"></a>

Work through these checks in order. The first one that fails tells
you where the problem is.

**1. Is the service running?**

```bash
sudo systemctl status quote-box
```

Look for the line that starts with **Active:**. You want
`active (running)`. If it says `failed` or `inactive`, jump to
[The service won't start](#wont-start).

**2. Is it listening on the expected port?**

```bash
sudo ss -tlnp | grep 8035
```

You should see a line containing `0.0.0.0:8035` and `python`. If the
port is different in your `config.json`, swap it in. If nothing
prints, the app isn't really listening even if systemd thinks it's
running — check the logs as in section 2.

**3. Does the app respond from the server itself?**

```bash
curl http://localhost:8035/api/health
```

Expected:

```
{"ok":true}
```

If this works but other devices can't reach it, the problem is
between the server and the rest of your network — keep going.

**4. Is a firewall blocking the port?**

```bash
sudo ufw status
```

If you see `Status: inactive`, the firewall isn't the problem. If
it's active, allow the port:

```bash
sudo ufw allow 8035/tcp
```

(Change the port if you're using a different one.)

**5. Are you using the right IP address?**

```bash
hostname -I
```

You want one that starts with `192.168.` or `10.` — that's a
local-network address. An address starting with `127.` is the
machine talking to itself only; that's not what you want to type
into another device.

**6. Can the other device reach the server at all?**

From your phone or laptop on the same network, try pinging the
server's IP. On macOS/Linux: `ping 192.168.1.42` (your IP).
On Windows: the same, in PowerShell.

If ping fails, the issue is network-level — the devices aren't on
the same subnet, your router is segregating Wi-Fi clients from wired
ones, or similar. Check your router's settings.

## The service won't start <a id="wont-start"></a>

Pull up the logs:

```bash
sudo journalctl -u quote-box -n 50
```

This shows the last 50 lines. For live monitoring while you try to
reproduce the problem:

```bash
sudo journalctl -u quote-box -f
```

Press **Ctrl + C** to stop following.

### Common error messages

#### `Address already in use`

Another program is using port 8035. See
[Port already in use](#port-in-use) below.

#### `Permission denied` on a file under `data/`

The service user (`quote-box`) lost ownership of one of the data
files. Re-set it:

```bash
cd /path/to/quote-box
sudo chown -R quote-box:quote-box .
sudo systemctl restart quote-box
```

#### `config.json not found`

The config file is missing. Re-run the installer from inside the
project folder:

```bash
sudo ./install.sh
```

It restores `config.json` from `config.example.json` without
touching the database.

#### `ModuleNotFoundError`

The Python virtualenv is missing or its packages got corrupted.
Rebuild it:

```bash
cd /path/to/quote-box
sudo rm -rf .venv
sudo ./install.sh
```

This regenerates `.venv/` and reinstalls dependencies. Your database
and config are not touched.

#### `Unable to locate executable '/.../.venv/bin/python'`

The systemd service can't see its own venv Python even though the
file exists on disk. This was a known problem with installs under
`/home/<user>/...` in older versions of quote-box — `ProtectHome=yes`
in the unit file hid the home directory from the service.

Pull the latest version (which removes `ProtectHome=yes`) and
re-run the installer:

```bash
cd /path/to/quote-box
sudo git pull
sudo ./install.sh
```

If you can't pull (no git, isolated server), edit the unit file
directly and delete the line `ProtectHome=yes`:

```bash
sudo nano /etc/systemd/system/quote-box.service
# Find and delete the line: ProtectHome=yes
sudo systemctl daemon-reload
sudo systemctl restart quote-box
```

## Port already in use <a id="port-in-use"></a>

Find what's holding the port:

```bash
sudo ss -tlnp | grep 8035
```

The last column shows the program name and PID. If it's something
you don't recognize and don't need, stop or uninstall it. If it's
something you do need, change quote-box to use a different port.

Edit `config.json`:

```bash
sudo nano config.json
```

Find the line:

```json
  "port": 8035,
```

Change it to a free port. `8085`, `8090`, `9001` are all common
choices. Save with **Ctrl + O**, **Enter**, then **Ctrl + X**.

If you have `ufw` active, allow the new port and remove the rule
for the old one:

```bash
sudo ufw allow 8085/tcp
sudo ufw delete allow 8035/tcp
```

Restart quote-box:

```bash
sudo systemctl restart quote-box
```

Then open the new URL on your other devices: `http://your-ip:8085`.

## I want to reset everything <a id="reset"></a>

There are two flavors of reset, depending on how clean you want the
slate.

### Safe reset (re-seeds the original quotes, keeps the install)

This puts the database back to the original seed of quotes and wipes
all profiles, notes, and tags you've added.

```bash
cd /path/to/quote-box
sudo ./backup.sh                        # always back up first
sudo systemctl stop quote-box
sudo rm data/quotes.db
sudo systemctl start quote-box
```

The service notices the empty database on startup and re-seeds it
from `data/quotes.json` automatically.

### Full uninstall and reinstall

This removes the service, the virtualenv, all configuration, all
data, and the `quote-box` system user — then installs fresh.

```bash
cd /path/to/quote-box
sudo ./uninstall.sh --purge
# Type 'yes' when prompted to confirm.
sudo ./install.sh
```

The project folder itself is preserved either way.

## The picker keeps appearing every visit

This is a cookie issue, not a quote-box problem. Your browser is
either set to clear cookies on exit, or you're using a private/
incognito window. Open the site in a normal browser window or change
your browser's cookie settings to keep them.

If a single device keeps prompting even after you pick a profile,
the cookie isn't being set — check that your browser isn't blocking
third-party cookies for `192.168.x.x` style addresses; some browsers
get strict about that.

## The display shows the same quote over and over

This is correct behavior when the filter has narrowed to one matching
quote. Check the URL you opened — anything after the `?` is a filter.

Examples:

- `/display?author=Plato` only shows Plato quotes; if there's just
  one, it shows that one forever.
- `/display?tags=irish,humor` shows quotes tagged irish OR humor; if
  the intersection is small or empty, you'll see very few.

To see everything, open `/display` with no parameters.

If you see "No quotes match these filters" instead of a quote, your
filter has narrowed to zero. Remove the parameters or relax them.

## The app feels slow

At the scale this is designed for (hundreds to low-thousands of
quotes), it should never be slow. If it is, check:

```bash
df -h
```

Make sure the disk isn't full.

```bash
top
```

Look for runaway processes eating CPU or memory. Press `q` to quit.

If everything looks normal but the app is still sluggish, restart it:

```bash
sudo systemctl restart quote-box
```

## I accidentally deleted a quote

If you have a recent backup, you can restore the database from it.
See [admin.md → Restoring from backup](admin.md#restoring).

If you don't have a backup, the quote is gone — set up a daily
backup now so this doesn't happen again. See
[admin.md → Backing up](admin.md#backing-up).

## Where are the logs?

`journalctl` is the source of truth.

```bash
sudo journalctl -u quote-box                  # everything ever logged
sudo journalctl -u quote-box -n 100           # last 100 lines
sudo journalctl -u quote-box -f               # live tail; Ctrl+C to stop
sudo journalctl -u quote-box --since "1 hour ago"
sudo journalctl -u quote-box --since today
```

When something goes wrong, the time-windowed form is the most useful
— look at the minutes around when the problem happened.

For deeper diagnostics or unusual setups, see the
[admin guide](admin.md).
