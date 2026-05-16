# STATUS

**Last updated:** 2026-05-16T07:00:00Z
**Current phase:** ✅ Audit complete, fixes applied, demo-ready

## Live URLs

- **Repo:** https://github.com/ragsivanandan-byte/Wand-deployment-readiness-score
- **Dashboard:** https://ragsivanandan-byte.github.io/Wand-deployment-readiness-score/

## Audit report (this session)

### What I checked

| Area | Method | Result |
|---|---|---|
| File structure & .gitignore | `git ls-files`, `git check-ignore` | ✅ Clean — no secrets, no build artefacts tracked |
| Unit tests (14) | `pytest tests/` | ✅ 14/14 pass |
| Mock harness end-to-end | `python -m harness.run` | ✅ VERDICT GO, deterministic |
| CLI flag combinations | --list / --category / --capability / --limit | ✅ All work; bad inputs now error cleanly |
| Live-mode code path | Import + construct without calling API | ✅ Settings, adapter, client wire up |
| Live-mode missing key | `HARNESS_MODE=live` no `ANTHROPIC_API_KEY` | ✅ Now prints one-line error (was stack trace) |
| Test case YAML (33 cases) | Field validation + ID uniqueness | ✅ All have required fields, no dup IDs |
| Dashboard TypeScript | `npx tsc --noEmit` | ✅ No errors |
| Dashboard SSG | Inspect built `out/index.html` | ✅ Verdict, heatmap, cases baked into initial HTML (17.8KB visible body) |
| Threshold sliders logic | Verified `goNoGo()` in `metrics.ts` matches Python | ✅ Same semantics |
| Determinism | Two consecutive mock runs, hash-compare | ✅ Identical content (modulo run_id/timestamp) |
| Rubric hash stability | Reload + recompute | ✅ Stable: `1745b09f15c1` |
| Judge JSON parser | Malformed inputs: trailing commas, prose-wrapped, fenced | ✅ Tolerant; defaults to fail on unparseable |
| Anthropic model IDs | Cross-check against SDK's known list | ✅ `claude-haiku-4-5`, `claude-sonnet-4-6` both valid |
| Workflow YAML | `yaml.safe_load`, step inventory | ✅ Valid, 16 eval steps + deploy job |
| README link integrity | Resolve every relative link | ✅ All resolve |
| Deployed Pages site | GitHub API: pages, builds/latest | ✅ status=`built`, public, https_enforced |
| Deployed gh-pages content | Fetch raw `index.html` + `run.json` | ✅ Run-id, metrics consistent with local |
| Mobile-responsive Tailwind classes | grep `md:` / `flex-wrap` / `overflow-x-auto` | ✅ Filter bar wraps, heatmap scrolls, drawer full-width |
| Secrets in repo | Regex sweep across tracked files | ✅ Only placeholder `sk-ant-...` example in README |

### Issues found and fixed

| # | Severity | Issue | Fix |
|---|---|---|---|
| 1 | UX | `--capability foobar` raised Python traceback | `argparse choices=` + try/except in `main()` |
| 2 | Bug | `--limit 0` treated as "no limit" because of `if args.limit:` | Switched to `is not None` |
| 3 | UX | Live mode without API key showed stack trace | Caught in `main()`, prints one-line error |
| 4 | Doc | README ASCII architecture diagram claimed CI runs on push | Replaced with honest pipeline showing the actual gh-pages flow |
| 5 | Doc | "Two ways to view a report" table said static report is "uploaded as CI artifact" | Changed to "Generated on disk after `python -m harness.run`" |
| 6 | Doc | "Status of this work" claimed "Tested end-to-end in CI" | Trimmed to what's actually true |
| 7 | Doc | No `LICENSE` file though README claimed MIT | Added `LICENSE` (MIT) |
| 8 | Doc | `docs/SETUP.md` didn't mention you must flip Pages source from "branch" to "Actions" when enabling CI | Added that step |
| 9 | Doc | `docs/architecture.svg` block 6 referenced `.github/workflows/eval.yml` | Updated to point at `docs/ci-workflow.yml` + describe gh-pages reality |
| 10 | Hygiene | `dashboard/tsconfig.tsbuildinfo` was being staged | Added to `dashboard/.gitignore` |
| 11 | UX | Dashboard threshold panel used `absolute` positioning → could glitch on mobile because no positioned ancestor | Removed `absolute md:static`, flows inline now |
| 12 | UX | Footer missing utility links | Added "Download raw run.json" and "Source on GitHub" |

### Design tradeoffs I noticed but did **not** fix

- **Reviewer-specific test cases** (3 of them: `golden_reviewer_pass`, `golden_reviewer_clean`, `adv_review_should_fail`) run through the full 4-step workflow, not the reviewer in isolation. In live mode the reviewer would evaluate the writer's freshly-generated note rather than the user-supplied "wrong note" in the test fixture. The judge catches this as a (correct) failure for `adv_review_should_fail`. In mock mode the discrepancy is masked because mock targets receive `must_contain` hints. Fixing this would mean routing test cases to a single sub-agent based on `capability`, which is a larger refactor than the demo needs.
- **Report-preview SVG** in the README shows the original Jinja report layout, not the current Next.js dashboard (which adds filter chips + slider panel on top of the same visual language). Close enough — the README text already names the interactive features. Replacing the SVG would be busywork.

## Final commit / branch state

- Default branch: `claude/wand-deployment-readiness-CDmcU` (12 commits, tip `0c1f76e`)
- Deploy branch: `gh-pages` (force-pushed as the dashboard is rebuilt; latest commit `ca1ed19`)
- Pages: built, public, https_enforced, source = `gh-pages`/`/`

## Open todo for you

1. **Open the dashboard on your phone** — verify the verdict banner, tiles, heatmap, click a failing case, drag a threshold slider. Should take 30 seconds.
2. **Revoke the PAT** at https://github.com/settings/tokens (token name "Claude Code push session") — security hygiene.
3. **Optional, before the Tony interview:** read `docs/DEMO_SCRIPT.md` once aloud.

## Open todo for me (only if you ask)

- Enable the CI workflow loop (requires either a PAT with `workflow` scope, or you copy `docs/ci-workflow.yml` to `.github/workflows/eval.yml` via the GitHub web editor — see `docs/SETUP.md` step 1).
- Decompose the reviewer-specific test cases so they exercise the reviewer step in isolation (would make live-mode results cleaner for those 3 cases).
- Generate a real screenshot of the live dashboard to replace `docs/report-preview.svg`.

## How to resume

Say "continue" and I'll re-read this STATUS.md and pick up from "Open todo for me".
