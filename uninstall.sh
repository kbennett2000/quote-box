#!/usr/bin/env bash
#
# Remove the quote-box systemd unit and (with --purge) the data
# directory, backups, virtualenv, config, and service user. Idempotent
# against partial state. Run as root.

set -euo pipefail
IFS=$'\n\t'

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_PATH="/etc/systemd/system/quote-box.service"
SERVICE_USER="quote-box"

PURGE=0
for arg in "$@"; do
    case "$arg" in
        --purge) PURGE=1 ;;
        -h|--help)
            cat <<EOF
Usage: $0 [--purge]

  (no flag)  Stop and remove the quote-box service. Data, backups,
             config, virtualenv, and the service user are preserved.

  --purge    Also delete data/quotes.db, backups/, .venv/, config.json,
             and remove the 'quote-box' service user. Prompts for
             confirmation; the project files themselves are preserved.
EOF
            exit 0
            ;;
        *) echo "unknown flag: $arg" >&2; exit 2 ;;
    esac
done

say()  { printf '%s\n' "$1"; }
fail() { printf '\nERROR: %s\n' "$1" >&2; exit 1; }

if [[ $EUID -ne 0 ]]; then
    fail "must run as root (try: sudo $0)"
fi

# ---- service teardown (always) --------------------------------------------

say "Stopping quote-box service (if running)..."
systemctl stop quote-box 2>/dev/null || true

say "Disabling quote-box service (if enabled)..."
systemctl disable quote-box 2>/dev/null || true

if [[ -f "$SERVICE_PATH" ]]; then
    say "Removing $SERVICE_PATH..."
    rm -f "$SERVICE_PATH"
fi

systemctl daemon-reload

if [[ "$PURGE" -ne 1 ]]; then
    cat <<EOF

Service removed. Data preserved at:
  $INSTALL_DIR/data/
  $INSTALL_DIR/backups/

Run with --purge to also remove the database, backups, virtualenv,
config.json, and the 'quote-box' system user.
EOF
    exit 0
fi

# ---- purge path -----------------------------------------------------------

printf '\nThis will delete the database AND all backups under %s.\n' "$INSTALL_DIR"
printf "Type 'yes' to continue: "
read -r ans
if [[ "$ans" != "yes" ]]; then
    say "Aborted; nothing further removed."
    exit 0
fi

say "Removing data/quotes.db..."
rm -f "$INSTALL_DIR/data/quotes.db"

say "Removing backups/..."
rm -rf "$INSTALL_DIR/backups"

say "Removing .venv/..."
rm -rf "$INSTALL_DIR/.venv"

say "Removing config.json..."
rm -f "$INSTALL_DIR/config.json"

if id -u "$SERVICE_USER" >/dev/null 2>&1; then
    say "Removing system user $SERVICE_USER..."
    userdel "$SERVICE_USER" 2>/dev/null || true
fi

cat <<EOF

Purge complete. The project directory itself is preserved at:
  $INSTALL_DIR

Remove it manually if desired (e.g., 'rm -rf $INSTALL_DIR').
EOF
