import { expect, test } from "@playwright/test";

// The Playwright FastAPI server runs with FLOODOPS_TWIN_MODE=replay, so the board reads the stored 2023 series.
test("the twin board shows the 2023 replay status, presets and backtest for the Osong underpass", async ({ page }) => {
  await page.goto("/#twin");
  await expect(page.locator("h1")).toContainText("지하차도 통제 판단 트윈");
  const frame = page.frameLocator('iframe[title="현재 지하차도 통제 판단 트윈"]');
  await expect(frame.locator("#twc-fname")).toContainText("궁평2지하차도");
  await expect(page.locator(".tw-mode")).toContainText("2023년 사건 재생");
  const reco = frame.locator("#twc-badge");
  await expect(reco).toContainText("통제 검토");
  await frame.locator('.twc-mk[data-t="04:10"]').click();
  await expect(page).toHaveURL(/at=2023-07-15T04%3A10%3A00/);
  await expect(reco).toContainText("감시");
  await expect(frame.locator("#twc-k-level")).toContainText("7.69");
  await frame.locator("#twc-root").evaluate((el) => (el as HTMLElement & { twc: { setTime: (at: string) => void } }).twc.setTime("06:50"));
  await expect(reco).toContainText("통제 검토");
  await expect(frame.locator("#twc-s-time")).toContainText("06:40");
  await frame.getByRole("button", { name: "판단 기준 안내" }).click();
  await expect(frame.getByRole("dialog", { name: "판단 기준", exact: true })).toContainText("침수심을 재지 않고");

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
