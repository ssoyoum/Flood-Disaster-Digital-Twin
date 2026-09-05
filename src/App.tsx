import { useEffect, useMemo, useRef, useState, type Dispatch, type SetStateAction } from "react";
import maplibregl, { type GeoJSONSource, type MapLayerMouseEvent, type Map as MapLibreMap, type Popup } from "maplibre-gl";
import { Activity, AlertTriangle, Bot, Building2, Check, CloudRain, Layers3, MapPin, Pause, Play, Route, Send, Waves } from "lucide-react";
import * as api from "./api";
import DarkConsole from "./dark/DarkConsole";
import type { AgentExampleQuestion, AgentIntentPlanResult, AgentWorkflowName, AgentWorkflowResult, DataStatusItem, DataStatusResponse, ExposureMetrics, FloodEvent, GeoJson, LayerPayload, LayersResponse, ReconstructionResponse } from "./types";

const emptyGeoJson: GeoJson = { type: "FeatureCollection", features: [] };

const emptyLayer = (key: string, label: string): LayerPayload => ({
  key,
  label,
  status: "UNAVAILABLE",
  feature_count: 0,
  data: emptyGeoJson,
});

const emptyLayers: LayersResponse = {
  aoi: emptyLayer("aoi", "AOI"),
  roads: emptyLayer("roads", "Roads"),
  buildings: emptyLayer("buildings", "Buildings"),
  waterways: emptyLayer("waterways", "Waterways"),
  terrain: emptyLayer("terrain", "Terrain Context"),
  approx_flood_envelope: emptyLayer("approx_flood_envelope", "Approximate Flood Envelope"),
  hand_reconstruction: emptyLayer("hand_reconstruction", "HAND Reconstruction"),
  facilities: emptyLayer("facilities", "Facilities"),
  underpass: emptyLayer("underpass", "Gungpyeong 2 Underpass"),
  flood_extent: emptyLayer("flood_extent", "Flood Extent"),
};

const layerLabels: Record<keyof LayersResponse, string> = {
  aoi: "AOI",
  roads: "Roads",
  buildings: "Buildings",
  waterways: "Waterways",
  terrain: "Terrain Context",
  approx_flood_envelope: "Approx Flood Envelope",
  hand_reconstruction: "HAND Reconstruction",
  facilities: "Facilities",
  underpass: "Gungpyeong 2 Underpass",
  flood_extent: "Flood Extent",
};

type ScenarioMode = "baseline" | "intervention";

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return "--";
  return new Intl.NumberFormat("ko-KR").format(value);
}

function formatDecimal(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined) return "--";
  return new Intl.NumberFormat("ko-KR", { maximumFractionDigits: digits }).format(value);
}

function formatClock(value?: string | null) {
  if (!value) return "--:--";
  return value.slice(11, 16);
}

function vintageFromLayer(layer: LayerPayload) {
  return layer.snapshot ?? "NOT RECORDED";
}

function compactVintage(value?: string | null) {
  if (!value) return "NOT RECORDED";
  const year = value.match(/\b(19|20)\d{2}\b/)?.[0];
  return year ?? value;
}

function vintageFromStatus(item?: { period?: string | null; data_year?: number | null; snapshot?: string | null }) {
  if (!item) return "NOT RECORDED";
  return item.period ?? item.snapshot ?? (item.data_year ? String(item.data_year) : "NOT RECORDED");
}

function layerSubLabel(layer: LayerPayload) {
  const source = layer.source_type?.replaceAll("_", " ") ?? "Source not recorded";
  return `${source} · ${compactVintage(vintageFromLayer(layer))}`;
}

function collectCoordinates(value: unknown, points: [number, number][] = []): [number, number][] {
  if (!Array.isArray(value)) return points;
  if (typeof value[0] === "number" && typeof value[1] === "number") {
    points.push([value[0], value[1]]);
    return points;
  }
  value.forEach((item) => collectCoordinates(item, points));
  return points;
}

function fitToFocusArea(map: MapLibreMap, underpass: GeoJson, fallback: GeoJson) {
  const bounds = new maplibregl.LngLatBounds();
  const focus = underpass.features.length ? underpass : fallback;
  focus.features.forEach((feature) => {
    collectCoordinates(feature.geometry.coordinates).forEach(([lng, lat]) => bounds.extend([lng, lat]));
  });
  if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: 170, duration: 0, maxZoom: 17.2 });
}

function centerOfGeoJson(data: GeoJson): [number, number] | null {
  const points = data.features.flatMap((feature) => collectCoordinates(feature.geometry.coordinates));
  if (!points.length) return null;
  const sum = points.reduce(([lngSum, latSum], [lng, lat]) => [lngSum + lng, latSum + lat], [0, 0]);
  return [sum[0] / points.length, sum[1] / points.length];
}

function replaySeverity(state?: string) {
  const severityByState: Record<string, number> = {
    warning: 1,
    hydraulic_warning: 2,
    overtopping: 3,
    levee_failure: 4,
    underpass_inflow: 5,
    unsafe_driving: 6,
    full_inundation: 7,
  };
  return state ? severityByState[state] ?? 1 : 0;
}

function replayColor(state?: string, scenario: ScenarioMode = "baseline") {
  if (scenario === "intervention" && replaySeverity(state) >= 5) return "#1f9d78";
  const colorByState: Record<string, string> = {
    warning: "#d6a342",
    hydraulic_warning: "#4e8ec7",
    overtopping: "#2b8ec4",
    levee_failure: "#c65b50",
    underpass_inflow: "#d8793c",
    unsafe_driving: "#a94848",
    full_inundation: "#713f58",
  };
  return state ? colorByState[state] ?? "#d8793c" : "#9aa8ad";
}

function replayMapFeature(reconstruction: ReconstructionResponse | null, time: number, scenario: ScenarioMode, center: [number, number] | null): GeoJson {
  const active = reconstruction?.replay[time];
  if (!active || !center) return emptyGeoJson;
  const severity = replaySeverity(active.state);
  const interventionActive = scenario === "intervention" && severity >= 5;
  return {
    type: "FeatureCollection",
    features: [{
      type: "Feature",
      geometry: { type: "Point", coordinates: center },
      properties: {
        time: formatClock(active.time),
        label: interventionActive ? "Auto closure active" : active.label,
        state: active.state,
        severity,
        color: replayColor(active.state, scenario),
        radius: interventionActive ? 74 : 44 + (severity * 8),
      },
    }],
  };
}

function popupHtml(title: string, rows: Array<[string, unknown]>) {
  const clean = (value: unknown) => String(value ?? "Unknown").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[char] ?? char));
  return `<div class="map-popup"><strong>${clean(title)}</strong>${rows.map(([label, value]) => `<span><em>${clean(label)}</em>${clean(value)}</span>`).join("")}</div>`;
}

