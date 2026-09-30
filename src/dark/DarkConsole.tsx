import { useEffect, useMemo, useRef, useState, type Dispatch, type PointerEvent as ReactPointerEvent, type SetStateAction } from "react";
import maplibregl, { type GeoJSONSource, type MapLayerMouseEvent } from "maplibre-gl";
import * as api from "../api";
import CrossSection from "./CrossSection";
import type {
  AgentExampleQuestion,
  AgentAskResult,
  AgentWorkflowName,
  DataStatusResponse,
  ExposureMetrics,
  FloodEvent,
  GeoJson,
  LayersResponse,
  ReconstructionResponse,
  HandThresholdResult,
  HandThresholdStage,
  ClosureTimingScenario,
} from "../types";
import "./dark.css";

import { stageKo, statusKo, textKo } from "./ko";
import { FloodOpsLogo } from "./Landing";

/*
 * 어두운 관제 화면.
 *
 * 기존 화면(App.tsx)과 같은 데이터·API 를 그대로 받아서 배치와 상호작용만 바꾼다.
 *   [상단바: 현재 사건 단계 · 대응 여유 · 건물/도로/시설 수 · 시각]
 *   [왼쪽: 판단 우선순위 · 사건 단계 · 시나리오 · 재고 · Agent] [중앙: 깨끗한 지도] [오른쪽: HAND 단면 · 관측 근거]
 * 화면에 나오는 모든 수치는 API 가 준 값이다. 강수 시뮬레이션·침수 속도처럼 이 모델에 없는 값은
 * 만들어 넣지 않았고, 그 자리에는 관측값(KMA 강우 피크, 홍수통제소 수위 피크)을 둔다.
 */

type ScenarioMode = "baseline" | "intervention";
type LayerKey = keyof LayersResponse;
type ConsoleView = "console" | "compare" | "insights";

// Count envelope cells at the current stage and how close they reach the underpass.
function spatialStatus(layers: LayersResponse, stage: number) {
  const cells = (layers.hand_reconstruction.data?.features ?? []).filter(
    (feature) => feature.geometry?.type === "Polygon" && feature.properties?.stage_index === stage,
  );
  if (!cells.length) return "침수 추정 셀 없음 · 하천 수위 관측 단계";
  const nearest = Math.min(...cells.map((feature) => Number(feature.properties?.distance_to_underpass_m ?? Infinity)));
  return `침수 추정 ${cells.length}셀 · 지하차도까지 ${Number.isFinite(nearest) ? `${Math.round(nearest)}m` : "—"} (HAND 근사)`;
}

const STAGE_TONE: Record<string, string> = {
  warning: "#60a5fa",
  hydraulic_warning: "#38bdf8",
  overtopping: "#fbbf24",
  levee_failure: "#fb923c",
  underpass_inflow: "#f87171",
  unsafe_driving: "#ef4444",
  full_inundation: "#b91c1c",
};

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

const ESRI = "https://services.arcgisonline.com/ArcGIS/rest/services/Canvas";
// Offline fallback only. The live chips come from GET /api/agent/examples so the
// starter questions and the suggestions attached to a refusal share one source.
const FALLBACK_EXAMPLES: AgentExampleQuestion[] = [
  { workflow: "closure_timing", label: "08:25 통제", question: "08:25에 지하차도를 통제했다면 유입까지 몇 분 남나요?" },
  { workflow: "inflow_delay", label: "유입 30분 지연", question: "차수벽으로 유입이 30분 늦어졌다면 어떻게 되나요?" },
  { workflow: "exposure_inventory", label: "반경 500m 재고", question: "지하차도 반경 500m 안에 건물이 몇 개인가요?" },
];

const clock = (value?: string | null) => (value && value.length >= 16 ? value.slice(11, 16) : "--:--");
const num = (value: number | null | undefined) => (typeof value === "number" ? value.toLocaleString() : "—");
const dec = (value: number | null | undefined, digits = 1) => (typeof value === "number" ? value.toFixed(digits) : "—");
const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
const toMinutes = (hhmm: string) => {
  const [h, m] = hhmm.split(":").map(Number);
  return Number.isFinite(h) && Number.isFinite(m) ? h * 60 + m : 0;
};
const fromMinutes = (value: number) => `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`;
const leadText = (minutes: number) => (minutes === 0 ? "같은 시각 통제" : minutes > 0 ? `${minutes}분 전 통제` : `${-minutes}분 늦게 통제`);
const CLOSURE_CLASS: Record<string, string> = {
  PREEMPTIVE_BEFORE_LEVEE_FAILURE: "제방 붕괴 전 선제 통제",
  BEFORE_UNDERPASS_INFLOW: "유입 전 통제",
  AFTER_INFLOW_BEFORE_UNSAFE_DRIVING: "유입 후 · 주행불능 전 통제",
  AFTER_UNSAFE_DRIVING: "주행불능 후 통제",
  AFTER_FULL_INUNDATION: "완전침수 후 통제",
};
const escapeHtml = (value: unknown) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c] as string));

/** GeoJSON 안의 모든 좌표를 훑어 bbox 중심을 돌려준다. 형상 종류에 의존하지 않는다. */
function centerOf(geojson: GeoJson): [number, number] | null {
  let minX = Infinity; let minY = Infinity; let maxX = -Infinity; let maxY = -Infinity;
  const walk = (coords: unknown) => {
    if (!Array.isArray(coords)) return;
    if (typeof coords[0] === "number" && typeof coords[1] === "number") {
      const [x, y] = coords as [number, number];
      minX = Math.min(minX, x); minY = Math.min(minY, y); maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
      return;
    }
    coords.forEach(walk);
  };
  geojson.features.forEach((feature) => walk(feature.geometry.coordinates));
  return Number.isFinite(minX) ? [(minX + maxX) / 2, (minY + maxY) / 2] : null;
}

const cardHtml = (title: string, rows: Array<[string, unknown]>, tone?: string) => `
  <div class="dk-card">
    <b style="${tone ? `color:${tone}` : ""}">${escapeHtml(title)}</b>
    <dl>${rows
      .filter(([, value]) => value !== undefined && value !== null && value !== "")
      .map(([key, value]) => `<div><dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd></div>`)
      .join("")}</dl>
  </div>`;

