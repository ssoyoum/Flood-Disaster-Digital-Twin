import { expect, test, type Page } from "@playwright/test";

// Stage 5 measurement, not a regression gate: MEASURE_LATENCY=1 npx playwright test e2e/agent-latency.spec.ts
test.skip(!process.env.MEASURE_LATENCY, "Set MEASURE_LATENCY=1 to measure browser-side Agent latency.");

type Row = { label: string; send_to_response_ms: number; server_ms: number; response_bytes: number; response_to_render_ms: number };

async function ask(page: Page, label: string, question: string, rendered: string): Promise<Row> {
  const input = page.getByRole("textbox", { name: "Agent request" });
  await expect(input).toBeEnabled();
  await input.fill(question);
  const pending = page.waitForResponse((r) => r.url().endsWith("/api/agent/ask") && r.request().method() === "POST");
  const sent = Date.now();
  await input.press("Enter");
  const response = await pending;
  const body = await response.json();
  const received = Date.now();
  await expect(page.locator(".dk-agent-answer").last()).toContainText(rendered, { timeout: 60_000 });
  const shown = Date.now();
  return {
    label,
    send_to_response_ms: received - sent,
    server_ms: body.diagnostics?.duration_ms ?? -1,
    response_bytes: (await response.body()).length,
    response_to_render_ms: shown - received,
  };
}

test("browser-side Agent latency: cold and warm requests", async ({ page }, testInfo) => {
  test.setTimeout(240_000);
  const rows: Row[] = [];
  await page.goto("/#event/osong-2023");
  rows.push(await ask(page, "osong closure (cold)", "08:20에 통제했다면?", "결과 표"));
  rows.push(await ask(page, "osong closure (warm)", "08:10에 통제했다면?", "결과 표"));
  rows.push(await ask(page, "osong HAND (23 KB result)", "HAND 선택 임계를 1.5m 낮추면 단계별 붉은 셀이 어떻게 바뀌나요?", "결과 표"));
  rows.push(await ask(page, "osong exposure (cold)", "반경 500m 안 건물은 몇 동이야?", "결과 표"));

  await page.locator(".dk-agent-scope-picker > summary").click();
  await page.getByRole("button", { name: "시설 통제 판단", exact: true }).click();
  await page.getByLabel("Agent 과거 재생 시각").fill("2023-07-15T08:00");
  rows.push(await ask(page, "facility criteria (cold)", "기준별로 다른 해 권고가 몇 번 나오는지 비교해줘", "보관 수위"));
  rows.push(await ask(page, "facility criteria (warm)", "기준을 경보+120분으로 바꾸면 몇 분 먼저 검토하나요?", "보관 수위"));

  console.log(JSON.stringify(rows));
  await testInfo.attach("agent-latency", { body: JSON.stringify(rows, null, 2), contentType: "application/json" });
  for (const row of rows) expect(row.send_to_response_ms).toBeGreaterThanOrEqual(0);
});
