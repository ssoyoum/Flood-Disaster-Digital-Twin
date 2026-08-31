import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl, { type GeoJSONSource, type MapLayerMouseEvent, type Map as MapLibreMap, type Popup } from "maplibre-gl";
import { Activity, AlertTriangle, Building2, Check, CloudRain, Factory, Layers3, MapPin, Mountain, Route, Waves } from "lucide-react";
import * as api from "./api";
import type { DataStatusItem, DataStatusResponse, ExposureMetrics, FloodEvent, GeoJson, LayerPayload, LayersResponse } from "./types";

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
  facilities: "Facilities",
  underpass: "Gungpyeong 2 Underpass",
  flood_extent: "Flood Extent",
};

type ProvenanceItem = {
  source: string;
  vintage: string;
  role: string;
};

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return "--";
  return new Intl.NumberFormat("ko-KR").format(value);
}

function formatDecimal(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined) return "--";
  return new Intl.NumberFormat("ko-KR", { maximumFractionDigits: digits }).format(value);
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

function ProvenanceCard({ item }: { item: ProvenanceItem }) {
  return (
    <div className="provenance-card">
      <div><span>SOURCE</span><strong>{item.source}</strong></div>
      <div><span>VINTAGE</span><strong>{item.vintage}</strong></div>
      <div><span>ROLE</span><strong>{item.role}</strong></div>
    </div>
  );
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
}: {
  layers: LayersResponse;
  visible: Record<keyof LayersResponse, boolean>;
  safemapVisible: boolean;
  safemapOverlay?: DataStatusItem;
}) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const hoverPopupRef = useRef<Popup | null>(null);

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
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
    const visibility = (key: keyof LayersResponse) => visible[key] ? "visible" : "none";
    [["aoi-fill", "aoi"], ["aoi-line", "aoi"], ["terrain-fill", "terrain"], ["terrain-line", "terrain"], ["waterways-fill", "waterways"], ["waterways-line", "waterways"], ["roads-line", "roads"], ["buildings-fill", "buildings"], ["buildings-line", "buildings"], ["facilities-point", "facilities"], ["underpass-line", "underpass"]].forEach(([layerId, key]) => {
      if (map.getLayer(layerId)) map.setLayoutProperty(layerId, "visibility", visibility(key as keyof LayersResponse));
    });
    if (map.getLayer("safemap-floodmarks-raster")) {
      map.setLayoutProperty("safemap-floodmarks-raster", "visibility", safemapVisible ? "visible" : "none");
    }
  }, [visible, safemapVisible]);

  return (
    <div className="map-panel">
      <div ref={mapContainer} className="map-canvas" />
      <div className="map-label"><span className="pulse-dot" /> Osong 2023 MVP | Online OSM basemap</div>
      <div className="map-attribution">Basemap © OpenStreetMap contributors | Flood marks © MOIS Safemap WMS | Current basemap is context only</div>
      <div className="map-legend">
        <div><i className="legend-aoi" />AOI</div>
        <div><i className="legend-floodmarks" />Safemap flood marks</div>
        <div><i className="legend-terrain" />Low elevation context</div>
        <div><i className="legend-water" />Official river area</div>
        <div><i className="legend-road" />Road</div>
        <div><i className="legend-building" />Residential/other</div>
        <div><i className="legend-building-commercial" />Commercial</div>
        <div><i className="legend-building-public" />School/public</div>
        <div><i className="legend-underpass" />Underpass</div>
      </div>
    </div>
  );
}