export default function DarkConsole({
  eventData,
  layers,
  summary,
  dataStatus,
  reconstruction,
  time,
  setTime,
  playing,
  setPlaying,
  scenario,
  setScenario,
}: {
  eventData: FloodEvent;
  layers: LayersResponse;
  summary: ExposureMetrics | null;
  dataStatus: DataStatusResponse | null;
  reconstruction: ReconstructionResponse | null;
  time: number;
  setTime: Dispatch<SetStateAction<number>>;
  playing: boolean;
  setPlaying: Dispatch<SetStateAction<boolean>>;
  scenario: ScenarioMode;
  setScenario: Dispatch<SetStateAction<ScenarioMode>>;
}) {
  const mapElementRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const hoverRef = useRef<maplibregl.Popup | null>(null);
  const [ready, setReady] = useState(false);
  const [now, setNow] = useState(() => new Date());
  const [view, setView] = useState<ConsoleView>("console");
  const [visible, setVisible] = useState<Record<LayerKey, boolean>>({
    aoi: true, roads: true, buildings: true, waterways: true, terrain: false,
    approx_flood_envelope: false, hand_reconstruction: true, facilities: false, underpass: true, flood_extent: false,
  });
  const [layersOpen, setLayersOpen] = useState(false);
  const [panelWidths, setPanelWidths] = useState({ left: 290, right: 360 });
  const resizeRef = useRef<{ side: "left" | "right"; startX: number; startWidth: number } | null>(null);

  const stages = reconstruction?.replay ?? [];
  const current = stages[time];
  const tone = STAGE_TONE[current?.state ?? ""] ?? "#38bdf8";
  const underpassCenter = useMemo(() => centerOf(layers.underpass.data), [layers.underpass.data]);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30_000);
    return () => window.clearInterval(timer);
  }, []);

  const beginResize = (side: "left" | "right", event: ReactPointerEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    resizeRef.current = { side, startX: event.clientX, startWidth: panelWidths[side] };
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  };

  const nudgeResize = (side: "left" | "right", key: string) => {
    if (key !== "ArrowLeft" && key !== "ArrowRight") return;
    const delta = side === "left" ? (key === "ArrowRight" ? 16 : -16) : (key === "ArrowLeft" ? 16 : -16);
    setPanelWidths((currentWidths) => ({
      ...currentWidths,
      [side]: clamp(currentWidths[side] + delta, side === "left" ? 220 : 260, side === "left" ? 460 : 520),
    }));
  };

  useEffect(() => {
    const onMove = (event: PointerEvent) => {
      const resize = resizeRef.current;
      if (!resize) return;
      const delta = event.clientX - resize.startX;
      const width = resize.side === "right" ? resize.startWidth - delta : resize.startWidth + delta;
      setPanelWidths((currentWidths) => ({
        ...currentWidths,
        [resize.side]: clamp(width, resize.side === "left" ? 220 : 260, resize.side === "left" ? 460 : 520),
      }));
    };
    const onEnd = () => {
      resizeRef.current = null;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onEnd);
    return () => { window.removeEventListener("pointermove", onMove); window.removeEventListener("pointerup", onEnd); onEnd(); };
  }, []);

  useEffect(() => {
    if (!mapRef.current) return;
    window.requestAnimationFrame(() => mapRef.current?.resize());
  }, [panelWidths]);

  // 지도 1회 초기화. 글리프가 필요한 symbol 레이어는 쓰지 않고 글자는 HTML 마커·팝업으로 올린다.
  useEffect(() => {
    if (!mapElementRef.current || mapRef.current) return undefined;
    const map = new maplibregl.Map({
      container: mapElementRef.current,
      attributionControl: false,
      style: {
        version: 8,
        sources: {
          "esri-dark": {
            type: "raster",
            tiles: [`${ESRI}/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}`],
            tileSize: 256,
            maxzoom: 16,
            attribution: "Tiles © Esri",
          },
          "esri-dark-ref": { type: "raster", tiles: [`${ESRI}/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}`], tileSize: 256, maxzoom: 16 },
        },
        layers: [
          { id: "background", type: "background", paint: { "background-color": "#0b1220" } },
          { id: "esri-dark", type: "raster", source: "esri-dark", paint: { "raster-opacity": 0.92 } },
          { id: "esri-dark-ref", type: "raster", source: "esri-dark-ref", paint: { "raster-opacity": 0.75 } },
        ],
      },
      center: underpassCenter ?? [127.31, 36.63],
      zoom: 13.6,
      maxZoom: 16,
    });
    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-left");

    map.on("load", () => {
      const add = (key: LayerKey) => map.addSource(key, { type: "geojson", data: layers[key].data as never });
      add("aoi"); add("waterways"); add("roads"); add("buildings"); add("hand_reconstruction"); add("underpass");

      map.addLayer({ id: "aoi-line", type: "line", source: "aoi", paint: { "line-color": "#22d3ee", "line-width": 1.2, "line-dasharray": [3, 3], "line-opacity": 0.55 } });
      map.addLayer({ id: "buildings-fill", type: "fill", source: "buildings", paint: { "fill-color": "#3b4a63", "fill-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 0.95, 0.55] } });
      map.addLayer({ id: "roads-line", type: "line", source: "roads", paint: { "line-color": "#64748b", "line-width": 0.9, "line-opacity": 0.45 } });
      map.addLayer({ id: "waterways-fill", type: "fill", source: "waterways", paint: { "fill-color": "#1d6fa5", "fill-opacity": 0.45 } });
      map.addLayer({ id: "waterways-line", type: "line", source: "waterways", paint: { "line-color": "#7dd3fc", "line-width": 1.2, "line-opacity": 0.9 } });
      // HAND 재구성 envelope: 현재 단계 셀만. 기준 시나리오는 붉게, 개입 시나리오는 청록으로.
      map.addLayer({
        id: "hand-outline", type: "line", source: "hand_reconstruction",
        filter: ["all", ["==", ["geometry-type"], "Polygon"], ["==", ["get", "stage_index"], time]],
        paint: { "line-color": "#f87171", "line-width": 1, "line-opacity": 0.9 },
      });
      map.addLayer({
        id: "hand-fill", type: "fill", source: "hand_reconstruction",
        filter: ["all", ["==", ["geometry-type"], "Polygon"], ["==", ["get", "stage_index"], time]],
        paint: { "fill-color": "#f87171", "fill-opacity": ["interpolate", ["linear"], ["get", "hand_threshold_m"], 0, 0.18, 6, 0.42] },
      });
      map.addLayer({
        id: "hand-flow", type: "line", source: "hand_reconstruction",
        filter: ["all", ["==", ["geometry-type"], "LineString"], ["==", ["get", "stage_index"], time]],
        paint: { "line-color": "#fbbf24", "line-width": 3, "line-dasharray": [1.2, 0.8], "line-opacity": 0.9 },
      });
      map.addLayer({ id: "underpass-line", type: "line", source: "underpass", paint: { "line-color": "#ff6b6b", "line-width": 5, "line-opacity": 0.95 } });

      let hoverId: string | number | undefined;
      map.on("mousemove", "buildings-fill", (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0];
        if (!feature) return;
        if (hoverId !== undefined) map.setFeatureState({ source: "buildings", id: hoverId }, { hover: false });
        hoverId = feature.id;
        if (hoverId !== undefined) map.setFeatureState({ source: "buildings", id: hoverId }, { hover: true });
        map.getCanvas().style.cursor = "pointer";
        const props = feature.properties ?? {};
        hoverRef.current?.remove();
        hoverRef.current = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10, className: "dk-popup" })
          .setLngLat(event.lngLat)
          .setHTML(cardHtml("건축물", [["식별자", props.official_feature_id], ["출처", layers.buildings.source], ["기준", layers.buildings.snapshot]]))
          .addTo(map);
      });
      map.on("mouseleave", "buildings-fill", () => {
        if (hoverId !== undefined) map.setFeatureState({ source: "buildings", id: hoverId }, { hover: false });
        hoverId = undefined;
        map.getCanvas().style.cursor = "";
        hoverRef.current?.remove(); hoverRef.current = null;
      });
      map.on("click", "hand-fill", (event: MapLayerMouseEvent) => {
        const props = event.features?.[0]?.properties ?? {};
        new maplibregl.Popup({ offset: 12, className: "dk-popup" })
          .setLngLat(event.lngLat)
          .setHTML(cardHtml(stageKo(props.state, props.label ?? "침수 추정 셀"), [
            ["단계", stageKo(props.state, props.state)], ["HAND", `${props.hand_m ?? "?"} m`], ["임계", `${props.hand_threshold_m ?? "?"} m`],
            ["관측 수위", `${props.observed_water_level_m ?? "?"} m`], ["상태", `${statusKo(props.status)} · 공식 침수범위 아님`],
          ], "#f87171"))
          .addTo(map);
      });
      map.on("click", "waterways-fill", (event: MapLayerMouseEvent) => {
        const props = event.features?.[0]?.properties ?? {};
        new maplibregl.Popup({ offset: 12, className: "dk-popup" })
          .setLngLat(event.lngLat)
          .setHTML(cardHtml(String(props.RIVNM_2 ?? "하천"), [["등급", props.CLAS2], ["하천코드", props.RIVCD_2], ["출처", layers.waterways.source]], "#7dd3fc"))
          .addTo(map);
      });
      setReady(true);
    });

    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; markerRef.current = null; };
    // 최초 1회만 만든다. 데이터 갱신은 아래 효과들이 setData/setFilter 로 처리한다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 지하차도 위치에 맥동 마커. 누르면 사건 시각 카드가 열린다.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready || !underpassCenter) return;
    markerRef.current?.remove();
    const element = document.createElement("button");
    element.type = "button";
    element.className = "dk-pulse";
    element.setAttribute("aria-label", eventData.focus_feature);
    element.style.setProperty("--tone", tone);
    element.innerHTML = `<i></i><span>${escapeHtml(clock(current?.time))}</span>`;
    // 마커 클릭이 캔버스까지 번지면 아래 envelope 셀 카드가 같이 열린다. 마커에서 끊는다.
    element.addEventListener("click", (event) => event.stopPropagation());
    const rows: Array<[string, unknown]> = reconstruction
      ? [
          ["현재 단계", `${clock(current?.time)} ${current?.label ?? ""}`],
          ["제방붕괴→유입", `${reconstruction.baseline.failure_to_inflow_min}분`],
          ["유입→주행불능", `${reconstruction.baseline.inflow_to_unsafe_min}분`],
          ["유입→완전침수", `${reconstruction.baseline.inflow_to_full_inundation_min}분`],
          ["개입 시나리오", reconstruction.intervention.name],
        ]
      : [["상태", "재구성 데이터 없음"]];
    const popup = new maplibregl.Popup({ offset: 22, className: "dk-popup" }).setHTML(cardHtml(eventData.focus_feature, rows, tone));
    markerRef.current = new maplibregl.Marker({ element, anchor: "center" }).setLngLat(underpassCenter).setPopup(popup).addTo(map);
  }, [ready, underpassCenter, tone, current, eventData.focus_feature, reconstruction]);

  // 단계·시나리오가 바뀌면 envelope 필터와 색만 바꾼다.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const stageFilter = (geometry: string) => ["all", ["==", ["geometry-type"], geometry], ["==", ["get", "stage_index"], time]] as never;
    const color = scenario === "intervention" ? "#2dd4bf" : "#f87171";
    for (const id of ["hand-outline", "hand-fill"]) { if (map.getLayer(id)) map.setFilter(id, stageFilter("Polygon")); }
    if (map.getLayer("hand-flow")) map.setFilter("hand-flow", stageFilter("LineString"));
    if (map.getLayer("hand-outline")) map.setPaintProperty("hand-outline", "line-color", color);
    if (map.getLayer("hand-fill")) map.setPaintProperty("hand-fill", "fill-color", color);
  }, [ready, time, scenario]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const groups: Partial<Record<LayerKey, string[]>> = {
      aoi: ["aoi-line"], buildings: ["buildings-fill"], roads: ["roads-line"],
      waterways: ["waterways-fill", "waterways-line"],
      hand_reconstruction: ["hand-outline", "hand-fill", "hand-flow"], underpass: ["underpass-line"],
    };
    (Object.keys(groups) as LayerKey[]).forEach((key) => {
      groups[key]?.forEach((id) => { if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", visible[key] ? "visible" : "none"); });
    });
  }, [ready, visible]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    (Object.keys(layers) as LayerKey[]).forEach((key) => {
      const source = map.getSource(key) as GeoJSONSource | undefined;
      if (source) source.setData(layers[key].data as never);
    });
  }, [ready, layers]);

  const step = (delta: number) => {
    if (!stages.length) return;
    setPlaying(false);
    setTime((index) => Math.min(stages.length - 1, Math.max(0, index + delta)));
  };
  const togglePlayback = () => {
    if (!stages.length) return;
    // 마지막 단계에서 다시 재생하면 처음부터 사건을 다시 보여준다.
    if (!playing && time >= stages.length - 1) setTime(0);
    setPlaying((value) => !value);
  };
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.target as HTMLElement | null)?.closest?.("input, select, textarea")) return;
      if (event.key === "ArrowRight") step(1);
      if (event.key === "ArrowLeft") step(-1);
      if (event.key === " ") { event.preventDefault(); togglePlayback(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stages.length, playing, time]);

  const layerRows: LayerKey[] = ["hand_reconstruction", "waterways", "roads", "buildings", "underpass", "aoi"];
  const layerNames: Record<LayerKey, string> = {
    aoi: "행정경계(AOI)", roads: "도로", buildings: "건축물", waterways: "하천", terrain: "저지대", approx_flood_envelope: "근사 침수 범위",
    hand_reconstruction: "침수 추정 범위(HAND)", facilities: "시설", underpass: eventData.focus_feature, flood_extent: "공식 침수범위",
  };

  return (
    <div className="dk-root" style={{ ["--tone" as string]: tone, ["--dk-left-width" as string]: `${panelWidths.left}px`, ["--dk-right-width" as string]: `${panelWidths.right}px` }}>
      <header className="dk-topbar">
        <div className="dk-brand">
          <a className="dk-brand-mark" href="#cases" title="사례 선택으로 돌아가기" aria-label="사례 선택으로 돌아가기"><FloodOpsLogo size={30} /></a>
          <div>
            <h1>{eventData.name}</h1>
            <p>홍수 대응 디지털 트윈 · {eventData.location}</p>
          </div>
        </div>
        <nav className="dk-view-tabs" aria-label="FloodOps 화면">
          <button type="button" className={view === "console" ? "active" : ""} onClick={() => setView("console")}>관제 화면</button>
          <button type="button" className={view === "compare" ? "active" : ""} onClick={() => { if (view !== "compare" && time === 0 && stages.length > 4) setTime(4); setView("compare"); }}>시나리오 비교</button>
          <button type="button" className={view === "insights" ? "active" : ""} onClick={() => setView("insights")}>인사이트</button>
        </nav>
        <div className="dk-header-agent">
          <div className="dk-header-agent-title"><span><strong>대응 에이전트</strong><small>근거 기반 조치 질의</small></span></div>
          <AgentDock eventId={eventData.id} compact />
        </div>
        <div className="dk-topbar-right">
          <span className="dk-clock">{now.toLocaleDateString("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit" })} {now.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })} KST</span>
        </div>
      </header>

      {view === "console" ? <div className="dk-body">
        <aside className="dk-side">
          <div className="dk-side-head"><p>사건 재생</p><h2>사건 단계 · {stages.length}단계</h2></div>
          <section className="dk-priority" aria-label="판단 우선순위">
            <div className="dk-priority-head"><p>판단 우선순위</p><span>먼저 볼 자료</span></div>
            <ol>
              <li className="primary"><b>01 · 대응 시점</b><span>{current ? `${clock(current.time)} ${current.label}` : "현재 단계 확인"} · 여유 {reconstruction?.baseline.inflow_to_unsafe_min ?? "—"}분</span></li>
              <li><b>02 · 공간 상태</b><span>{spatialStatus(layers, time)}</span></li>
            </ol>
          </section>
          <ol className="dk-stages">
            {stages.map((item, index) => (
              <li key={`${item.time}-${item.state}`}>
                <button
                  type="button"
                  className={index === time ? "active" : index < time ? "past" : ""}
                  style={{ ["--tone" as string]: STAGE_TONE[item.state] ?? "#38bdf8" }}
                  onClick={() => { setPlaying(false); setTime(index); }}
                >
                  <time>{clock(item.time)}</time>
                  <b>{item.label}</b>
                  <small>{item.role} · {item.confidence}</small>
                </button>
              </li>
            ))}
          </ol>
          <div className="dk-side-block">
            <button type="button" className="dk-collapse" aria-expanded={layersOpen} onClick={() => setLayersOpen((open) => !open)}>
              <span><p>레이어</p><b>지도 레이어 표시 설정</b></span><strong>{layersOpen ? "닫기" : "열기"}</strong>
            </button>
            {layersOpen && <div className="dk-layer-list">
              {layerRows.map((key) => (
                <label key={key} className="dk-toggle">
                  <input type="checkbox" checked={visible[key]} onChange={(event) => setVisible((state) => ({ ...state, [key]: event.target.checked }))} />
                  <span>{layerNames[key]} <small>{num(layers[key].feature_count)} · {statusKo(layers[key].status)}</small></span>
                </label>
              ))}
            </div>}
          </div>
        </aside>

        <div
          className="dk-resize-handle"
          role="separator"
          aria-label="왼쪽 정보 패널 너비 조절"
          aria-orientation="vertical"
          tabIndex={0}
          onPointerDown={(event) => beginResize("left", event)}
          onKeyDown={(event) => nudgeResize("left", event.key)}
          title="드래그하거나 방향키로 왼쪽 패널 너비 조절"
        />

        <section className="dk-map-wrap" aria-label="지도">
          <div ref={mapElementRef} className="dk-map" />
          <button type="button" className="dk-nav prev" aria-label="이전 단계" title="이전 단계 (←)" onClick={() => step(-1)}>‹</button>
          <button type="button" className="dk-nav next" aria-label="다음 단계" title="다음 단계 (→)" onClick={() => step(1)}>›</button>
          <div className="dk-replay">
            <button type="button" disabled={!stages.length} onClick={togglePlayback}>{playing ? "❚❚ 일시정지" : "▶ 재생"}</button>
            <input type="range" min={0} max={Math.max(0, stages.length - 1)} value={time} onChange={(event) => { setPlaying(false); setTime(Number(event.target.value)); }} />
            <span>{current ? `${clock(current.time)} · ${current.label}` : "재구성 없음"}</span>
          </div>
          <div className="dk-legend">
            <p>범례</p>
            <span><i style={{ background: scenario === "intervention" ? "#2dd4bf" : "#f87171" }} />침수 추정 범위 (HAND 근사)</span>
            <span><i style={{ background: "#38bdf8" }} />하천</span>
            <span><i style={{ background: "#ff6b6b" }} />{eventData.focus_feature}</span>
            <span><i style={{ background: "#3b4a63" }} />건축물</span>
          </div>
          <div className="dk-hint">← → 단계 이동 · 스페이스 재생 · 지하차도 마커나 침수 셀을 누르면 카드가 열립니다</div>
        </section>

        <div
          className="dk-resize-handle"
          role="separator"
          aria-label="오른쪽 정보 패널 너비 조절"
          aria-orientation="vertical"
          tabIndex={0}
          onPointerDown={(event) => beginResize("right", event)}
          onKeyDown={(event) => nudgeResize("right", event.key)}
          title="드래그하거나 방향키로 오른쪽 패널 너비 조절"
        />

        <aside className="dk-detail">
          <div className="dk-detail-head"><p>관측 근거 · 단면</p><h2>관측 근거 · {eventData.focus_feature} 단면</h2></div>
          <div className="dk-detail-body">
            <EvidenceHandSection eventData={eventData} layers={layers} summary={summary} dataStatus={dataStatus} reconstruction={reconstruction} time={time} tone={tone} />
          </div>
        </aside>
      </div> : view === "compare"
        ? <ScenarioComparePage eventData={eventData} layers={layers} summary={summary} dataStatus={dataStatus} reconstruction={reconstruction} time={time} playing={playing} setTime={setTime} setPlaying={setPlaying} onTogglePlayback={togglePlayback} onBack={() => setView("console")} />
        : <InsightsPage eventData={eventData} layers={layers} summary={summary} dataStatus={dataStatus} reconstruction={reconstruction} time={time} onBack={() => setView("console")} />}
    </div>
  );
}

