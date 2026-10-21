import { expect, test } from "@playwright/test";

// The Playwright FastAPI server runs with FLOODOPS_TWIN_MODE=replay, so the board reads the stored 2023 series.
test("the facility detail replays 2023 by the guideline's conditions and keeps the backtest", async ({ page }) => {
  await page.goto("/#twin");
  await expect(page.locator("h1")).toContainText("운영 시설 통제 판단");
  await expect(page.locator(".tw-mode")).toContainText("2023년 사건 재생");

  // The "now" tab is the static twin page in an iframe; its replay opens at 08:00.
  const twin = page.frameLocator(".tw-now-frame iframe");
  await expect(twin.locator("#twc-fname")).toContainText("궁평2지하차도");
  const conditions = twin.locator("#twc-crit-list");
  await expect(conditions.locator("li").first()).toContainText("②");
  await expect(conditions.locator("li").first()).toContainText("충족");
  await expect(conditions).toContainText("06:34 금강홍수통제소");
  await expect(conditions).toContainText("판정 보류");
  await expect(twin.locator("#twc-ref-list")).toContainText("FloodOps 규칙");
  await expect(twin.locator("#twc-marks")).toContainText("06:34");

  await twin.locator("#twc-marks .twc-mk", { hasText: "04:10" }).click();
  await expect(conditions).not.toContainText("06:34 금강홍수통제소");

  await page.getByRole("navigation", { name: "FloodOps 화면" }).getByRole("button", { name: "백테스트" }).click();
  const backtest = page.locator('[aria-label="백테스트"]');
  await expect(backtest).toContainText("첫 «통제 검토» 권고");
  await expect(backtest).toContainText("05:50");
  await expect(backtest).toContainText("계획홍수위 도달");
  await expect(page.locator('[aria-label="사건으로 검증"] a[href="#event/osong-2023"]')).toBeVisible();
});

test("the criteria tab trades 2023 lead time against review episodes in other flood seasons", async ({ page }) => {
  await page.goto("/#twin");
  await page.getByRole("navigation", { name: "FloodOps 화면" }).getByRole("button", { name: "통제 기준 검토" }).click();

  const result = page.locator('[aria-label="기준 검토 결과"]');
  await expect(result).toContainText("현재 규칙");
  await expect(result).toContainText("05:50");
  await expect(result).toContainText("157분 전");
  await expect(result).toContainText("다른 시기에는 권고가 없었습니다");

  await page.getByRole("group", { name: "계획홍수위 도달 예상 시간" }).getByRole("button", { name: /^120분/ }).click();
  await expect(result).toContainText("04:40");
  await expect(result).toContainText("227분 전");
  await expect(result).toContainText("2025.07.17");
  await expect(page.locator('[aria-label="연도별 권고"]')).toContainText("검증 사건(오송)");
  await expect(page.locator('[aria-label="연도별 권고"]')).toContainText("연중 10분 수위");
  await expect(page.locator('[aria-label="연도별 권고"]')).toContainText("연구 격리 2023-05-16 01:00~12:00(67개 값)");

  await page.locator('[aria-label="기준 비교표"] tr', { hasText: "계획홍수위 도달만" }).click();
  await expect(result).toContainText("06:50");
  await expect(result).toContainText("97분 전");
});
