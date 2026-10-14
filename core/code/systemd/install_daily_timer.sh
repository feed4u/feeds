#!/bin/bash
# Install and enable the daily briefing timer as a user unit on this host.
# Idempotent: re-running refreshes the unit files and reloads systemd.
#
# Usage: core/code/systemd/install_daily_timer.sh [--start]
#   --start  also start one run now (in the background; follow it with
#            journalctl --user -u news-daily-briefing -f)

set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
# Non-login shells (cron, remote runners) may lack the user bus address.
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"

mkdir -p "$DEST"
install -m 0644 "$SRC/news-daily-briefing.service" "$SRC/news-daily-briefing.timer" "$DEST/"
systemctl --user daemon-reload
systemctl --user enable --now news-daily-briefing.timer
if [ "${1:-}" = "--start" ]; then
  systemctl --user start --no-block news-daily-briefing.service
fi
systemctl --user list-timers news-daily-briefing.timer --all --no-pager