type MapSync = { maps: maplibregl.Map[]; syncing: boolean };

function ScenarioMap({
  layers,
  reconstruction,
  time,
  mode,
  title,
  sync,
  handStage,
  scenarioKind = "closure",
  closureClock,
}: {
  layers: LayersResponse;
  reconstruction: ReconstructionResponse;
  time: number;
  mode: ScenarioMode;
  title: string;
  sync: MapSync;
  handStage?: HandThresholdStage | null;
  scenarioKind?: "closure" | "hand";
  closureClock?: string;
}) {
  const elementRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const [ready, setReady] = useState(false);
  const center = useMemo(() => centerOf(layers.underpass.data), [layers.underpass.data]);
  const current = reconstruction.replay[time];
  const isHandScenario = mode === "intervention" && scenarioKind === "hand";
  const color = mode === "intervention" && !isHandScenario ? "#2dd4bf" : "#f87171";
  const closureActive = mode === "intervention" && !isHandScenario && Boolean(closureClock) && Boolean(current) && clock(current.time) >= (closureClock ?? "");
  const underpassColor = mode === "intervention" && !isHandScenario ? (closureActive ? "#2dd4bf" : "#f87171") : "#94a3b8";
  const markerColor = mode === "intervention" ? "#2dd4bf" : color;

  useEffect(() => {
    if (!elementRef.current || mapRef.current) return undefined;
    const map = new maplibregl.Map({
      container: elementRef.current,
      attributionControl: false,
      style: {
        version: 8,
        sources: {
          "esri-dark": { type: "raster", tiles: [`${ESRI}/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}`], tileSize: 256, maxzoom: 16, attribution: "Tiles © Esri" },
          "esri-dark-ref": { type: "raster", tiles: [`${ESRI}/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}`], tileSize: 256, maxzoom: 16 },
        },
        layers: [
          { id: "background", type: "background", paint: { "background-color": "#0b1220" } },
          { id: "esri-dark", type: "raster", source: "esri-dark", paint: { "raster-opacity": 0.92 } },
          { id: "esri-dark-ref", type: "raster", source: "esri-dark-ref", paint: { "raster-opacity": 0.75 } },
        ],
      },
      center: center ?? [127.31, 36.63],
      zoom: 13.6,
      maxZoom: 16,
    });
    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-left");
    sync.maps.push(map);
    // 한쪽 지도를 움직이면 다른 비교 지도도 같은 중심·배율로 맞춘다.
    map.on("move", () => {
      if (sync.syncing) return;
      sync.syncing = true;
      const camera = { center: map.getCenter(), zoom: map.getZoom(), bearing: map.getBearing(), pitch: map.getPitch() };
      sync.maps.forEach((other) => { if (other !== map) other.jumpTo(camera); });
      sync.syncing = false;
    });
    map.on("load", () => {
      const add = (key: LayerKey) => map.addSource(key, { type: "geojson", data: layers[key].data as never });
      add("aoi"); add("waterways"); add("roads"); add("buildings"); add("hand_reconstruction"); add("underpass");
      map.addLayer({ id: "aoi-line", type: "line", source: "aoi", paint: { "line-color": "#22d3ee", "line-width": 1, "line-dasharray": [3, 3], "line-opacity": 0.5 } });
      map.addLayer({ id: "buildings-fill", type: "fill", source: "buildings", paint: { "fill-color": "#3b4a63", "fill-opacity": 0.52 } });
      map.addLayer({ id: "roads-line", type: "line", source: "roads", paint: { "line-color": "#64748b", "line-width": 0.8, "line-opacity": 0.42 } });
      map.addLayer({ id: "waterways-line", type: "line", source: "waterways", paint: { "line-color": "#7dd3fc", "line-width": 1.1, "line-opacity": 0.82 } });
      map.addLayer({ id: "hand-outline", type: "line", source: "hand_reconstruction", filter: ["all", ["==", ["geometry-type"], "Polygon"], ["==", ["get", "stage_index"], time]], paint: { "line-color": color, "line-width": 1, "line-opacity": 0.9 } });
      map.addLayer({ id: "hand-fill", type: "fill", source: "hand_reconstruction", filter: ["all", ["==", ["geometry-type"], "Polygon"], ["==", ["get", "stage_index"], time]], paint: { "fill-color": color, "fill-opacity": 0.28 } });
      map.addLayer({ id: "hand-removed", type: "fill", source: "hand_reconstruction", filter: ["==", ["get", "grid_id"], "__none__"], paint: { "fill-color": "#2dd4bf", "fill-opacity": 0.64, "fill-outline-color": "#99f6e4" } });
      map.addLayer({ id: "hand-flow", type: "line", source: "hand_reconstruction", filter: ["all", ["==", ["geometry-type"], "LineString"], ["==", ["get", "stage_index"], time]], paint: { "line-color": "#fbbf24", "line-width": 2.5, "line-dasharray": [1.2, 0.8], "line-opacity": 0.85 } });
      map.addLayer({ id: "underpass-line", type: "line", source: "underpass", paint: { "line-color": underpassColor, "line-width": closureActive ? 7 : 5, "line-opacity": 0.95 } });
      setReady(true);
      window.requestAnimationFrame(() => map.resize());
    });
    mapRef.current = map;
    return () => {
      sync.maps = sync.maps.filter((item) => item !== map);
      markerRef.current?.remove();
      map.remove();
      mapRef.current = null;
    };
    // 비교 지도는 최초 1회 초기화하고, 데이터·단계는 아래 효과에서 갱신한다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const stageFilter = ["all", ["==", ["geometry-type"], "Polygon"], ["==", ["get", "stage_index"], time]];
    const polygonFilter = (!isHandScenario ? stageFilter : handStage
      ? ["all", ...stageFilter.slice(1), ["in", ["get", "grid_id"], ["literal", handStage.selected_grid_ids]]]
      : ["==", ["get", "grid_id"], "__pending__"]) as never;
    const removedFilter = (isHandScenario && handStage
      ? ["all", ...stageFilter.slice(1), ["in", ["get", "grid_id"], ["literal", handStage.removed_grid_ids]]]
      : ["==", ["get", "grid_id"], "__none__"]) as never;
    const lineFilter = ["all", ["==", ["geometry-type"], "LineString"], ["==", ["get", "stage_index"], time]] as never;
    if (map.getLayer("hand-outline")) map.setFilter("hand-outline", polygonFilter);
    if (map.getLayer("hand-fill")) map.setFilter("hand-fill", polygonFilter);
    if (map.getLayer("hand-removed")) map.setFilter("hand-removed", removedFilter);
    if (map.getLayer("hand-flow")) map.setFilter("hand-flow", lineFilter);
    if (map.getLayer("hand-outline")) map.setPaintProperty("hand-outline", "line-color", color);
    if (map.getLayer("hand-fill")) map.setPaintProperty("hand-fill", "fill-color", color);
    if (map.getLayer("underpass-line")) {
      map.setPaintProperty("underpass-line", "line-color", underpassColor);
      map.setPaintProperty("underpass-line", "line-width", closureActive ? 7 : 5);
    }
  }, [ready, time, isHandScenario, handStage, color, underpassColor, closureActive]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    (Object.keys(layers) as LayerKey[]).forEach((key) => {
      const source = map.getSource(key) as GeoJSONSource | undefined;
      if (source) source.setData(layers[key].data as never);
    });
    map.resize();
  }, [ready, layers]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready || !center) return;
    markerRef.current?.remove();
    const marker = document.createElement("div");
    marker.className = "dk-compare-marker";
    marker.style.setProperty("--tone", markerColor);
    marker.innerHTML = `<i></i>`;
    markerRef.current = new maplibregl.Marker({ element: marker, anchor: "center" }).setLngLat(center).addTo(map);
  }, [ready, center, markerColor]);

  return (
    <section className={`dk-compare-map-card ${mode}`} aria-label={`${title} 지도`}>
      <div className="dk-compare-map-head">
        <div><span className="dk-compare-card-label"><i />{title}</span><strong>{current ? `${clock(current.time)} · ${current.label}` : "재구성 단계 없음"}</strong></div>
        <small>{mode === "baseline" ? "기준 HAND 재구성" : isHandScenario ? (handStage ? `붉은 셀 ${handStage.scenario_cell_count}개 · 제외 ${handStage.removed_cell_count}개` : "HAND 재분류 계산 중") : closureActive ? `${closureClock} 이후 신규 진입 통제 가정` : `통제 전 · ${closureClock ?? "--:--"} 예정`}</small>
      </div>
      <div className="dk-compare-map"><div ref={elementRef} /></div>
      <div className="dk-compare-map-foot"><span><i className="hand" />침수 추정 범위 (HAND 근사)</span><span><i className={isHandScenario ? "changed" : "road"} />{isHandScenario ? "청록: 임계 변경으로 제외된 셀" : "공통 공간 레이어"}</span></div>
    </section>
  );
}

