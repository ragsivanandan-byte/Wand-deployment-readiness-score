# STATUS

**Last updated:** 2026-05-16T06:35:00Z
**Current phase:** ✅ READY FOR DEMO — site live, repo public-clean

## Live URLs

- **Repo:** https://github.com/ragsivanandan-byte/Wand-deployment-readiness-score
- **Dashboard (the thing you show Tony):** https://ragsivanandan-byte.github.io/Wand-deployment-readiness-score/

## What's deployed

- 9 commits on default branch `claude/wand-deployment-readiness-CDmcU` (tip `daa1133`)
- gh-pages branch with the built Next.js static export, serving the live dashboard
- GitHub Pages enabled, `build_type: legacy`, source = `gh-pages` branch, public=true, build status=`built`

## What you should do next

1. **Open the dashboard URL above on your phone.** Verify the verdict banner, metric tiles, heatmap, and failing-cases list render. Try the threshold sliders.
2. **Revoke the temporary PAT** at https://github.com/settings/tokens (find "Claude Code push session", click Delete). The token has done its job; killing it removes the risk of accidental misuse.
3. **(Optional) Walk through `docs/DEMO_SCRIPT.md`** out loud, in front of a mirror, ideally with your phone showing the dashboard live. 60 seconds.

## What's intentionally not done

- **CI workflow:** lives at `docs/ci-workflow.yml`, NOT at `.github/workflows/eval.yml`. The PAT I received was `repo`-scoped, not `workflow`-scoped — GitHub rejects PAT pushes to `.github/workflows/*` without the `workflow` scope. To enable CI auto-deploy on future pushes:
  - Quickest path: open the repo on github.com → copy the contents of `docs/ci-workflow.yml` → use **Add file → Create new file** → name it `.github/workflows/eval.yml` → paste → commit. The web UI bypasses the scope check. See `docs/SETUP.md` step 1.
  - Or: regenerate the PAT with `repo` AND `workflow` scopes, give it back, I'll push.
- **ANTHROPIC_API_KEY repo secret:** without it, CI runs in mock mode (still produces a valid report with deterministic data). With it, CI runs live against Anthropic for ~$0.17/run. See `docs/SETUP.md` step 3.

## Open decisions made

- **gh-pages branch deploy instead of GitHub Actions:** Plan B because the PAT lacked workflow scope. Same end-user experience (dashboard at the same URL) but no CI loop until the workflow file is moved into `.github/workflows/`.
- **Default branch = `claude/wand-deployment-readiness-CDmcU`** so the README is the repo landing page. You can rename it to `main` via Settings → Branches if you prefer.
- **Mock calibration unchanged:** suite lands on GO with 2 visible failing cases (good demo story).

## Blockers

None. Demo-ready.

## How to resume

If you want me to push the workflow file (so CI auto-deploys on every push going forward), regenerate the PAT with `repo` + `workflow` scopes, paste it, and say "push the workflow".

If something on the live site looks wrong, tell me what and I'll fix it (I can rebuild the dashboard and force-push gh-pages without needing any additional scope).
