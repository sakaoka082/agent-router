# Delegation Log

`agent_router.py log` appends records here. You can also write them by hand —
the format is the contract, not the tool.

Copy the block below to start one manually:

```md
## Task — 2026-01-01T00:00:00+09:00
- requested: claude
- assigned:  deepseek
- reason:    claude limited
- risk:      review
- status:    queued

### Instruction
<exactly what the assigned agent must do — and must NOT do (e.g. "do not post externally")>

### Review
Verify with the premium agent after it returns.

---
```

Why log at all: a delegated task is unverified material until a premium agent
checks it. The log is what lets that check actually happen later instead of the
cheap output silently becoming "done".
