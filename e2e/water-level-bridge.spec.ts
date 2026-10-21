import { expect, test } from "@playwright/test";

// 트윈 상세(iframe)는 저장된 2023년 10분 수위를 재생 시각에 맞춰 읽는다. 연구 모델(상승 예측)이 실패해도 관측과 조건 판정은 남는다.
test("the twin follows the replay time with the stored 10-minute water levels", async ({ page }) => {
  await page.goto("/#twin");
  const twin = page.frameLocator(".tw-now-frame iframe");
  await expect(twin.locator("#twc-at")).toContainText("08:00");
  await expect(twin.locator("#twc-k-level")).toHaveText("9.91");
  await twin.locator("#twc-marks .twc-mk", { hasText: "04:10" }).click();
  await expect(twin.locator("#twc-at")).toContainText("04:10");
  await expect(twin.locator("#twc-k-level")).toHaveText("7.69");
});

test("a failed rise model leaves the observation and the guideline conditions usable", async ({ page }) => {
  await page.route("**/rise-forecast**", (route) => route.fulfill({ status: 503, json: { detail: "unavailable" } }));
  await page.goto("/#twin");
  const twin = page.frameLocator(".tw-now-frame iframe");
  await expect(twin.locator("#twc-k-level")).toHaveText("9.91");
  await expect(twin.locator("#twc-rise-v")).toHaveText("예측 없음");
  await expect(twin.locator("#twc-crit-list li").first()).toContainText("충족");
});
