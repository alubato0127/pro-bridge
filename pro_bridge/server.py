"""pro-bridge MCP server: exposes GPT Pro (ChatGPT web) as an MCP tool.

Runs on the laptop where Chrome is logged in. Serves streamable-HTTP MCP so a
remote Claude Code (over Tailscale) can call `ask_gpt_pro`.
"""
import logging

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from . import config
from .chatgpt import ChatGPTDriver

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("pro_bridge")

# MCP streamable-HTTP has DNS-rebinding protection that only allows localhost
# Host headers. We're reached over Tailscale (a private network) + bearer token,
# so that protection just blocks us. Disable it where supported.
try:
    from mcp.server.transport_security import TransportSecuritySettings
    _SEC = TransportSecuritySettings(enable_dns_rebinding_protection=False)
except Exception:
    _SEC = None

try:
    mcp = FastMCP("gpt-pro", transport_security=_SEC) if _SEC else FastMCP("gpt-pro")
except TypeError:
    mcp = FastMCP("gpt-pro")

_driver = ChatGPTDriver()


@mcp.tool()
async def ask_gpt_pro(prompt: str, conversation_id: str | None = None) -> dict:
    """Ask GPT Pro (ChatGPT web, Pro model) and return its full reply.

    GPT Pro reasons for several minutes; this call BLOCKS until the answer is
    complete. The prompt must be self-contained (Pro shares no other context).
    Pass `conversation_id` from a previous reply to continue the same thread —
    essential for a multi-turn debate so Pro remembers the earlier rounds.

    Returns {text, model, conversation_id}.
    """
    log.info("ask_gpt_pro: %d chars, conv=%s", len(prompt), conversation_id)
    res = await _driver.ask(prompt, conversation_id)
    log.info("ask_gpt_pro done: model=%s conv=%s, %d chars",
             res.get("model"), res.get("conversation_id"), len(res.get("text", "")))
    return res


class TokenAuth(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if config.TOKEN and request.headers.get("authorization", "") != f"Bearer {config.TOKEN}":
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


class RewriteHost:
    """Backup for the DNS-rebinding check: present a localhost Host to the inner
    MCP app regardless of the real (Tailscale IP) Host header."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            host = f"localhost:{config.PORT}".encode()
            headers = [(k, v) for (k, v) in scope["headers"] if k.lower() != b"host"]
            headers.append((b"host", host))
            scope = dict(scope, headers=headers)
        await self.app(scope, receive, send)


def main():
    app = mcp.streamable_http_app()
    app.add_middleware(TokenAuth)
    app = RewriteHost(app)
    log.info("pro-bridge MCP listening on http://%s:%s/mcp  (token=%s, model_slug=%s)",
             config.HOST, config.PORT, "set" if config.TOKEN else "NONE",
             config.MODEL_SLUG or "current")
    uvicorn.run(app, host=config.HOST, port=config.PORT)


if __name__ == "__main__":
    main()