function EvidenceHandSection({
  eventData,
  layers,
  summary,
  dataStatus,
  reconstruction,
  time,
  tone,
  compact = false,
}: {
  eventData: FloodEvent;
  layers: LayersResponse;
  summary: ExposureMetrics | null;
  dataStatus: DataStatusResponse | null;
  reconstruction: ReconstructionResponse | null;
  time: number;
  tone: string;
  compact?: boolean;
}) {
  const current = reconstruction?.replay[time];
  const underpassCenter = useMemo(() => centerOf(layers.underpass.data), [layers.underpass.data]);

  return (
    <div className={`dk-evidence-section${compact ? " compact" : ""}`}>
      {compact && <div className="dk-detail-head dk-evidence-section-head"><p>관측 근거 · 단면</p><h2>관측 근거 · {eventData.focus_feature} 단면</h2></div>}
      {reconstruction && (
        <CrossSection
          hand={layers.hand_reconstruction.data}
          center={underpassCenter}
          stageIndex={time}
          stageLabel={current?.label ?? ""}
          stageTime={current ? clock(current.time) : "--:--"}
          tone={tone}
          focusName={eventData.focus_feature}
        />
      )}
    </div>
  );
}

function InsightsPage({
  eventData,
  layers,
  summary,
  dataStatus,
  reconstruction,
  time,
  onBack,
}: {
  eventData: FloodEvent;
  layers: LayersResponse;
  summary: ExposureMetrics | null;
  dataStatus: DataStatusResponse | null;
  reconstruction: ReconstructionResponse | null;
  time: number;
  onBack: () => void;
}) {
  const current = reconstruction?.replay[time];
  const officialExtent = summary?.flooded_area_km2;

  return (
    <main className="dk-insights">
      <div className="dk-insights-head">
        <div>
          <p>판단 근거 요약</p>
          <h2>인사이트 · 데이터 해석과 다음 조치</h2>
          <span>{eventData.name}의 현재 위험을 어떻게 읽고, 어떤 근거로 다음 조치를 선택하는지 정리합니다.</span>
        </div>
        <button type="button" className="dk-compare-back" onClick={onBack}>관제 화면으로</button>
      </div>

      <div className="dk-insight-kpis">
        <div><span>현재 단계</span><strong>{current ? `${clock(current.time)} · ${current.label}` : "—"}</strong><small>재생 기준 {time + 1}단계</small></div>
        <div><span>판단 우선순위</span><strong>시간 · 시설 상태</strong><small>반경 재고는 보조 근거</small></div>
        <div><span>대응 여유</span><strong>{reconstruction ? `${reconstruction.baseline.inflow_to_unsafe_min}분` : "—"}</strong><small>관측 재현 기준</small></div>
        <div><span>공식 침수범위</span><strong className="pending">{officialExtent == null ? "확보 전" : String(officialExtent)}</strong><small>공식 벡터 자료 확보 전</small></div>
      </div>

      <div className="dk-insight-grid">
        <article className="dk-insight-card priority">
          <div className="dk-insight-label"><i />01 · 판단 우선순위</div>
          <h3>무엇을 먼저 봐야 하는가</h3>
          <p>관제 담당자는 현재 단계와 지하차도 상태를 먼저 확인하고, 그 다음 공간 위험과 노출 재고를 확인합니다.</p>
          <ol>
            <li><b>01</b><span><strong>대응 시점</strong> {current ? `${clock(current.time)} ${current.label}` : "현재 단계 확인"}</span></li>
            <li><b>02</b><span><strong>공간 상태</strong> {spatialStatus(layers, time)}</span></li>
            <li><b>03</b><span><strong>노출 재고</strong> 반경 내 시설 수 · 피해 추정 아님</span></li>
          </ol>
        </article>

        <article className="dk-insight-card data">
          <div className="dk-insight-label"><i />02 · 데이터 상태</div>
          <h3>숫자의 성격을 구분한다</h3>
          <p>같은 미터 단위라도 관측소 기준면과 DEM 표고 기준이 다를 수 있습니다. UI는 원시·파생·대리값을 분리합니다.</p>
          <dl className="dk-insight-dl">
            <div><dt>관측</dt><dd>수위 {dec(summary?.water_level_peak_m, 2)} m · 강우 {dec(summary?.rainfall_peak_mm_per_hour)} mm/h</dd></div>
            <div><dt>지형 분석</dt><dd>HAND {num(layers.hand_reconstruction.feature_count)} cells · DEM {dec(dataStatus?.dem?.mean_elevation_m)} m</dd></div>
            <div><dt>대리 표현</dt><dd>단면 수면 · 재생 위험 진행</dd></div>
          </dl>
        </article>

        <article className="dk-insight-card engineering">
          <div className="dk-insight-label"><i />03 · 데이터 엔지니어링</div>
          <h3>오늘 조정한 데이터 흐름</h3>
          <p>화면에 값을 직접 넣지 않고 API 응답을 공통 계약으로 묶어 지도·단면·시나리오가 같은 데이터를 바라보게 했습니다.</p>
          <div className="dk-insight-tags"><span>API 응답 형식 고정</span><span>레이어 출처 기록</span><span>재생 타임라인</span><span>단일 컨테이너 배포</span></div>
          <small>레이어 메타데이터: {layers.hand_reconstruction.status} · {layers.hand_reconstruction.source_type ?? "출처 미기록"}</small>
        </article>

        <article className="dk-insight-card scenario">
          <div className="dk-insight-label"><i />04 · 개입 해석</div>
          <h3>개입은 운영 상태를 바꾼다</h3>
          <p>선택 시나리오는 지정 시각부터 신규 차량 진입을 막았다고 가정합니다. 물의 진행과 이미 진입한 차량, 사상자 수의 변화는 계산하지 않습니다.</p>
          <div className="dk-insight-compare"><span className="base">원시나리오<br /><b>관측 재현</b></span><em>→</em><span className="intervention">선택 시나리오<br /><b>시간 지정 통제 가정</b></span></div>
        </article>

        <article className="dk-insight-card limitation">
          <div className="dk-insight-label"><i />05 · 한계와 다음 검증</div>
          <h3>어디까지 말할 수 있는가</h3>
          <ul>
            <li>관측소 기준면과 DEM 수직 기준 정합 필요</li>
            <li>공식 침수범위 또는 수리모형과 HAND 검증 필요</li>
            <li>개입 효과의 정량화를 위한 노출 변화 모델 필요</li>
            <li>브라우저 실제 화면 QA와 상호작용 테스트 필요</li>
          </ul>
        </article>
      </div>

      <div className="dk-insights-footer"><strong>보고서용 요약</strong><span>FloodOps는 침수 데이터를 많이 보여주는 시스템이 아니라, 데이터의 신뢰도와 의미를 구분한 상태에서 담당자의 다음 조치를 빠르게 만드는 운영형 디지털 트윈입니다.</span></div>
    </main>
  );
}