function Metric({ icon: Icon, label, value, note }: { icon: typeof Building2; label: string; value: string; note?: string }) {
  return (
    <div className="metric-card">
      <div className="metric-icon"><Icon size={16} /></div>
      <div className="metric-copy">
        <span>{label}</span>
        <strong>{value}</strong>
        {note && <small>{note}</small>}
      </div>
    </div>
  );
}

function MapPanel({
  layers,
  visible,
  safemapVisible,
  safemapOverlay,
  reconstruction,
  time,
  scenario,
}: {
  layers: LayersResponse;
  visible: Record<keyof LayersResponse, boolean>;
  safemapVisible: boolean;
  safemapOverlay?: DataStatusItem;
  reconstruction: ReconstructionResponse | null;
  time: number;
  scenario: ScenarioMode;
}) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const hoverPopupRef = useRef<Popup | null>(null);
  const activeReplay = reconstruction?.replay[time];

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
        sources: {
          "osm-basemap": {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors",
          },
        },
        layers: [
          { id: "background", type: "background", paint: { "background-color": "#e7eef0" } },
          { id: "osm-basemap", type: "raster", source: "osm-basemap", paint: { "raster-opacity": 0.74, "raster-saturation": -0.35 } },
        ],
      },
      center: [127.3377, 36.6247],
      zoom: 15.4,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.on("load", () => {
      map.addSource("aoi", { type: "geojson", data: layers.aoi.data as never });
      map.addLayer({ id: "aoi-fill", type: "fill", source: "aoi", paint: { "fill-color": "#7bb6b2", "fill-opacity": 0.08 } });
      map.addLayer({ id: "aoi-line", type: "line", source: "aoi", paint: { "line-color": "#2e7b84", "line-width": 2, "line-dasharray": [2, 2] } });

      map.addSource("terrain", { type: "geojson", data: layers.terrain.data as never });
      map.addLayer({
        id: "terrain-fill",
        type: "fill",
        source: "terrain",
        paint: { "fill-color": "#c9d05b", "fill-opacity": 0.28 },
      });
      map.addLayer({ id: "terrain-line", type: "line", source: "terrain", paint: { "line-color": "#8d9430", "line-width": 0.6, "line-opacity": 0.45 } });

      map.addSource("approx_flood_envelope", { type: "geojson", data: layers.approx_flood_envelope.data as never });
      map.addLayer({
        id: "approx-flood-envelope-fill",
        type: "fill",
        source: "approx_flood_envelope",
        filter: ["all", ["==", ["geometry-type"], "Polygon"], ["==", ["get", "stage_index"], time]],
        paint: {
          "fill-color": scenario === "intervention" ? "#28a77d" : "#d8793c",
          "fill-opacity": ["interpolate", ["linear"], ["get", "stage_index"], 1, 0.12, 6, 0.34],
        },
      });
      map.addLayer({
        id: "approx-flood-envelope-line",
        type: "line",
        source: "approx_flood_envelope",
        filter: ["all", ["==", ["geometry-type"], "Polygon"], ["==", ["get", "stage_index"], time]],
        paint: { "line-color": "#b75a39", "line-width": 0.7, "line-opacity": 0.35 },
      });
      map.addLayer({
        id: "approx-flow-path-line",
        type: "line",
        source: "approx_flood_envelope",
        filter: ["all", ["==", ["geometry-type"], "LineString"], ["==", ["get", "stage_index"], time]],
        paint: { "line-color": "#d93f35", "line-width": 3.2, "line-dasharray": [1, 1], "line-opacity": 0.88 },
      });

      map.addSource("hand_reconstruction", { type: "geojson", data: layers.hand_reconstruction.data as never });
      map.addLayer({
        id: "hand-reconstruction-fill",
        type: "fill",
        source: "hand_reconstruction",
        filter: ["all", ["==", ["geometry-type"], "Polygon"], ["==", ["get", "stage_index"], time]],
        paint: {
          "fill-color": scenario === "intervention" ? "#37a881" : "#2f8ec9",
          "fill-opacity": ["interpolate", ["linear"], ["get", "hand_threshold_m"], 0, 0.12, 6, 0.38],
        },
      });
      map.addLayer({
        id: "hand-reconstruction-line",
        type: "line",
        source: "hand_reconstruction",
        filter: ["all", ["==", ["geometry-type"], "Polygon"], ["==", ["get", "stage_index"], time]],
        paint: { "line-color": "#1c648d", "line-width": 0.7, "line-opacity": 0.45 },
      });
      map.addLayer({
        id: "hand-connection-line",
        type: "line",
        source: "hand_reconstruction",
        filter: ["all", ["==", ["geometry-type"], "LineString"], ["==", ["get", "stage_index"], time]],
        paint: { "line-color": "#1b7d68", "line-width": 3.4, "line-dasharray": [1.2, 0.8], "line-opacity": 0.9 },
      });

      const bbox = safemapOverlay?.bbox;
      const imageUrl = api.assetUrl(safemapOverlay?.image_url);
      if (bbox && imageUrl) {
        map.addSource("safemap-floodmarks", {
          type: "image",
          url: imageUrl,
          coordinates: [
            [bbox[0], bbox[3]],
            [bbox[2], bbox[3]],
            [bbox[2], bbox[1]],
            [bbox[0], bbox[1]],
          ],
        });
        map.addLayer({
          id: "safemap-floodmarks-raster",
          type: "raster",
          source: "safemap-floodmarks",
          layout: { visibility: safemapVisible ? "visible" : "none" },
          paint: { "raster-opacity": 0.58 },
        });
      }

      map.addSource("waterways", { type: "geojson", data: layers.waterways.data as never });
      map.addLayer({ id: "waterways-fill", type: "fill", source: "waterways", paint: { "fill-color": "#2b8ec4", "fill-opacity": 0.28 } });
      map.addLayer({ id: "waterways-line", type: "line", source: "waterways", paint: { "line-color": "#0f6898", "line-width": 2.2, "line-opacity": 0.9 } });

      map.addSource("roads", { type: "geojson", data: layers.roads.data as never });
      map.addLayer({ id: "roads-line", type: "line", source: "roads", paint: { "line-color": "#6c7480", "line-width": 1.4, "line-opacity": 0.55 } });

      map.addSource("buildings", { type: "geojson", data: layers.buildings.data as never });
      map.addLayer({
        id: "buildings-fill",
        type: "fill",
        source: "buildings",
        paint: {
          "fill-color": [
            "match",
            ["get", "building"],
            "apartments", "#315c73",
            "commercial", "#7d5b9f",
            "school", "#2f8f70",
            "university", "#2f8f70",
            "train_station", "#b06a31",
            "#57707b",
          ],
          "fill-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 0.68, 0.42],
        },
      });
      map.addLayer({ id: "buildings-line", type: "line", source: "buildings", paint: { "line-color": "#183645", "line-width": ["case", ["boolean", ["feature-state", "hover"], false], 1.4, 0.45], "line-opacity": 0.65 } });

      map.addSource("facilities", { type: "geojson", data: layers.facilities.data as never });
      map.addLayer({
        id: "facilities-point",
        type: "circle",
        source: "facilities",
        paint: {
          "circle-color": [
            "match",
            ["get", "amenity"],
            "school", "#2f8f70",
            "hospital", "#c74f4a",
            "parking", "#6d7482",
            "restaurant", "#d49534",
            "fuel", "#7d5b9f",
            "#e0a13c",
          ],
          "circle-radius": ["case", ["boolean", ["feature-state", "hover"], false], 7, 4.8],
          "circle-stroke-width": 1.5,
          "circle-stroke-color": "#fff",
        },
      });

      map.addSource("underpass", { type: "geojson", data: layers.underpass.data as never });
      map.addLayer({ id: "underpass-line", type: "line", source: "underpass", paint: { "line-color": "#d93f35", "line-width": 6, "line-opacity": 0.95 } });

      map.addSource("replay-risk", { type: "geojson", data: replayMapFeature(reconstruction, time, scenario, centerOfGeoJson(layers.underpass.data)) as never });
      map.addLayer({
        id: "replay-risk-halo",
        type: "circle",
        source: "replay-risk",
        paint: {
          "circle-color": ["get", "color"],
          "circle-radius": ["get", "radius"],
          "circle-opacity": 0.18,
          "circle-stroke-color": ["get", "color"],
          "circle-stroke-width": 2,
          "circle-stroke-opacity": 0.75,
        },
      });
      map.addLayer({
        id: "replay-risk-core",
        type: "circle",
        source: "replay-risk",
        paint: {
          "circle-color": ["get", "color"],
          "circle-radius": 8,
          "circle-opacity": 0.9,
          "circle-stroke-color": "#fff",
          "circle-stroke-width": 2,
        },
      });
      map.addLayer({
        id: "replay-risk-label",
        type: "symbol",
        source: "replay-risk",
        layout: {
          "text-field": ["concat", ["get", "time"], "  ", ["get", "label"]],
          "text-size": 12,
          "text-font": ["Open Sans Semibold", "Arial Unicode MS Bold"],
          "text-offset": [0, -2.2],
          "text-anchor": "bottom",
          "text-allow-overlap": true,
        },
        paint: {
          "text-color": "#17333d",
          "text-halo-color": "#ffffff",
          "text-halo-width": 1.5,
        },
      });

      map.on("mouseenter", "buildings-fill", () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", "buildings-fill", () => { map.getCanvas().style.cursor = ""; hoverPopupRef.current?.remove(); hoverPopupRef.current = null; });
      map.on("mousemove", "buildings-fill", (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0];
        if (!feature) return;
        const properties = feature.properties ?? {};
        hoverPopupRef.current?.remove();
        hoverPopupRef.current = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 12 })
          .setLngLat(event.lngLat)
          .setHTML(popupHtml(String(properties.name ?? "Unnamed building"), [["layer", "Building"], ["type", properties.building], ["source", layers.buildings.source], ["data vintage", vintageFromLayer(layers.buildings)]]))
          .addTo(map);
      });
      map.on("click", "buildings-fill", (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0];
        if (!feature) return;
        const properties = feature.properties ?? {};
        new maplibregl.Popup({ offset: 14 })
          .setLngLat(event.lngLat)
          .setHTML(popupHtml(String(properties.name ?? "Unnamed building"), [["layer", "Building"], ["building", properties.building], ["osm id", properties.osm_id], ["source", layers.buildings.source], ["data vintage", vintageFromLayer(layers.buildings)]]))
          .addTo(map);
      });

      map.on("mouseenter", "facilities-point", () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", "facilities-point", () => { map.getCanvas().style.cursor = ""; });
      map.on("click", "facilities-point", (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0];
        if (!feature) return;
        const properties = feature.properties ?? {};
        new maplibregl.Popup({ offset: 14 })
          .setLngLat(event.lngLat)
          .setHTML(popupHtml(String(properties.name ?? "Unnamed facility"), [["layer", "Facility / POI"], ["amenity", properties.amenity ?? properties.kind], ["osm id", properties.osm_id], ["source", layers.facilities.source], ["data vintage", vintageFromLayer(layers.facilities)]]))
          .addTo(map);
      });

      map.on("mouseenter", "waterways-fill", () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", "waterways-fill", () => { map.getCanvas().style.cursor = ""; });
      map.on("click", "waterways-fill", (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0];
        if (!feature) return;
        const properties = feature.properties ?? {};
        new maplibregl.Popup({ offset: 14 })
          .setLngLat(event.lngLat)
          .setHTML(popupHtml(String(properties.RIVNM_2 ?? "Unnamed river"), [["layer", "River polygon"], ["class", properties.CLAS2], ["river code", properties.RIVCD_2], ["source", layers.waterways.source], ["data vintage", vintageFromLayer(layers.waterways)]]))
          .addTo(map);
      });

      map.on("mouseenter", "terrain-fill", () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", "terrain-fill", () => { map.getCanvas().style.cursor = ""; });
      map.on("click", "terrain-fill", (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0];
        if (!feature) return;
        const properties = feature.properties ?? {};
        new maplibregl.Popup({ offset: 14 })
          .setLngLat(event.lngLat)
          .setHTML(popupHtml(String(properties.terrain_class ?? "Terrain context"), [["layer", "DEM terrain context"], ["mean elevation", `${properties.mean_elevation_m ?? "Unknown"} m`], ["source", layers.terrain.source], ["data vintage", vintageFromLayer(layers.terrain)]]))
          .addTo(map);
      });

      map.on("click", "hand-reconstruction-fill", (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0];
        if (!feature) return;
        const properties = feature.properties ?? {};
        new maplibregl.Popup({ offset: 14 })
          .setLngLat(event.lngLat)
          .setHTML(popupHtml("HAND reconstruction cell", [["stage", properties.label], ["HAND", `${properties.hand_m ?? "Unknown"} m`], ["threshold", `${properties.hand_threshold_m ?? "Unknown"} m`], ["water level", `${properties.observed_water_level_m ?? "Unknown"} m`], ["source", layers.hand_reconstruction.source], ["data vintage", vintageFromLayer(layers.hand_reconstruction)]]))
          .addTo(map);
      });

      map.on("click", "underpass-line", (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0];
        if (!feature) return;
        const properties = feature.properties ?? {};
        new maplibregl.Popup({ offset: 14 })
          .setLngLat(event.lngLat)
          .setHTML(popupHtml(String(properties.facility_name ?? "Gungpyeong 2 Underpass"), [["layer", "Transport Facility"], ["type", properties.facility_type], ["route", properties.road_route], ["agency", properties.managing_agency], ["source", layers.underpass.source], ["data vintage", vintageFromLayer(layers.underpass)]]))
          .addTo(map);
      });

      fitToFocusArea(map, layers.underpass.data, layers.aoi.data);
    });
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    (Object.keys(layers) as Array<keyof LayersResponse>).forEach((key) => {
      const source = map.getSource(key) as GeoJSONSource | undefined;
      if (source) source.setData(layers[key].data as never);
    });
    if (layers.underpass.data.features.length || layers.aoi.data.features.length) fitToFocusArea(map, layers.underpass.data, layers.aoi.data);
  }, [layers]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    const source = map.getSource("replay-risk") as GeoJSONSource | undefined;
    if (source) source.setData(replayMapFeature(reconstruction, time, scenario, centerOfGeoJson(layers.underpass.data)) as never);
    if (map.getLayer("approx-flood-envelope-fill")) {
      map.setFilter("approx-flood-envelope-fill", ["all", ["==", ["geometry-type"], "Polygon"], ["==", ["get", "stage_index"], time]]);
      map.setPaintProperty("approx-flood-envelope-fill", "fill-color", scenario === "intervention" ? "#28a77d" : "#d8793c");
    }
    if (map.getLayer("approx-flood-envelope-line")) {
      map.setFilter("approx-flood-envelope-line", ["all", ["==", ["geometry-type"], "Polygon"], ["==", ["get", "stage_index"], time]]);
      map.setPaintProperty("approx-flood-envelope-line", "line-color", scenario === "intervention" ? "#1f8064" : "#b75a39");
    }
    if (map.getLayer("approx-flow-path-line")) {
      map.setFilter("approx-flow-path-line", ["all", ["==", ["geometry-type"], "LineString"], ["==", ["get", "stage_index"], time]]);
      map.setPaintProperty("approx-flow-path-line", "line-color", scenario === "intervention" ? "#1f8064" : "#d93f35");
    }
    if (map.getLayer("hand-reconstruction-fill")) {
      map.setFilter("hand-reconstruction-fill", ["all", ["==", ["geometry-type"], "Polygon"], ["==", ["get", "stage_index"], time]]);
      map.setPaintProperty("hand-reconstruction-fill", "fill-color", scenario === "intervention" ? "#37a881" : "#2f8ec9");
    }
    if (map.getLayer("hand-reconstruction-line")) {
      map.setFilter("hand-reconstruction-line", ["all", ["==", ["geometry-type"], "Polygon"], ["==", ["get", "stage_index"], time]]);
      map.setPaintProperty("hand-reconstruction-line", "line-color", scenario === "intervention" ? "#1f8064" : "#1c648d");
    }
    if (map.getLayer("hand-connection-line")) {
      map.setFilter("hand-connection-line", ["all", ["==", ["geometry-type"], "LineString"], ["==", ["get", "stage_index"], time]]);
      map.setPaintProperty("hand-connection-line", "line-color", scenario === "intervention" ? "#1f8064" : "#1b7d68");
    }
    if (map.getLayer("underpass-line")) {
      map.setPaintProperty("underpass-line", "line-color", replayColor(activeReplay?.state, scenario));
      map.setPaintProperty("underpass-line", "line-width", scenario === "intervention" && replaySeverity(activeReplay?.state) >= 5 ? 8 : 6);
    }
  }, [activeReplay?.state, layers.underpass.data, reconstruction, scenario, time]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    const visibility = (key: keyof LayersResponse) => visible[key] ? "visible" : "none";
    [["aoi-fill", "aoi"], ["aoi-line", "aoi"], ["terrain-fill", "terrain"], ["terrain-line", "terrain"], ["approx-flood-envelope-fill", "approx_flood_envelope"], ["approx-flood-envelope-line", "approx_flood_envelope"], ["approx-flow-path-line", "approx_flood_envelope"], ["hand-reconstruction-fill", "hand_reconstruction"], ["hand-reconstruction-line", "hand_reconstruction"], ["hand-connection-line", "hand_reconstruction"], ["waterways-fill", "waterways"], ["waterways-line", "waterways"], ["roads-line", "roads"], ["buildings-fill", "buildings"], ["buildings-line", "buildings"], ["facilities-point", "facilities"], ["underpass-line", "underpass"]].forEach(([layerId, key]) => {
      if (map.getLayer(layerId)) map.setLayoutProperty(layerId, "visibility", visibility(key as keyof LayersResponse));
    });
    if (map.getLayer("safemap-floodmarks-raster")) {
      map.setLayoutProperty("safemap-floodmarks-raster", "visibility", safemapVisible ? "visible" : "none");
    }
  }, [visible, safemapVisible]);

  return (
    <div className="map-panel">
      <div ref={mapContainer} className="map-canvas" />
      {activeReplay && (
        <div className={`map-replay-banner ${scenario}`}>
          <span>{formatClock(activeReplay.time)}</span>
          <strong>{scenario === "intervention" && replaySeverity(activeReplay.state) >= 5 ? "Auto closure active" : activeReplay.label}</strong>
          <small>{scenario === "baseline" ? "HAND-based reconstruction, not official extent" : "Road closure what-if, not official extent"}</small>
        </div>
      )}
      <div className="map-label"><span className="pulse-dot" /> Osong 2023 MVP | Online OSM basemap</div>
      <div className="map-attribution">Basemap © OpenStreetMap contributors | Flood marks © MOIS Safemap WMS | Current basemap is context only</div>
      <div className="map-legend">
        <div><i className="legend-replay" />Replay status</div>
        <div><i className="legend-hand" />HAND reconstruction</div>
        <div><i className="legend-approx-flood" />Approx envelope</div>
        <div><i className="legend-aoi" />AOI</div>
        <div><i className="legend-water" />Official river area</div>
        <div><i className="legend-road" />Road</div>
        <div><i className="legend-building" />Building</div>
        <div><i className="legend-underpass" />Underpass</div>
      </div>
    </div>
  );
}

