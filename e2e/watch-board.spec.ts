import { expect, test, type Locator, type Page } from "@playwright/test";

// FLOODOPS_TWIN_MODE=replay makes the control board read the stored hours, so the morning of 2023-07-15
// is reproducible without the live HRFCO feed. The board itself is a static page inside an iframe.
const board = (page: Page) => page.frameLocator('iframe[title="FloodOps 전국 하천 감시 보드"]');
const OSONG_0600 = "/#watch?at=2023-07-15T06%3A00%3A00";
const count = async (tab: Locator) => Number((await tab.locator("b").textContent()) ?? "0");

// A separate proxy client from the event conversation suite keeps the real 6/minute gate intact.
test.beforeEach(async ({ page }) => {
  await page.setExtraHTTPHeaders({ "X-Forwarded-For": "198.51.100.42" });
  // Exercise the actual failure boundary instead of relying on CI access to a public CDN.
  await page.route("https://unpkg.com/**", (route) => route.abort());
});

test("home lists facilities under official warnings and keeps selected region and facility in the URL", async ({ page }) => {
  await page.goto("/");
  const frame = board(page);
  await expect(frame.getByRole("heading", { name: "특보 영향 시설" })).toBeVisible();
  await expect(frame.locator(".demo-brand")).toContainText("통제 판단 보드");
  await expect(frame.locator("#demo-mode")).toContainText("수위 재생");
  await expect(frame.locator("#wx-map")).toContainText("시설 목록과 판정 근거는 계속 확인");
  const tabs = frame.locator("#wx-sum button");
  await expect(tabs).toHaveCount(4);
  await expect(tabs.nth(0)).toContainText("특보 영향");
  await expect(tabs.nth(1)).toContainText("② 충족");
  await expect(tabs.nth(3)).toContainText("전체 시설");
  await expect(frame.locator("#wx-kpis")).toContainText("② 즉시 통제 조건 충족 시설");
  await frame.locator("#wx-rbtn").click();
  await frame.locator('[data-r="충북"]').click();
  await expect(page).toHaveURL(/region=%EC%B6%A9%EB%B6%81/);
  await tabs.nth(3).click();
  await frame.getByRole("searchbox", { name: "시설 검색" }).fill("궁평2");
  await frame.locator(".wx-row").filter({ hasText: "궁평2" }).first().click();
  await expect(frame.locator("#wx-st-name")).toContainText("궁평2");
  await expect(frame.locator("#wx-fac-list")).toContainText("하천");
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

test("watch agent moves the view using registered tools without a model", async ({ page }) => {
  await page.goto("/");
  const frame = board(page);
  await frame.locator("#wx-launch").click();
  await frame.getByRole("textbox", { name: "질문", exact: true }).fill("강원도로 가자");
  await frame.locator("#wx-ag-send").click();
  await expect(frame.locator("#wx-turns")).toContainText("강원");
  await expect(frame.locator("#wx-rname")).toContainText("강원");
  await expect(page).toHaveURL(/region=%EA%B0%95%EC%9B%90/);
  await frame.getByRole("textbox", { name: "질문", exact: true }).fill("미호강교 지금 몇 단계야?");
  await frame.locator("#wx-ag-send").click();
  await expect(frame.locator("#wx-turns")).toContainText("청주시(미호강교)");
  await expect(frame.locator("#wx-ag-error")).toBeHidden();
});

test("missing rain stays explicit and cannot be mistaken for zero rain", async ({ page }) => {
  await page.goto("/");
  const frame = board(page);
  const rain = frame.locator("#demo-rain-mode");
  await expect(rain).toHaveAttribute("data-available", "false");
  await expect(rain).toContainText("자료 없음");
  await frame.locator("#wx-info-btn").click();
  await expect(frame.getByRole("dialog", { name: "판정 기준", exact: true })).toContainText("시설이 실제로 잠기는지는 배수·펌프 용량이 정한다");
});

test("the board menu changes the app screen, not the frame", async ({ page }) => {
  await page.goto("/");
  const frame = board(page);
  await frame.locator(".demo-menu summary").click();
  await frame.getByRole("navigation", { name: "FloodOps 화면" }).getByRole("link", { name: "운영 시설 상세" }).click();
  await expect(page).toHaveURL(/\/#twin$/);
  await expect(page.locator("h1")).toContainText("운영 시설 통제 판단");
});
