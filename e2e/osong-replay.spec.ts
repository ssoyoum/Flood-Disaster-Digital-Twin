import { expect, test } from "@playwright/test";

test("enter Osong, replay stages, toggle a layer, and show provenance", async ({ page }) => {
  await page.goto("/");
  await page.locator(".fo-primary").click();
  await expect(page).toHaveURL(/#cases$/);

  await page.locator(".fo-case-slide.is-center .fo-case.is-ready").click();
  await expect(page).toHaveURL(/#event\/osong-2023$/);

  const stages = page.locator(".dk-stages button");
  await expect(stages).toHaveCount(7);
  await expect(page.locator(".dk-stages button.active")).toContainText("04:10");
  await expect(stages.first()).toContainText("출처 쪽수 확인 필요");

  await page.locator(".dk-replay").getByRole("button", { name: "▶ 재생" }).click();
  await expect(page.locator(".dk-stages button.active")).toContainText("06:40");
  await page.locator(".dk-replay").getByRole("button", { name: "❚❚ 일시정지" }).click();

  const layerSettings = page.locator(".dk-collapse");
  await layerSettings.click();
  await expect(layerSettings).toHaveAttribute("aria-expanded", "true");
  const handLayer = page.getByRole("checkbox", { name: /침수 추정 범위\(HAND\)/ });
  await expect(handLayer).toBeChecked();
  await handLayer.uncheck();
  await expect(handLayer).not.toBeChecked();
  await handLayer.check();
  await expect(handLayer).toBeChecked();

  await expect(page.locator(".dk-legend")).toContainText("HAND 근사");
  await expect(page.locator(".maplibregl-ctrl-attrib")).toContainText("OpenStreetMap contributors");
  await expect(page.locator(".maplibregl-ctrl-attrib")).toContainText("국토교통부 GIS건물통합정보");
});

test("change the closure scenario and keep the flood timeline limitation visible", async ({ page }) => {
  await page.goto("/#event/osong-2023");
  await page.getByRole("navigation", { name: "FloodOps 화면" }).getByRole("button", { name: "시나리오 비교" }).click();
  await page.getByRole("navigation", { name: "시나리오 분석 선택" }).getByRole("button", { name: /지하차도 통제 시각/ }).click();

  await page.locator(".dk-closure-presets").getByRole("button", { name: /08:09/ }).click();
  await expect(page.locator(".dk-compare-card.intervention h3")).toHaveText("08:09 지하차도 진입 통제");
  await expect(page.getByRole("region", { name: "통제 시각 비교 결과" })).toContainText("18분 전");
  await expect(page.getByRole("region", { name: "통제 시각 비교 결과" })).toContainText("물의 유입과 완전침수");
  await expect(page.locator(".dk-compare-map-note")).toContainText("공식 범위나 수리모형 결과가 아니라");
});

test("show source, data vintage, role, and limitations together", async ({ page }) => {
  await page.goto("/#event/osong-2023");
  const views = page.getByRole("navigation", { name: "FloodOps 화면" });
  await views.getByRole("button", { name: "출처·한계" }).click();

  const sources = page.getByRole("region", { name: "자료별 출처와 쓰임" });
  await expect(sources.locator("article")).toHaveCount(7);
  await expect(sources).toContainText("관측 입력");
  await expect(sources).toContainText("HAND 재구성 범위");
  await expect(sources).toContainText("2023-07-15");
  await expect(sources).toContainText("Flood Control Office water-level observation");

  const limitations = page.getByRole("region", { name: "재구성의 한계" });
  await expect(limitations).toContainText("공식 침수범위나 수리해석 결과가 아닙니다");
  await expect(limitations).toContainText("원문 쪽수와 시각 근거");
  await views.getByRole("button", { name: "인사이트" }).click();
  await expect(page.locator(".dk-insight-card.engineering")).toContainText("사건 연도와 자료 시점을 구분한다");
  await expect(page.locator(".dk-insight-card.engineering")).not.toContainText("TEMPORARY");
});
