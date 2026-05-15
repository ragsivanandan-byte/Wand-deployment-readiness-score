"""LLM-as-judge with a versioned rubric.

The rubric version is hashed into the report so a reviewer can tell if two
runs are comparable.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from anthropic import Anthropic

from harness.adapters import TestCase, call_llm
from harness.config import Settings

RUBRIC_VERSION = "v1.0"

JUDGE_SYSTEM = """You are a strict evaluator of a multi-agent finance workflow.
You will receive:
  - the test case (prompt, source context, expected answer, must_contain/must_not_contain)
  - the agent's full output

Score the output on three axes. Return a SINGLE JSON object, no prose:

{
  "task_success": 0 | 1,                // 1 iff the output substantively answers the prompt using the source context
  "hallucination_score": 0 | 1 | 2 | 3, // 0 = fully grounded, 3 = severe unsupported claims
  "instruction_following": 0 | 1 | 2 | 3, // 0 = ignores format/length/scope rules, 3 = perfect
  "rationale": "<one sentence>"
}

Hard rules:
  - Numbers in the output that are NOT in the source context = hallucination ≥ 2.
  - Missing any item from must_contain = task_success = 0.
  - Any item from must_not_contain present = task_success = 0 and hallucination_score = 3.
  - Output longer than 200 words when a short note was requested = instruction_following ≤ 1.
"""


@dataclass
class JudgeVerdict:
    task_success: int
    hallucination_score: int   # 0–3
    instruction_following: int # 0–3
    rationale: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


def rubric_hash() -> str:
    return hashlib.sha256((RUBRIC_VERSION + JUDGE_SYSTEM).encode()).hexdigest()[:12]


def judge(
    case: TestCase,
    agent_output: str,
    *,
    settings: Settings,
    client: Anthropic | None,
) -> JudgeVerdict:
    # Embed quality hints so mock mode produces a realistic spread; the live
    # judge ignores HTML comments and judges the actual output.
    must_contain_ok = all(m.lower() in agent_output.lower() for m in case.must_contain)
    forbidden_hit = any(m.lower() in agent_output.lower() for m in case.must_not_contain)
    quality_marker = "good" if must_contain_ok and not forbidden_hit else "bad"
    halluc_hint = 1 if forbidden_hit else 0

    user = (
        f"# TEST CASE\nid: {case.id}\ncapability: {case.capability}\n"
        f"category: {case.category}\nprompt: {case.prompt}\n\n"
        f"# SOURCE CONTEXT\n{case.context}\n\n"
        f"# EXPECTED\n{case.expected}\n\n"
        f"# MUST_CONTAIN\n{case.must_contain}\n\n"
        f"# MUST_NOT_CONTAIN\n{case.must_not_contain}\n\n"
        f"# AGENT OUTPUT\n{agent_output}\n\n"
        f"<!-- MOCK_QUALITY={quality_marker} HINT_HALLUC={halluc_hint} -->"
    )

    text, in_tok, out_tok, lat = call_llm(
        settings, client,
        system=JUDGE_SYSTEM, user=user,
        model=settings.judge_model,
        role_label="judge",
        max_tokens=400,
    )

    parsed = _safe_json(text)
    return JudgeVerdict(
        task_success=int(parsed.get("task_success", 0)),
        hallucination_score=int(parsed.get("hallucination_score", 3)),
        instruction_following=int(parsed.get("instruction_following", 0)),
        rationale=str(parsed.get("rationale", "judge returned unparseable output"))[:240],
        input_tokens=in_tok,
        output_tokens=out_tok,
        latency_ms=lat,
    )


def _safe_json(text: str) -> dict:
    """Pull the first JSON object out of the judge's reply. Tolerant of prose."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
