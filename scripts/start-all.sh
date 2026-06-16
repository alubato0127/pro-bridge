#!/usr/bin/env bash
# One-shot launcher (macOS / Linux): bring the bridge up after a reboot.
# Starts the debug browser (if not already running) and then the MCP server.
# NOTE: the `claude mcp add` registration is one-time — not redone here.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(dirname "$here")"
port="${PRO_BRIDGE_CDP_PORT:-9222}"

# 1. Bridge browser — only if nothing is listening on the CDP port yet.
if curl -s -o /dev/null -m 1 "http://localhost:${port}/json/version"; then
  echo "Bridge browser already running on port ${port}."
else
  echo "Launching bridge browser on CDP port ${port} ..."
  "$here/start-chrome-debug.sh" >/dev/null 2>&1 &
  sleep 3
fi

# 2. MCP server (foreground — Ctrl+C to stop).
cd "$repo"
echo "Starting pro-bridge MCP server ..."
exec python -m pro_bridge.server
