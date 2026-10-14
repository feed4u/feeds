#!/bin/bash
# Show the daily briefing timer, the last run's state and its log tail.
# Usage: core/code/systemd/daily_status.sh [LINES]

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"

systemctl --user list-timers news-daily-briefing.timer --all --no-pager
systemctl --user status news-daily-briefing.service --no-pager --lines=0 || true
journalctl --user -u news-daily-briefing --no-pager -n "${1:-40}"
