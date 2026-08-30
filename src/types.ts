export type DataStatus = "VERIFIED" | "DERIVED" | "REANALYSIS" | "TEMPORARY" | "UNAVAILABLE";

export type GeoJson = {
  type: "FeatureCollection";
  features: GeoJsonFeature[];
};

export type GeoJsonFeature = {
  type: "Feature";
  properties: Record<string, string | number | boolean | undefined | null>;
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
  origin: DataStatus;
  data_status: string;
  flood_extent: GeoJson;
};

export type LayerPayload = {
  key: string;
  label: string;
  status: DataStatus;
  source_type?: string;
  source?: string;
  snapshot?: string | null;
  path?: string | null;
  feature_count: number;
  geometry_types?: string[];
  data: GeoJson;
};

export type LayersResponse = {
  aoi: LayerPayload;
  roads: LayerPayload;
  buildings: LayerPayload;
  waterways: LayerPayload;
  terrain: LayerPayload;
  facilities: LayerPayload;
  underpass: LayerPayload;
  flood_extent: LayerPayload;
};

export type DataStatusItem = {
  status: DataStatus;
  source?: string;
  source_type?: string;
  snapshot?: string | null;
  period?: string | null;
  data_year?: number | null;
  unit?: string;
  records?: number;
};

export type DataStatusResponse = {
  flood_extent: LayerPayload;
  population: DataStatusItem;
  rainfall: DataStatusItem;
  dem: DataStatusItem & {
    min_elevation_m?: number;
    max_elevation_m?: number;
    mean_elevation_m?: number;
    low_elevation_threshold_m?: number;
    grid_feature_count?: number;
    low_elevation_feature_count?: number;
  };
  layers: Record<string, Omit<LayerPayload, "data">>;
};

export type SafetyDataApiTestResult = {
  connected: boolean;
  result_code: string;
  message: string;
};

export type ExposureMetrics = {
  event_id: string;
  origin: DataStatus;
  official_population: number | null;
  building_count: number;
  road_count: number;
  waterway_count: number;
  terrain_low_elevation_cells: number;
  terrain_low_elevation_threshold_m: number | null;
  rainfall_peak_mm_per_hour: number | null;
  rainfall_records: number | null;
  facility_count: number;
  underpass_available: boolean;
  flooded_area_km2: number | string;
  exposed_population: number | string;
  exposed_buildings: number | string;
  affected_road_length_km: number | string;
  critical_infrastructure: number | string;
  affected_shelters: number | string;
  data_status: string;
};

export type Observation = {
  timestamp: string;
  observation_type: "rainfall" | "water_level";
  station_id: string;
  value: number;
  unit: string;
  quality_flag: string;
  origin: DataStatus;
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
  origin: "TEMPORARY";
};
