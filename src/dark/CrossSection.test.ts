import { describe, expect, it } from "vitest";
import { buildProfile } from "./CrossSection";
import type { GeoJson } from "../types";

const polygon = (stageIndex: number, gridId: string, handM: number, threshold: number): GeoJson["features"][number] => ({
  type: "Feature",
  geometry: {
    type: "Polygon",
    coordinates: [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]],
  },
  properties: {
    stage_index: stageIndex,
    state: "underpass_inflow",
    label: "Underpass inflow starts",
    grid_id: gridId,
    hand_m: handM,
    hand_threshold_m: threshold,
    relative_water_level_rise_m: threshold - 0.2,
    observed_water_level_m: 10.01,
    water_level_timestamp_kst: "2023-07-15T08:27:00+09:00",
    stage_hourly_rainfall_mm: 32.5,
    mean_elevation_m: 41.2,
    local_drainage_elevation_m: 39.1,
    distance_to_river_m: 18,
  },
});

describe("buildProfile", () => {
  it("uses the HAND cell containing the underpass center and preserves stage values", () => {
    const hand: GeoJson = {
      type: "FeatureCollection",
      features: [
        polygon(2, "dem-17-20", 2.03, 2.96),
        polygon(3, "dem-17-20", 2.03, 3.87),
      ],
    };

    const profile = buildProfile(hand, [1, 1]);

    expect(profile.cell?.grid_id).toBe("dem-17-20");
    expect(profile.included.has(2)).toBe(true);
    expect(profile.included.has(3)).toBe(true);
    expect(profile.byStage.get(2)?.threshold).toBe(2.96);
    expect(profile.byStage.get(2)?.observed_wl).toBe(10.01);
    expect(profile.byStage.get(2)?.rain).toBe(32.5);
  });

  it("does not invent a cell when the center is outside the HAND geometry", () => {
    const hand: GeoJson = { type: "FeatureCollection", features: [polygon(2, "dem-17-20", 2.03, 2.96)] };

    expect(buildProfile(hand, [3, 3]).cell).toBeNull();
  });
});
