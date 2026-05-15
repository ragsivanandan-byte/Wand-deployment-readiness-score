"""Entry point: `python -m harness.run`.

Loads test cases, runs the target agent + judge on each, renders the HTML
report, persists raw JSON. Honours HARNESS_MODE=mock|live.
"""
from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone

from harness.config import Settings
from harness.report import render
from harness.runner import run_suite


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


def main() -> int:
    run_id = _run_id()
    settings = Settings.from_env(run_id=run_id)
    print(f"Wand Deployment Readiness Harness")
    print(f"  run_id: {run_id}")
    print(f"  mode:   {settings.mode}")
    print(f"  target: {settings.target_model}")
    print(f"  judge:  {settings.judge_model}")
    print("Running suite...")
    payload = run_suite(settings)
    print("Rendering report...")
    out = render(payload, commit_sha=_commit_sha())
    print(f"  → {out.relative_to(out.parent.parent)}")
    print(f"  → reports/latest/index.html")
    # Surface the verdict on stdout so CI logs make it obvious.
    from harness.report import aggregate, go_no_go
    verdict, _ = go_no_go(aggregate(payload["results"]))
    print(f"VERDICT: {verdict}")
    return 0 if verdict == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