type ScenarioPageProps = {
  eventData: FloodEvent;
  layers: LayersResponse;
  summary: ExposureMetrics | null;
  dataStatus: DataStatusResponse | null;
  reconstruction: ReconstructionResponse | null;
  time: number;
  playing: boolean;
  setTime: Dispatch<SetStateAction<number>>;
  setPlaying: Dispatch<SetStateAction<boolean>>;
  onTogglePlayback: () => void;
  onBack: () => void;
};

function ScenarioComparePage(props: ScenarioPageProps) {
  const [panel, setPanel] = useState<"hand" | "closure">("hand");
  return <div className="dk-scenario-shell">
    <div className="dk-scenario-picker">
      <strong>무엇을 비교할까요?</strong>
      <p>Agent를 거치지 않고 아래 값을 직접 고릅니다. 두 분석은 서로 다른 질문에 답하며, 결과를 합쳐 하나의 위험도 점수로 만들지 않습니다.</p>
      <nav className="dk-scenario-tabs" aria-label="시나리오 분석 선택">
        <button type="button" className={panel === "hand" ? "active" : ""} aria-pressed={panel === "hand"} onClick={() => setPanel("hand")}>
          <span>지도 표시 민감도</span><strong>HAND 셀 선택 기준</strong><small>바꾸는 값: 판정 임계 · 보는 값: 선택된 셀 수</small>
        </button>
        <button type="button" className={panel === "closure" ? "active" : ""} aria-pressed={panel === "closure"} onClick={() => setPanel("closure")}>
          <span>대응 시각 비교</span><strong>지하차도 통제 시각</strong><small>바꾸는 값: 통제 시각 · 보는 값: 유입 전후 시간차</small>
        </button>
      </nav>
      <small className="dk-scenario-limit">실제 침수 위험도 점수·침수심·피해 감소율은 계산하지 않습니다. 분석 API 연결은 필요합니다.</small>
    </div>
    {panel === "hand" ? <HandScenarioView {...props} /> : <ClosureScenarioView {...props} />}
  </div>;
}

