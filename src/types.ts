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
  approx_flood_envelope: LayerPayload;
  hand_reconstruction: LayerPayload;
  facilities: LayerPayload;
  underpass: LayerPayload;
  flood_extent: LayerPayload;
};

export type DataStatusItem = {
  status: DataStatus;
  source?: string;
  source_type?: string;
  snapshot?: string | null;
  data_vintage?: string | null;
  role?: string;
  bbox?: [number, number, number, number];
  image_url?: string | null;
  image_size_bytes?: number;
  notes?: string;
  period?: string | null;
  data_year?: number | null;
  unit?: string;
  records?: number;
};

export type DataStatusResponse = {
  flood_extent: LayerPayload;
  safemap_floodmarks?: DataStatusItem;
  population: DataStatusItem;
  rainfall: DataStatusItem;
  water_level?: DataStatusItem;
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
  model_type?: string | null;
  baseline_state?: string | null;
  intervention_state?: string | null;
  response_window_min?: number | null;
  time_until_full_inundation_min?: number | null;
  official_population: number | null;
  building_count: number;
  road_count: number;
  waterway_count: number;
  terrain_low_elevation_cells: number;
  terrain_low_elevation_threshold_m: number | null;
  hand_reconstruction_features?: number;
  rainfall_peak_mm_per_hour: number | null;
  rainfall_peak_timestamp?: string | null;
  rainfall_peak_station_name?: string | null;
  rainfall_records: number | null;
  water_level_peak_m?: number | null;
  water_level_peak_timestamp?: string | null;
  water_level_peak_station_name?: string | null;
  primary_water_level_peak_m?: number | null;
  primary_water_level_peak_timestamp?: string | null;
  facility_count: number;
  underpass_available: boolean;
  safemap_floodmarks_available?: boolean;
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

export type ReconstructionEvent = {
  time: string;
  label: string;
  state: string;
  description: string;
  source: string;
  role: string;
  confidence: string;
};

export type ReconstructionResponse = {
  event_id: string;
  title: string;
  model_type: string;
  event_year: number;
  status: string;
  replay: ReconstructionEvent[];
  baseline: {
    name: string;
    description: string;
    states: Array<{
      state: string;
      time: string;
      underpass_status: string;
      risk: string;
    }>;
    failure_to_inflow_min: number;
    inflow_to_unsafe_min: number;
    inflow_to_full_inundation_min: number;
  };
  intervention: {
    name: string;
    type: InterventionType;
    trigger: string;
    trigger_time: string;
    trigger_basis: string;
    closure_action: string;
    estimated_effect: string;
    available_response_window_min: number;
    time_until_full_inundation_min: number;
    result_status: string;
  };
  provenance: Array<{
    source: string;
    data_vintage: string;
    role: string;
    status: DataStatus | string;
  }>;
  envelope_comparison?: {
    status: DataStatus | string;
    source_type: string;
    role: string;
    area_crs?: string;
    data_warning?: string[];
    methods?: Record<string, string>;
    rows: Array<{
      stage: string;
      label: string;
      approx_features: number;
      approx_area_km2: number;
      hand_features: number;
      hand_area_km2: number;
      hand_minus_approx_area_km2: number;
      hand_to_approx_area_ratio: number | null;
    }>;
  };
  limitations: string[];
};

export type InterventionType =
  | "EVACUATION"
  | "ROAD_CLOSURE"
  | "SHELTER_OPEN"
  | "TEMPORARY_BARRIER"
  | "LEVEE_IMPROVEMENT"
  | "INFRASTRUCTURE_PROTECTION";

export type ScenarioIntervention =
  | "flood_barrier"
  | "evacuation_support"
  | "road_closure"
  | "levee_improvement"
  | "infrastructure_protection";

export type PortfolioScenario = {
  scenario_id: number;
  name: string;
  event_id: string;
  building_ids: number[];
  interventions: ScenarioIntervention[];
  status: "DRAFT" | "COMPLETED";
  created_at: string;
};

export type PortfolioScenarioRunResult = {
  scenario_id: number;
  name: string;
  event_id: string;
  building_ids: number[];
  interventions: ScenarioIntervention[];
  status: "COMPLETED";
  before_priority_buildings: number;
  after_priority_buildings: number;
  risk_reduction: number;
  before_risk_score: number;
  after_risk_score: number;
  priority_building_ids_before: number[];
  priority_building_ids_after: number[];
  assumptions: string[];
  origin: "TEMPORARY";
};

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

export type AgentWorkflowName = "situation" | "closure_timing" | "inflow_delay" | "exposure_inventory";

export type AgentIntentPlanResult = {
  status: "READY" | "NEEDS_CLARIFICATION" | "UNSUPPORTED";
  event_id: string;
  workflow?: AgentWorkflowName | null;
  parameters: Record<string, unknown>;
  tool_names: string[];
  reason: string;
  assumptions: string[];
  limitations: string[];
};

export type AgentWorkflowResult = {
  workflow: AgentWorkflowName;
  event_id: string;
  status: "COMPLETED";
  tool_calls: Array<{
    order: number;
    tool_name: string;
    status: "completed";
    result_keys: string[];
  }>;
  result: Record<string, unknown>;
  provenance: Array<Record<string, unknown>>;
  coverage_status?: string | null;
  coverage_note?: string | null;
};
