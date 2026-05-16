# First-time setup checklist

Three things need to be in place before the CI can publish a public report.
None of them is automatable from a GitHub App; they all need a human at
`github.com/settings`.

## 0. Quick start — site is already live

The dashboard at
**https://ragsivanandan-byte.github.io/Wand-deployment-readiness-score/**
is published from the `gh-pages` branch (a manual deploy of
`dashboard/out/`). It works out-of-the-box without any CI configuration.
You only need the steps below if you want fresh runs to redeploy
automatically on every push.

## 1. Enable the CI workflow

The repository ships a ready-to-use GitHub Actions workflow at
[`docs/ci-workflow.yml`](ci-workflow.yml). It is **not** under
`.github/workflows/` by default because pushing files in that path
requires a Personal Access Token with the `workflow` scope, and we
shipped without it.

To enable it:

1. Open the repo on github.com.
2. Navigate to `docs/ci-workflow.yml`.
3. Click the pencil (Edit) icon, copy the contents.
4. Use **Add file → Create new file** at the repo root, name it
   `.github/workflows/eval.yml`, paste, commit. GitHub will accept
   workflow file edits made directly through the web UI without
   special scopes.
5. Every push from now on will run the eval suite, rebuild the
   dashboard, and redeploy GitHub Pages.

## 2. Grant the Claude Code GitHub App `contents:write`

This is only needed if you want Claude (the agent that built this) to
push follow-up commits in future sessions. For the demo itself, it's
optional.

Go to **https://github.com/settings/installations** → **Claude Code** →
**Repository access** → make sure `Wand-deployment-readiness-score` is
in the allowed list with full repository scope.

## 3. (Optional) Add `ANTHROPIC_API_KEY` for live mode

Settings → **Secrets and variables** → **Actions** → **New repository
secret**.

- **Name:** `ANTHROPIC_API_KEY`
- **Value:** an Anthropic API key with access to Claude Sonnet 4.6 and
  Haiku 4.5.

The workflow auto-detects: if the secret exists, it runs live (real API
calls); if not, it runs in mock mode (deterministic, free, same report
structure). The report layout is identical either way — only the
underlying numbers differ.

Cost estimate for one live run on the shipped 33-case suite:
- 33 cases × (4 sub-agent calls + 1 judge call) ≈ 165 API calls
- ~$0.005/case → **~$0.17 per full run.** Negligible.

## Verifying it works

After the workflow finishes:

1. Look at the Actions tab — the `eval` and `deploy` jobs should both
   be green.
2. Open the Pages URL. You should see the **Next.js dashboard** —
   verdict banner, five metric tiles, the heatmap, filters at the top
   (category, capability, threshold sliders), and clickable failing
   cases that open a side drawer with the full per-step trace.
3. The CI also uploads the raw static report and the run JSON as a
   downloadable artifact named `readiness-bundle` (Actions → workflow
   run → bottom of the page).
4. If anything is red, the Actions log will say which step failed and
   why. The most common first-run issues are:
   - Pages not enabled → "Pages site not found" on `deploy-pages` step
   - Secret name typo → live mode tries, fails on the first request,
     workflow falls back to NO-GO verdict (still produces a report)
   - `pnpm install` failure → usually a transient registry hiccup;
     re-run the workflow.
