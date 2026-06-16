#!/usr/bin/env bash
# Launch a dedicated, logged-in Chromium-family browser for the bridge
# (macOS / Linux). Windows users: use start-chrome-debug.ps1 instead.
#
# FIRST RUN: a fresh browser window opens -> log into chatgpt.com and select the
# model you want (e.g. Pro). The profile lives in ~/.pro-bridge-chrome and
# persists, so later runs stay logged in. Keep the window open while debating.
#
# Override the browser with: BROWSER=brave ./start-chrome-debug.sh
set -euo pipefail

PORT="${PRO_BRIDGE_CDP_PORT:-9222}"
PROFILE="${PRO_BRIDGE_PROFILE_DIR:-$HOME/.pro-bridge-chrome}"

# Candidate executables, in priority order. BROWSER env (if set) goes first.
candidates=()
[ -n "${BROWSER:-}" ] && candidates+=("$BROWSER")
candidates+=(
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
  "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
  "/Applications/Chromium.app/Contents/MacOS/Chromium"
  google-chrome google-chrome-stable chromium chromium-browser
  brave-browser microsoft-edge microsoft-edge-stable
)

bin=""
for c in "${candidates[@]}"; do
  if [ -x "$c" ]; then bin="$c"; break; fi
  if command -v "$c" >/dev/null 2>&1; then bin="$(command -v "$c")"; break; fi
done

if [ -z "$bin" ]; then
  echo "No Chromium-family browser found. Set BROWSER=/path/to/browser and retry." >&2
  exit 127
fi

echo "Starting bridge browser: $bin"
echo "  CDP port: $PORT   profile: $PROFILE"
exec "$bin" \
  --remote-debugging-port="$PORT" \
  --user-data-dir="$PROFILE" \
  --no-first-run --no-default-browser-check \
  "https://chatgpt.com/"
