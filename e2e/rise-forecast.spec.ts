import { expect, test } from "@playwright/test";

// 6시간 최대 상승 예측은 트윈 상세(iframe)의 참고 카드다. 재생 04:10에 값이 나오고, 상태 배지는 수위 규칙 결과를 그대로 유지한다.
test("the 6-hour rise estimate stays a reference card apart from the recommendation", async ({ page }) => {
  await page.goto("/#twin");
  const twin = page.frameLocator(".tw-now-frame iframe");
  await twin.locator("#twc-marks .twc-mk", { hasText: "04:10" }).click();
  await expect(twin.locator("#twc-at")).toContainText("04:10");
  const card = twin.locator("#twc-rise");
  await expect(card).toContainText("권고에 반영 안 됨");
  await expect(twin.locator("#twc-rise-v")).toHaveText(/^[+−-]?\d+\.\d\d m$/, { timeout: 20_000 });
  await expect(twin.locator("#twc-rise-lin")).toHaveText(/m$/);
  // 같은 시각의 상태는 규칙 결과(감시)이고 예측 카드와 무관하다.
  await expect(twin.locator("#twc-badge")).toContainText("감시");
});
