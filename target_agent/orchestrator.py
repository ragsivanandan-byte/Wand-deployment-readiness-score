"""The thing being evaluated: a 4-step buy-side earnings workflow.

researcher → analyst → writer → reviewer

Each step is one LLM call. The orchestrator is plain Python — no LangGraph,
no DAG framework. A non-technical reader can follow the control flow.
"""
from __future__ import annotations

from anthropic import Anthropic

from harness.adapters import TargetResponse, TestCase, call_llm
from harness.config import Settings

RESEARCHER_SYSTEM = (
    "You are a buy-side equity research associate. Extract from the earnings call "
    "transcript ONLY the following facts, one per line, no preamble:\n"
    "- Revenue (with consensus comparison if stated)\n"
    "- EPS (with consensus comparison if stated)\n"
    "- Forward guidance change (raised / maintained / lowered / not given)\n"
    "- One notable management quote, verbatim, in quotes.\n"
    "If a fact is not in the transcript, write 'not disclosed'. Do NOT invent numbers."
)

ANALYST_SYSTEM = (
    "You are a sell-side analyst writing a 2-sentence beat/miss summary. "
    "Compare reported metrics to consensus, classify guidance direction, and "
    "name the main driver. Use only the facts in the input — do not add new "
    "numbers."
)

WRITER_SYSTEM = (
    "You are a portfolio manager writing a 4-sentence client-facing note. "
    "Headline + reported metrics vs consensus + guidance + a directional rating "
    "(constructive / neutral / cautious). Keep it under 120 words. No new numbers."
)

REVIEWER_SYSTEM = (
    "You are a compliance reviewer. Check that every number in the note appears "
    "in the source transcript. Output exactly one line: 'PASS' if all numbers "
    "cross-check, otherwise 'FAIL: <reason>'. Then list any other flags."
)


def run_workflow(
    case: TestCase,
    *,
    settings: Settings,
    client: Anthropic | None,
) -> TargetResponse:
    trace: list[dict] = []
    total_in = total_out = total_latency = 0

    hints = {"must_contain": case.must_contain, "must_not_contain": case.must_not_contain}

    def step(role: str, system: str, user: str) -> str:
        nonlocal total_in, total_out, total_latency
        text, i_tok, o_tok, lat = call_llm(
            settings, client,
            system=system, user=user,
            model=settings.target_model,
            role_label=role,
            mock_hints=hints,
        )
        total_in += i_tok
        total_out += o_tok
        total_latency += lat
        trace.append({
            "step": role,
            "latency_ms": lat,
            "input_tokens": i_tok,
            "output_tokens": o_tok,
            "output_preview": text[:240],
        })
        return text

    research = step("researcher", RESEARCHER_SYSTEM,
                    f"TRANSCRIPT:\n{case.context}\n\nQUESTION: {case.prompt}")
    analysis = step("analyst", ANALYST_SYSTEM,
                    f"EXTRACTED FACTS:\n{research}")
    note = step("writer", WRITER_SYSTEM,
                f"ANALYST SUMMARY:\n{analysis}\n\nQUESTION: {case.prompt}")
    review = step("reviewer", REVIEWER_SYSTEM,
                  f"TRANSCRIPT:\n{case.context}\n\nNOTE:\n{note}")

    final_output = f"=== NOTE ===\n{note}\n\n=== COMPLIANCE REVIEW ===\n{review}"

    return TargetResponse(
        output=final_output,
        latency_ms=total_latency,
        input_tokens=total_in,
        output_tokens=total_out,
        model=settings.target_model,
        trace=trace,
    )
