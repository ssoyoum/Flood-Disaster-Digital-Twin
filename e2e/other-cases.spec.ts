import { expect, test, type Page } from "@playwright/test";

// The case carousel lists events in API order: osong, seoul, pohang, iksan, andong.
async function openCase(page: Page, nextClicks: number, eventId: string) {
  await page.goto("/#cases");
  const next = page.getByRole("button", { name: "다음 사례" });
  for (let index = 0; index < nextClicks; index += 1) await next.click();
  await page.locator(".fo-case-slide.is-center .fo-case.is-ready").click();
  await expect(page).toHaveURL(new RegExp(`#event/${eventId}$`));
}

test("Seoul 2022 opens from the case library and compares alert timing", async ({ page }) => {
  await openCase(page, 1, "seoul-2022");
  await expect(page.locator("h1")).toContainText("서울 도림천");
  await expect(page.locator(".dk-stages button")).toHaveCount(7);
  await expect(page.getByRole("region", { name: "강우 관측" })).toContainText("설계강우 95 mm/h");
  await expect(page.getByRole("region", { name: "공식 침수흔적 노출" })).toContainText("10,468");
  // Traces stay hidden until the 60-minute rainfall passes the design target, then appear deepest-first.
  const legend = page.locator(".dk-legend");
  await expect(legend).toContainText("현재 0 / 10,468건");
  await page.getByRole("button", { name: "다음 단계" }).click();
  await page.getByRole("button", { name: "다음 단계" }).click();
  await expect(legend).toContainText("현재 1,557 / 10,468건");
  await page.getByRole("button", { name: "다음 단계" }).click();
  await expect(legend).toContainText("현재 10,468 / 10,468건");
  await expect(legend).toContainText("HAND 근사");
  await expect(legend).toContainText("1,218셀");

  await page.getByRole("navigation", { name: "FloodOps 화면" }).getByRole("button", { name: "시나리오 비교" }).click();
  const table = page.locator(".ub-whatif .ub-table").first();
  await expect(table).toContainText("20:49");
  await expect(table).toContainText("30분 빠름");
  await expect(page.locator(".ub-storage-chart")).toBeVisible();
});

test("Pohang 2022 replays reported times and compares the entry-ban time", async ({ page }) => {
  await openCase(page, 2, "pohang-2022");
  await expect(page.locator("h1")).toContainText("포항");
  await expect(page.locator(".dk-stages button")).toHaveCount(8);
  await expect(page.locator(".dk-status")).toContainText("언론 보도 시각");
  // The HAND cells appear at the reported overflow (stage 3) and keep growing in reported order.
  const legend = page.locator(".dk-legend");
  await expect(legend).toContainText("HAND 근사");
  await expect(legend).toContainText("현재 0셀");
  await page.getByRole("button", { name: "다음 단계" }).click();
  await page.getByRole("button", { name: "다음 단계" }).click();
  await expect(legend).toContainText("현재 236셀");
  await page.getByRole("button", { name: "다음 단계" }).click();
  await expect(legend).toContainText("현재 370셀");

  await page.getByRole("button", { name: "시나리오 비교 열기" }).click();
  await page.getByRole("checkbox", { name: /06:00/ }).check();
  const table = page.locator(".ub-table");
  await expect(table).toContainText("(실제)");
  await expect(table).toContainText("30분 빠름");
  await expect(table).toContainText("37분");
  await expect(table).toContainText("45분");
});

test("Iksan 2024 stays locked in the case library", async ({ page }) => {
  await page.goto("/#cases");
  const next = page.getByRole("button", { name: "다음 사례" });
  for (let index = 0; index < 3; index += 1) await next.click();
  const card = page.locator(".fo-case-slide.is-center .fo-case");
  await expect(card).toHaveClass(/is-locked/);
  await expect(card).toBeDisabled();
  await expect(card).toContainText("데이터 연결 예정");
});

test("Andong-Uiseong 2026 replays overnight times and compares the evacuation order", async ({ page }) => {
  await openCase(page, 4, "andong-uiseong-2026");
  await expect(page.locator("h1")).toContainText("안동");
  await expect(page.locator(".dk-stages button")).toHaveCount(7);
  // The HAND band is already present at the first reported isolation and widens up to the predicted peak.
  const legend = page.locator(".dk-legend");
  await expect(legend).toContainText("HAND 근사");
  const cellsAt = async () => Number((await legend.textContent())?.match(/현재 ([\d,]+)셀/)?.[1].replace(/,/g, "") ?? "0");
  const first = await cellsAt();
  expect(first).toBeGreaterThan(0);
  for (let index = 0; index < 4; index += 1) await page.getByRole("button", { name: "다음 단계" }).click();
  await expect.poll(cellsAt).toBeGreaterThan(first);

  await page.getByRole("navigation", { name: "FloodOps 화면" }).getByRole("button", { name: "시나리오 비교" }).click();
  // Two interventions render their own panels; the evacuation order comes first.
  const panels = page.locator(".dk-compare-panel");
  await expect(panels).toHaveCount(2);
  const evacuation = panels.first();
  await expect(evacuation).toContainText("대피명령 시각");
  await evacuation.getByRole("checkbox", { name: /23:40/ }).check();
  const table = evacuation.locator(".ub-table");
  await expect(table).toContainText("(실제)");
  await expect(table).toContainText("20분 빠름");
  await expect(table).toContainText("50분");
  await expect(panels.nth(1)).toContainText("산사태 위기경보");
});
