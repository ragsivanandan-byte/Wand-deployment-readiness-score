# STATUS

**Last updated:** 2026-05-15T21:50:00Z
**Current phase:** P0.1 — Scaffolding
**Last completed:** Repo init, deps installed (anthropic, pydantic, jinja2, pyyaml)
**Next action:** Write core modules (config, adapters, runner, judge, report) + target agent

## Open decisions made

- **Branch:** Working on `claude/wand-deployment-readiness-CDmcU` per SDK directive. User can fast-forward `main` to it on return. GitHub Pages will deploy from `gh-pages` branch produced by CI, so the source branch is irrelevant for the public report URL.
- **Stack:** anthropic SDK + pydantic + jinja2 + pyyaml. No matplotlib/plotly — heatmaps rendered as inline SVG (zero runtime deps for visualization, faster CI).
- **Mock mode:** `HARNESS_MODE=mock` (default) returns deterministic seeded outputs so the harness runs offline without API credits. `HARNESS_MODE=live` calls Anthropic.
- **Models:** `claude-haiku-4-5` for target sub-agents (cheap, fast), `claude-sonnet-4-6` for the judge (rubric needs reasoning).
- **No LangChain / LangGraph:** custom orchestrator. More readable for a non-technical reviewer (Tony) and easier to debug.
- **Vertical:** Finance / buy-side earnings workflow. Plays into the user's FactSet background.

## Blockers

None.

## How to resume

Just say "continue". I'll re-read this file, the latest commit, and pick up at "Next action".
