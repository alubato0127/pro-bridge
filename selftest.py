"""Validate the CDP connection before wiring up MCP.

Run on the laptop (with the bridge Chrome already open and logged in):
    python selftest.py
It prints the page URL and the detected model. If you also pass a prompt:
    python selftest.py "Reply with one word: PONG"
it sends it and prints Pro's reply (this takes minutes on Pro).
"""
import asyncio
import sys

from pro_bridge.chatgpt import ChatGPTDriver


async def main():
    d = ChatGPTDriver()
    page = await d._get_page()
    print("Connected. Page URL:", page.url)
    print("Model (UI):", await d.current_model(page))
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        print(f"\nSending: {prompt!r}\n(waiting — Pro is slow)...")
        res = await d.ask(prompt)
        print("\n--- model:", res["model"], "conv:", res["conversation_id"], "---")
        print(res["text"])
    await d.aclose()


if __name__ == "__main__":
    asyncio.run(main())