function ClosureScenarioView({
  eventData,
  layers,
  summary,
  dataStatus,
  reconstruction,
  time,
  playing,
  setTime,
  setPlaying,
  onTogglePlayback,
  onBack,
}: ScenarioPageProps) {
  const states = reconstruction?.baseline.states ?? [];
  const inflow = states.find((item) => item.state === "underpass_inflow");
  const unsafe = states.find((item) => item.state === "unsafe_driving");
  const full = states.find((item) => item.state === "full_inundation");
  const intervention = reconstruction?.intervention;
  const current = reconstruction?.replay[time];
  const syncRef = useRef<MapSync>({ maps: [], syncing: false });
  const triggerClock = clock(intervention?.trigger_time);
  const [closureClock, setClosureClock] = useState(() => (triggerClock === "--:--" ? "08:25" : triggerClock));
  const [latestClosure, setClosureResult] = useState<ClosureTimingScenario | null>(null);
  const [closureError, setClosureError] = useState<string | null>(null);
  const replayMinutes = (reconstruction?.replay ?? []).map((item) => toMinutes(clock(item.time)));
  const leveeFailure = states.find((item) => item.state === "levee_failure");
  const sliderMin = replayMinutes.length ? Math.max(0, toMinutes(clock(leveeFailure?.time ?? reconstruction?.replay[0]?.time)) - 30) : 0;
  const sliderMax = replayMinutes.length ? Math.max(...replayMinutes) : 0;
  const presets = [
    { label: "제방 붕괴", state: "levee_failure" },
    { label: "유입 시작", state: "underpass_inflow" },
    { label: "주행불능", state: "unsafe_driving" },
  ].flatMap((item) => {
    const hit = states.find((entry) => entry.state === item.state);
    return hit ? [{ ...item, value: clock(hit.time) }] : [];
  });
  const showTriggerPreset = triggerClock !== "--:--" && !presets.some((item) => item.value === triggerClock);
  const closureResult = latestClosure && clock(latestClosure.closure_time) === closureClock ? latestClosure : null;

  useEffect(() => {
    let live = true;
    const timer = window.setTimeout(() => {
      api.getClosureTiming(eventData.id, [closureClock])
        .then((result) => { if (live) { setClosureResult(result.scenarios[0] ?? null); setClosureError(null); } })
        .catch(() => { if (live) setClosureError("통제 시각 계산 API를 호출하지 못했습니다."); });
    }, 200);
    return () => { live = false; window.clearTimeout(timer); };
  }, [eventData.id, closureClock]);

  if (!reconstruction || !intervention) {
    return <main className="dk-compare dk-compare-empty"><strong>시나리오 비교 데이터를 불러오지 못했습니다.</strong><button type="button" onClick={onBack}>관제 화면으로 돌아가기</button></main>;
  }

  return (
    <main className="dk-compare">
      <div className="dk-compare-head">
        <div>
          <p>가정 대응 분석</p>
          <h2>{eventData.focus_feature} 통제 시각에 따른 대응 여유</h2>
          <span>Agent 없이 통제 시각을 직접 고릅니다. 결과는 유입 전후의 시간 차이이며 침수 위험도 자체는 다시 계산하지 않습니다.</span>
        </div>
        <button type="button" className="dk-compare-back" onClick={onBack}>관제 화면으로</button>
      </div>

      <div className="dk-compare-replay">
        <div className="dk-compare-replay-label"><span>사건 재생</span><strong>{current ? `${clock(current.time)} · ${current.label}` : "재구성 단계 없음"}</strong></div>
        <button type="button" aria-label="이전 단계" title="이전 단계" disabled={time <= 0} onClick={() => { setPlaying(false); setTime((index) => Math.max(0, index - 1)); }}>‹</button>
        <button type="button" className="primary" disabled={!reconstruction.replay.length} onClick={onTogglePlayback}>{playing ? "❚❚ 일시정지" : "▶ 재생"}</button>
        <button type="button" aria-label="다음 단계" title="다음 단계" disabled={time >= reconstruction.replay.length - 1} onClick={() => { setPlaying(false); setTime((index) => Math.min(reconstruction.replay.length - 1, index + 1)); }}>›</button>
        <input type="range" min={0} max={Math.max(0, reconstruction.replay.length - 1)} value={time} onChange={(event) => { setPlaying(false); setTime(Number(event.target.value)); }} />
        <span>{reconstruction.replay.length ? `${time + 1} / ${reconstruction.replay.length}` : "—"}</span>
      </div>

      <div className="dk-compare-cards">
        <section className="dk-compare-card baseline">
          <div className="dk-compare-card-label"><i />원시나리오 · 관측 재현</div>
          <h3>{reconstruction.baseline.name}</h3>
          <p>{reconstruction.baseline.description}</p>
          <dl>
            <div><dt>유입 시작</dt><dd>{inflow ? clock(inflow.time) : "—"}</dd></div>
            <div><dt>주행불능까지</dt><dd>{reconstruction.baseline.inflow_to_unsafe_min}분</dd></div>
            <div><dt>완전침수까지</dt><dd>{reconstruction.baseline.inflow_to_full_inundation_min}분</dd></div>
          </dl>
        </section>
        <section className="dk-compare-card intervention">
          <div className="dk-compare-card-label"><i />선택 시나리오 · 지하차도 통제 시각 조절</div>
          <h3>{closureClock} 지하차도 진입 통제</h3>
          <div className="dk-closure-control">
            <label className="dk-scenario-input-label" htmlFor="closure-time-range">가정할 통제 시각 <strong>{closureClock}</strong></label>
            <input id="closure-time-range" type="range" min={sliderMin} max={sliderMax} step={1} value={clamp(toMinutes(closureClock), sliderMin, sliderMax)} onChange={(event) => setClosureClock(fromMinutes(Number(event.target.value)))} />
            <span className="dk-closure-presets-label">사건 단계 시각으로 통제 가정하기</span>
            <div className="dk-closure-presets">
              {presets.map((item) => <button key={item.state} type="button" className={`dk-closure-preset ${item.value === closureClock ? "active" : ""}`} style={{ ["--tone" as string]: STAGE_TONE[item.state] ?? "#38bdf8" }} aria-pressed={item.value === closureClock} onClick={() => setClosureClock(item.value)}>{item.label} {item.value}</button>)}
              {showTriggerPreset && <button type="button" className={`dk-closure-default ${triggerClock === closureClock ? "active" : ""}`} aria-pressed={triggerClock === closureClock} onClick={() => setClosureClock(triggerClock)}>기본 비교 {triggerClock}</button>}
            </div>
            <small className="dk-closure-hint">버튼은 사건 시각을 통제 시각으로 대입하는 가정이며, 실제 통제 기록이 아닙니다.</small>
          </div>
          {closureError ? <p className="dk-compare-warn">{closureError}</p> : (
            <dl>
              <div><dt>통제 판정</dt><dd>{closureResult ? CLOSURE_CLASS[closureResult.classification] ?? closureResult.classification : "계산 중"}</dd></div>
              <div><dt>유입까지</dt><dd>{closureResult ? leadText(closureResult.minutes_before_underpass_inflow) : "—"}</dd></div>
              <div><dt>주행불능까지</dt><dd>{closureResult ? leadText(closureResult.minutes_before_unsafe_driving) : "—"}</dd></div>
              <div><dt>완전침수까지</dt><dd>{closureResult ? leadText(closureResult.minutes_before_full_inundation) : "—"}</dd></div>
            </dl>
          )}
        </section>
      </div>

      <section className="dk-compare-panel dk-compare-summary" aria-label="통제 시각 비교 결과">
        <div className="dk-compare-panel-head"><p>통제 시각 비교 결과</p><span>위에서 통제 시각을 바꾸고 첫 번째 값을 확인하세요.</span></div>
        <div className="dk-compare-summary-grid">
          <article className={`dk-compare-summary-card focus ${closureResult ? (closureResult.minutes_before_underpass_inflow > 0 ? "ahead" : closureResult.minutes_before_underpass_inflow < 0 ? "late" : "same") : "pending"}`}>
            <span>01 · 유입 대비 통제 시점</span>
            <strong aria-live="polite">{closureError ? "계산 불가" : closureResult ? leadText(closureResult.minutes_before_underpass_inflow) : "계산 중"}</strong>
            <p>{closureClock} 통제 가정과 {clock(inflow?.time)} 유입 사이의 시간 차이입니다.</p>
          </article>
          <article className="dk-compare-summary-card">
            <span>02 · 가정에서 바꾸는 것</span>
            <strong>신규 차량 진입 통제 시각</strong>
            <p>원시나리오에는 통제가 없고, 선택 시나리오는 {closureClock}부터 신규 진입을 막았다고 가정합니다.</p>
          </article>
          <article className="dk-compare-summary-card">
            <span>03 · 그대로인 사건 기록</span>
            <strong>{clock(inflow?.time)} 유입 → {clock(unsafe?.time)} 주행불능</strong>
            <p>통제 시각을 바꿔도 물의 유입과 완전침수({clock(full?.time)}) 시각은 바뀌지 않습니다.</p>
          </article>
        </div>
        <small className="dk-compare-summary-note">이 비교는 관측된 사건 시각과 통제 가정의 차이입니다. 차량·인명 피해 감소 효과는 계산하지 않습니다.</small>
      </section>

      <section className="dk-compare-panel dk-compare-stage-panel">
        <div className="dk-compare-panel-head"><p>공간 비교</p><span>두 시나리오는 같은 사건 단계, 오른쪽 근거는 현재 단계를 고정 표시</span></div>
        <div className="dk-compare-stage-grid">
          <ScenarioMap layers={layers} reconstruction={reconstruction} time={time} mode="baseline" title="원시나리오" sync={syncRef.current} />
          <ScenarioMap layers={layers} reconstruction={reconstruction} time={time} mode="intervention" title="선택 시나리오" sync={syncRef.current} closureClock={closureClock} />
          <aside className="dk-compare-evidence">
            <EvidenceHandSection eventData={eventData} layers={layers} summary={summary} dataStatus={dataStatus} reconstruction={reconstruction} time={time} tone="#2dd4bf" compact />
          </aside>
        </div>
        <small className="dk-compare-map-note">두 지도는 같은 재생 시점과 화면 배율을 공유합니다. 선택 시나리오의 지하차도 색은 통제 시각 전(붉음)·후(청록) 상태이며, 침수범위는 공식 범위나 수리모형 결과가 아니라 두 지도에서 같습니다.</small>
      </section>

      <small className="dk-compare-limit">근거: {intervention.trigger_basis} · {intervention.estimated_effect} · 공식 피해 감소율/사상자/실제 침수심은 산출하지 않습니다.</small>
    </main>
  );
}

