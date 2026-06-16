"""Step-by-step ask, with prints, to locate where it stalls.

    python debug_ask.py "Reply with one word: PONG"
"""
import asyncio
import sys

from pro_bridge.chatgpt import ChatGPTDriver

ASSIST = '[data-message-author-role="assistant"]'


async def main():
    prompt = " ".join(sys.argv[1:]) or "Reply with exactly one word: PONG"
    d = ChatGPTDriver()
    page = await d._get_page()
    print("URL:", page.url)
    print("pages in context:",
          [p.url for p in page.context.pages])

    before = await page.locator(ASSIST).count()
    print("assistant count BEFORE:", before)

    print("sending...")
    await d._send(page, prompt)
    print("sent. polling assistant count for 90s...")

    for i in range(45):
        await asyncio.sleep(2)
        cnt = await page.locator(ASSIST).count()
        try:
            gen = await page.locator('[data-testid="stop-button"]').count()
        except Exception:
            gen = -1
        slug = await d._last_assistant_slug(page)
        ans = ""
        try:
            ans = (await d._extract_answer(page))[:40].replace("\n", " ")
        except Exception as e:
            ans = f"<err {e}>"
        print(f"[{i*2:3d}s] url={page.url[-12:]} count={cnt} stopbtn={gen} "
              f"slug={slug} ans={ans!r}")
        if cnt > before and gen == 0 and ans:
            print(">>> looks complete")
            break

    await d.aclose()


if __name__ == "__main__":
    asyncio.run(main())
