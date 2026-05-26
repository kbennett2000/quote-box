#!/usr/bin/env bash
#
# quote-box installer. Idempotent: re-running on a working install
# upgrades dependencies and restarts the service without touching the
# database or config.json. Run as root (typically via sudo).

set -euo pipefail
IFS=$'\n\t'

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_PATH="/etc/systemd/system/quote-box.service"
SERVICE_USER="quote-box"

# ---- output helpers --------------------------------------------------------

step_num=0
step() {
    step_num=$((step_num + 1))
    printf '\n[%d/%d] %s\n' "$step_num" "$total_steps" "$1"
}
ok()   { printf '      \xE2\x9C\x93 %s\n' "$1"; }
warn() { printf '      ! %s\n' "$1" >&2; }
fail() { printf '\nERROR: %s\n' "$1" >&2; exit 1; }

total_steps=15

# ---- step bodies -----------------------------------------------------------

require_root() {
    step "verifying root privileges"
    if [[ $EUID -ne 0 ]]; then
        fail "must run as root (try: sudo $0)"
    fi
    ok "running as root"
}

check_distro() {
    step "checking distribution"
    if [[ ! -r /etc/os-release ]]; then
        fail "/etc/os-release not found; cannot identify distro"
    fi
    # shellcheck disable=SC1091
    . /etc/os-release
    local id="${ID:-unknown}"
    local id_like="${ID_LIKE:-}"
    if [[ "$id" == "ubuntu" ]]; then
        ok "Ubuntu ${VERSION_ID:-?} detected"
        if [[ -n "${VERSION_ID:-}" ]] && \
           [[ "$(printf '%s\n' "$VERSION_ID" "22.04" | sort -V | head -n1)" != "22.04" ]]; then
            warn "Ubuntu < 22.04 — supported but untested"
        fi
    elif [[ "$id_like" == *"debian"* ]] || [[ "$id" == "debian" ]]; then
        warn "Debian-family non-Ubuntu detected ($id); proceeding"
    else
        fail "unsupported distribution: $id (need Ubuntu or a Debian derivative)"
    fi
}

check_python() {
    step "checking Python 3.10+"
    if ! command -v python3 >/dev/null 2>&1; then
        fail "python3 not found; install with: apt install python3 python3-venv"
    fi
    if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'; then
        fail "python3 is older than 3.10; install a newer version"
    fi
    ok "$(python3 --version)"
}

ensure_service_user() {
    step "ensuring service user '$SERVICE_USER' exists"
    if id -u "$SERVICE_USER" >/dev/null 2>&1; then
        ok "user already exists"
    else
        useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
        ok "created system user $SERVICE_USER"
    fi
}

report_install_dir() {
    step "install directory"
    ok "$INSTALL_DIR"
}

ensure_venv() {
    step "ensuring Python virtualenv at .venv/"
    if [[ -x "$INSTALL_DIR/.venv/bin/python" ]]; then
        ok ".venv already present"
    else
        python3 -m venv "$INSTALL_DIR/.venv"
        ok "created .venv"
    fi
}

install_deps() {
    step "installing Python dependencies"
    "$INSTALL_DIR/.venv/bin/pip" install --quiet --upgrade pip >/dev/null
    "$INSTALL_DIR/.venv/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt"
    ok "dependencies up to date"
}

ensure_dirs() {
    step "creating data/ and backups/ if missing"
    mkdir -p "$INSTALL_DIR/data" "$INSTALL_DIR/backups"
    ok "directories ready"
}

ensure_config() {
    step "ensuring config.json"
    if [[ -f "$INSTALL_DIR/config.json" ]]; then
        ok "config.json already exists (left untouched)"
    else
        cp "$INSTALL_DIR/config.example.json" "$INSTALL_DIR/config.json"
        ok "copied config.example.json -> config.json"
    fi
}

