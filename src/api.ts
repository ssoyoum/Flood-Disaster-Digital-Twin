import type { DataStatusResponse, ExposureMetrics, FloodEvent, GeoJson, LayersResponse, Observation, SafetyDataApiTestResult, ScenarioResult, InterventionType } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export const assetUrl = (path?: string | null) => {
  if (!path) return "";
  if (/^https?:\/\//.test(path)) return path;
  return `${API_BASE}${path}`;
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, options);
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${path}`);
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

export const testSafetyDataApi = (serviceKey: string) =>
  request<SafetyDataApiTestResult>("/api/integrations/safety-data/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ service_key: serviceKey }),
  });
