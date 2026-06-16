---
description: High-stakes debate with GPT Pro (web, via pro-bridge MCP) — few rounds, deep, then synthesize
argument-hint: [question or decision; defaults to current context/selection]
allowed-tools: mcp__gpt-pro__ask_gpt_pro, Read, Grep, Glob, Bash
---

You are running a high-stakes debate between **yourself (Claude)** and **GPT Pro**
(OpenAI's strongest web-only reasoning model, reachable via the
`mcp__gpt-pro__ask_gpt_pro` tool through the pro-bridge MCP server).

## Topic
$ARGUMENTS

If empty, infer it from the current conversation, the user's IDE selection, and
the open files. State the topic explicitly before starting.

## Why this command exists
GPT Pro is the heavy artillery — bring it in for genuinely hard or high-stakes
decisions. It reasons for **several minutes per turn**, so keep rounds few and
each message dense and self-contained.

## Protocol
1. **Frame & position.** Write a tight statement of the question and what a good
   answer must satisfy. Take your own reasoned position first.
2. **Round 1 (open).** Call `mcp__gpt-pro__ask_gpt_pro` with: the framing, ALL
   the concrete context Pro needs (paste the actual code, errors, constraints —
   Pro shares none of your history), your position, and a request for Pro's own
   position plus its strongest objection to yours. **Save the `conversation_id`**
   from the result.
3. **Round 2 (rebut).** Call `ask_gpt_pro` again **passing that
   `conversation_id`** so Pro remembers round 1. Steelman Pro's best point,
   concede what's right, then push back on the weakest load-bearing claim with
   specific evidence (run code, read files, cite line numbers).
4. **Default to 2 rounds** (open + rebut). Add a 3rd only if a crux is still
   genuinely unresolved. Do not pad — Pro turns are expensive.
5. **Synthesize.** End with: points of **agreement**, remaining
   **disagreements** (and each side's reason), and **your recommendation** with a
   confidence level. Say honestly if Pro changed your mind.

## Rules
- Each `ask_gpt_pro` call BLOCKS for minutes — tell the user you're waiting on
  Pro before each call, and show its reply when it returns.
- Always thread rounds with the same `conversation_id`; a fresh call with no id
  starts Pro over with no memory of the debate.
- The tool verifies the model is actually Pro; if it errors about the model,
  surface that to the user (their bridge Chrome may have a non-Pro model
  selected) rather than retrying blindly.
- Every message to Pro must be self-contained (re-include code/snippets each
  round as needed). Don't just relay Pro verbatim — engage critically.
- If `mcp__gpt-pro__ask_gpt_pro` is unavailable, tell the user the pro-bridge
  server/Chrome on their laptop probably isn't running (see ~/pro-bridge/README).
