"""Configuration for pro-bridge, read from environment / a local .env file."""
import os


def _load_dotenv():
    # Minimal .env loader so we don't add a dependency.
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()

# CDP endpoint of the debug Chrome — local to this laptop, never exposed.
CDP_URL = os.environ.get("PRO_BRIDGE_CDP_URL", "http://localhost:9222")

# Where the MCP server listens. Bind 0.0.0.0 (or your tailnet IP) so the
# remote machine running Claude Code can reach it over Tailscale.
HOST = os.environ.get("PRO_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.environ.get("PRO_BRIDGE_PORT", "8765"))

# Shared secret. If set, callers must send `Authorization: Bearer <TOKEN>`.
TOKEN = os.environ.get("PRO_BRIDGE_TOKEN", "")

# Optional: force a Pro model slug on *new* chats (e.g. "gpt-5-pro", "o1-pro").
# Empty = use whatever model the bridge Chrome currently has selected.
MODEL_SLUG = os.environ.get("GPT_PRO_MODEL_SLUG", "")

# Refuse to return an answer if the active model isn't a Pro model.
STRICT_MODEL = os.environ.get("PRO_BRIDGE_STRICT_MODEL", "1") not in ("0", "false", "False")

# Max seconds to wait for a single Pro answer. Pro reasons for minutes.
ANSWER_TIMEOUT = int(os.environ.get("PRO_BRIDGE_TIMEOUT", "1800"))
