import type { CriteriaFloor, RiseForecast, TwinBacktest, TwinCriteriaReview, TwinFacility, TwinMode, TwinStatus, CaseLeadTimes, ResponseTimingResult, TimelineReconstructionResponse, AlertTimingResult, StorageCaptureResult, UrbanReconstructionResponse, ClosureTimingResult, ExposureInventory, AgentAskResult, AgentExampleQuestion, AgentIntentPlanResult, AgentWorkflowName, AgentWorkflowResult, HandThresholdResult, DataStatusResponse, ExposureMetrics, FloodEvent, GeoJson, LayersResponse, Observation, ReconstructionResponse, SafetyDataApiTestResult, ScenarioResult, InterventionType, PortfolioScenario, PortfolioScenarioRunResult, ScenarioIntervention } from "./types";
import { boundedAgentHistory, type ConversationMessage } from "./agentConversation";
import type { WaterLevelReadiness, WatchChanges, WatchFacilityLink, WatchFacilityStatus, WatchOverview, WatchStage, WatchStationDetail, SeoulRiverStageFeed } from "./types";

const configuredApiBase = import.meta.env.VITE_API_BASE;
const API_BASE = configuredApiBase === "same-origin" ? "" : configuredApiBase ?? (import.meta.env.PROD ? "" : "http://localhost:8033");

export const assetUrl = (path?: string | null) => {
  if (!path) return "";
  if (/^https?:\/\//.test(path)) return path;
  return `${API_BASE}${path}`;
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    // FastAPI puts a readable reason in `detail`; rate limits (429) rely on it.
    const detail = await response.json().then((body) => (typeof body?.detail === "string" ? body.detail : "")).catch(() => "");
    throw new Error(`API ${response.status}: ${detail || path}`);
  }
  return response.json() as Promise<T>;
}

export const getEvents = () => request<FloodEvent[]>("/api/events");
export const getEvent = (eventId: string) => request<FloodEvent>(`/api/events/${eventId}`);
export const getFlood = (eventId: string) => request<GeoJson>(`/api/events/${eventId}/flood`);
export const getTimeline = (eventId: string) => request<Observation[]>(`/api/events/${eventId}/flood/timeline`);
export const getLayers = (eventId: string, layerYear = 2023) => request<LayersResponse>(`/api/events/${eventId}/layers?layer_year=${encodeURIComponent(layerYear)}`);
export const getSummary = (eventId: string) => request<ExposureMetrics>(`/api/events/${eventId}/summary`);
export const getStatus = (eventId: string) => request<DataStatusResponse>(`/api/events/${eventId}/status`);
export const getReconstruction = (eventId: string) => request<ReconstructionResponse>(`/api/events/${eventId}/reconstruction`);
export const getBuildings = () => request<GeoJson>("/api/buildings");
export const getRoads = () => request<GeoJson>("/api/roads");
export const getInfrastructure = () => request<GeoJson>("/api/infrastructure");
export const getShelters = () => request<GeoJson>("/api/shelters");
export const getBaseline = (eventId: string) => request<{ result: ExposureMetrics }>(`/api/scenarios/baseline?event_id=${encodeURIComponent(eventId)}`);

export const createScenario = (name: string, interventionType: InterventionType, eventId: string) =>
  request<ScenarioResult>("/api/scenarios", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, intervention_type: interventionType, event_id: eventId }),
  });

export const createPortfolioScenario = (payload: {
  name?: string;
  event_id?: string;
  building_ids: number[];
  interventions: ScenarioIntervention[];
}) =>
  request<PortfolioScenario>("/api/scenarios", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

export const runPortfolioScenario = (scenarioId: number) =>
  request<PortfolioScenarioRunResult>(`/api/scenarios/${scenarioId}/run`, { method: "POST" });

export const testSafetyDataApi = (serviceKey: string) =>
  request<SafetyDataApiTestResult>("/api/integrations/safety-data/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ service_key: serviceKey }),
  });

export const getExposureInventory = (eventId: string, radii: number[] = [300, 500, 1000, 2000]) =>
  request<ExposureInventory>(`/api/events/${eventId}/exposure-inventory?${radii.map((radius) => `radii_m=${radius}`).join("&")}`);

export const getAgentExamples = (eventId = "osong-2023", facilityId?: string | null, board?: "watch" | null) => request<AgentExampleQuestion[]>(`/api/agent/examples?event_id=${encodeURIComponent(eventId)}${facilityId ? `&facility_id=${encodeURIComponent(facilityId)}` : ""}${board ? `&board=${board}` : ""}`);

export type AgentFacility = { id: string; name: string; event_id: string; mode: "live" | "replay" };
export type AgentFacilityScope = { facility_id?: string; observation_at?: string | null; board?: "watch" };
export const getAgentFacilities = () => request<AgentFacility[]>("/api/twin/facilities");

export const askAgent = (eventId: string, message: string, history: ConversationMessage[] = [], signal?: AbortSignal, scope?: AgentFacilityScope) =>
  request<AgentAskResult>("/api/agent/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event_id: eventId, message, history: boundedAgentHistory(history), ...scope }),
    signal,
  });

