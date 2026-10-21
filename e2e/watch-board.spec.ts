import { expect, test, type Locator, type Page } from "@playwright/test";

// FLOODOPS_TWIN_MODE=replay makes the control board read the stored hours, so the morning of 2023-07-15
// is reproducible without the live HRFCO feed. The board itself is a static page inside an iframe.
const board = (page: Page) => page.frameLocator(".wb-root iframe");
const OSONG_0600 = "/#watch?at=2023-07-15T06%3A00%3A00";
const count = async (tab: Locator) => Number((await tab.locator("b").textContent()) ?? "0");

test("the control board is the first screen and counts facilities by the guideline's condition ②", async ({ page }) => {
  await page.goto("/");
  const frame = board(page);
  await expect(frame.locator(".demo-brand")).toContainText("통제 판단 보드");
  const tabs = frame.locator("#wx-sum button");
  await expect(tabs).toHaveCount(4);
  await expect(tabs.nth(0)).toContainText("특보 영향");
  await expect(tabs.nth(1)).toContainText("② 충족");
  await expect(tabs.nth(3)).toContainText("전체 시설");
  await expect(frame.locator("#wx-kpis")).toContainText("② 즉시 통제 조건 충족 시설");
});

test("an Osong replay hour marks condition ② and explains every condition in the facility panel", async ({ page }) => {
  await page.goto(OSONG_0600);
  const frame = board(page);
  const row = frame.locator("#wx-body .wx-row", { hasText: "궁평2지하차도" }).first();
  await expect(row.locator(".wx-c2tag")).toContainText("②");
  await row.click();

  await expect(frame.locator("#wx-cond-sum")).toContainText("즉시 통제 조건 ② 충족");
  const conditions = frame.locator("#wx-crit");
  await expect(conditions.locator("li").first()).toContainText("②");
  // ④ needs the live heavy-rain advisory, so a replay keeps it open instead of guessing.
  await expect(conditions).toContainText("④");
  await expect(conditions).toContainText("판정 보류");
  await expect(frame.locator("#wx-eta")).not.toBeEmpty();
  await expect(frame.locator("#wx-guide")).toContainText("하천 중심선");
});

test("reading condition ② from advisories never shrinks the set it counts", async ({ page }) => {
  await page.goto(OSONG_0600);
  const frame = board(page);
  const condTab = frame.locator("#wx-sum button", { hasText: "② 충족" });
  await expect(frame.locator("#wx-body .wx-row").first()).toBeVisible();
  const fromWarning = await count(condTab);
  await frame.locator("#wx-interp button[data-interp=advisory]").click();
  await expect(frame.locator("#wx-interp button[data-interp=advisory]")).toHaveAttribute("aria-pressed", "true");
  await expect.poll(() => count(condTab)).toBeGreaterThanOrEqual(fromWarning);
});

test("the duty record keeps one checker for each direction", async ({ page }) => {
  await page.goto(OSONG_0600);
  const frame = board(page);
  await frame.locator("#wx-body .wx-row", { hasText: "궁평2지하차도" }).first().click();
  const form = frame.locator("#wx-dec-form");
  await expect(frame.locator("#wx-dec-card")).toBeVisible();
  await form.locator("input[name=checked_by]").fill("상행 당직(E2E)");
  await form.locator("input[name=checked_by_down]").fill("하행 당직(E2E)");
  await form.locator("input[name=acknowledged]").check();
  await frame.locator("#wx-dec-submit").click();
  const latest = frame.locator("#wx-dec-list li").first();
  await expect(latest).toContainText("상행 당직(E2E)");
  await expect(latest).toContainText("하행 당직(E2E)");
});

test("the score tab lays the Osong official timeline next to condition ②", async ({ page }) => {
  await page.goto(OSONG_0600);
  const frame = board(page);
  await frame.locator("#wx-body .wx-row", { hasText: "궁평2지하차도" }).first().click();
  await frame.locator("#wx-tab-vc").click();
  await expect(frame.locator(".wx-tline")).toContainText("06:34");
  await expect(frame.locator(".wx-vc-key").first()).toContainText("② 충족");
});

test("the board agent moves the region from the registered tools without a model", async ({ page }) => {
  await page.goto("/");
  const frame = board(page);
  await frame.locator("#wx-launch").click();
  await frame.locator("#wx-ag-input").fill("강원도로 가자");
  await frame.locator("#wx-ag-send").click();
  await expect(frame.locator("#wx-rname")).toContainText("강원");
  await expect(page).toHaveURL(/region=%EA%B0%95%EC%9B%90/);
});

test("the board menu changes the app screen, not the frame", async ({ page }) => {
  await page.goto("/");
  const frame = board(page);
  await frame.locator(".demo-menu summary").click();
  await frame.getByRole("navigation", { name: "FloodOps 화면" }).getByRole("link", { name: "운영 시설 상세" }).click();
  await expect(page).toHaveURL(/\/#twin$/);
  await expect(page.locator("h1")).toContainText("운영 시설 통제 판단");
});
