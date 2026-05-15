# STATUS

**Last updated:** 2026-05-15T23:00:00Z
**Current phase:** P0.6 — Next.js dashboard layered on top of Python harness; blocked on push
**Last completed:**
  - Full Python harness scaffolding (5 modules, 33 cases, 14 tests passing)
  - Mock run: VERDICT GO (94% success, 6% halluc, 4.4s p95, $0.005/run)
  - **NEW: Next.js 14 interactive dashboard** under `dashboard/`
    - Static export, deploys to GitHub Pages
    - SSG: verdict + heatmap + cases pre-rendered into initial HTML (no spinner)
    - Interactive: category/capability filters, failures-only toggle, threshold sliders that recompute verdict live, click-to-open case drawer with full per-step trace
    - Tailwind dark theme matching the Jinja report aesthetic
  - GitHub Action updated: Python harness → JSON → Next.js build → Pages deploy
  - README, DEMO_SCRIPT, DECISIONS, SETUP all updated to reflect the dashboard
  - 7 local commits on `claude/wand-deployment-readiness-CDmcU`

**Next action:** Wait for the GitHub App `contents:write` re-authorization, then `git push -u origin claude/wand-deployment-readiness-CDmcU` and watch CI. **On "continue" → retry push.**

## Open decisions made

- **Dashboard architecture (user-requested pivot):** User asked "can we use Next.js instead of Python". Recommended option 2 ("Next.js dashboard on top of Python harness") since the Python eval logic was already working — replaced only the presentation layer. Python emits `reports/latest/run.json`, Next.js reads it at build time, ships a static export. Best of both worlds: Python for orchestration / LLM calls / YAML tests, React for interactive UI.
- **SSG over CSR:** `app/page.tsx` is a server component that reads JSON at build time and passes it as props to the client `Dashboard` component. Initial HTML contains the verdict and heatmap — no "Loading..." flash.
- **Static export, no server:** No Vercel, no API routes, deploys to GitHub Pages with no infrastructure beyond a single GitHub Action job.
- **Push blocker (CRITICAL — still open):** Local git proxy and GitHub MCP both return `403 Resource not accessible by integration`. Local state has 7+ commits ready. Unblock = grant `contents:write` to the Claude Code GitHub App on this repo. See `docs/SETUP.md`.
- **Mock calibration unchanged:** Per-role error profile in `harness/adapters.py:_mock_target` lands the suite on GO with 2 visible failures.
- **Rubric versioning unchanged:** 12-char SHA of judge system prompt embedded in every report.

## Blockers

- ❌ Cannot push to GitHub until App permissions are widened. All work continues to be local, ready to ship in one batch.

## How to resume

After granting `contents:write`, say "continue". I'll re-run `git push -u origin claude/wand-deployment-readiness-CDmcU` and watch the CI run (Python harness → Next.js build → Pages deploy).
