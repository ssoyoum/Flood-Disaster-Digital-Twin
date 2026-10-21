import os from "node:os";
import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  workers: 1,
  reporter: "list",
  use: {
    ...devices["Desktop Chrome"],
    baseURL: "http://127.0.0.1:5175",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8035",
      url: "http://127.0.0.1:8035/health",
      reuseExistingServer: false,
      timeout: 120_000,
      name: "FastAPI",
      // Browser regression tests exercise registered tools without paid model calls, and the twin board
      // replays the stored 2023 series so E2E never depends on the live gauge API.
      // Duty records written by the board test go to a temp file, not the local operational log.
      env: { GEMINI_API_KEY: "", FLOODOPS_TWIN_MODE: "replay", FLOODOPS_DECISION_LOG_PATH: path.join(os.tmpdir(), "floodops-e2e-decisions.jsonl") },
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5175",
      url: "http://127.0.0.1:5175",
      env: { VITE_API_BASE: "http://127.0.0.1:8035" },
      reuseExistingServer: false,
      timeout: 120_000,
      name: "Vite",
    },
  ],
});
