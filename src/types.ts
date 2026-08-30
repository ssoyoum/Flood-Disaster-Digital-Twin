export type DataOrigin = "OBSERVED" | "DERIVED" | "SIMULATED";

export type GeoJson = {
  type: "FeatureCollection";
  features: GeoJsonFeature[];
};

export type GeoJsonFeature = {
  type: "Feature";
  properties: Record<string, string | number | undefined>;
  geometry: {
    type: string;
    coordinates: unknown;
  };
};

export type FloodEvent = {
  id: string;
  name: string;
  location: string;
  data_year: number;
  theme: string;
  focus_feature: string;
  analysis_flow: string;
  source: string;
  started_at: string;
  ended_at: string;
  origin: DataOrigin;
  data_status: string;
  flood_extent: GeoJson;
};

export type SafetyDataApiTestResult = {
  connected: boolean;
  result_code: string;
  message: string;
};

export type ExposureMetrics = {
  flooded_area_km2: number;
  exposed_population: number;
  exposed_buildings: number;
  affected_road_length_km: number;
  critical_infrastructure: number;
  affected_shelters: number;
  origin: "DERIVED";
};

export type Observation = {
  timestamp: string;
  observation_type: "rainfall" | "water_level";
  station_id: string;
  value: number;
  unit: string;
  quality_flag: string;
  origin: DataOrigin;
};

export type InterventionType =
  | "EVACUATION"
  | "ROAD_CLOSURE"
  | "SHELTER_OPEN"
  | "TEMPORARY_BARRIER"
  | "LEVEE_IMPROVEMENT"
  | "INFRASTRUCTURE_PROTECTION";

export type ScenarioResult = {
  scenario_id: string;
  name: string;
  intervention: { type: InterventionType; label: string; description: string };
  baseline: ExposureMetrics;
  result: ExposureMetrics;
  reduction_percent: number;
  assumptions: string[];
  origin: "SIMULATED";
};
