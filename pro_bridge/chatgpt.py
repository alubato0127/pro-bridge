"""Drive an already-logged-in ChatGPT (GPT Pro) via CDP.

Robustness design:
- Attach to the *real* Chrome (connect_over_cdp) so the session, cookies and
  anti-bot proof-of-work tokens are produced by the genuine page. No fresh
  automation context, no login, minimal detection surface.
- Read the answer from the assistant turn by its semantic attribute
  (`data-message-author-role="assistant"`) and a text-stability check, rather
  than scraping fragile CSS classes or parsing the evolving SSE delta protocol.
- Verify the model from the outgoing /backend-api/conversation request body and
  refuse the answer if it isn't a Pro model (verification over blind clicking).
"""
import asyncio
import logging
import re
import time

from playwright.async_api import async_playwright

from . import config

log = logging.getLogger("pro_bridge.chatgpt")

CONV_RE = re.compile(r"/c/([0-9a-fA-F-]{36})")
ASSISTANT = '[data-message-author-role="assistant"]'


class ChatGPTDriver:
    def __init__(self):
        self._pw = None
        self._browser = None
        self._lock = asyncio.Lock()  # serialize: Pro answers one at a time anyway

    async def _ensure(self):
        if self._browser is not None and self._browser.is_connected():
            return
        if self._pw is None:
            self._pw = await async_playwright().start()
        log.info("Connecting to Chrome via CDP at %s", config.CDP_URL)
        self._browser = await self._pw.chromium.connect_over_cdp(config.CDP_URL)

    async def _get_page(self, conversation_id=None):
        await self._ensure()
        contexts = self._browser.contexts
        if not contexts:
            raise RuntimeError(
                "No browser context over CDP. Start Chrome with "
                "--remote-debugging-port and a logged-in profile (see scripts/)."
            )
        ctx = contexts[0]
        page = None
        for p in ctx.pages:
            if "chatgpt.com" in p.url or "chat.openai.com" in p.url:
                page = p
                break
        if page is None:
            page = await ctx.new_page()
            target = "https://chatgpt.com/"
            if conversation_id:
                target = f"https://chatgpt.com/c/{conversation_id}"
            elif config.MODEL_SLUG:
                target = f"https://chatgpt.com/?model={config.MODEL_SLUG}"
            await page.goto(target, wait_until="domcontentloaded")
        elif conversation_id and conversation_id not in page.url:
            await page.goto(f"https://chatgpt.com/c/{conversation_id}",
                            wait_until="domcontentloaded")
        elif conversation_id is None and config.MODEL_SLUG and "/c/" not in page.url:
            await page.goto(f"https://chatgpt.com/?model={config.MODEL_SLUG}",
                            wait_until="domcontentloaded")
        return page

    async def _last_assistant_slug(self, page):
        # Ground truth: each assistant turn carries the model that produced it.
        try:
            return await page.evaluate(
                """() => {
                    const els = document.querySelectorAll('[data-message-author-role=assistant]');
                    if (!els.length) return null;
                    return els[els.length - 1].getAttribute('data-message-model-slug');
                }"""
            )
        except Exception:
            return None

    async def current_model(self, page):
        slug = await self._last_assistant_slug(page)
        if slug:
            return slug
        # No answer yet: infer from the composer's Pro effort control.
        try:
            if await page.locator(
                '[data-testid="composer-intelligence-pro-thinking-effort-trigger"]'
            ).count():
                return "pro (composer)"
        except Exception:
            pass
        return None

    async def ask(self, prompt, conversation_id=None):
        async with self._lock:
            page = await self._get_page(conversation_id)
            try:
                await page.bring_to_front()
            except Exception:
                pass

            model_holder = {}

            def on_request(req):
                try:
                    if req.method == "POST" and "/backend-api/conversation" in req.url:
                        data = req.post_data_json
                        if isinstance(data, dict) and data.get("model"):
                            model_holder["model"] = data["model"]
                except Exception:
                    pass

            page.on("request", on_request)
            try:
                before = await page.locator(ASSISTANT).count()
                await self._send(page, prompt)
                await page.wait_for_function(
                    "n => document.querySelectorAll"
                    "('[data-message-author-role=assistant]').length > n",
                    arg=before,
                    timeout=config.ANSWER_TIMEOUT * 1000,
                )
                await self._wait_complete(page)
                text = await self._extract_answer(page)
            finally:
                page.remove_listener("request", on_request)

            # Prefer the answer's own model slug (data-message-model-slug);
            # fall back to the model from the outgoing request body.
            model = await self._last_assistant_slug(page) or model_holder.get("model")
            if config.STRICT_MODEL and model and "pro" not in model.lower():
                raise RuntimeError(
                    f"Refusing answer: active model is '{model}', not a Pro model. "
                    "Select GPT Pro in the bridge Chrome, or set GPT_PRO_MODEL_SLUG."
                )
            conv = None
            m = CONV_RE.search(page.url)
            if m:
                conv = m.group(1)
            return {"text": text, "model": model, "conversation_id": conv}

    async def _extract_answer(self, page):
        loc = page.locator(ASSISTANT).last  # .last is a property in Python Playwright
        md = loc.locator(".markdown")
        try:
            if await md.count():
                return (await md.last.inner_text()).strip()
        except Exception:
            pass
        return (await loc.inner_text()).strip()

    async def _send(self, page, prompt):
        composer = page.locator("#prompt-textarea")
        try:
            await composer.wait_for(state="visible", timeout=30000)
        except Exception:
            composer = page.get_by_role("textbox").first
            await composer.wait_for(state="visible", timeout=30000)
        await composer.click()
        try:
            await composer.fill(prompt)  # works on the contenteditable composer
        except Exception:
            await page.keyboard.insert_text(prompt)  # literal insert, no key handling
        for sel in ('[data-testid="send-button"]', 'button[aria-label*="Send" i]'):
            try:
                btn = page.locator(sel)
                if await btn.count() and await btn.first.is_enabled():
                    await btn.first.click()
                    return
            except Exception:
                continue
        await composer.press("Enter")  # fallback: Enter sends

    async def _wait_complete(self, page):
        # Done when the stop button is gone AND the answer text has stopped
        # changing for a few polls. Pure polling — never blocks on a single
        # locator state, so a selector drift can't hang the call.
        deadline = time.time() + config.ANSWER_TIMEOUT
        last, stable = None, 0
        needed = 4  # ~6s of no change
        while time.time() < deadline:
            try:
                generating = await page.locator('[data-testid="stop-button"]').count() > 0
            except Exception:
                generating = False
            try:
                cur = await self._extract_answer(page)
            except Exception:
                cur = None
            if not generating and cur and cur == last:
                stable += 1
                if stable >= needed:
                    return
            else:
                stable, last = 0, cur
            await asyncio.sleep(1.5)

    async def aclose(self):
        # Disconnect only; never close the user's real browser.
        try:
            if self._pw:
                await self._pw.stop()
        except Exception:
            pass
