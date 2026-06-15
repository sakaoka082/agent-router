#!/usr/bin/env python3
"""
Claude Code Limit Survival Kit — agent_router
=============================================

A tiny, dependency-free CLI that turns the "3-lane routing" method from the
guide into something you actually run. When Claude Code hits its usage limit,
this tells you — deterministically — which agent should pick up the next task,
or whether the task must stop for human approval.

No pip install. No API keys. Pure Python 3 standard library. State lives in a
single JSON file you own (default: ./agent_status.json).

QUICK START
-----------
    python3 agent_router.py init
    python3 agent_router.py set claude limited --reason "session limit" --fallback deepseek
    python3 agent_router.py route claude --task "draft 10 posts" --risk review
    # -> deepseek   (because claude is limited and the task is low-risk)

    python3 agent_router.py route claude --task "publish to production" --risk publish
    # -> HUMAN_APPROVAL_REQUIRED   (never auto-routed)

COMMANDS
--------
  init                         create a starter agent_status.json
  set <agent> <state>          update one agent (states below)
  get [agent]                  print current status (all, or one agent)
  route <requested> --risk R   resolve who should take the task
  log ...                      append a delegation record to delegation_log.md

STATES
------
  available  ready to take work
  standby    healthy but reserved for low-risk / batch work (e.g. cheap models)
  limited    rate/usage limited — do not send new work, follow fallback
  down       unreachable / errored — follow fallback
  unknown    login or health not verified — must be checked before use

RISK LEVELS (drive the routing decision)
----------------------------------------
  judge      needs the strongest model's judgement -> only available premium agents
  review     low-risk draft; a premium agent will review later -> fallback OK
  publish | payment | credential | delete
             irreversible / sensitive -> ALWAYS returns HUMAN_APPROVAL_REQUIRED
"""

import argparse
import datetime
import json
import os
import sys

DEFAULT_STATE_FILE = "agent_status.json"
DEFAULT_LOG_FILE = "delegation_log.md"

VALID_STATES = ("available", "standby", "limited", "down", "unknown")
ROUTABLE_STATES = ("available", "standby")  # states that can actually take work
HUMAN_ONLY_RISKS = ("publish", "payment", "credential", "delete")

# A sensible starter roster. Edit freely — this is YOUR file.
STARTER = {
    "claude": {
        "state": "available",
        "reason": "primary: judgement, design, code edits, final review",
        "fallback": "deepseek",
    },
    "codex": {
        "state": "standby",
        "reason": "secondary premium worker for code",
        "fallback": "deepseek",
    },
    "deepseek": {
        "state": "standby",
        "reason": "cheap: drafts, classification, summaries, batch work",
        "fallback": None,
    },
    "gemini": {
        "state": "unknown",
        "reason": "verify CLI/login before use",
        "fallback": "deepseek",
    },
}


def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _load(path):
    if not os.path.exists(path):
        sys.exit(
            f"error: {path} not found. Run `python3 {os.path.basename(__file__)} init` first."
        )
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        sys.exit(f"error: could not read {path}: {exc}")


def _save(path, data):
    data["_updated"] = _now()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def cmd_init(args):
    if os.path.exists(args.file) and not args.force:
        sys.exit(f"refusing to overwrite existing {args.file} (use --force)")
    data = {"_updated": _now(), "agents": json.loads(json.dumps(STARTER))}
    _save(args.file, data)
    print(f"wrote starter roster to {args.file}")
    print("edit it, then try:  python3 agent_router.py route claude --risk review")


def cmd_set(args):
    if args.state not in VALID_STATES:
        sys.exit(f"invalid state '{args.state}'. valid: {', '.join(VALID_STATES)}")
    data = _load(args.file)
    agents = data.setdefault("agents", {})
    entry = agents.setdefault(args.agent, {"state": "unknown", "reason": "", "fallback": None})
    entry["state"] = args.state
    if args.reason is not None:
        entry["reason"] = args.reason
    if args.fallback is not None:
        entry["fallback"] = args.fallback or None
    _save(args.file, data)
    print(f"{args.agent}: {args.state}" + (f"  (fallback -> {entry.get('fallback')})" if entry.get("fallback") else ""))


def cmd_get(args):
    data = _load(args.file)
    agents = data.get("agents", {})
    if args.agent:
        if args.agent not in agents:
            sys.exit(f"unknown agent '{args.agent}'")
        print(json.dumps({args.agent: agents[args.agent]}, indent=2, ensure_ascii=False))
        return
    width = max((len(a) for a in agents), default=6)
    for name, e in agents.items():
        fb = f" -> {e.get('fallback')}" if e.get("fallback") else ""
        print(f"{name:<{width}}  {e.get('state','?'):<9}{fb}   {e.get('reason','')}")