function HandScenarioView({
  eventData, layers, summary, dataStatus, reconstruction, time, playing,
  setTime, setPlaying, onTogglePlayback, onBack,
}: ScenarioPageProps) {
  const syncRef = useRef<MapSync>({ maps: [], syncing: false });
  const [reductionM, setReductionM] = useState(0);
  const [latestHand, setLatestHand] = useState<HandThresholdResult | null>(null);
  const [handError, setHandError] = useState<string | null>(null);
  const current = reconstruction?.replay[time];
  const handResult = latestHand?.event_id === eventData.id && latestHand.reduction_m === reductionM ? latestHand : null;
  const handStage = handResult?.stages.find((stage) => stage.stage_index === time) ?? null;

  useEffect(() => {
    let live = true;
    const timer = window.setTimeout(() => {
      api.getHandThreshold(eventData.id, reductionM)
        .then((result) => { if (live) { setLatestHand(result); setHandError(null); } })
        .catch(() => { if (live) setHandError("HAND 임계 민감도 분석을 불러오지 못했습니다."); });
    }, 160);
    return () => { live = false; window.clearTimeout(timer); };
  }, [eventData.id, reductionM]);

  if (!reconstruction) {
    return <main className="dk-compare dk-compare-empty"><strong>HAND 사건 재구성 데이터가 연결되지 않았습니다.</strong><button type="button" onClick={onBack}>관제 화면으로 돌아가기</button></main>;
  }

  return <main className="dk-compare">
    <div className="dk-compare-head">
      <div><p>HAND 판정 기준 민감도</p><h2>{eventData.focus_feature} 지도 선택 셀 비교</h2>
        <span>같은 사건 시각에서 지도 셀을 고르는 임계만 바꿉니다. 셀 수 변화는 분석 설정의 민감도이며 실제 침수 위험 감소가 아닙니다.</span></div>
      <button type="button" className="dk-compare-back" onClick={onBack}>관제 화면으로</button>
    </div>

    <div className="dk-compare-replay">
      <div className="dk-compare-replay-label"><span>사건 재생</span><strong>{current ? `${clock(current.time)} · ${current.label}` : "재구성 단계 없음"}</strong></div>
      <button type="button" aria-label="이전 단계" disabled={time <= 0} onClick={() => { setPlaying(false); setTime((index) => Math.max(0, index - 1)); }}>‹</button>
      <button type="button" className="primary" disabled={!reconstruction.replay.length} onClick={onTogglePlayback}>{playing ? "❚❚ 일시정지" : "▶ 재생"}</button>
      <button type="button" aria-label="다음 단계" disabled={time >= reconstruction.replay.length - 1} onClick={() => { setPlaying(false); setTime((index) => Math.min(reconstruction.replay.length - 1, index + 1)); }}>›</button>
      <input type="range" min={0} max={Math.max(0, reconstruction.replay.length - 1)} value={time} onChange={(event) => { setPlaying(false); setTime(Number(event.target.value)); }} />
      <span>{reconstruction.replay.length ? `${time + 1} / ${reconstruction.replay.length}` : "—"}</span>
    </div>

    <div className="dk-compare-cards">
      <section className="dk-compare-card baseline">
        <div className="dk-compare-card-label"><i />기준 · HAND 재구성</div>
        <h3>기준 선택 임계</h3>
        <p>관측 수위의 상대 상승분과 사건 단계 가중분을 적용한 임시 공간 재구성입니다.</p>
        <dl>
          <div><dt>사건 단계</dt><dd>{current ? `${clock(current.time)} · ${current.label}` : "—"}</dd></div>
          <div><dt>선택 임계</dt><dd>{handStage ? `${handStage.baseline_threshold_m.toFixed(2)} m` : "—"}</dd></div>
          <div><dt>붉은 셀</dt><dd>{num(handStage?.baseline_cell_count)}개</dd></div>
        </dl>
      </section>
      <section className="dk-compare-card intervention">
        <div className="dk-compare-card-label"><i />가정 · HAND 임계 민감도</div>
        <h3>{reductionM === 0 ? "기준 그대로" : `판정 임계 ${reductionM.toFixed(1)} m 낮춤`}</h3>
        <div className="dk-closure-control">
          <label className="dk-scenario-input-label" htmlFor="hand-threshold-range">지도 셀 판정 기준 <strong>{reductionM === 0 ? "변경 없음" : `${reductionM.toFixed(1)} m 낮춤`}</strong></label>
          <input id="hand-threshold-range" type="range" min={0} max={2.5} step={0.1} value={reductionM} onChange={(event) => setReductionM(Number(Number(event.target.value).toFixed(1)))} />
          <div className="dk-hand-presets">{[0, 0.5, 1, 1.5, 2, 2.5].map((value) => <button key={value} type="button" className={value === reductionM ? "active" : ""} aria-pressed={value === reductionM} onClick={() => setReductionM(value)}>{value === 0 ? "기준 그대로" : `${value.toFixed(1)} m 낮춤`}</button>)}</div>
          <small className="dk-closure-hint">값을 높이면 임시 HAND 지도에서 선택되는 셀을 더 엄격하게 거릅니다. 실제 수위·제방·차수벽 효과를 바꾸는 입력이 아닙니다.</small>
        </div>
        {handError ? <p className="dk-compare-warn">{handError}</p> : <dl>
          <div><dt>변경 임계</dt><dd>{handStage ? `${handStage.scenario_threshold_m.toFixed(2)} m` : "계산 중"}</dd></div>
          <div><dt>남은 붉은 셀</dt><dd>{num(handStage?.scenario_cell_count)}개</dd></div>
          <div><dt>제외된 셀</dt><dd>{num(handStage?.removed_cell_count)}개</dd></div>
        </dl>}
      </section>
    </div>

    <section className="dk-compare-panel dk-compare-summary" aria-label="HAND 셀 비교 결과">
      <div className="dk-compare-panel-head"><p>지도 선택 셀 비교 결과</p><span>같은 사건 단계에서 판정 기준만 변경</span></div>
      <div className="dk-compare-summary-grid">
        <article className="dk-compare-summary-card focus ahead"><span>01 · 기준에서 선택된 셀</span><strong>{num(handStage?.baseline_cell_count)}개</strong><p>현재 재생 단계의 임시 HAND 지도 셀 수입니다.</p></article>
        <article className="dk-compare-summary-card"><span>02 · 변경 후 선택된 셀</span><strong>{num(handStage?.scenario_cell_count)}개</strong><p>낮춘 판정 기준과 하천 쪽 연결 조건을 만족한 셀입니다.</p></article>
        <article className="dk-compare-summary-card"><span>03 · 기준에서 제외된 셀</span><strong>{num(handStage?.removed_cell_count)}개</strong><p>오른쪽 지도에서 청록색으로 표시합니다. 실제 침수 감소 면적이 아닙니다.</p></article>
      </div>
    </section>

    <section className="dk-compare-panel dk-compare-stage-panel">
      <div className="dk-compare-panel-head"><p>공간 비교</p><span>두 지도는 같은 사건 시각과 화면 범위를 공유합니다.</span></div>
      <div className="dk-compare-stage-grid">
        <ScenarioMap layers={layers} reconstruction={reconstruction} time={time} mode="baseline" title="기준 재구성" sync={syncRef.current} scenarioKind="hand" />
        <ScenarioMap layers={layers} reconstruction={reconstruction} time={time} mode="intervention" title="임계 변경 가정" sync={syncRef.current} scenarioKind="hand" handStage={handStage} />
        <aside className="dk-compare-evidence"><EvidenceHandSection eventData={eventData} layers={layers} summary={summary} dataStatus={dataStatus} reconstruction={reconstruction} time={time} tone="#f87171" compact /></aside>
      </div>
      <small className="dk-compare-map-note">붉은 셀은 임시 HAND 선택 셀, 청록 셀은 임계를 낮추며 제외된 셀입니다. 오른쪽 단면은 기준 재구성 값이며, 변경된 임계는 위 카드에 표시합니다.</small>
    </section>
    <small className="dk-compare-limit">{textKo(handResult?.coverage_note) ?? "HAND 재구성 자료 확인 중"} · 이 값은 공간 선택 규칙의 민감도이며 실제 침수범위·침수심·시설 효과가 아닙니다.</small>
  </main>;
}

/* ------------------------------------------------------------------ */
/* Agent — 질문 → 도구 선택 → 관찰 → 추가 도구 또는 근거 답변.                   */
/* ------------------------------------------------------------------ */

