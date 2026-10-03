import { describe, expect, it } from "vitest";
import { analyticsConfigured, configuredIds } from "./analytics";

describe("configuredIds", () => {
  it("keeps analytics off when no IDs are set", () => {
    expect(analyticsConfigured(configuredIds({}))).toBe(false);
  });

  it("accepts well-formed GA4 and Meta Pixel IDs", () => {
    expect(configuredIds({ VITE_GA4_ID: " G-AB12CD34EF ", VITE_META_PIXEL_ID: "1234567890123" })).toEqual({ ga4: "G-AB12CD34EF", pixel: "1234567890123" });
  });

  it("drops IDs that could inject script text", () => {
    const ids = configuredIds({ VITE_GA4_ID: "G-1\"><script>", VITE_META_PIXEL_ID: "12345abc" });
    expect(ids).toEqual({ ga4: undefined, pixel: undefined });
    expect(analyticsConfigured(ids)).toBe(false);
  });
});
