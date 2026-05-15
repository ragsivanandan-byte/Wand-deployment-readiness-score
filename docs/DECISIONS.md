# Design decisions

Short rationales for the choices that aren't obvious from the code.

## Finance vertical

The shipped test suite is buy-side earnings analysis. It plays to the
author's FactSet background and avoids the saturated "support chatbot"
example. Swapping verticals is a one-file change (`harness/adapters.py`
+ new YAML); the harness itself is domain-agnostic.

## No agent framework

We could have used LangChain / LangGraph / CrewAI for the target agent.
We didn't because:

1. **Readability** — the orchestrator is 50 lines a non-technical
   reviewer can read end-to-end. A graph DSL would hide that.
2. **Debuggability** — each sub-agent is a single LLM call with a
   visible system prompt. No middleware, no callbacks, no retry policy
   surprises.
3. **The harness is the product** — the target agent is intentionally
   simple so the eye lands on the eval scaffolding, which is what we're
   actually selling.

If you replace the target with a LangGraph workflow, only the adapter
changes.

## LLM-as-judge over rule-based scoring

We do both. The `must_contain` / `must_not_contain` lists catch obvious
regressions cheaply. The LLM judge catches the qualitative failures —
"the right number but the wrong framing", "technically correct but
violates the requested format". The combo is more robust than either
alone, and it mirrors what a senior engineer would do reviewing the
output themselves.

The judge runs on **claude-sonnet-4-6** because the rubric needs
reasoning. The target agent runs on **claude-haiku-4-5** because it's
the cheap workhorse and the judge will catch its mistakes.

## Rubric versioning

Every report includes a 12-char hash of the judge's system prompt.
If you change the rubric, the hash moves, and the regression diff
warns that results aren't comparable. This is what makes the harness
trustworthy over time — the report says "this run, on this rubric,
on this commit".

## Mock mode

Two reasons:

1. **Local dev** — iterating on the report HTML, the heatmap, or a new
   test case shouldn't cost API credits. Mock mode is seeded and
   deterministic: same input, same output, every time.
2. **CI without secrets** — open-source contributors can fork, push,
   and watch the workflow turn green without needing a Wand-issued
   API key.

The mock is intentionally calibrated to produce a realistic failure mix
(94% success, 6% hallucination on the shipped suite) so the report looks
substantive even without a live key.

## Pricing in code (not config)

Pricing per million tokens is hard-coded in `harness/config.py`. This
means the cost numbers in the report are reproducible from the commit
alone — re-render an old report a year from now and you get the same
cost figures. We accept the maintenance burden of bumping it when
Anthropic changes pricing.

## Reports persisted to disk, latest copied to `latest/`

GitHub Pages publishes `reports/latest/index.html` plus a redirect
from the site root. Historical runs are kept under
`reports/run-<timestamp>.html`. The regression panel reads the
most-recent prior JSON to compute the diff — no DB needed.

## Concurrency = 1

Sequential is fine for a 33-case suite (~90s end-to-end live). The
config has a knob to lift it to ~5 when the suite grows; we didn't
need it for the demo.

## Next.js dashboard on top of the Python harness

The Python harness emits two artifacts: a self-contained HTML report
(Jinja2) and a `run.json`. The Next.js app (`dashboard/`) is a static
export that reads the JSON at *build time* — so the deployed Pages URL
ships pre-rendered HTML (verdict, tiles, heatmap, failing cases all
visible on first paint, no loading spinner), and React hydrates on top
to add the interactive bits:

- filter by category / capability,
- "failures only" toggle,
- threshold sliders that recompute the verdict client-side (negotiate
  what "ready" means with the customer, live),
- click-to-open drawer with the full per-step trace.

Splitting eval logic (Python) from presentation (Next.js) lets each
half use the best tool for the job: Python for orchestrating LLM
calls and YAML test cases, React for interactive UI. The seam is a
versioned JSON schema (`dashboard/lib/types.ts` mirrors what
`harness/runner.py` writes).

The static Jinja report is still produced, uploaded as a CI artifact,
and works in environments with no JS runtime — useful when emailing the
verdict to someone who can't open Pages.

## What we deliberately did not build

- **Multi-judge consensus** — useful when scaling rubrics, but adds
  complexity that distracts from the demo story.
- **Slack alerting / webhooks** — easy to add (one POST in
  `harness/run.py`), but the GitHub Action's job summary covers 90% of
  the use case for now.
- **Custom DSL for thresholds** — they're a dict in `harness/config.py`
  because a YAML file would invite arguments about syntax instead of
  arguments about values.
- **Token-level caching** — meaningful at scale; premature here.
- **Server-rendered dashboard** — Next.js could run on Vercel with API
  routes, but static export keeps the surface tiny: no server, no env
  vars in production, deploys on GitHub Pages with no infrastructure.
