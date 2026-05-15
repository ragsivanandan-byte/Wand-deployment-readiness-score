# First-time setup checklist

Three things need to be in place before the CI can publish a public report.
None of them is automatable from a GitHub App; they all need a human at
`github.com/settings`.

## 1. Grant the Claude Code GitHub App `contents:write`

The App can already read this repo but not write to it, which blocks both
my `git push` and the MCP `push_files` calls.

Go to **https://github.com/settings/installations** → **Claude Code** →
**Repository access** → make sure `Wand-deployment-readiness-score` is in
the allowed list with full repository scope. If you see "Read access to
contents", click **Configure** and bump it to write.

Once that's done, say "continue" and I'll push.

## 2. Enable GitHub Pages

Settings → **Pages** for the repo.

- **Source:** *GitHub Actions* (not "Deploy from a branch").

That's it. The workflow (`.github/workflows/eval.yml`) uses the modern
`actions/deploy-pages` action; there is no `gh-pages` branch to create.

Once enabled, every push runs the eval suite and publishes a fresh
`reports/latest/index.html` to:

> https://ragsivanandan-byte.github.io/Wand-deployment-readiness-score/

If you skip this step, the workflow still runs and uploads the report as
an artifact you can download from the Actions tab — but the public URL
won't exist.

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
2. Open the Pages URL. You should see the report banner, five metric
   tiles, the heatmap, and the failing-cases section.
3. If anything is red, the Actions log will say which step failed and
   why. The most common first-run issues are:
   - Pages not enabled → "Pages site not found" on `deploy-pages` step
   - Secret name typo → live mode tries, fails on the first request,
     workflow falls back to NO-GO verdict (still produces a report)
   - App permission not refreshed → push step would fail before this
     point, so you wouldn't see CI at all
