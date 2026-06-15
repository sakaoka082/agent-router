# agent-router

A tiny, dependency-free CLI that decides which AI agent should take the next task when one of your agents hits its usage limit — and refuses to route work a cheaper model has no business doing.

Pure Python 3, standard library only. No `pip install`, no API keys, no network calls. State lives in one JSON file you own.

## The problem

If you run more than one AI coding agent, you've hit this: the strong one (Claude, Codex, whatever) reaches its usage limit mid-session and your whole flow stalls — including the parts that never needed the strong model. So you wait, or you start hand-routing tasks in your head.

agent-router makes that decision explicit and deterministic, so one agent's limit doesn't block the whole team.

## Install

```
git clone https://github.com/sakaoka082/agent-router
cd agent-router
python3 agent_router.py init
```

That's it. Python 3 is the only requirement.

## Use it

```
# tell the router an agent is limited
python3 agent_router.py set claude limited --reason "session limit" --fallback deepseek

# ask who should take a low-risk task
python3 agent_router.py route claude --risk review --task "draft 10 posts"
# -> deepseek

# judgement work is never handed to a cheap standby
python3 agent_router.py route claude --risk judge
# -> NO_ROUTE   (wait or escalate — don't let a cheap model decide)

# irreversible actions are never auto-routed
python3 agent_router.py route claude --risk publish
# -> HUMAN_APPROVAL_REQUIRED
```

See [`examples/sample_session.md`](examples/sample_session.md) for a full start-to-finish walkthrough.

## The model

Work splits into lanes by who should do it:

| work | lane |
|---|---|
| judgement, design, code review, final sign-off | your strong model (Claude / Codex) |
| drafts, classification, summaries, batch work | a cheap model (DeepSeek / Gemini / …) |
| anything irreversible — publish, payment, delete, credentials | **you**, by hand |

Routing rules:

- An explicitly requested agent is a *preference*, not a guarantee.
- `limited` / `down` / `unknown` agents are never given work directly — the router follows the `fallback` chain to an `available` or `standby` agent.
- Judgement-risk work is never sent down a cheap lane. If no premium agent is available, the honest answer is "wait or escalate," not "let the cheap model guess."
- `publish` / `payment` / `delete` / `credential` risk is **hardcoded** to `HUMAN_APPROVAL_REQUIRED` — not configurable.
- Every delegation can be logged, with a reminder to review the cheap output before calling it done.

## A few things I got wrong (so you don't)

- **A reasoning model can return an empty response when it runs out of output budget.** A light prompt works, a heavy one comes back blank — it spent its whole budget thinking. Raising the output limit fixed it.
- **A background job's "success" exit code can lie.** A trailing command can overwrite the real failure. Decide "done" by checking the artifact you expected actually exists — not by the exit code alone.
- **An empty log isn't proof of death.** If a tool only writes on error, an empty log means quiet success. Judge liveness by the freshness of what the tool produces, not its stdout.
- **Always tell a cheaper model: "write 'no evidence' for anything you can't support."** That one instruction turns a knowledge gap into a flagged gap instead of a confident fabrication you have to catch later.

## Honest scope

This does **not** remove, raise, or bypass any usage limit. Those are unchanged. It's a small, readable routing tool plus the method behind it — for staying productive, and safe, within whatever limits you have. It's ~250 lines of plain Python: read it, fork it, change the rules to fit your own setup.

## License

MIT — see [LICENSE](LICENSE). Use it, fork it, ship it.

---

*If you want the extended write-up — more worked scenarios and additional templates — there's a small paid pack: <https://sakaoka.gumroad.com/l/wllgxa>. Everything you need to actually use agent-router is already in this repo.*
