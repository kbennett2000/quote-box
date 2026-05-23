#!/usr/bin/env bash
#
# Timestamped SQLite backup of the quote-box database. Uses SQLite's
# online backup API via the venv's Python, so it's safe to run against
# a live database (no locking issues, no need for the sqlite3 CLI).
#
# Output: prints the absolute path of the new backup file on success.
# Exit non-zero with an explicit message if config, DB, or venv is
# missing.

set -euo pipefail
IFS=$'\n\t'

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$INSTALL_DIR/config.json"
PY="$INSTALL_DIR/.venv/bin/python"

if [[ ! -f "$CONFIG" ]]; then
    echo "config.json not found at $CONFIG (run install.sh first)" >&2
    exit 1
fi

if [[ ! -x "$PY" ]]; then
    echo ".venv not found at $INSTALL_DIR/.venv (run install.sh first)" >&2
    exit 1
fi

DB_PATH="$("$PY" -c \
    "import json; print(json.load(open('$CONFIG'))['db_path'])")"

# Resolve relative paths against the install directory.
case "$DB_PATH" in
    /*) ;;
    *)  DB_PATH="$INSTALL_DIR/$DB_PATH" ;;
esac

if [[ ! -f "$DB_PATH" ]]; then
    echo "database not found at $DB_PATH" >&2
    exit 1
fi

mkdir -p "$INSTALL_DIR/backups"
TS="$(date +%Y-%m-%d_%H%M)"
DEST="$INSTALL_DIR/backups/quotes-$TS.db"

"$PY" - "$DB_PATH" "$DEST" <<'PY'
import sqlite3
import sys

src_path, dst_path = sys.argv[1], sys.argv[2]
src = sqlite3.connect(src_path)
dst = sqlite3.connect(dst_path)
try:
    with dst:
        src.backup(dst)
finally:
    src.close()
    dst.close()
PY

echo "$DEST"