function EventHeader({ eventData }: { eventData: FloodEvent }) {
  return (
    <header className="topbar">
      <div className="brand"><div className="brand-mark"><Waves size={19} /></div><div><strong>FloodOps</strong><span>REACT ASSIGNMENT</span></div></div>
      <div className="topbar-context"><span className="status-dot" /> Historical Disaster Reconstruction <span className="divider" /> representative event: {eventData.id}</div>
    </header>
  );
}

function ProvenancePanel({
  events,
  eventData,
  layers,
  dataStatus,
  layerRows,
  showLayers,
  showSafemapFloodmarks,
  setShowLayers,
  setShowSafemapFloodmarks,
}: {
  events: FloodEvent[];
  eventData: FloodEvent;
  layers: LayersResponse;
  dataStatus: DataStatusResponse | null;
  layerRows: Array<keyof LayersResponse>;
  showLayers: Record<keyof LayersResponse, boolean>;
  showSafemapFloodmarks: boolean;
  setShowLayers: Dispatch<SetStateAction<Record<keyof LayersResponse, boolean>>>;
  setShowSafemapFloodmarks: Dispatch<SetStateAction<boolean>>;
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-scroll">
        <section className="section-block event-block">
          <div className="eyebrow">EVENT</div>
          <div className="event-picker"><span className="event-pin"><MapPin size={15} /></span><select value={eventData.id} disabled aria-label="Event selector">{events.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div>
          <div className="event-meta"><span>{eventData.started_at.slice(0, 10)}</span><span>Osong case</span></div>
          <div className="incident-vintage"><span>Incident: Osong Flood</span><strong>Event Year: {eventData.data_year}</strong></div>
          <p className="event-analysis"><strong>{eventData.theme}</strong><span>{eventData.analysis_flow}</span><small>{eventData.focus_feature}</small><small>{eventData.source}</small></p>
        </section>

        <section className="section-block layers-block">
          <div className="section-heading"><div><div className="eyebrow">LAYERS</div><h2>Map controls</h2></div><Layers3 size={16} className="muted-icon" /></div>
          {layerRows.map((key) => (
            <label className="layer-row" key={key}>
              <input type="checkbox" checked={showLayers[key]} onChange={(event) => setShowLayers((state) => ({ ...state, [key]: event.target.checked }))} />
              <span className={`layer-swatch ${key}`} />
              <span><strong>{layerLabels[key]}</strong><small>{compactVintage(vintageFromLayer(layers[key]))} · {layers[key].feature_count.toLocaleString()} features</small></span>
              {layers[key].status !== "UNAVAILABLE" && <Check size={14} className="check-icon" />}
            </label>
          ))}
          <label className="layer-row">
            <input
              type="checkbox"
              checked={showSafemapFloodmarks}
              onChange={(event) => setShowSafemapFloodmarks(event.target.checked)}
              disabled={dataStatus?.safemap_floodmarks?.status !== "VERIFIED"}
            />
            <span className="layer-swatch safemap_floodmarks" />
            <span>
              <strong>Safemap Flood Marks</strong>
              <small>MOIS WMS Snapshot · {dataStatus?.safemap_floodmarks?.data_vintage ?? "NOT RECORDED"}</small>
              <small>visual verification only</small>
            </span>
            {dataStatus?.safemap_floodmarks?.status === "VERIFIED" && <Check size={14} className="check-icon" />}
          </label>
        </section>

        <section className="section-block">
          <div className="section-heading"><div><div className="eyebrow">DATA</div><h2>Map meaning</h2></div></div>
          <div className="reference-layer-list">
            <div><strong>Replay</strong><small>Timeline status plus HAND-based reconstruction envelope</small></div>
            <div><strong>Analysis layers</strong><small>2023 event data where recorded</small></div>
            <div><strong>Basemap</strong><small>Current online reference only</small></div>
            <div><strong>Flood extent</strong><small>HAND/approx envelopes are temporary, not official vector data</small></div>
          </div>
        </section>
      </div>
      <div className="sidebar-footer"><span>v0.1</span><span>External map tiles enabled</span></div>
    </aside>
  );
}

function Timeline({
  reconstruction,
  time,
  playing,
  setTime,
  setPlaying,
}: {
  reconstruction: ReconstructionResponse;
  time: number;
  playing: boolean;
  setTime: Dispatch<SetStateAction<number>>;
  setPlaying: Dispatch<SetStateAction<boolean>>;
}) {
  return (
    <div className="reconstruction-panel">
      <div className="reconstruction-head">
        <div>
          <div className="eyebrow">HISTORICAL REPLAY</div>
          <h2>{reconstruction.model_type}</h2>
          <p>Play through warning, river level, levee failure, underpass inflow, and response timing.</p>
        </div>
        <div className="window-badge">
          <span>Response window</span>
          <strong>{reconstruction.intervention.available_response_window_min} min</strong>
        </div>
      </div>
      <div className="replay-control">
        <button type="button" onClick={() => setPlaying((value) => !value)}>
          {playing ? <Pause size={14} /> : <Play size={14} />}
          {playing ? "Pause" : "Play"}
        </button>
        <input
          type="range"
          min={0}
          max={reconstruction.replay.length - 1}
          value={time}
          onChange={(event) => {
            setPlaying(false);
            setTime(Number(event.target.value));
          }}
        />
        <div>
          <span>{formatClock(reconstruction.replay[time]?.time)}</span>
          <strong>{reconstruction.replay[time]?.label}</strong>
        </div>
      </div>
      <div className="event-timeline">
        {reconstruction.replay.map((item, index) => (
          <div className={`timeline-event ${item.state} ${index === time ? "active" : ""}`} key={`${item.time}-${item.state}`}>
            <time>{formatClock(item.time)}</time>
            <div>
              <strong>{item.label}</strong>
              <span>{item.description}</span>
              <small>{item.role} · {item.confidence}</small>
            </div>
          </div>
        ))}
      </div>
      {reconstruction.envelope_comparison?.rows?.length ? (
        <div className="method-comparison">
          <div className="method-comparison-head">
            <div>
              <div className="eyebrow">METHOD COMPARISON</div>
              <h3>Approx envelope vs HAND reconstruction</h3>
            </div>
            <span>{reconstruction.envelope_comparison.area_crs ?? "EPSG:5179"} area check</span>
          </div>
          <div className="comparison-table">
            <div className="comparison-table-header">
              <span>Stage</span>
              <span>Approx</span>
              <span>HAND</span>
              <span>Delta</span>
            </div>
            {reconstruction.envelope_comparison.rows.map((row) => (
              <div className={`comparison-table-row ${row.stage === reconstruction.replay[time]?.state ? "active" : ""}`} key={row.stage}>
                <span><strong>{row.label || row.stage}</strong><small>{row.stage}</small></span>
                <span>{row.approx_area_km2.toFixed(2)} km2<small>{row.approx_features} cells</small></span>
                <span>{row.hand_area_km2.toFixed(2)} km2<small>{row.hand_features} cells</small></span>
                <span>+{row.hand_minus_approx_area_km2.toFixed(2)} km2<small>{row.hand_to_approx_area_ratio ? `${row.hand_to_approx_area_ratio}x` : "n/a"}</small></span>
              </div>
            ))}
          </div>
          <p className="data-note">Comparison areas are method diagnostics only. They are not official inundation area or exposure KPI evidence.</p>
        </div>
      ) : null}
    </div>
  );
}

function HydrometPanel({ summary }: { summary: ExposureMetrics | null }) {
  return (
    <div className="hydromet-panel">
      <div>
        <div className="eyebrow">OBSERVED HYDROMET</div>
        <h2>Observed rainfall and river level</h2>
      </div>
      <div className="hydromet-flow">
        <div>
          <span>KMA rainfall</span>
          <strong>{formatDecimal(summary?.rainfall_peak_mm_per_hour)} mm/hr</strong>
          <small>{summary?.rainfall_peak_station_name ?? "station not recorded"} · {summary?.rainfall_peak_timestamp ?? "time not recorded"}</small>
        </div>
        <div>
          <span>Miho River water level</span>
          <strong>{formatDecimal(summary?.primary_water_level_peak_m, 2)} m</strong>
          <small>청주시(미호강교) · {summary?.primary_water_level_peak_timestamp ?? "time not recorded"}</small>
        </div>
        <div>
          <span>Flood marks layer</span>
          <strong>{summary?.safemap_floodmarks_available ? "Visible" : "Pending"}</strong>
          <small>Safemap WMS raster · visual verification only</small>
        </div>
      </div>
      <p className="data-note">The map shows a HAND-like reconstruction envelope driven by observed water-level timing. It is not official Flood Extent, depth, or velocity.</p>
    </div>
  );
}

function ScenarioToggle({
  reconstruction,
  scenario,
  setScenario,
  summary,
}: {
  reconstruction: ReconstructionResponse | null;
  scenario: ScenarioMode;
  setScenario: Dispatch<SetStateAction<ScenarioMode>>;
  summary: ExposureMetrics | null;
}) {
  const active = scenario === "baseline" ? reconstruction?.baseline : reconstruction?.intervention;
  return (
    <div className="scenario-section">
      <div className="scenario-title">
        <div><div className="eyebrow">BASELINE / INTERVENTION</div><h2>{scenario === "baseline" ? "Observed baseline replay" : "Observed-inflow closure comparison"}</h2><p>No intervention effect KPI is calculated until source-backed model output exists.</p></div>
        <div className="scenario-toggle" role="group" aria-label="Scenario toggle">
          <button type="button" className={scenario === "baseline" ? "active" : ""} onClick={() => setScenario("baseline")}>Baseline</button>
          <button type="button" className={scenario === "intervention" ? "active" : ""} onClick={() => setScenario("intervention")}>Intervention</button>
        </div>
      </div>
      {reconstruction && (
        <div className="scenario-cards">
          <div className={scenario === "baseline" ? "selected" : ""}>
            <span>BASELINE</span>
            <strong>{reconstruction.baseline.name}</strong>
            <p>{reconstruction.baseline.description}</p>
            <small>Levee failure to inflow: {reconstruction.baseline.failure_to_inflow_min} min · inflow to full inundation: {reconstruction.baseline.inflow_to_full_inundation_min} min</small>
          </div>
          <div className={scenario === "intervention" ? "selected" : ""}>
            <span>INTERVENTION</span>
            <strong>{reconstruction.intervention.name}</strong>
            <p>{reconstruction.intervention.closure_action}</p>
            <small>{reconstruction.intervention.trigger} · {reconstruction.intervention.estimated_effect}</small>
          </div>
        </div>
      )}
      <div className="pending-grid">
        <div><span>Selected scenario</span><strong>{active?.name ?? "Not loaded"}</strong></div>
        <div><span>Gungpyeong 2 Underpass</span><strong>{summary?.underpass_available ? "Available" : "Unavailable"}</strong></div>
        <div><span>Exposed population</span><strong>{summary?.exposed_population}</strong></div>
        <div><span>Flooded buildings</span><strong>{summary?.exposed_buildings}</strong></div>
      </div>
      {reconstruction && (
        <div className="limitation-box">
          <strong>Limitations</strong>
          {reconstruction.limitations.map((item) => <span key={item}>{item}</span>)}
        </div>
      )}
    </div>
  );
}

const hhmm = (value: unknown) => (typeof value === "string" && value.length >= 16 ? value.slice(11, 16) : String(value ?? "-"));
const rows = (result: Record<string, unknown>, key: string) => (Array.isArray(result[key]) ? (result[key] as Array<Record<string, unknown>>) : []);

function AgentFindings({ workflow, result }: { workflow: AgentWorkflowName; result: Record<string, unknown> }) {
  if (workflow === "closure_timing") {
    const scenarios = rows(result, "scenarios");
    if (!scenarios.length) return null;
    return (
      <div className="agent-findings">
        <strong>분석 결과</strong>
        <table>
          <thead><tr><th>차단 시각</th><th>차단 시점 상태</th><th>유입까지</th><th>주행불능까지</th><th>완전침수까지</th><th>감지차단 대비</th></tr></thead>
          <tbody>
            {scenarios.map((row) => (
              <tr key={String(row.closure_time)}>
                <td>{hhmm(row.closure_time)}</td>
                <td className="agent-findings-label">{String(row.classification ?? "-")}</td>
                <td>{String(row.minutes_before_underpass_inflow ?? "-")}분</td>
                <td>{String(row.minutes_before_unsafe_driving ?? "-")}분</td>
                <td>{String(row.minutes_before_full_inundation ?? "-")}분</td>
                <td>{String(row.lead_time_vs_detection_trigger_min ?? "-")}분</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  if (workflow === "inflow_delay") {
    const scenarios = rows(result, "scenarios");
    if (!scenarios.length) return null;
    return (
      <div className="agent-findings">
        <strong>분석 결과</strong>
        {scenarios.map((scenario) => (
          <div key={String(scenario.delay_minutes)} className="agent-findings-block">
            <em>유입 {String(scenario.delay_minutes)}분 지연 가정</em>
            <table>
              <thead><tr><th>사건 상태</th><th>기준 시각</th><th>이동 후</th></tr></thead>
              <tbody>
                {(Array.isArray(scenario.milestones) ? (scenario.milestones as Array<Record<string, unknown>>) : []).map((milestone) => (
                  <tr key={String(milestone.state)}>
                    <td className="agent-findings-label">{String(milestone.label ?? milestone.state)}</td>
                    <td>{hhmm(milestone.baseline_time)}</td>
                    <td>{hhmm(milestone.shifted_time)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    );
  }

  if (workflow === "exposure_inventory") {
    const rings = rows(result, "rings");
    if (!rings.length) return null;
    return (
      <div className="agent-findings">
        <strong>분석 결과 · {String(result.focus_feature ?? "focus feature")} 기준</strong>
        <table>
          <thead><tr><th>반경</th><th>면적</th><th>건물</th><th>도로</th><th>시설</th></tr></thead>
          <tbody>
            {rings.map((ring) => (
              <tr key={String(ring.radius_m)}>
                <td>{String(ring.radius_m)} m</td>
                <td>{String(ring.area_km2)} km²</td>
                <td>{Number(ring.buildings).toLocaleString()}동</td>
                <td>{String(ring.roads_km)} km</td>
                <td>{String(ring.facilities)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  const replay = rows(result, "replay");
  if (!replay.length) return null;
  return (
    <div className="agent-findings">
      <strong>사건 재구성 타임라인</strong>
      <table>
        <thead><tr><th>시각</th><th>상태</th><th>근거 상태</th></tr></thead>
        <tbody>
          {replay.map((step) => (
            <tr key={String(step.time)}>
              <td>{hhmm(step.time)}</td>
              <td className="agent-findings-label">{String(step.label ?? step.state)}</td>
              <td>{String(step.confidence ?? "-")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AgentPanel({ eventId }: { eventId: string }) {
  const [message, setMessage] = useState("오송 지하차도 08:25와 08:35 차단 시각을 비교해줘");
  const [plan, setPlan] = useState<AgentIntentPlanResult | null>(null);
  const [workflowResult, setWorkflowResult] = useState<AgentWorkflowResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [examples, setExamples] = useState<AgentExampleQuestion[]>([]);

  useEffect(() => {
    let live = true;
    api.getAgentExamples()
      .then((items) => { if (live) setExamples(items); })
      .catch(() => { /* chips are optional; the free-text box still works */ });
    return () => { live = false; };
  }, []);

  const ask = (question: string) => {
    setMessage(question);
    setPlan(null);
    setWorkflowResult(null);
    setError(null);
  };

  const planIntent = async () => {
    if (!message.trim()) return;
    setBusy(true);
    setError(null);
    setWorkflowResult(null);
    try {
      setPlan(await api.planAgentIntent(eventId, message.trim()));
    } catch {
      setError("Agent planner API를 호출하지 못했습니다.");
    } finally {
      setBusy(false);
    }
  };

  const runWorkflow = async () => {
    if (!plan?.workflow || plan.status !== "READY") return;
    setBusy(true);
    setError(null);
    try {
      setWorkflowResult(await api.runAgentWorkflow(eventId, plan.workflow, plan.parameters));
    } catch {
      setError("계획된 Agent workflow를 실행하지 못했습니다.");
    } finally {
      setBusy(false);
    }
  };

  const resultAssumptions = workflowResult?.result.assumptions;
  const resultLimitations = workflowResult?.result.limitations;

  return (
    <section className="agent-panel">
      <div className="agent-head">
        <div>
          <div className="eyebrow">AI-ASSISTED RESEARCH WORKFLOW</div>
          <h2><Bot size={18} /> Agent workflow</h2>
          <p>등록된 분석 도구를 계획하고 실행합니다. 자연어 요청 자체로 수치를 계산하지 않습니다.</p>
        </div>
        <span className="agent-status" title={plan?.planner_note ?? ""}>
          {plan ? (plan.planner_used === "llm" ? "LLM PLAN" : "DETERMINISTIC PLAN") : "PLANNER READY"}
        </span>
      </div>
      {examples.length > 0 && (
        <div className="agent-chips" aria-label="답할 수 있는 예시 질문">
          {examples.map((item) => (
            <button key={item.workflow} type="button" title={item.question} onClick={() => ask(item.question)}>{item.label}</button>
          ))}
        </div>
      )}
      <form className="agent-form" onSubmit={(event) => { event.preventDefault(); void planIntent(); }}>
        <input
          aria-label="Agent request"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="예: 오송 침수 상황을 보여줘"
        />
        <button className="primary-button" type="submit" disabled={busy || !message.trim()}>
          <Send size={13} /> 계획 생성
        </button>
      </form>

      {plan && (
        <div className={`agent-plan ${plan.status.toLowerCase()}`}>
          <div className="agent-plan-title">
            <div><span>PLAN STATUS</span><strong>{plan.status}</strong></div>
            <div><span>WORKFLOW</span><strong>{plan.workflow ?? "선택되지 않음"}</strong></div>
          </div>
          <p className="agent-reason">{plan.reason}</p>
          {plan.planner_note && <small className="agent-assumption">{plan.planner_note}</small>}
          {plan.tool_names.length > 0 && <div className="agent-tools">{plan.tool_names.map((tool, index) => <span key={tool}>{index + 1}. {tool}</span>)}</div>}
          {Object.keys(plan.parameters).length > 1 && <pre className="agent-parameters">{JSON.stringify(plan.parameters, null, 2)}</pre>}
          {plan.assumptions.map((item) => <small className="agent-assumption" key={item}>{item}</small>)}
          {plan.suggestions.length > 0 && (
            <div className="agent-suggestions">
              <span>이렇게는 답할 수 있어요</span>
              <div className="agent-chips">
                {plan.suggestions.map((item) => <button key={item} type="button" onClick={() => ask(item)}>{item}</button>)}
              </div>
            </div>
          )}
          {plan.status === "READY" && plan.workflow && (
            <button className="primary-button agent-run" type="button" onClick={() => void runWorkflow()} disabled={busy}>
              <Play size={13} /> {busy ? "실행 중..." : "계획 실행"}
            </button>
          )}
        </div>
      )}

      {workflowResult && (
        <div className="agent-result">
          <div className="agent-result-head"><strong>Workflow completed</strong><span>{workflowResult.workflow}</span></div>
          <div className="agent-tools">{workflowResult.tool_calls.map((call) => <span key={call.order}>{call.order}. {call.tool_name}</span>)}</div>
          {workflowResult.provenance.length > 0 && (
            <div className="agent-provenance">
              <strong>Provenance</strong>
              {workflowResult.provenance.map((item, index) => <small key={`${String(item.key ?? item.source ?? "source")}-${index}`}>{String(item.label ?? item.key ?? "source")} · {String(item.source ?? "source not recorded")} · {String(item.snapshot ?? item.data_vintage ?? item.status ?? "status not recorded")}</small>)}
            </div>
          )}
          <AgentFindings workflow={workflowResult.workflow} result={workflowResult.result} />
          {workflowResult.coverage_note && <small className="agent-coverage">Coverage · {workflowResult.coverage_status ?? "not recorded"} · {workflowResult.coverage_note}</small>}
          <div className="agent-result-boundary">
            <strong>근거와 한계</strong>
            {Array.isArray(resultAssumptions) && resultAssumptions.map((item) => <small key={String(item)}>가정 · {String(item)}</small>)}
            {Array.isArray(resultLimitations) && resultLimitations.map((item) => <small key={String(item)}>한계 · {String(item)}</small>)}
          </div>
        </div>
      )}
      {error && <p className="agent-error">{error}</p>}
    </section>
  );
}

export default function App() {
  const [events, setEvents] = useState<FloodEvent[]>([]);
  const [eventData, setEventData] = useState<FloodEvent | null>(null);
  const [layers, setLayers] = useState<LayersResponse>(emptyLayers);
  const [summary, setSummary] = useState<ExposureMetrics | null>(null);
  const [dataStatus, setDataStatus] = useState<DataStatusResponse | null>(null);
  const [reconstruction, setReconstruction] = useState<ReconstructionResponse | null>(null);
  const [time, setTime] = useState(0);
  const [scenario, setScenario] = useState<ScenarioMode>("baseline");
  const [replayPlaying, setReplayPlaying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showLayers, setShowLayers] = useState<Record<keyof LayersResponse, boolean>>({
    aoi: true,
    roads: true,
    buildings: true,
    waterways: true,
    terrain: false,
    approx_flood_envelope: false,
    hand_reconstruction: true,
    facilities: false,
    underpass: true,
    flood_extent: false,
  });
  const [showSafemapFloodmarks, setShowSafemapFloodmarks] = useState(true);
  // 어두운 관제 화면 미리보기. 브라우저에 기억해 새로고침해도 유지된다.
  const [uiMode, setUiMode] = useState<"light" | "dark">(() => {
    try { return localStorage.getItem("floodops-ui") === "dark" ? "dark" : "light"; } catch { return "light"; }
  });
  const switchUi = (mode: "light" | "dark") => {
    try { localStorage.setItem("floodops-ui", mode); } catch { /* 저장 못 해도 전환은 된다 */ }
    setUiMode(mode);
  };

  useEffect(() => {
    async function load() {
      try {
        const nextEvents = await api.getEvents();
        const selected = nextEvents.find((item) => item.id === "osong-2023") ?? nextEvents[0];
        const [nextEvent, nextLayers, nextSummary, nextStatus, nextReconstruction] = await Promise.all([
          api.getEvent(selected.id),
          api.getLayers(selected.id, 2023),
          api.getSummary(selected.id),
          api.getStatus(selected.id),
          api.getReconstruction(selected.id),
        ]);
        setEvents(nextEvents);
        setEventData(nextEvent);
        setLayers(nextLayers);
        setSummary(nextSummary);
        setDataStatus(nextStatus);
        setReconstruction(nextReconstruction);
      } catch {
        setError("Backend API connection failed. Start the FastAPI server and reload.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  useEffect(() => {
    if (!reconstruction || !replayPlaying) return undefined;
    const timer = window.setInterval(() => {
      setTime((index) => {
        const nextIndex = index + 1;
        if (nextIndex >= reconstruction.replay.length) {
          setReplayPlaying(false);
          return index;
        }
        return nextIndex;
      });
    }, 1100);
    return () => window.clearInterval(timer);
  }, [reconstruction, replayPlaying]);

  const layerRows = useMemo<Array<keyof LayersResponse>>(() => ["aoi", "hand_reconstruction", "approx_flood_envelope", "waterways", "roads", "buildings", "underpass"], []);

  if (loading) return <div className="app-state"><Activity className="spin" /><strong>Loading FloodOps offline MVP</strong><span>Reading local processed Osong data.</span></div>;
  if (error || !eventData) return <div className="app-state error-state"><AlertTriangle /><strong>Unable to load MVP</strong><span>{error}</span></div>;

  if (uiMode === "dark") {
    return (
      <DarkConsole
        eventData={eventData}
        layers={layers}
        summary={summary}
        dataStatus={dataStatus}
        reconstruction={reconstruction}
        time={time}
        setTime={setTime}
        playing={replayPlaying}
        setPlaying={setReplayPlaying}
        scenario={scenario}
        setScenario={setScenario}
        onSwitchBack={() => switchUi("light")}
      />
    );
  }

  return (
    <div className="app-shell">
      <EventHeader eventData={eventData} />
      <main className="workspace">
        <ProvenancePanel
          events={events}
          eventData={eventData}
          layers={layers}
          dataStatus={dataStatus}
          layerRows={layerRows}
          showLayers={showLayers}
          showSafemapFloodmarks={showSafemapFloodmarks}
          setShowLayers={setShowLayers}
          setShowSafemapFloodmarks={setShowSafemapFloodmarks}
        />

        <section className="main-canvas">
          <div className="map-wrap">
            <MapPanel
              layers={layers}
              visible={showLayers}
              safemapVisible={showSafemapFloodmarks}
              safemapOverlay={dataStatus?.safemap_floodmarks}
              reconstruction={reconstruction}
              time={time}
              scenario={scenario}
            />
          </div>
          <div className="analysis-panel">
            <div className="analysis-head">
              <div><div className="eyebrow">BASELINE DATA</div><h1>Osong 2023 processed data connection</h1><p>{"Repository -> API -> React/Vite -> MapLibre using local files only."}</p></div>
              <button type="button" className="primary-button" onClick={() => switchUi("dark")}>다크 관제 UI 미리보기</button>
            </div>
            <div className="metrics-grid assignment-metrics">
              <Metric icon={Building2} label="Buildings in AOI" value={formatNumber(summary?.building_count)} note="Official GIS Building Integrated Information" />
              <Metric icon={Route} label="Road objects" value={formatNumber(summary?.road_count)} note="OSM historical snapshot" />
              <Metric icon={CloudRain} label="Peak hourly rainfall" value={`${formatDecimal(summary?.rainfall_peak_mm_per_hour)} mm`} note={`${formatNumber(summary?.rainfall_records)} KMA AWS records`} />
              <Metric icon={Waves} label="Peak water level" value={`${formatDecimal(summary?.water_level_peak_m, 2)} m`} note={summary?.water_level_peak_station_name ?? "Flood Control Office"} />
            </div>
            {reconstruction && <Timeline reconstruction={reconstruction} time={time} playing={replayPlaying} setTime={setTime} setPlaying={setReplayPlaying} />}
            <HydrometPanel summary={summary} />
            <ScenarioToggle reconstruction={reconstruction} scenario={scenario} setScenario={setScenario} summary={summary} />
            <AgentPanel eventId={eventData.id} />
          </div>
        </section>
      </main>
    </div>
  );
}


