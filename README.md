# pro-bridge

Expose **web-only GPT Pro** (or any ChatGPT model) to MCP clients — so a coding
agent like Claude Code can talk to GPT Pro programmatically, even though Pro has
no API.

It works by **attaching to your real, logged-in Chrome over CDP** instead of
launching a fresh automated browser. Your genuine session computes the cookies
and anti-bot proof-of-work tokens, so there's no login step and a minimal
detection surface. Answers are read from the assistant turn's semantic
attribute + a text-stability check (resilient to UI/CSS changes), and the active
model is verified from the network request so you never get a non-Pro answer by
mistake.

> ⚠️ This automates the ChatGPT web UI of *your own* account. That's a gray area
> under OpenAI's terms — use at your own risk.

```
[ your laptop ]                                    [ remote box ]
 Chrome (logged in, --remote-debugging-port=9222)
        ▲ CDP (localhost only)
 pro-bridge  ── streamable-HTTP MCP over Tailscale ──▶  Claude Code
   tool: ask_gpt_pro(prompt, conversation_id?)             /debate-high
```

The browser automation stays entirely on the host with the browser; only the MCP
request/reply crosses the network (and on a single machine, it doesn't even do
that).

## Topologies

pro-bridge is network-transparent: run it on whatever machine has the logged-in
browser, then point your MCP client at it. Both of these work with the same code
— only the URL the client uses changes.

| Client (Claude Code, etc.) | Browser host | `PRO_BRIDGE_HOST` | Client connects to |
|---|---|---|---|
| **Same machine** as the browser | same | `127.0.0.1` | `http://localhost:8765/mcp` |
| **Different machine** (e.g. headless server) | your laptop/desktop | `0.0.0.0` | `http://<host-LAN/Tailscale-IP>:8765/mcp` |

The browser host can be **Windows, macOS, or Linux** — use the matching launch
script in `scripts/`. The client can be any MCP-capable tool (Claude Code,
Cursor, etc.) on any OS. For the same-machine case you can leave the token unset
(localhost only); for cross-machine, keep a token and put it behind a private
network like Tailscale.

## Setup (the machine that has the browser)

1. **Install deps** (Python 3.10+):
   ```powershell
   pip install -r requirements.txt
   ```
   No `playwright install` needed — we attach to your existing Chrome.

2. **Start the bridge browser** (logs in once, stays logged in):
   ```powershell
   # Windows
   powershell -ExecutionPolicy Bypass -File scripts\start-chrome-debug.ps1
   ```
   ```bash
   # macOS / Linux (auto-detects chrome/chromium/brave/edge; override with BROWSER=)
   ./scripts/start-chrome-debug.sh
   ```
   In the window that opens: log into chatgpt.com, confirm Pro, select the Pro
   model. Leave it open (minimize is fine).

3. **Configure**:
   ```powershell
   copy .env.example .env
   ```
   Edit `.env`: set a long random `PRO_BRIDGE_TOKEN`. Leave `PRO_BRIDGE_HOST=0.0.0.0`.

4. **Sanity check the connection** (no MCP yet):
   ```powershell
   python selftest.py
   ```
   It should print the page URL and detected model. Add a prompt to do a full
   round-trip (slow — Pro thinks for minutes):
   ```powershell
   python selftest.py "Reply with exactly one word: PONG"
   ```
   Note the model string it logs — if you want new chats forced to Pro, put that
   slug in `GPT_PRO_MODEL_SLUG`.

5. **Run the MCP server**:
   ```powershell
   python -m pro_bridge.server
   ```
   It listens on `http://0.0.0.0:8765/mcp`. Find your tailnet IP with
   `tailscale ip -4`.

## Wire up Claude Code

**Same machine** as the browser (simplest — no token needed):
```bash
claude mcp add --transport http gpt-pro http://localhost:8765/mcp --scope user
```

**Different machine** (client on a headless server, browser on your laptop):
```bash
claude mcp add --transport http gpt-pro \
  http://<browser-host-ip>:8765/mcp \
  --scope user \
  --header "Authorization: Bearer <PRO_BRIDGE_TOKEN>"
```

The tool appears as `mcp__gpt-pro__ask_gpt_pro`. A `/debate-high` slash command
that drives a Claude-vs-Pro debate is included separately.

## Tuning / robustness knobs

| env | default | meaning |
|-----|---------|---------|
| `GPT_PRO_MODEL_SLUG` | (current) | force a model on new chats; empty = use selected |
| `PRO_BRIDGE_STRICT_MODEL` | `1` | refuse answers if the active model isn't a Pro model |
| `PRO_BRIDGE_TIMEOUT` | `1800` | max seconds to wait for one answer |
| `PRO_BRIDGE_TOKEN` | (none) | bearer token required on every MCP request |

## When it might break (and the fix)

- **ChatGPT changes the composer / assistant DOM** → update the few selectors in
  `pro_bridge/chatgpt.py` (`#prompt-textarea`, `data-message-author-role`,
  `data-testid="send-button"`/`stop-button`). These are the only UI couplings.
- **Model slug changes** → re-run `selftest.py`, copy the new slug to `.env`.
- **Session expires** → the bridge Chrome will show a login; just log in again.
