import { expect, test } from "@playwright/test";

const reply = (eventId: string, answer: string) => ({
  event_id: eventId, status: "ANSWERED", answer, model: null,
  tool_calls: [], evidence_calls: [], limitations: [], follow_ups: [],
});

test("facility Agent separates replay observations, review rules and historical backtests", async ({ page }, testInfo) => {
  await page.goto("/#event/osong-2023");
  const scopePicker = page.locator(".dk-agent-scope-picker > summary");
  await scopePicker.click();
  await page.getByRole("button", { name: "시설 통제 판단", exact: true }).click();
  await expect(page.getByRole("combobox", { name: "Agent 대상 시설" })).toContainText("궁평2지하차도");
  await page.getByLabel("Agent 과거 재생 시각").fill("2023-07-15T08:00");
  await expect(page.getByRole("button", { name: "시설 상태", exact: true })).toBeVisible();
  const input = page.getByRole("textbox", { name: "Agent request" });
  for (const item of [
    { question: "시설 상태를 설명해줘", tool: "get_facility_status", text: "과거 재생" },
    { question: "통제 검토 기준과 근거를 설명해줘", tool: "get_control_rule", text: "현장 계측" },
    { question: "과거 수위 백테스트를 설명해줘", tool: "get_facility_backtest", text: "DQ-009" },
  ]) {
    await expect(input).toBeEnabled();
    await input.fill(item.question);
    const pending = page.waitForResponse((response) => response.url().endsWith("/api/agent/ask"));
    await input.press("Enter");
    const response = await pending;
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.facility_id).toBe("gungpyeong2-underpass");
    expect(body.tool_calls[0].tool_name).toBe(item.tool);
    expect(body.diagnostics.model_requests).toBe(0);
    await expect(page.locator(".dk-agent-answer")).toContainText(item.text);
    await page.locator(".dk-agent-evidence > summary").first().click();
    await expect(page.locator(".dk-agent-evidence .dk-table")).toBeVisible();
  }
  await testInfo.attach("facility-agent-results", { body: await page.screenshot(), contentType: "image/png" });
  await scopePicker.click();
  await expect(page.getByRole("button", { name: "시설 상태", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "과거 사건 분석", exact: true }).click();
  await expect(page.locator(".dk-result")).toHaveCount(0);
});

test("real local Agent API reuses and replaces user conditions in a browser conversation", async ({ page }) => {
  await page.goto("/#event/osong-2023");
  const input = page.getByRole("textbox", { name: "Agent request" });
  for (const item of [
    { question: "08:20에 통제했다면?", mode: "current", time: "08:20", minutes: 7 },
    { question: "그 조건으로 다시 비교해줘", mode: "reused", time: "08:20", minutes: 7 },
    { question: "그럼 08:10은?", mode: "updated", time: "08:10", minutes: 17 },
  ]) {
    await expect(input).toBeEnabled();
    await input.fill(item.question);
    const pending = page.waitForResponse((response) => response.url().endsWith("/api/agent/ask") && response.request().method() === "POST");
    await input.press("Enter");
    const response = await pending;
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.diagnostics.context_mode).toBe(item.mode);
    expect(body.diagnostics.model_requests).toBe(0);
    expect(body.tool_calls[0].parameters.closure_times).toEqual([item.time]);
    expect(body.tool_calls[0].result.scenarios[0].minutes_before_underpass_inflow).toBe(item.minutes);
    await expect(page.locator(".dk-result > strong")).toHaveText(`질문 · ${item.question}`);
    if (item.mode !== "current") await expect(page.locator(".dk-result")).toContainText(body.context_note);
  }
});

test("a long Agent answer does not invalidate the next request's history", async ({ page }) => {
  const bodies: Array<{ message: string; history: Array<{ role: string; content: string }> }> = [];
  await page.route("**/api/agent/ask", async (route) => {
    bodies.push(route.request().postDataJSON());
    await route.fulfill({ json: reply("osong-2023", bodies.length === 1 ? "가".repeat(1800) : "이어서 확인했습니다.") });
  });
  await page.goto("/#event/osong-2023");
  const input = page.getByRole("textbox", { name: "Agent request" });
  await expect(input).toHaveAttribute("maxlength", "1000");
  await input.fill("연결 자료를 알려줘");
  await input.press("Enter");
  await expect(page.locator(".dk-agent-answer")).toContainText("가".repeat(20));
  await input.fill("이어서 설명해줘");
  await input.press("Enter");
  await expect(page.locator(".dk-agent-answer")).toHaveText("이어서 확인했습니다.");
  expect(bodies).toHaveLength(2);
  expect(bodies[1].history).toEqual([
    { role: "user", content: "연결 자료를 알려줘" },
    { role: "assistant", content: "가".repeat(1500) },
  ]);
});

test("switching cases while a request is pending cannot show the old case's answer", async ({ page }) => {
  let releaseOld!: () => void;
  const held = new Promise<void>((resolve) => { releaseOld = resolve; });
  let oldDeliveryDone!: () => void;
  const delivered = new Promise<void>((resolve) => { oldDeliveryDone = resolve; });
  let oldReceived = false;
  await page.route("**/api/agent/ask", async (route) => {
    const body = route.request().postDataJSON();
    if (body.event_id === "osong-2023") {
      oldReceived = true;
      await held;
      await route.fulfill({ json: reply("osong-2023", "이전 오송 사건의 늦은 답변입니다.") }).catch(() => {});
      oldDeliveryDone();
    } else {
      expect(body.history).toEqual([]);
      await route.fulfill({ json: reply(body.event_id, "서울 사건의 자료를 확인했습니다.") });
    }
  });
  await page.goto("/#event/osong-2023");
  const input = page.getByRole("textbox", { name: "Agent request" });
  await input.fill("연결 자료를 알려줘");
  await input.press("Enter");
  await expect.poll(() => oldReceived).toBe(true);
  await expect(input).toBeDisabled();
  await page.evaluate(() => { window.location.hash = "event/seoul-2022"; });
  await expect(input).toBeEnabled();
  await input.fill("서울 연결 자료를 알려줘");
  await input.press("Enter");
  await expect(page.locator(".dk-agent-answer")).toHaveText("서울 사건의 자료를 확인했습니다.");
  releaseOld();
  await delivered;
  await expect(page.locator(".dk-agent-answer")).toHaveText("서울 사건의 자료를 확인했습니다.");
  await expect(page.locator(".dk-error")).toHaveCount(0);
});