export default function App() {
  const [events, setEvents] = useState<FloodEvent[]>([]);
  const [event, setEvent] = useState<FloodEvent | null>(null);
  const [layers, setLayers] = useState<LayersResponse>(emptyLayers);
  const [summary, setSummary] = useState<ExposureMetrics | null>(null);
  const [dataStatus, setDataStatus] = useState<DataStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showLayers, setShowLayers] = useState<Record<keyof LayersResponse, boolean>>({
    aoi: true,
    roads: true,
    buildings: true,
    waterways: true,
    terrain: true,
    facilities: true,
    underpass: true,
    flood_extent: false,
  });
  const [showSafemapFloodmarks, setShowSafemapFloodmarks] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const nextEvents = await api.getEvents();
        const selected = nextEvents.find((item) => item.id === "osong-2023") ?? nextEvents[0];
        const [nextEvent, nextLayers, nextSummary, nextStatus] = await Promise.all([
          api.getEvent(selected.id),
          api.getLayers(selected.id, 2023),
          api.getSummary(selected.id),
          api.getStatus(selected.id),
        ]);
        setEvents(nextEvents);
        setEvent(nextEvent);
        setLayers(nextLayers);
        setSummary(nextSummary);
        setDataStatus(nextStatus);
      } catch {
        setError("Backend API connection failed. Start the FastAPI server and reload.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  const layerRows = useMemo(() => (Object.keys(layerLabels) as Array<keyof LayersResponse>).filter((key) => key !== "flood_extent"), []);
  const provenanceItems = useMemo<ProvenanceItem[]>(() => [
    {
      source: layers.buildings.source ?? "Official building layer",
      vintage: vintageFromLayer(layers.buildings),
      role: "Analysis Layer",
    },
    {
      source: layers.waterways.source ?? "Official river layer",
      vintage: vintageFromLayer(layers.waterways),
      role: "Analysis Layer",
    },
    {
      source: layers.terrain.source ?? "DEM terrain context",
      vintage: vintageFromLayer(layers.terrain),
      role: "Terrain Context",
    },
    {
      source: "Official KOSIS Population",
      vintage: vintageFromStatus(dataStatus?.population),
      role: "Reference / Exposure Input",
    },
    {
      source: dataStatus?.rainfall?.source ?? "Rainfall",
      vintage: vintageFromStatus(dataStatus?.rainfall),
      role: "Environmental Input",
    },
    {
      source: dataStatus?.safemap_floodmarks?.source ?? "Safemap Flood Marks WMS",
      vintage: dataStatus?.safemap_floodmarks?.data_vintage ?? "NOT RECORDED",
      role: "Hazard Layer / Visual Verification",
    },
    {
      source: "Vector Flood Extent",
      vintage: vintageFromLayer(layers.flood_extent),
      role: "Hazard Layer / Pending Vector Data",
    },
    {
      source: "Online Basemap",
      vintage: "CURRENT / LIVE REFERENCE",
      role: "Geographic Context Only",
    },
  ], [dataStatus, layers]);

  if (loading) return <div className="app-state"><Activity className="spin" /><strong>Loading FloodOps offline MVP</strong><span>Reading local processed Osong data.</span></div>;
  if (error || !event) return <div className="app-state error-state"><AlertTriangle /><strong>Unable to load MVP</strong><span>{error}</span></div>;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><div className="brand-mark"><Waves size={19} /></div><div><strong>FloodOps</strong><span>OFFLINE MVP</span></div></div>
        <div className="topbar-context"><span className="status-dot" /> Local processed data + online basemap <span className="divider" /> representative event: osong-2023</div>
      </header>
      <main className="workspace">
        <aside className="sidebar">
          <div className="sidebar-scroll">
            <section className="section-block event-block">
              <div className="eyebrow">EVENT</div>
              <div className="event-picker"><span className="event-pin"><MapPin size={15} /></span><select value={event.id} disabled aria-label="Event selector">{events.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div>
              <div className="event-meta"><span>{event.started_at.slice(0, 10)}</span><span>Event metadata</span></div>
              <div className="incident-vintage"><span>Incident: Osong Flood</span><strong>Event Year: {event.data_year}</strong></div>
              <p className="data-note">Event year describes the incident, not the vintage of every analysis layer.</p>
              <p className="event-analysis"><strong>{event.theme}</strong><span>{event.analysis_flow}</span><small>{event.focus_feature}</small><small>{event.source}</small></p>
            </section>

            <section className="section-block layers-block">
              <div className="section-heading"><div><div className="eyebrow">MAP LAYERS</div><h2>Processed Layers</h2></div><Layers3 size={16} className="muted-icon" /></div>
              <div className="vintage-controls">
                <div>
                  <span>Analysis Layer Vintage</span>
                  <strong>2023 event snapshot</strong>
                  <small>OSM 2026 is excluded from incident analysis.</small>
                </div>
                <div>
                  <span>Basemap Vintage</span>
                  <strong>CURRENT / LIVE REFERENCE</strong>
                </div>
              </div>
              {layerRows.map((key) => (
                <label className="layer-row" key={key}>
                  <input type="checkbox" checked={showLayers[key]} onChange={(e) => setShowLayers((state) => ({ ...state, [key]: e.target.checked }))} />
                  <span className={`layer-swatch ${key}`} />
                  <span><strong>{layerLabels[key]}</strong><small>{layerSubLabel(layers[key])}</small><small>{layers[key].feature_count.toLocaleString()} features</small></span>
                  {layers[key].status !== "UNAVAILABLE" && <Check size={14} className="check-icon" />}
                </label>
              ))}
              <label className="layer-row">
                <input
                  type="checkbox"
                  checked={showSafemapFloodmarks}
                  onChange={(e) => setShowSafemapFloodmarks(e.target.checked)}
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
              <div className="reference-layer-list">
                <div><strong>Vector Flood Extent</strong><small>{vintageFromLayer(layers.flood_extent)} · awaiting official vector dataset</small></div>
                <div><strong>Safemap WMS Snapshot</strong><small>{dataStatus?.safemap_floodmarks?.data_vintage ?? "NOT RECORDED"} · not used for exposure counts</small></div>
                <div><strong>Population</strong><small>KOSIS · {vintageFromStatus(dataStatus?.population)}</small></div>
                <div><strong>DEM</strong><small>Copernicus · {vintageFromStatus(dataStatus?.dem)}</small></div>
              </div>
            </section>

            <section className="section-block">
              <div className="section-heading"><div><div className="eyebrow">DATA VINTAGE</div><h2>Provenance</h2></div></div>
              <div className="provenance-list">{provenanceItems.map((item) => <ProvenanceCard key={`${item.source}-${item.role}`} item={item} />)}</div>
              <p className="data-note">Basemap is geographic context only and may differ from the selected analysis layer vintage. Safemap WMS is a raster snapshot for visual verification; exposure counts remain locked until vector Flood Extent is available.</p>
            </section>
          </div>
          <div className="sidebar-footer"><span>v0.1</span><span>External map tiles enabled</span></div>
        </aside>

        <section className="main-canvas">
          <div className="map-wrap"><MapPanel layers={layers} visible={showLayers} safemapVisible={showSafemapFloodmarks} safemapOverlay={dataStatus?.safemap_floodmarks} /></div>
          <div className="analysis-panel">
            <div className="analysis-head">
              <div><div className="eyebrow">BASELINE DATA</div><h1>Osong 2023 processed data connection</h1><p>{"Repository -> API -> React/Vite -> MapLibre using local files only."}</p></div>
            </div>
            <div className="metrics-grid">
              <Metric icon={Building2} label="Buildings in AOI" value={formatNumber(summary?.building_count)} note="Official GIS Building Integrated Information" />
              <Metric icon={Route} label="Road objects" value={formatNumber(summary?.road_count)} note="OSM historical snapshot" />
              <Metric icon={Waves} label="River polygons" value={formatNumber(summary?.waterway_count)} note="WAMIS official river network" />
              <Metric icon={Mountain} label="Low elevation cells" value={formatNumber(summary?.terrain_low_elevation_cells)} note={`DEM p25 <= ${formatDecimal(summary?.terrain_low_elevation_threshold_m)} m`} />
              <Metric icon={CloudRain} label="Peak hourly rainfall" value={`${formatDecimal(summary?.rainfall_peak_mm_per_hour)} mm`} note={`${formatNumber(summary?.rainfall_records)} KMA AWS records`} />
              <Metric icon={Waves} label="Peak water level" value={`${formatDecimal(summary?.water_level_peak_m, 2)} m`} note={summary?.water_level_peak_station_name ?? "Flood Control Office"} />
              <Metric icon={Factory} label="Facilities" value={formatNumber(summary?.facility_count)} note="OSM historical POI" />
              <Metric icon={Waves} label="Safemap flood marks" value={summary?.safemap_floodmarks_available ? "Available" : "Unavailable"} note="WMS raster overlay, not vector analysis" />
            </div>
            <div className="hydromet-panel">
              <div>
                <div className="eyebrow">OBSERVED HYDROMET</div>
                <h2>Rainfall → river level → mapped flood marks</h2>
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
              <p className="data-note">This panel explains the observed event context. It does not calculate exposure until vector Flood Extent is available.</p>
            </div>
            <div className="scenario-section">
              <div className="scenario-title">
                <div><div className="eyebrow">PENDING FLOOD EXTENT</div><h2>Exposure KPIs are intentionally locked</h2><p>{summary?.data_status}</p></div>
              </div>
              <div className="pending-grid">
                <div><span>Official Osong-eup population</span><strong>{formatNumber(summary?.official_population)} people</strong></div>
                <div><span>Gungpyeong 2 Underpass</span><strong>{summary?.underpass_available ? "Available" : "Unavailable"}</strong></div>
                <div><span>Exposed population</span><strong>{summary?.exposed_population}</strong></div>
                <div><span>Flooded buildings</span><strong>{summary?.exposed_buildings}</strong></div>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
