import { expect, test } from "@playwright/test";

test("real water-level history follows replay time without presenting the research model as a forecast", async ({ page }, testInfo) => {
  await page.goto("/#twin?at=2023-07-15T08%3A00%3A00");
  const history = page.getByLabel("수위 이력과 예측 연결");
  await expect(history).toContainText("07.15 08:00");
  await expect(history).toContainText("9.91 m");
  await expect(history.locator("tbody tr")).toHaveCount(6);
  await history.locator("summary").click();
  await expect(history).toContainText("입력 22종 중 수위 6종");
  await expect(history).toContainText("0.222 m");
  await expect(history).toContainText("모델 예측이나 통제 권고가 아닙니다");
  await page.getByRole("button", { name: /04:10/ }).click();
  await expect(history).toContainText("07.15 04:10");
  await expect(history).toContainText("7.69 m");
  await expect(page.getByLabel("관측과 임계")).toContainText("관측 04:10");
  await expect(page.getByLabel("관측과 임계")).toContainText("7.69 m");
  await history.locator("summary").click();
  await history.scrollIntoViewIfNeeded();
  await expect(history.locator("tbody tr").last()).toBeInViewport();
  await expect(history.locator("details small")).toBeInViewport();
  await testInfo.attach("water-level-history", { body: await page.screenshot(), contentType: "image/png" });
});

test("research input failure leaves the facility observation and review board usable", async ({ page }) => {
  await page.route("**/forecast-readiness**", (route) => route.fulfill({ status: 503, json: { detail: "unavailable" } }));
  await page.goto("/#twin?at=2023-07-15T08%3A00%3A00");
  await expect(page.getByLabel("수위 이력과 예측 연결")).toContainText("수위 이력을 불러오지 못했습니다");
  await expect(page.getByLabel("관측과 임계")).toContainText("9.91 m");
  await expect(page.getByLabel("통제 검토 권고")).toContainText("통제 검토");
});
