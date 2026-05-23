#!/usr/bin/env bash
set -euo pipefail
export FLASK_DEBUG=1
exec python -m app
