"""Adapter layer: how the harness talks to a target agent.

The harness is agent-agnostic. To evaluate a different system you implement
`TargetAdapter.run(test_case)` for your stack — REST call, LangGraph,
in-process Python, whatever — and return a `TargetResponse`.

We ship one concrete adapter: `FinanceWorkflowAdapter`, wired to the
multi-agent buy-side earnings workflow under `target_agent/`.
"""
from __future__ import annotations

import hashlib
import random
import time
from dataclasses import dataclass
from typing import Protocol

from anthropic import Anthropic

from harness.config import PRICING, Settings


@dataclass
class TestCase:
    __test__ = False  # tell pytest this isn't a test class

    id: str
    capability: str           # researcher / analyst / writer / reviewer / orchestrator
    category: str             # golden / adversarial / edge_case
    prompt: str
    context: str              # e.g. transcript excerpt
    expected: str             # reference answer or expected behaviour
    must_contain: list[str]   # substrings that MUST appear
    must_not_contain: list[str]  # red flags (hallucination markers, leaked PII, etc.)


@dataclass
class TargetResponse:
    output: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    model: str
    trace: list[dict]         # per-sub-agent step log, useful for the report

    def cost_usd(self) -> float:
        p = PRICING.get(self.model, {"input": 0.0, "output": 0.0})
        return (self.input_tokens / 1_000_000) * p["input"] + (
            self.output_tokens / 1_000_000
        ) * p["output"]


class TargetAdapter(Protocol):
    def run(self, case: TestCase) -> TargetResponse: ...


# --- Concrete adapter ---------------------------------------------------------


