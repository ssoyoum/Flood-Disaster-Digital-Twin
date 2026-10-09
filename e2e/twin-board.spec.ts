import { expect, test } from "@playwright/test";

// The Playwright FastAPI server runs with FLOODOPS_TWIN_MODE=replay, so the board reads the stored 2023 series.
test("the twin board shows the 2023 replay status, presets and backtest for the Osong underpass", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /지하차도 통제 판단 보드/ }).click();
  await expect(page).toHaveURL(/#twin$/);
  await expect(page.locator("h1")).toContainText("지하차도 통제 판단 트윈");
  await expect(page.locator('[aria-label="시설"]')).toContainText("궁평2지하차도");
  await expect(page.locator(".tw-mode")).toContainText("2023년 사건 재생");

  const reco = page.locator('[aria-label="통제 검토 권고"]');
  await expect(reco).toContainText("통제 검토"); // default replay "now" is 08:00, past the planned flood level

  await page.getByRole("button", { name: /04:10/ }).click();
  await expect(page).toHaveURL(/at=2023-07-15T04%3A10%3A00/);
  await expect(reco).toContainText("감시");
  await expect(page.locator('[aria-label="관측과 임계"]')).toContainText("7.69 m");

  await page.getByRole("button", { name: /06:50/ }).click();
  await expect(reco).toContainText("통제 검토");
  await expect(reco).toContainText("계획홍수위에 도달");

  const backtest = page.locator('[aria-label="백테스트"]');
  await expect(backtest).toContainText("첫 «통제 검토» 권고");
  await expect(backtest).toContainText("계획홍수위 도달");
  await expect(page.locator('[aria-label="규칙과 한계"]')).toContainText("침수심을 측정하지 않는다");
});
