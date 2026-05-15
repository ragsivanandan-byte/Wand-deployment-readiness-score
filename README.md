# Wand Deployment Readiness Harness

**A pre-flight check for any multi-agent system before it touches a client's
production traffic.** Plug in your agent, run the suite, get a GO / NO-GO
verdict and a public HTML report you can hand to the customer's CTO.

> 🟢 **[View the latest live report →](https://ragsivanandan-byte.github.io/Wand-deployment-readiness-score/)**
> *(published by GitHub Actions on every push)*

---

## Why this exists

Most multi-agent failures in production happen for one of five reasons:
the agent gives the wrong answer, it hallucinates a number, it ignores
the instructions, it's too slow, or it's too expensive. Asking *"is the
demo working?"* doesn't catch any of them. Asking *"what's our hallucination
rate on the 30 cases the customer actually cares about?"* does.

This harness:

1. **Loads** a YAML suite of business-relevant test cases (finance vertical
   shipped; bring your own for other domains).
2. **Runs** them through a target multi-agent system (here: a 4-step
   buy-side earnings workflow — *researcher → analyst → writer → reviewer*).
3. **Scores** every response on five axes — task success, hallucination,
   instruction following, p95 latency, and cost per interaction — using
   Claude Sonnet 4.6 as a versioned LLM-as-judge.
4. **Compares** against the previous run to surface regressions.
5. **Publishes** a single HTML report with a heatmap, the verdict, the
   failing cases, and the cost breakdown — ready to share with non-technical
   stakeholders.

It is the artifact a Forward Deployed Engineer would ship to a customer
the week before their go-live.

---

## What the report looks like

The report is one self-contained HTML page with:

- **Verdict banner** — GO or NO-GO at a glance, with the failing gate(s)
  spelled out.
- **Five readiness gates** — task success, factuality, instruction
  following, p95 latency, cost — each with the threshold and the measured
  value.
- **Capability × axis heatmap** — drill into which sub-agent
  (researcher, analyst, writer, reviewer) is dragging which dimension.
- **Regression panel** — diff vs the previous run: new passes, new
  failures, unchanged.
- **Per-step cost & latency** — spot the sub-agent that's eating the budget.
- **Failing cases** — the prompt, the judge's rationale, and the raw
  output for every case that didn't pass.

Run a fresh report yourself in 30 seconds (see below).

---

## Quickstart

```bash
git clone https://github.com/ragsivanandan-byte/Wand-deployment-readiness-score.git
cd Wand-deployment-readiness-score
pip install -r requirements.txt

# Mock mode — no API key needed, runs in ~2 seconds with deterministic outputs.
HARNESS_MODE=mock python -m harness.run

# Live mode — uses Anthropic API.
export ANTHROPIC_API_KEY=sk-ant-...
HARNESS_MODE=live python -m harness.run

# Open the HTML report
open reports/latest/index.html
```

That's it. No Docker, no orchestrator, no vector DB.

### CLI flags

```bash
python -m harness.run --list                          # show all cases
python -m harness.run --category adversarial          # run only adversarial
python -m harness.run --capability writer --limit 5   # subset
```

---

## How it fits a customer engagement

Imagine the third Wand customer who churned because nobody measured their
use-case before turning it on. Here's where this harness slots in:

| Phase | Activity | This harness |
|---|---|---|
| **Pre-sale** | Scope the use case with the customer | Build 5–10 representative test cases together; the scoping doc is the YAML file |
| **Build** | Wire up the target agent against customer data | Run the harness on every prompt change — judge + heatmap tells you what broke |
| **Pre-launch** | Decide go / no-go | The report IS the go-live deliverable. Customer's CTO clicks one URL. |
| **Post-launch** | Monitor for regression | Same suite runs in CI on every change. New failures alert before users notice. |

The harness is intentionally agent-agnostic. Swap `FinanceWorkflowAdapter`
for your own adapter (3 dozen lines — see `harness/adapters.py`) and the
same suite covers any vertical: legal contract review, medical coding,
support triage, anything.

---

## Architecture

![Pipeline](docs/architecture.svg)

```
┌──────────────────────────────────────────────────────────────────────┐
│                          GitHub Actions                              │
│                                                                      │
│   push ─►  pytest  ─►  harness.run  ─►  reports/latest/index.html    │
│                            │                       │                 │
│                            │                       └─► GitHub Pages  │
│                            │                                         │
└────────────────────────────┼─────────────────────────────────────────┘
                             │
        ┌────────────────────┼─────────────────────┐
        ▼                    ▼                     ▼
  test_cases/*.yaml   target_agent/           harness/
     33 finance       4 sub-agents:           runner   ─► loads cases, runs adapter
     cases across     researcher              adapters ─► thin shim to target system
     golden /         analyst                 judge    ─► Claude Sonnet 4.6, rubric v1.0
     adversarial /    writer                  report   ─► aggregates → HTML + heatmap
     edge cases       reviewer                config   ─► thresholds & pricing
```

- **No LangChain / LangGraph.** The orchestrator is 50 lines of plain
  Python you can read end-to-end. Adapters make it trivial to swap the
  target system without touching the harness.
- **Mock mode for fast local iteration.** Deterministic, seeded outputs —
  same input always produces the same report — so you can debug the
  rendering, the rubric, or a new test case without burning API credits.
- **Rubric versioning.** The judge prompt is hashed into every report.
  If you change how you grade, the hash moves, and the regression panel
  warns that results aren't comparable to prior runs.

---

## Adding a test case

```yaml
# test_cases/your_case.yaml
cases:
  - id: my_first_case
    capability: writer        # researcher | analyst | writer | reviewer | orchestrator
    prompt: "Summarise the quarter."
    context: |
      <transcript excerpt or source documents>
    expected: |
      <what a correct answer looks like>
    must_contain:     ["$12.4B", "raised"]
    must_not_contain: ["lowered", "$99.9"]
```

The judge will fail any case whose output omits a `must_contain` token
or includes a `must_not_contain` one — even before the qualitative
scoring kicks in.

---

## Status of this work

Built as a Forward Deployed Engineer reference implementation. Vertical
shipped: **finance / buy-side earnings**. 33 test cases. Tested end-to-end
in CI. Report deploys automatically to GitHub Pages.

See [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) for the 60-second walk-through.
See [`docs/DECISIONS.md`](docs/DECISIONS.md) for design trade-offs.

---

## License

MIT.