set_ownership() {
    step "setting ownership and traversal permissions"

    # data/ and backups/ are owned by the service user so it can write
    # to them. Everything else is owned by the installing user — the
    # service reads source files, config, and venv via filesystem
    # 'other' perms (default 644/755), and the installer keeps the
    # ability to git pull, edit, and remove the project later without
    # sudo. ProtectSystem=strict in the unit blocks writes outside of
    # ReadWritePaths regardless of ownership.
    chown -R "$SERVICE_USER:$SERVICE_USER" \
        "$INSTALL_DIR/data" "$INSTALL_DIR/backups"

    local owner="${SUDO_USER:-root}"
    local owner_group
    owner_group="$(id -gn "$owner" 2>/dev/null || echo "$owner")"

    # Fix the install dir's own ownership first — the find -mindepth 1
    # below operates on its CONTENTS and skips the directory itself, so
    # if the dir drifted (e.g. a previous wide chown to quote-box), it
    # would stay broken and subsequent git pull would fail to unlink
    # files because git needs write on the containing directory.
    chown "$owner:$owner_group" "$INSTALL_DIR"

    find "$INSTALL_DIR" -mindepth 1 -maxdepth 1 \
        ! -name data ! -name backups \
        -exec chown -R "$owner:$owner_group" {} +

    # If the install dir is under /home/<user>/..., Ubuntu's default
    # /home/<user> mode of 0750 blocks anyone outside that user's
    # group (including the service user) from traversing INTO the
    # home directory to reach the project. Grant world-traversal
    # (x-only, not r) on each parent up to /home. The home dir's
    # contents stay unlistable to others; only the path becomes
    # walkable.
    if [[ "$INSTALL_DIR" == /home/* ]]; then
        local p
        p="$(dirname "$INSTALL_DIR")"
        while [[ "$p" != "/" && "$p" != "/home" ]]; do
            chmod o+x "$p" 2>/dev/null || true
            p="$(dirname "$p")"
        done
    fi

    ok "permissions configured (data/+backups/ owned by $SERVICE_USER, rest by $owner)"
}

install_service_unit() {
    step "installing systemd unit"
    local rendered="/tmp/quote-box.service.new"
    sed "s|__INSTALL_DIR__|$INSTALL_DIR|g" \
        "$INSTALL_DIR/quote-box.service" > "$rendered"
    if [[ -f "$SERVICE_PATH" ]] && cmp -s "$rendered" "$SERVICE_PATH"; then
        rm -f "$rendered"
        ok "unit already current at $SERVICE_PATH"
    else
        install -m 644 "$rendered" "$SERVICE_PATH"
        rm -f "$rendered"
        ok "wrote $SERVICE_PATH"
    fi
}

daemon_reload() {
    step "systemctl daemon-reload"
    systemctl daemon-reload
    ok "reloaded"
}

enable_and_restart() {
    step "enabling + restarting quote-box service"
    systemctl enable quote-box >/dev/null 2>&1
    systemctl restart quote-box
    ok "service restarted"
}

health_check() {
    step "waiting for /api/health"
    local port
    port="$("$INSTALL_DIR/.venv/bin/python" -c \
        "import json; print(json.load(open('$INSTALL_DIR/config.json'))['port'])")"
    local i=0
    while [[ $i -lt 25 ]]; do
        if curl -sf "http://localhost:$port/api/health" >/dev/null 2>&1; then
            ok "service responding on port $port"
            return
        fi
        sleep 0.2
        i=$((i + 1))
    done
    printf '\n--- last 50 lines of journalctl -u quote-box ---\n' >&2
    journalctl -u quote-box -n 50 --no-pager >&2 || true
    fail "service did not respond on port $port within 5s"
}

print_success() {
    local port
    port="$("$INSTALL_DIR/.venv/bin/python" -c \
        "import json; print(json.load(open('$INSTALL_DIR/config.json'))['port'])")"
    local ips
    ips="$(hostname -I 2>/dev/null | xargs || echo "<unknown>")"
    cat <<EOF

================================================================
  quote-box is up and running.

  Open in this machine's browser:
      http://localhost:$port

  Open from another device on your LAN (try one of):
      $(for ip in $ips; do echo "      http://$ip:$port"; done)

  Service controls:
      systemctl status quote-box
      systemctl restart quote-box
      journalctl -u quote-box -f

  Install location: $INSTALL_DIR
================================================================
EOF
}

# ---- main ------------------------------------------------------------------

require_root
check_distro
check_python
ensure_service_user
report_install_dir
ensure_venv
install_deps
ensure_dirs
ensure_config
set_ownership
install_service_unit
daemon_reload
enable_and_restart
health_check
print_success
