import { expect, test } from "@playwright/test";

test("replay deep link and hash changes update observation time in the current iframe", async ({ page }) => {
  await page.goto("/#twin?at=2023-07-15T08%3A00%3A00");
  const frame = page.frameLocator('iframe[title="현재 지하차도 통제 판단 트윈"]');
  await expect(frame.locator("#twc-at")).toContainText("08:00");
  await expect(frame.locator("#twc-k-level")).toContainText("9.91");
  await page.evaluate(() => { window.location.hash = "twin?at=2023-07-15T04%3A10%3A00"; });
  await expect(frame.locator("#twc-at")).toContainText("04:10");
  await expect(frame.locator("#twc-k-level")).toContainText("7.69");
  await expect(frame.locator("#twc-badge")).toContainText("감시");
});

test("research forecast failure leaves observation and review usable even without the map CDN", async ({ page }) => {
  await page.route("**/rise-forecast**", (route) => route.fulfill({ status: 503, json: { detail: "unavailable" } }));
  await page.route(/https:\/\/(unpkg\.com|cdn\.jsdelivr\.net)\//, (route) => route.abort());
  await page.goto("/#twin?at=2023-07-15T08%3A00%3A00");
  const frame = page.frameLocator('iframe[title="현재 지하차도 통제 판단 트윈"]');
  await expect(frame.locator("#twc-rise-v")).toContainText("예측 없음");
  await expect(frame.locator("#twc-k-level")).toContainText("9.91");
  await expect(frame.locator("#twc-badge")).toContainText("통제 검토");
  await expect(frame.locator("#twc-crit-list li").first()).toContainText("충족");
});


test("a failed later observation cannot retain the previous level or recommendation", async ({ page }) => {
  await page.goto("/#twin?at=2023-07-15T08%3A00%3A00");
  const frame = page.frameLocator('iframe[title="현재 지하차도 통제 판단 트윈"]');
  await expect(frame.locator("#twc-k-level")).toContainText("9.91");
  await page.route("**/api/twin/facilities/*/status**", route => {
    if (route.request().frame().parentFrame()) return route.fulfill({ status: 503, json: { detail: "test failure" } });
    return route.continue();
  });
  await page.evaluate(() => { window.location.hash = "twin?at=2023-07-15T04%3A10%3A00"; });
  await expect(frame.locator("#twc-badge")).toHaveText("관측 없음");
  await expect(frame.locator("#twc-k-level")).toHaveText("—");
  await expect(frame.locator("#twc-alert")).toContainText("판단 보류");
  await expect(frame.locator("#twc-crit-list")).toContainText("판정하지 않습니다");
  await expect(frame.locator("#twc-crit-list")).not.toContainText("충족");
});