function AgentDock({ eventId, compact = false }: { eventId: string; compact?: boolean }) {
  const [message, setMessage] = useState("");
  const [turns, setTurns] = useState<Array<{ question: string; response: AgentAskResult }>>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [examples, setExamples] = useState<AgentExampleQuestion[]>(FALLBACK_EXAMPLES);

  useEffect(() => { setTurns([]); setMessage(""); setError(null); }, [eventId]);

  useEffect(() => {
    let live = true;
    api.getAgentExamples()
      .then((items) => { if (live && items.length) setExamples(items); })
      .catch(() => { /* keep the offline fallback chips */ });
    return () => { live = false; };
  }, []);

  const ask = async (question: string) => {
    const text = question.trim();
    if (!text || busy) return;
    setBusy(true); setError(null);
    try {
      const history = turns.flatMap((turn): Array<{ role: "user" | "assistant"; content: string }> => [
        { role: "user", content: turn.question },
        { role: "assistant", content: turn.response.answer },
      ]).slice(-6);
      const response = await api.askAgent(eventId, text, history);
      setTurns((previous) => [...previous, { question: text, response }]);
      setMessage(response.status === "UNAVAILABLE" ? text : "");
    } catch (cause) {
      setMessage(text);
      const detail = cause instanceof Error ? cause.message : "";
      setError(detail.includes("API 429")
        ? detail.replace(/^API 429:\s*/, "")
        : detail.includes("API 404")
          ? "Agent API 경로를 찾을 수 없습니다. API 서버를 최신 코드로 다시 실행해 주세요."
          : "Agent API에 연결하지 못했습니다. 서버 실행 상태를 확인해 주세요.");
    }
    finally { setBusy(false); }
  };

  const status = busy ? "자료를 확인하고 다음 도구를 판단하는 중…" : turns.length ? "다른 조건이나 후속 질문을 이어서 물어보세요." : "예: HAND 임계를 1.5m 낮추면 붉은 셀이 어떻게 바뀌나요?";

  return (
    <div className={`dk-agent${compact ? " dk-agent-compact" : ""}`}>
      <div className="dk-agent-head"><p>FloodOps 에이전트</p><span className="dk-agent-badge llm">Gemini + 분석 도구</span></div>
      {!compact && <div className="dk-agent-intro">질문에 따라 등록된 분석 도구를 차례로 호출하고 결과를 읽어 답합니다. 질문·대화 기록·도구 결과는 Gemini에 전송됩니다. 도구로 확인할 수 없는 피해 효과는 추정하지 않습니다.</div>}
      {!compact && <div className="dk-agent-suggestions" aria-label="추천 질문">
        <button type="button" disabled={busy} onClick={() => void ask("HAND 선택 임계를 1.5m 낮추면 붉은 셀이 단계별로 어떻게 바뀌나요?")}>HAND 붉은 셀 변화</button>
        <button type="button" disabled={busy} onClick={() => void ask("08:25 통제와 유입 10분 지연을 함께 비교하면 무엇이 다르고, 무엇은 알 수 없나요?")}>통제 + 유입 지연 함께</button>
        {examples.map((item) => <button key={item.workflow} type="button" title={item.question} disabled={busy} onClick={() => void ask(item.question)}>{item.label}</button>)}
      </div>}
      <form className="dk-agent-bar" onSubmit={(event) => { event.preventDefault(); void ask(message); }}>
        <input aria-label="Agent request" value={message} onChange={(event) => setMessage(event.target.value)} placeholder="사건과 개입 조건을 자유롭게 물어보세요" />
        <button type="submit" disabled={busy || !message.trim()}>질문</button>
      </form>
      <small className="dk-agent-status" aria-live="polite">{status}</small>
      {(compact ? turns.slice(-1) : turns).map((turn, index) => (
        <div className={`dk-result ${turn.response.status.toLowerCase()}`} key={`${index}-${turn.question}`}>
          <strong>질문 · {turn.question}</strong>
          {turn.response.status !== "ANSWERED" && <small className="dk-agent-response-state">{turn.response.status === "UNAVAILABLE" ? "Agent 응답 실패 · 입력란에서 다시 시도할 수 있습니다." : "분석 근거 부족"}</small>}
          <p className="dk-agent-answer">{turn.response.answer}</p>
          {index === (compact ? 0 : turns.length - 1) && (turn.response.follow_ups?.length ?? 0) > 0 && (
            <div className="dk-agent-followups" aria-label="이어서 물어볼 질문">
              {turn.response.follow_ups!.map((item) => <button key={item} type="button" disabled={busy} onClick={() => void ask(item)}>{item}</button>)}
            </div>
          )}
          <div className="dk-tools">{turn.response.tool_calls.map((call) => <em key={call.order}>[{call.order}] {call.tool_name}</em>)}</div>
          {turn.response.tool_calls.map((call) => (
            <details className="dk-agent-evidence" key={call.order}>
              <summary>[{call.order}] {call.tool_name} · 호출 결과 보기</summary>
              {call.reason && <small className="dk-note">선택 이유 · {call.reason}</small>}
              {Object.keys(call.parameters).length > 0 && <small className="dk-note">입력 · {JSON.stringify(call.parameters)}</small>}
              <Findings workflow={call.tool_name === "analyze_hand_threshold" ? "hand_threshold" : call.tool_name === "analyze_closure_timing" ? "closure_timing" : call.tool_name === "analyze_inflow_delay" ? "inflow_delay" : call.tool_name === "get_exposure_inventory" ? "exposure_inventory" : "situation"} result={call.result} />
              {typeof call.result.coverage_note === "string" && <small className="dk-note">{call.result.coverage_note}</small>}
              {Array.isArray(call.result.limitations) && (call.result.limitations as string[]).slice(0, 3).map((item) => <small key={item} className="dk-note">한계 · {item}</small>)}
              <details className="dk-agent-raw"><summary>도구 원본 데이터</summary><pre>{JSON.stringify(call.result, null, 2)}</pre></details>
            </details>
          ))}
          {turn.response.limitations.map((item) => <small key={item} className="dk-note">제한 · {item}</small>)}
        </div>
      ))}
      {error && <small className="dk-error">{error}</small>}
    </div>
  );
}

const rows = (result: Record<string, unknown>, key: string) => (Array.isArray(result[key]) ? (result[key] as Array<Record<string, unknown>>) : []);

function Findings({ workflow, result }: { workflow: AgentWorkflowName | "hand_threshold"; result: Record<string, unknown> }) {
  if (workflow === "hand_threshold") {
    const stages = rows(result, "stages");
    return <table className="dk-table"><thead><tr><th>단계</th><th>기준 셀</th><th>변경 후</th><th>제외</th></tr></thead><tbody>{stages.map((stage) => <tr key={String(stage.stage_index)}><td>{clock(String(stage.time))}</td><td>{String(stage.baseline_cell_count)}</td><td>{String(stage.scenario_cell_count)}</td><td>{String(stage.removed_cell_count)}</td></tr>)}</tbody></table>;
  }
  if (workflow === "closure_timing") {
    const scenarios = rows(result, "scenarios");
    return scenarios.length ? (
      <div className="dk-findings-stack">
        <table className="dk-table">
          <thead><tr><th>통제 가정</th><th>유입까지</th><th>주행불능까지</th><th>완전침수까지</th></tr></thead>
          <tbody>{scenarios.map((row) => (
            <tr key={String(row.closure_time)}><td>{clock(String(row.closure_time))}</td><td>{String(row.minutes_before_underpass_inflow)}분</td><td>{String(row.minutes_before_unsafe_driving)}분</td><td>{String(row.minutes_before_full_inundation)}분</td></tr>
          ))}</tbody>
        </table>
        <small>통제 이후 신규 진입 차단을 가정한 시간 비교입니다. 실제 차량·사상자 감소는 계산하지 않습니다.</small>
      </div>
    ) : null;
  }
  if (workflow === "inflow_delay") {
    const scenarios = rows(result, "scenarios");
    return scenarios.length ? (
      <div className="dk-findings-stack">{scenarios.map((scenario) => (
        <table className="dk-table" key={String(scenario.delay_minutes)}>
          <thead><tr><th colSpan={3}>유입 {String(scenario.delay_minutes)}분 지연 가정</th></tr></thead>
          <tbody>{(Array.isArray(scenario.milestones) ? (scenario.milestones as Array<Record<string, unknown>>) : []).map((m) => (
            <tr key={String(m.state)}><td>{String(m.label ?? m.state)}</td><td>{clock(String(m.baseline_time))}</td><td>→ {clock(String(m.shifted_time))}</td></tr>
          ))}</tbody>
        </table>
      ))}</div>
    ) : null;
  }
  if (workflow === "exposure_inventory") {
    const rings = rows(result, "rings");
    return rings.length ? (
      <table className="dk-table">
        <thead><tr><th>반경</th><th>건물</th><th>도로</th><th>시설</th></tr></thead>
        <tbody>{rings.map((ring) => <tr key={String(ring.radius_m)}><td>{String(ring.radius_m)} m</td><td>{Number(ring.buildings).toLocaleString()}동</td><td>{String(ring.roads_km)} km</td><td>{String(ring.facilities)}</td></tr>)}</tbody>
      </table>
    ) : null;
  }
  const replay = rows(result, "replay");
  return replay.length ? (
    <table className="dk-table">
      <thead><tr><th>시각</th><th>상태</th><th>근거</th></tr></thead>
      <tbody>{replay.map((step) => <tr key={String(step.time)}><td>{clock(String(step.time))}</td><td>{String(step.label ?? step.state)}</td><td>{String(step.confidence ?? "-")}</td></tr>)}</tbody>
    </table>
  ) : null;
}