def _resolve(agents, start, risk, _visited=None):
    """Walk the fallback chain until we find a routable agent. Cycle-safe."""
    if risk in HUMAN_ONLY_RISKS:
        return ("HUMAN_APPROVAL_REQUIRED", f"risk='{risk}' is never auto-routed")
    if _visited is None:
        _visited = []
    if start is None:
        return (None, "no fallback configured — chain exhausted")
    if start in _visited:
        return (None, "fallback cycle detected: " + " -> ".join(_visited + [start]))
    _visited.append(start)
    entry = agents.get(start)
    if entry is None:
        return (None, f"agent '{start}' not in roster")
    state = entry.get("state", "unknown")
    if state in ROUTABLE_STATES:
        # 'judge' work must go to a premium, available agent — never to standby cheap lane
        if risk == "judge" and state != "available":
            return _resolve(agents, entry.get("fallback"), risk, _visited)
        return (start, f"{start} is {state}")
    # not routable -> follow fallback
    return _resolve(agents, entry.get("fallback"), risk, _visited)


def cmd_route(args):
    data = _load(args.file)
    agents = data.get("agents", {})
    if args.requested not in agents and args.risk not in HUMAN_ONLY_RISKS:
        sys.exit(f"unknown agent '{args.requested}' (add it with `set` first)")
    target, why = _resolve(agents, args.requested, args.risk)
    if target is None:
        print("NO_ROUTE", file=sys.stderr)
        print(f"  reason: {why}", file=sys.stderr)
        sys.exit(2)
    print(target)
    if args.explain:
        print(f"  reason: {why}", file=sys.stderr)
        if args.task:
            print(f"  task:   {args.task}", file=sys.stderr)
    return 0


def cmd_log(args):
    risk = args.risk or "review"
    record = (
        f"## Task — {_now()}\n"
        f"- requested: {args.requested}\n"
        f"- assigned:  {args.assigned}\n"
        f"- reason:    {args.reason or ''}\n"
        f"- risk:      {risk}\n"
        f"- status:    {args.status or 'queued'}\n\n"
        f"### Instruction\n{args.instruction or ''}\n\n"
        f"### Review\n{'HUMAN APPROVAL REQUIRED before any external effect.' if risk in HUMAN_ONLY_RISKS else 'Verify with the premium agent after it returns.'}\n\n"
        f"---\n\n"
    )
    with open(args.logfile, "a", encoding="utf-8") as fh:
        fh.write(record)
    print(f"appended delegation record to {args.logfile}")


def build_parser():
    p = argparse.ArgumentParser(
        prog="agent_router.py",
        description="Route work across AI agents when Claude Code hits its limit.",
    )
    p.add_argument("--file", default=DEFAULT_STATE_FILE, help=f"state file (default: {DEFAULT_STATE_FILE})")
    sub = p.add_subparsers(dest="cmd", required=True)

    s_init = sub.add_parser("init", help="create a starter agent_status.json")
    s_init.add_argument("--force", action="store_true", help="overwrite if it exists")
    s_init.set_defaults(func=cmd_init)

    s_set = sub.add_parser("set", help="update one agent's state")
    s_set.add_argument("agent")
    s_set.add_argument("state", help="one of: " + ", ".join(VALID_STATES))
    s_set.add_argument("--reason")
    s_set.add_argument("--fallback", help="agent to fall back to ('' to clear)")
    s_set.set_defaults(func=cmd_set)

    s_get = sub.add_parser("get", help="print status")
    s_get.add_argument("agent", nargs="?")
    s_get.set_defaults(func=cmd_get)

    s_route = sub.add_parser("route", help="resolve who should take a task")
    s_route.add_argument("requested", help="the agent you wanted to use")
    s_route.add_argument("--risk", default="review", help="judge|review|publish|payment|credential|delete")
    s_route.add_argument("--task", help="optional task description (printed with --explain)")
    s_route.add_argument("--explain", action="store_true", help="print the reason to stderr")
    s_route.set_defaults(func=cmd_route)

    s_log = sub.add_parser("log", help="append a delegation record")
    s_log.add_argument("--requested", required=True)
    s_log.add_argument("--assigned", required=True)
    s_log.add_argument("--reason")
    s_log.add_argument("--risk")
    s_log.add_argument("--status")
    s_log.add_argument("--instruction")
    s_log.add_argument("--logfile", default=DEFAULT_LOG_FILE)
    s_log.set_defaults(func=cmd_log)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
