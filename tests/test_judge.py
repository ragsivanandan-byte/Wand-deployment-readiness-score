"""Tests for the judge module."""
from __future__ import annotations

from harness.adapters import TestCase
from harness.config import Settings
from harness.judge import _safe_json, judge, rubric_hash


def test_rubric_hash_stable():
    h1 = rubric_hash()
    h2 = rubric_hash()
    assert h1 == h2
    assert len(h1) == 12


def test_safe_json_extracts_object():
    assert _safe_json('{"task_success": 1}') == {"task_success": 1}
    assert _safe_json('prose {"x": 1} more prose') == {"x": 1}
    assert _safe_json('no json here') == {}
    assert _safe_json('{"broken json') == {}


def test_judge_mock_pass():
    case = TestCase(
        id="t1", capability="writer", category="golden",
        prompt="p", context="c", expected="e",
        must_contain=["foo", "bar"], must_not_contain=["baz"],
    )
    settings = Settings(mode="mock", target_model="m", judge_model="j", api_key=None, run_id="r")
    output = "This contains foo and bar correctly."
    v = judge(case, output, settings=settings, client=None)
    assert v.task_success == 1
    assert v.hallucination_score <= 1


def test_judge_mock_hallucination():
    case = TestCase(
        id="t2", capability="writer", category="golden",
        prompt="p", context="c", expected="e",
        must_contain=["foo"], must_not_contain=["baz"],
    )
    settings = Settings(mode="mock", target_model="m", judge_model="j", api_key=None, run_id="r")
    output = "Contains foo but also the forbidden baz term."
    v = judge(case, output, settings=settings, client=None)
    assert v.task_success == 0
    assert v.hallucination_score >= 2
