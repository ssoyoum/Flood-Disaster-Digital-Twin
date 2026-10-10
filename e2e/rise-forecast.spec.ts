import { expect, test } from "@playwright/test";

// 6시간 최대 상승 예측 카드: 재생 04:10에 예측값이 나오고, 권고 배지는 수위 규칙 결과를 그대로 유지한다.
test("rise forecast card shows the model estimate apart from the recommendation", async ({ page }) => {
  await page.goto("/#twin?at=2023-07-15T04:10:00");
  const card = page.locator('[aria-label="6시간 최대 상승 예측"]');
  await expect(card).toBeVisible();
  await expect(card.getByText("권고에 반영하지 않음")).toBeVisible();
  await expect(card.locator(".tw-rise-badge")).toContainText(/\+\d\.\d\d m/, { timeout: 20_000 });
  await expect(card.locator(".tw-rise-reach")).toContainText("도달 예상");
  await expect(card.locator(".tw-rise-kpis")).toContainText("단순 외삽(최근 1시간 상승 × 6)");
  await card.locator("summary").click();
  await expect(card.getByText(/오송 2023-07-15: 모델은 계획홍수위 도달 \d+분 전/)).toBeVisible();
  // 같은 시각의 권고는 규칙 결과(감시)이고 예측 카드와 무관하다.
  await expect(page.locator('[aria-label="통제 검토 권고"] .tw-reco-badge')).toContainText("감시");
});