class FinanceWorkflowAdapter:
    """Calls the local multi-agent finance workflow.

    Lives here (not in target_agent/) because the adapter is the seam — the
    target agent itself doesn't know it's being evaluated.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = Anthropic(api_key=settings.api_key) if settings.mode == "live" else None

    def run(self, case: TestCase) -> TargetResponse:
        from target_agent.orchestrator import run_workflow
        return run_workflow(case, settings=self.settings, client=self._client)


# --- Shared LLM call helper ---------------------------------------------------


def call_llm(
    settings: Settings,
    client: Anthropic | None,
    *,
    system: str,
    user: str,
    model: str | None = None,
    max_tokens: int = 1024,
    role_label: str = "agent",
    mock_hints: dict | None = None,
) -> tuple[str, int, int, int]:
    """Single LLM call, used by every sub-agent and the judge.

    Returns (text, input_tokens, output_tokens, latency_ms).
    In mock mode produces deterministic pseudo-realistic text seeded by the
    user prompt so reruns are stable and tests are reproducible.

    `mock_hints` (mock mode only) lets the caller pass `must_contain` /
    `must_not_contain` lists so the mock can produce realistic
    pass/fail/hallucination cases rather than generic boilerplate.
    """
    model = model or settings.target_model
    start = time.perf_counter()

    if settings.mode == "mock":
        text, in_tok, out_tok = _mock_response(role_label, system, user, mock_hints or {})
        # Realistic latency profile: most calls 400-1200ms, occasional spike.
        seed = int(hashlib.sha256((user + role_label).encode()).hexdigest(), 16)
        rng = random.Random(seed)
        sim_latency = rng.randint(400, 1200)
        if rng.random() < 0.04:
            sim_latency += rng.randint(1500, 3500)
        time.sleep(0.001)  # keep wall-clock fast; the report uses sim_latency
        return text, in_tok, out_tok, sim_latency

    assert client is not None, "live mode requires Anthropic client"
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    latency_ms = int((time.perf_counter() - start) * 1000)
    return text, resp.usage.input_tokens, resp.usage.output_tokens, latency_ms


# --- Mock generation ----------------------------------------------------------
#
# The mock target is intentionally calibrated to produce a realistic outcome
# mix on the shipped test suite: ~85% task success, ~8–12% hallucination,
# a couple of instruction-following misses. This keeps the demo report
# substantive (failures to discuss) without looking broken.

def _mock_response(role: str, system: str, user: str, hints: dict) -> tuple[str, int, int]:
    seed = int(hashlib.sha256(user.encode()).hexdigest(), 16)
    rng = random.Random(seed)
    must_contain = hints.get("must_contain", []) or []
    must_not_contain = hints.get("must_not_contain", []) or []

    if role == "judge":
        text = _mock_judge(user, rng)
    else:
        text = _mock_target(role, must_contain, must_not_contain, rng)

    in_tok = max(200, len(user) // 4 + len(system) // 4)
    out_tok = max(80, len(text) // 4)
    return text, in_tok, out_tok


def _mock_target(role: str, must_contain: list[str], must_not_contain: list[str], rng: random.Random) -> str:
    """Generate target output that satisfies must_contain most of the time.

    Failure rates are tuned per role: researcher/analyst/reviewer are
    near-perfect (these are deterministic extraction/check steps in real
    systems), while the writer step carries most of the variance because
    it's where the LLM does open-ended generation.
    """
    # Per-role error profile. Numbers chosen so the end-to-end suite lands
    # comfortably inside the readiness thresholds with a few flagged cases.
    profile = {
        "writer":     {"halluc": 0.06, "incomplete": 0.05, "format": 0.02},
        "researcher": {"halluc": 0.02, "incomplete": 0.02, "format": 0.01},
        "analyst":    {"halluc": 0.02, "incomplete": 0.02, "format": 0.01},
        "reviewer":   {"halluc": 0.01, "incomplete": 0.01, "format": 0.01},
    }.get(role, {"halluc": 0.03, "incomplete": 0.03, "format": 0.02})

    bucket = rng.random()
    if bucket < profile["halluc"]:
        body = _render_clean(role, must_contain)
        if must_not_contain:
            body += f"\nAdditional commentary: {rng.choice(must_not_contain)}."
        else:
            body += "\nAdditional commentary: Revenue $99.9B (unsupported)."
        return body
    if bucket < profile["halluc"] + profile["incomplete"]:
        partial = must_contain[:-1] if len(must_contain) > 1 else must_contain
        return _render_clean(role, partial)
    if bucket < profile["halluc"] + profile["incomplete"] + profile["format"]:
        return " ".join(must_contain) + " — see transcript for full detail."
    return _render_clean(role, must_contain)


def _render_clean(role: str, tokens: list[str]) -> str:
    joined = ", ".join(tokens) if tokens else "—"
    if role == "researcher":
        return (
            "Key extractions from transcript:\n"
            f"- Headline figures: {joined}\n"
            "- Notes: figures sourced directly from prepared remarks and CFO commentary."
        )
    if role == "analyst":
        return (
            f"Beat/miss summary referencing {joined}. "
            "Direction and drivers are consistent with the extracted facts."
        )
    if role == "writer":
        return (
            "Quarterly note — quick take\n\n"
            f"The company reported results referencing {joined}. "
            "Management commentary and guidance language are consistent with the transcript. "
            "We frame the rating in line with the directional read from the analyst step."
        )
    if role == "reviewer":
        if any(t.upper() == "FAIL" for t in tokens):
            return "FAIL: numbers in the note do not reconcile to the transcript."
        if any(t.upper() == "PASS" for t in tokens):
            return "PASS — numbers cross-check; no additional flags."
        return f"PASS — numbers cross-check. References checked: {joined}."
    return f"[mock {role}] {joined}"


def _mock_judge(user: str, rng: random.Random) -> str:
    """Use the marker the judge module embeds to decide pass/fail."""
    quality_good = "MOCK_QUALITY=good" in user
    if quality_good:
        ts = 1
        hs = 0 if rng.random() > 0.08 else 1
        if_score = 3 if rng.random() > 0.12 else 2
        rationale = "Output is grounded in the transcript and respects the required format."
    else:
        # Look for the more granular signal we embed: HINT_HALLUC / HINT_FORMAT
        if "HINT_HALLUC=1" in user:
            ts = 0
            hs = rng.choice([2, 3])
            if_score = rng.choice([1, 2])
            rationale = "Output contains numbers or claims that are not present in the source transcript."
        else:
            ts = 0
            hs = rng.choice([1, 2])
            if_score = rng.choice([0, 1])
            rationale = "Output is missing required content or violates the requested format."
    return (
        f'{{"task_success": {ts}, "hallucination_score": {hs}, '
        f'"instruction_following": {if_score}, "rationale": "{rationale}"}}'
    )
