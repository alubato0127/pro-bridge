"""Deep DOM probe (sends nothing). Finds message + send-button selectors.

Run on the laptop with the bridge Chrome open on chatgpt.com:
    python probe_dom.py
Paste the output back.
"""
import asyncio
import json

from pro_bridge.chatgpt import ChatGPTDriver

MSG_SELECTORS = [
    '[data-message-author-role="assistant"]',
    '[data-message-author-role]',
    '[data-message-id]',
    '[data-testid^="conversation-turn"]',
    'article',
    'main article',
    '.markdown',
    'main .markdown',
]


async def counts(page):
    for sel in MSG_SELECTORS:
        try:
            print(f"  {sel!r}: {await page.locator(sel).count()}")
        except Exception as e:
            print(f"  {sel!r}: ERR {e}")


async def main():
    d = ChatGPTDriver()
    page = await d._get_page()

    # Open an existing conversation and WAIT for messages to hydrate.
    href = await page.evaluate(
        "() => { const a = document.querySelector('a[href*=\"/c/\"]'); return a ? a.href : null; }"
    )
    if href:
        print("Opening:", href)
        await page.goto(href.split("?")[0], wait_until="domcontentloaded")
        # wait until something message-like shows up
        for _ in range(20):
            n = await page.locator("main article, .markdown, [data-message-id]").count()
            if n:
                break
            await asyncio.sleep(1)
        await asyncio.sleep(2)

    print("\nURL:", page.url)
    print("--- message selector counts ---")
    await counts(page)

    # Dump opening tags (attributes) of the last 2 turn-ish containers.
    tags = await page.evaluate(
        """() => {
            const pick = document.querySelectorAll('main article, [data-message-id], .markdown');
            const arr = Array.from(pick).slice(-2);
            return arr.map(el => {
                const a = {};
                for (const at of el.attributes) a[at.name] = at.value;
                return {tag: el.tagName.toLowerCase(), attrs: a,
                        textHead: (el.innerText||'').trim().slice(0,60)};
            });
        }"""
    )
    print("\n--- last 2 message-ish containers ---")
    for t in tags:
        print(json.dumps(t, ensure_ascii=False))

    # Reveal the send button by typing, then clear (no send).
    print("\n--- composer buttons while text present ---")
    try:
        comp = page.locator('#prompt-textarea')
        await comp.click()
        await comp.fill("probe (not sent)")
        await asyncio.sleep(1)
        btns = await page.evaluate(
            """() => Array.from(document.querySelectorAll('button,[role=button]')).map(b => ({
                testid: b.getAttribute('data-testid'),
                aria: b.getAttribute('aria-label')
            })).filter(b => {
                const s = ((b.testid||'')+' '+(b.aria||'')).toLowerCase();
                return s.includes('send') || s.includes('stop') || s.includes('composer') || s.includes('submit');
            })"""
        )
        for b in btns:
            print(json.dumps(b, ensure_ascii=False))
        await comp.fill("")  # clear so nothing is sent
    except Exception as e:
        print("composer probe ERR:", e)

    await d.aclose()


if __name__ == "__main__":
    asyncio.run(main())
