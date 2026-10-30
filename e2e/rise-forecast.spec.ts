import { expect, test } from "@playwright/test";

test("rise forecast stays separate from replay observation and review recommendation", async ({ page }) => {
  await page.goto("/#twin?at=2023-07-15T04%3A10%3A00");
  const frame = page.frameLocator('iframe[title="현재 지하차도 통제 판단 트윈"]');
  await expect(frame.locator("#twc-at")).toContainText("04:10");
  await expect(frame.locator("#twc-k-level")).toContainText("7.69");
  const card = frame.locator("#twc-rise");
  await expect(card).toBeVisible();
  await expect(card).toContainText("권고에 반영 안 됨");
  await expect(frame.locator("#twc-rise-v")).toContainText(/\+\d\.\d\d m/, { timeout: 20_000 });
  await expect(frame.locator("#twc-rise-lin")).not.toHaveText("—");
  await expect(frame.locator("#twc-badge")).toContainText("감시");
});
