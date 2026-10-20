import { expect, test } from "@playwright/test";

// A separate proxy client from the event conversation suite keeps the real 6/minute gate intact.
test.beforeEach(async ({ page }) => {
  await page.setExtraHTTPHeaders({ "X-Forwarded-For": "198.51.100.42" });
});

// Current home UI lives in an iframe and ranks facilities, rather than gauges.
test("home ranks facilities and keeps selected region and facility in the URL", async ({ page }) => {
  await page.goto("/");
  const board = page.frameLocator('iframe[title="FloodOps 전국 하천 감시 보드"]');
  await expect(board.getByRole("heading", { name: "실시간 위험 순위" })).toBeVisible();
  await expect(board.locator("#demo-mode")).toContainText("수위 재생");
  await board.locator("#wx-rbtn").click();
  await board.locator('[data-r="충북"]').click();
  await expect(page).toHaveURL(/region=%EC%B6%A9%EB%B6%81/);
  await board.getByRole("searchbox", { name: "시설 검색" }).fill("궁평2");
  await board.locator(".wx-row").filter({ hasText: "궁평2" }).first().click();
  await expect(board.locator("#wx-st-name")).toContainText("궁평2");
  await expect(board.locator("#wx-fac-list")).toContainText("하천");
});

test("watch agent moves the view using registered tools without a model", async ({ page }) => {
  await page.goto("/");
  const board = page.frameLocator('iframe[title="FloodOps 전국 하천 감시 보드"]');
  await board.locator("#wx-launch").click();
  await board.getByRole("textbox", { name: "질문", exact: true }).fill("강원도로 가자");
  await board.locator("#wx-ag-send").click();
  await expect(board.locator("#wx-turns")).toContainText("강원");
  await expect(page).toHaveURL(/region=%EA%B0%95%EC%9B%90/);
  await board.getByRole("textbox", { name: "질문", exact: true }).fill("미호강교 지금 몇 단계야?");
  await board.locator("#wx-ag-send").click();
  await expect(board.locator("#wx-turns")).toContainText("청주시(미호강교)");
  await expect(board.locator("#wx-ag-error")).toBeHidden();
});

test("missing rain stays explicit and cannot be mistaken for zero rain", async ({ page }) => {
  await page.goto("/");
  const board = page.frameLocator('iframe[title="FloodOps 전국 하천 감시 보드"]');
  const rain = board.locator("#demo-rain-mode");
  await expect(rain).toHaveAttribute("data-available", "false");
  await expect(rain).toContainText("자료 없음");
  await board.locator("#wx-info-btn").click();
  await expect(board.getByRole("dialog", { name: "판정 기준", exact: true })).toContainText("시설이 실제로 잠기는지는 배수·펌프 용량이 정한다");
});
