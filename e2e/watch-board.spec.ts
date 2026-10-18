import { expect, test } from "@playwright/test";

// FLOODOPS_TWIN_MODE=replay makes the watch board read the stored hourly series, so the national
// picture is the morning of 2023-07-15 without touching the live HRFCO feed.
test("the watch board is the first screen and ranks gauges by their own official levels", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toContainText("하천 접점 시설 감시 보드");
  await expect(page.locator(".tw-mode")).toContainText("저장 자료 재생");

  const priority = page.locator('[aria-label="우선순위"]');
  await expect(priority.locator("li").first()).toContainText("계획홍수위");

  await page.getByLabel("지역").selectOption("충북");
  await expect(page).toHaveURL(/region=%EC%B6%A9%EB%B6%81/);
  await expect(priority).toContainText("미호강교");

  await priority.getByRole("button", { name: /미호강교/ }).click();
  const station = page.locator('[aria-label="선택 관측소"]');
  await expect(station).toContainText("청주시(미호강교)");
  await expect(station).toContainText("예보 아님");
  await expect(page.locator('[aria-label="연결 시설"]')).toContainText("궁평2지하차도");
  await expect(page.locator('[aria-label="연결 시설"] a[href="#twin"]')).toBeVisible();
});

test("the board agent moves the map and answers from the watch tools without a model", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Agent request").fill("강원도로 가자");
  await page.getByRole("button", { name: "질문" }).click();
  await expect(page.locator(".dk-agent-answer")).toContainText("강원(으)로 이동했습니다");
  await expect(page).toHaveURL(/region=%EA%B0%95%EC%9B%90/);

  await page.getByLabel("Agent request").fill("미호강교 지금 몇 단계야?");
  await page.getByRole("button", { name: "질문" }).click();
  await expect(page.locator(".dk-agent-answer")).toContainText("청주시(미호강교)");
  await expect(page.locator('[aria-label="선택 관측소"]')).toContainText("청주시(미호강교)");
});
