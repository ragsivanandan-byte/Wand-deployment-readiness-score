import fs from "node:fs";
import path from "node:path";
import { RunPayload } from "@/lib/types";
import Dashboard from "./Dashboard";

// Read at build time so the static export bakes the data into the HTML —
// users see the verdict on first paint, no fetch round-trip.
function loadRun(): RunPayload | null {
  const candidates = [
    path.join(process.cwd(), "public/run.json"),
    path.join(process.cwd(), "../reports/latest/run.json"),
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) {
      return JSON.parse(fs.readFileSync(p, "utf-8")) as RunPayload;
    }
  }
  return null;
}

export default function Page() {
  const data = loadRun();
  if (!data) {
    return (
      <main className="max-w-3xl mx-auto p-8">
        <h1 className="text-xl font-semibold">No run data found</h1>
        <p className="text-muted mt-2 text-sm">
          The dashboard needs <code className="bg-panel px-1 rounded">public/run.json</code> at build time.
          Either copy <code className="bg-panel px-1 rounded">reports/latest/run.json</code> there, or let the
          GitHub Action do it (see <code className="bg-panel px-1 rounded">.github/workflows/eval.yml</code>).
        </p>
      </main>
    );
  }
  return <Dashboard data={data} />;
}
