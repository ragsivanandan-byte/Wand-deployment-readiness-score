"""Entry point: `python -m harness.run`.

Loads test cases, runs the target agent + judge on each, renders the HTML
report, persists raw JSON. Honours HARNESS_MODE=mock|live.

CLI flags:
  --category    {golden,adversarial,edge_cases}   filter cases by category
  --capability  <name>                             filter cases by capability
  --limit N                                        run only the first N cases
  --list                                           list cases and exit without running
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone

from harness.config import Settings
from harness.report import render
from harness.runner import load_test_cases, run_suite

CAPABILITY_CHOICES = ["researcher", "analyst", "writer", "reviewer", "orchestrator"]


def _run_id() -> str:
    return os.environ.get("HARNESS_RUN_ID") or datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")


def _commit_sha() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception:
        return None


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="harness.run", description=__doc__.splitlines()[0])
    p.add_argument("--category", choices=["golden", "adversarial", "edge_cases"])
    p.add_argument("--capability", choices=CAPABILITY_CHOICES)
    p.add_argument("--limit", type=int)
    p.add_argument("--list", action="store_true", help="List matching cases and exit")
    return p.parse_args()


def _list_cases(args: argparse.Namespace) -> int:
    cases = load_test_cases()
    if args.category:
        cases = [c for c in cases if c.category == args.category]
    if args.capability:
        cases = [c for c in cases if c.capability == args.capability]
    if args.limit is not None:
        cases = cases[: args.limit]
    if not cases:
        print("0 cases match the supplied filters.")
        return 1
    print(f"{len(cases)} cases:")
    for c in cases:
        print(f"  {c.id:<40} {c.category:<12} {c.capability}")
    return 0


def _run(args: argparse.Namespace) -> int:
    run_id = _run_id()
    settings = Settings.from_env(run_id=run_id)
    print("Wand Deployment Readiness Harness")
    print(f"  run_id: {run_id}")
    print(f"  mode:   {settings.mode}")
    print(f"  target: {settings.target_model}")
    print(f"  judge:  {settings.judge_model}")
    if args.category or args.capability or args.limit:
        print(f"  filter: category={args.category} capability={args.capability} limit={args.limit}")
    print("Running suite...")
    payload = run_suite(
        settings,
        category=args.category,
        capability=args.capability,
        limit=args.limit,
    )
    print("Rendering report...")
    out = render(payload, commit_sha=_commit_sha())
    print(f"  → {out.relative_to(out.parent.parent)}")
    print("  → reports/latest/index.html")
    from harness.report import aggregate, go_no_go
    verdict, _ = go_no_go(aggregate(payload["results"]))
    print(f"VERDICT: {verdict}")
    return 0 if verdict == "GO" else 1


def main() -> int:
    args = _parse_args()
    try:
        if args.list:
            return _list_cases(args)
        return _run(args)
    except (RuntimeError, ValueError, FileNotFoundError) as e:
        # Surface configuration / data errors as a one-line message, not a
        # stack trace — the harness is invoked by non-technical operators.
        print(f"\nharness.run: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