export const planAgentIntent = (eventId: string, message: string) =>
  request<AgentIntentPlanResult>("/api/agent/plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event_id: eventId, message }),
  });

export const runAgentWorkflow = (eventId: string, workflow: AgentWorkflowName, parameters: Record<string, unknown>) =>
  request<AgentWorkflowResult>("/api/agent/workflows", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event_id: eventId, workflow, ...parameters }),
  });

export const getClosureTiming = (eventId: string, closureTimes: string[]) =>
  request<ClosureTimingResult>(`/api/events/${eventId}/analysis/closure-timing`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ closure_times: closureTimes }),
  });

export const getHandThreshold = (eventId: string, reductionM: number) =>
  request<HandThresholdResult>(`/api/events/${eventId}/analysis/hand-threshold`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reduction_m: reductionM }),
  });

export const getUrbanReconstruction = (eventId: string) => request<UrbanReconstructionResponse>(`/api/events/${eventId}/reconstruction`);

export const getAlertTiming = (eventId: string, body: { station?: string; thresholds_mm_per_hour?: number[]; alert_times?: string[] }) =>
  request<AlertTimingResult>(`/api/events/${eventId}/analysis/alert-timing`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const getStorageCapture = (
  eventId: string,
  body: { station?: string; storage_m3?: number; capacity_mm_per_hour?: number; catchment_area_km2?: number; runoff_coefficient?: number },
) =>
  request<StorageCaptureResult>(`/api/events/${eventId}/analysis/storage-capture`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const getTimelineReconstruction = (eventId: string) => request<TimelineReconstructionResponse>(`/api/events/${eventId}/reconstruction`);

export const getResponseTiming = (eventId: string, interventionId: string, actionTimes: string[]) =>
  request<ResponseTimingResult>(`/api/events/${eventId}/analysis/response-timing`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ intervention_id: interventionId, action_times: actionTimes }),
  });

export const getCaseLeadTimes = () => request<CaseLeadTimes>("/api/cases/lead-times");

// Underpass control-decision twin
export const getTwinMode = () => request<TwinMode>("/api/twin/mode");
export const getTwinFacilities = () => request<TwinFacility[]>("/api/twin/facilities");
export const getTwinStatus = (facilityId: string, at?: string) => request<TwinStatus>(`/api/twin/facilities/${encodeURIComponent(facilityId)}/status${at ? `?at=${encodeURIComponent(at)}` : ""}`);
export const getTwinBacktest = (facilityId: string) => request<TwinBacktest>(`/api/twin/facilities/${encodeURIComponent(facilityId)}/backtest`);
export const getTwinCriteriaReview = (facilityId: string, stageFloor: CriteriaFloor, leadThresholdMin: number, signal?: AbortSignal) =>
  request<TwinCriteriaReview>(`/api/twin/facilities/${encodeURIComponent(facilityId)}/criteria-review?stage_floor=${stageFloor}&lead_threshold_min=${leadThresholdMin}`, { signal });
export const getWaterLevelReadiness = (facilityId: string, at?: string, signal?: AbortSignal) =>
  request<WaterLevelReadiness>(`/api/twin/facilities/${encodeURIComponent(facilityId)}/forecast-readiness${at ? `?at=${encodeURIComponent(at)}` : ""}`, { signal });
export const getRiseForecast = (facilityId: string, at?: string, signal?: AbortSignal) =>
  request<RiseForecast>(`/api/twin/facilities/${encodeURIComponent(facilityId)}/rise-forecast${at ? `?at=${encodeURIComponent(at)}` : ""}`, { signal });

// National watch board
const watchQuery = (params: Record<string, string | number | null | undefined>) => {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => { if (value !== null && value !== undefined && value !== "") search.set(key, String(value)); });
  const text = search.toString();
  return text ? `?${text}` : "";
};
export const getWatchOverview = (options: { at?: string | null; region?: string | null; min_stage?: WatchStage | null; limit?: number } = {}, signal?: AbortSignal) =>
  request<WatchOverview>(`/api/watch/overview${watchQuery(options)}`, { signal });
export const getWatchStation = (code: string, at?: string | null, signal?: AbortSignal) =>
  request<WatchStationDetail>(`/api/watch/stations/${encodeURIComponent(code)}${watchQuery({ at })}`, { signal });
export const getWatchChanges = (options: { at?: string | null; since_min?: number; region?: string | null } = {}, signal?: AbortSignal) =>
  request<WatchChanges>(`/api/watch/changes${watchQuery(options)}`, { signal });
export const getWatchFacilityStatus = (options: { at?: string | null } = {}, signal?: AbortSignal) =>
  request<WatchFacilityStatus>(`/api/watch/facility-status${watchQuery(options)}`, { signal });
export const getWatchFacilities = () => request<Array<WatchFacilityLink & { station_code: string }>>("/api/watch/facilities");
export const getSeoulRiverStages = (signal?: AbortSignal) => request<SeoulRiverStageFeed>("/api/watch/seoul-river-stages", { signal });
