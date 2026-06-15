# Sample session — one real limit hit, start to finish

This is the whole loop with real commands and the real output the tool prints.
Run it yourself — `python3 agent_router.py` from the repo root.

## 1. Set up your roster once

```
$ python3 agent_router.py init
wrote starter roster to agent_status.json

$ python3 agent_router.py get
claude    available -> deepseek   primary: judgement, design, code edits, final review
codex     standby   -> deepseek   secondary premium worker for code
deepseek  standby                 cheap: drafts, classification, summaries, batch work
gemini    unknown   -> deepseek   verify CLI/login before use
```

## 2. Claude hits its session limit

```
$ python3 agent_router.py set claude limited --reason "session limit · resets 7:30pm" --fallback deepseek
claude: limited  (fallback -> deepseek)
```

## 3. You have three pending tasks. Ask the router about each.

**Task A — draft 10 launch posts (low risk):**
```
$ python3 agent_router.py route claude --risk review --task "draft 10 launch posts" --explain
deepseek
  reason: deepseek is standby
  task:   draft 10 launch posts
```
→ Hand it to DeepSeek. Cheap, reviewable later.

**Task B — decide the pricing model (judgement):**
```
$ python3 agent_router.py route claude --risk judge --explain
NO_ROUTE
  reason: no fallback configured — chain exhausted
```
→ The router refuses to send judgement work to a cheap standby lane. With Claude
limited and no other *available premium* agent, the honest answer is "wait, or
escalate" — not "let the cheap model decide your pricing." This stop is the point.

**Task C — publish the product to the store:**
```
$ python3 agent_router.py route claude --risk publish --explain
HUMAN_APPROVAL_REQUIRED
  reason: risk='publish' is never auto-routed
```
→ Never auto-routed, regardless of who is available. You approve, by hand.

## 4. Log the one you delegated

```
$ python3 agent_router.py log \
    --requested claude --assigned deepseek \
    --reason "claude limited" --risk review \
    --instruction "Draft 10 launch posts. Do NOT post anything externally."
appended delegation record to delegation_log.md
```

`delegation_log.md` now holds the record, with a Review line reminding you to
verify DeepSeek's drafts once Claude is back. The cheap output is not "done"
until that check happens.

## What you just avoided

- You did **not** stall for two hours waiting for the reset.
- You did **not** let a cheap model make a pricing call it has no business making.
- You did **not** auto-publish anything.
- You have a written trail of what was delegated and why.
