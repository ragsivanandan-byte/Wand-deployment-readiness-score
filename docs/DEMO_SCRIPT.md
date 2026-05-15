# 60-second demo script

For Tony Gulley. Speak slowly. The goal isn't to flex the code — it's
to plant the idea that you ship deployment outcomes, not slide decks.

---

## 0:00 — The setup (8 seconds)

> "Most multi-agent rollouts that churn — and you've seen this at EliseAI —
> don't fail because the model is bad. They fail because nobody
> measured the customer's actual use-case before go-live. So before I
> joined a customer engagement at Wand, I'd build them this."

Open the GitHub repo. Show the README hero — the "View latest report" button.

---

## 0:08 — The artifact (12 seconds)

Click the button. The HTML report opens.

> "This is what I'd hand the customer's CTO the day before turning the
> agent on. One URL. GO or NO-GO. Five readiness gates."

Point to the verdict banner, then the five tiles.

> "Task success rate. Hallucination rate. Instruction following. p95
> latency. Cost per interaction. Each one has a threshold the customer
> agreed to during scoping. The system clears all five or it doesn't ship."

---

## 0:20 — The mechanics (15 seconds)

Scroll to the heatmap.

> "Behind it: 33 test cases the customer's analysts wrote with me — golden
> examples, adversarial prompts, edge cases like missing consensus or
> currency switches. Every case runs through their multi-agent workflow,
> then Claude Sonnet judges every response against a versioned rubric.
> The heatmap tells me which sub-agent is dragging which dimension.
> Researcher fine, writer occasionally hallucinates a number — that's
> where I'd focus the prompt work next."

---

## 0:35 — The failing cases (10 seconds)

Scroll to the "Failing cases" section.

> "And critically, when something fails, the customer sees the actual
> prompt, the judge's reasoning, and the raw agent output. No black
> box. They can argue with the judge."

---

## 0:45 — Why it matters for Wand (15 seconds)

> "Wand sells outcomes. This is the artifact that lets your CSMs prove
> the outcome before the customer logs in. It runs in CI on every prompt
> change, so the moment someone breaks a use case, we know — not the
> customer. And the same scaffolding works for any vertical: I shipped
> finance because of my FactSet background, but the adapter is 30 lines."

---

## 1:00 — Land

> "I'd rather be the person who delivers that report than the person who
> writes the QBR explaining why we missed the renewal."

Stop talking.

---

## If asked about live mode vs mock mode

> "Mock mode lets me iterate on the rubric and the report locally for
> free. Live mode hits the Anthropic API. CI runs live on every push if
> the API key is configured as a secret, mock otherwise. The reports look
> identical."

## If asked what's hard about this

> "Two things. First, calibrating the judge — getting it strict enough
> to catch real failures but tolerant enough not to flag stylistic
> variation. That's the versioned rubric. Second, picking test cases
> the customer actually cares about. The framework is easy; the cases
> are the work. They're the conversation."

## If asked about scale

> "Today it's 33 cases run sequentially in ~90 seconds live. To 10x
> the suite I'd add parallel calls (the harness has a concurrency knob
> at 1 today) and judge prompt caching. Probably 5 minutes of work."
