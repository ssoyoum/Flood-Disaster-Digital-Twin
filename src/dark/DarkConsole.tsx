import { useEffect, useMemo, useRef, useState, type Dispatch, type PointerEvent as ReactPointerEvent, type SetStateAction } from "react";
import maplibregl, { type GeoJSONSource, type MapLayerMouseEvent } from "maplibre-gl";
import * as api from "../api";
import CrossSection from "./CrossSection";
import type {
  AgentIntentPlanResult,
  AgentWorkflowName,
  AgentWorkflowResult,
  DataStatusResponse,
  ExposureMetrics,
  FloodEvent,
  GeoJson,
  LayersResponse,
  ReconstructionResponse,
} from "../types";
import "./dark.css";

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
const QUICK_REQUESTS = [
  { label: "08:25 차단", message: "08:25에 지하차도를 차단했으면?" },
  { label: "10분 유입 지연", message: "차수벽으로 유입이 10분 지연되면?" },
  { label: "500m 재고", message: "지하차도 500m 안에 무엇이 있어?" },
] as const;

const clock = (value?: string | null) => (value && value.length >= 16 ? value.slice(11, 16) : "--:--");
const num = (value: number | null | undefined) => (typeof value === "number" ? value.toLocaleString() : "—");
const dec = (value: number | null | undefined, digits = 1) => (typeof value === "number" ? value.toFixed(digits) : "—");
const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
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
  onSwitchBack,
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
  onSwitchBack: () => void;
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
      // 하천은 넓은 흐린 선을 아래에 깔아 물빛이 번지는 느낌을 낸다.
      map.addLayer({ id: "waterways-glow", type: "line", source: "waterways", paint: { "line-color": "#38bdf8", "line-width": 16, "line-blur": 12, "line-opacity": 0.28 } });
      map.addLayer({ id: "waterways-fill", type: "fill", source: "waterways", paint: { "fill-color": "#1d6fa5", "fill-opacity": 0.45 } });
      map.addLayer({ id: "waterways-line", type: "line", source: "waterways", paint: { "line-color": "#7dd3fc", "line-width": 1.2, "line-opacity": 0.9 } });
      // HAND 재구성 envelope: 현재 단계 셀만. 기준 시나리오는 붉게, 개입 시나리오는 청록으로.
      map.addLayer({
        id: "hand-glow", type: "line", source: "hand_reconstruction",
        filter: ["all", ["==", ["geometry-type"], "Polygon"], ["==", ["get", "stage_index"], time]],
        paint: { "line-color": "#f87171", "line-width": 10, "line-blur": 8, "line-opacity": 0.22 },
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
      map.addLayer({ id: "underpass-glow", type: "line", source: "underpass", paint: { "line-color": "#ff3b30", "line-width": 18, "line-blur": 10, "line-opacity": 0.35 } });
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
          .setHTML(cardHtml(String(props.label ?? "HAND 재구성 셀"), [
            ["단계", props.state], ["HAND", `${props.hand_m ?? "?"} m`], ["임계", `${props.hand_threshold_m ?? "?"} m`],
            ["관측 수위", `${props.observed_water_level_m ?? "?"} m`], ["상태", `${props.status} · 공식 침수범위 아님`],
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
    for (const id of ["hand-glow", "hand-fill"]) { if (map.getLayer(id)) map.setFilter(id, stageFilter("Polygon")); }
    if (map.getLayer("hand-flow")) map.setFilter("hand-flow", stageFilter("LineString"));
    if (map.getLayer("hand-glow")) map.setPaintProperty("hand-glow", "line-color", color);
    if (map.getLayer("hand-fill")) map.setPaintProperty("hand-fill", "fill-color", color);
  }, [ready, time, scenario]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const groups: Partial<Record<LayerKey, string[]>> = {
      aoi: ["aoi-line"], buildings: ["buildings-fill"], roads: ["roads-line"],
      waterways: ["waterways-glow", "waterways-fill", "waterways-line"],
      hand_reconstruction: ["hand-glow", "hand-fill", "hand-flow"], underpass: ["underpass-glow", "underpass-line"],
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
    aoi: "행정경계(AOI)", roads: "도로", buildings: "건축물", waterways: "하천", terrain: "저지대", approx_flood_envelope: "근사 envelope",
    hand_reconstruction: "HAND 재구성 envelope", facilities: "시설", underpass: eventData.focus_feature, flood_extent: "공식 침수범위",
  };

  return (
    <div className="dk-root" style={{ ["--tone" as string]: tone, ["--dk-left-width" as string]: `${panelWidths.left}px`, ["--dk-right-width" as string]: `${panelWidths.right}px` }}>
      <header className="dk-topbar">
        <div className="dk-brand">
          <span className="dk-brand-mark">▲</span>
          <div>
            <h1>{eventData.name}</h1>
            <p>FLOOD DECISION DIGITAL TWIN · {eventData.location}</p>
          </div>
        </div>
        <nav className="dk-view-tabs" aria-label="FloodOps 화면">
          <button type="button" className={view === "console" ? "active" : ""} onClick={() => setView("console")}>관제 화면</button>
          <button type="button" className={view === "compare" ? "active" : ""} onClick={() => setView("compare")}>Scenario 비교</button>
          <button type="button" className={view === "insights" ? "active" : ""} onClick={() => setView("insights")}>인사이트</button>
        </nav>
        <div className="dk-header-agent">
          <div className="dk-header-agent-title"><span><strong>FLOOD AGENT</strong><small>근거 기반 조치 질의</small></span></div>
          <AgentDock eventId={eventData.id} compact />
        </div>
        <div className="dk-topbar-right">
          <span className="dk-clock">{now.toLocaleDateString("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit" })} {now.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })} KST</span>
          <button type="button" onClick={onSwitchBack}>기존 UI</button>
        </div>
      </header>

      {view === "console" ? <div className="dk-body">
        <aside className="dk-side">
          <div className="dk-side-head"><p>Incident replay</p><h2>사건 단계 · {stages.length}단계</h2></div>
          <section className="dk-priority" aria-label="판단 우선순위">
            <div className="dk-priority-head"><p>Decision priority</p><span>자료 우선순위</span></div>
            <ol>
              <li className="primary"><b>01 · 대응 시점</b><span>{current ? `${clock(current.time)} ${current.label}` : "현재 단계 확인"} · 여유 {reconstruction?.baseline.inflow_to_unsafe_min ?? "—"}분</span></li>
              <li><b>02 · 공간 상태</b><span>지하차도 중심 HAND 재구성 · 임시/근사 자료</span></li>
            </ol>
            <small>시간과 현재 시설 상태가 즉시 대응 판단에 가장 중요합니다. 반경별 재고는 Agent에서 필요할 때 조회합니다.</small>
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
              <span><p>Layers</p><b>지도 레이어 표시 설정</b></span><strong>{layersOpen ? "닫기" : "열기"}</strong>
            </button>
            {layersOpen && <div className="dk-layer-list">
              {layerRows.map((key) => (
                <label key={key} className="dk-toggle">
                  <input type="checkbox" checked={visible[key]} onChange={(event) => setVisible((state) => ({ ...state, [key]: event.target.checked }))} />
                  <span>{layerNames[key]} <small>{num(layers[key].feature_count)} · {layers[key].status}</small></span>
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
            <p>Legend</p>
            <span><i style={{ background: scenario === "intervention" ? "#2dd4bf" : "#f87171" }} />HAND 재구성 envelope (임시·근사)</span>
            <span><i style={{ background: "#38bdf8" }} />하천</span>
            <span><i style={{ background: "#ff6b6b" }} />{eventData.focus_feature}</span>
            <span><i style={{ background: "#3b4a63" }} />건축물</span>
          </div>
          <div className="dk-hint">← → 단계 이동 · 스페이스 재생 · 지하차도 마커나 envelope 셀을 누르면 카드가 열립니다</div>
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
          <div className="dk-detail-head"><p>Evidence & HAND section</p><h2>관측 근거 · {eventData.focus_feature} 단면</h2></div>
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

function ScenarioMap({
  layers,
  reconstruction,
  time,
  mode,
  title,
}: {
  layers: LayersResponse;
  reconstruction: ReconstructionResponse;
  time: number;
  mode: ScenarioMode;
  title: string;
}) {
  const elementRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const [ready, setReady] = useState(false);
  const center = useMemo(() => centerOf(layers.underpass.data), [layers.underpass.data]);
  const current = reconstruction.replay[time];
  const color = mode === "intervention" ? "#2dd4bf" : "#f87171";
  const closureActive = mode === "intervention" && replaySeverity(current?.state) >= 5;

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
    map.on("load", () => {
      const add = (key: LayerKey) => map.addSource(key, { type: "geojson", data: layers[key].data as never });
      add("aoi"); add("waterways"); add("roads"); add("buildings"); add("hand_reconstruction"); add("underpass");
      map.addLayer({ id: "aoi-line", type: "line", source: "aoi", paint: { "line-color": "#22d3ee", "line-width": 1, "line-dasharray": [3, 3], "line-opacity": 0.5 } });
      map.addLayer({ id: "buildings-fill", type: "fill", source: "buildings", paint: { "fill-color": "#3b4a63", "fill-opacity": 0.52 } });
      map.addLayer({ id: "roads-line", type: "line", source: "roads", paint: { "line-color": "#64748b", "line-width": 0.8, "line-opacity": 0.42 } });
      map.addLayer({ id: "waterways-glow", type: "line", source: "waterways", paint: { "line-color": "#38bdf8", "line-width": 13, "line-blur": 8, "line-opacity": 0.2 } });
      map.addLayer({ id: "waterways-line", type: "line", source: "waterways", paint: { "line-color": "#7dd3fc", "line-width": 1.1, "line-opacity": 0.82 } });
      map.addLayer({ id: "hand-glow", type: "line", source: "hand_reconstruction", filter: ["all", ["==", ["geometry-type"], "Polygon"], ["==", ["get", "stage_index"], time]], paint: { "line-color": color, "line-width": 9, "line-blur": 7, "line-opacity": 0.22 } });
      map.addLayer({ id: "hand-fill", type: "fill", source: "hand_reconstruction", filter: ["all", ["==", ["geometry-type"], "Polygon"], ["==", ["get", "stage_index"], time]], paint: { "fill-color": color, "fill-opacity": 0.28 } });
      map.addLayer({ id: "hand-flow", type: "line", source: "hand_reconstruction", filter: ["all", ["==", ["geometry-type"], "LineString"], ["==", ["get", "stage_index"], time]], paint: { "line-color": "#fbbf24", "line-width": 2.5, "line-dasharray": [1.2, 0.8], "line-opacity": 0.85 } });
      map.addLayer({ id: "underpass-glow", type: "line", source: "underpass", paint: { "line-color": color, "line-width": closureActive ? 16 : 12, "line-blur": 8, "line-opacity": 0.3 } });
      map.addLayer({ id: "underpass-line", type: "line", source: "underpass", paint: { "line-color": color, "line-width": closureActive ? 7 : 5, "line-opacity": 0.95 } });
      setReady(true);
      window.requestAnimationFrame(() => map.resize());
    });
    mapRef.current = map;
    return () => { markerRef.current?.remove(); map.remove(); mapRef.current = null; };
    // 비교 지도는 최초 1회 초기화하고, 데이터·단계는 아래 효과에서 갱신한다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const polygonFilter = ["all", ["==", ["geometry-type"], "Polygon"], ["==", ["get", "stage_index"], time]] as never;
    const lineFilter = ["all", ["==", ["geometry-type"], "LineString"], ["==", ["get", "stage_index"], time]] as never;
    if (map.getLayer("hand-glow")) map.setFilter("hand-glow", polygonFilter);
    if (map.getLayer("hand-fill")) map.setFilter("hand-fill", polygonFilter);
    if (map.getLayer("hand-flow")) map.setFilter("hand-flow", lineFilter);
    if (map.getLayer("hand-glow")) map.setPaintProperty("hand-glow", "line-color", color);
    if (map.getLayer("hand-fill")) map.setPaintProperty("hand-fill", "fill-color", color);
    if (map.getLayer("underpass-glow")) {
      map.setPaintProperty("underpass-glow", "line-color", color);
      map.setPaintProperty("underpass-glow", "line-width", closureActive ? 16 : 12);
    }
    if (map.getLayer("underpass-line")) {
      map.setPaintProperty("underpass-line", "line-color", color);
      map.setPaintProperty("underpass-line", "line-width", closureActive ? 7 : 5);
    }
  }, [ready, time, color, closureActive]);

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
    marker.style.setProperty("--tone", color);
    marker.innerHTML = `<i></i>`;
    markerRef.current = new maplibregl.Marker({ element: marker, anchor: "center" }).setLngLat(center).addTo(map);
  }, [ready, center, color]);

  return (
    <section className={`dk-compare-map-card ${mode}`} aria-label={`${title} 지도`}>
      <div className="dk-compare-map-head">
        <div><span className="dk-compare-card-label"><i />{title}</span><strong>{current ? `${clock(current.time)} · ${current.label}` : "재구성 단계 없음"}</strong></div>
        <small>{closureActive ? "신규 차량 진입 차단" : "원시 위험 진행"}</small>
      </div>
      <div className="dk-compare-map"><div ref={elementRef} /></div>
      <div className="dk-compare-map-foot"><span><i className="hand" />{mode === "baseline" ? "HAND 위험 envelope" : "개입 시나리오 강조"}</span><span><i className="road" />공통 공간 레이어</span></div>
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
      {compact && <div className="dk-detail-head dk-evidence-section-head"><p>Evidence & HAND section</p><h2>관측 근거 · {eventData.focus_feature} 단면</h2></div>}
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
      <dl className="dk-evidence-list" aria-label="관측 근거">
        <div><dt>강우 피크</dt><dd>{dec(summary?.rainfall_peak_mm_per_hour)} mm/h <small>{clock(summary?.rainfall_peak_timestamp)} · {summary?.rainfall_peak_station_name ?? "KMA"}</small></dd></div>
        <div><dt>수위 피크</dt><dd>{dec(summary?.water_level_peak_m, 2)} m <small>{clock(summary?.water_level_peak_timestamp)} · {summary?.water_level_peak_station_name ?? "홍수통제소"}</small></dd></div>
        <div><dt>관측 기간</dt><dd>{dataStatus?.rainfall?.period ?? "—"}</dd></div>
        <div><dt>공식 침수범위</dt><dd className="dk-pending">{String(summary?.flooded_area_km2 ?? "PENDING")}</dd></div>
      </dl>
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
          <p>Decision intelligence</p>
          <h2>인사이트 · 데이터 해석과 다음 조치</h2>
          <span>{eventData.name}의 현재 위험을 어떻게 읽고, 어떤 근거로 다음 조치를 선택하는지 정리합니다.</span>
        </div>
        <button type="button" className="dk-compare-back" onClick={onBack}>관제 화면으로</button>
      </div>

      <div className="dk-insight-kpis">
        <div><span>현재 단계</span><strong>{current ? `${clock(current.time)} · ${current.label}` : "—"}</strong><small>Replay 기준 {time + 1}단계</small></div>
        <div><span>판단 우선순위</span><strong>시간 · 시설 상태</strong><small>반경 재고는 보조 근거</small></div>
        <div><span>대응 여유</span><strong>{reconstruction ? `${reconstruction.baseline.inflow_to_unsafe_min}분` : "—"}</strong><small>관측 재현 기준</small></div>
        <div><span>공식 침수범위</span><strong className="pending">{String(officialExtent ?? "PENDING")}</strong><small>공식 vector 확보 전</small></div>
      </div>

      <div className="dk-insight-grid">
        <article className="dk-insight-card priority">
          <div className="dk-insight-label"><i />01 · 판단 우선순위</div>
          <h3>무엇을 먼저 봐야 하는가</h3>
          <p>관제 담당자는 현재 단계와 지하차도 상태를 먼저 확인하고, 그 다음 공간 위험과 노출 재고를 확인합니다.</p>
          <ol>
            <li><b>01</b><span><strong>대응 시점</strong> {current ? `${clock(current.time)} ${current.label}` : "현재 단계 확인"}</span></li>
            <li><b>02</b><span><strong>공간 상태</strong> HAND 재구성 envelope · 임시/근사</span></li>
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
            <div><dt>대리 표현</dt><dd>단면 수면 · Replay 위험 진행</dd></div>
          </dl>
        </article>

        <article className="dk-insight-card engineering">
          <div className="dk-insight-label"><i />03 · 데이터 엔지니어링</div>
          <h3>오늘 조정한 데이터 흐름</h3>
          <p>화면에 값을 직접 넣지 않고 API 응답을 공통 계약으로 묶어 지도·단면·시나리오가 같은 데이터를 바라보게 했습니다.</p>
          <div className="dk-insight-tags"><span>API typed response</span><span>layer provenance</span><span>replay timeline</span><span>5173 / 8033 fixed</span></div>
          <small>레이어 메타데이터: {layers.hand_reconstruction.status} · {layers.hand_reconstruction.source_type ?? "source not recorded"}</small>
        </article>

        <article className="dk-insight-card scenario">
          <div className="dk-insight-label"><i />04 · 개입 해석</div>
          <h3>개입은 운영 상태를 바꾼다</h3>
          <p>선택 시나리오는 같은 사건 진행 위에서 감지 후 신규 차량 진입을 차단합니다. 현재 모델만으로 물이 차오르는 속도나 침수범위가 감소했다고 말하지 않습니다.</p>
          <div className="dk-insight-compare"><span className="base">원시나리오<br /><b>관측 재현</b></span><em>→</em><span className="intervention">선택 시나리오<br /><b>자동 차단</b></span></div>
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

function ScenarioComparePage({
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
}: {
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
}) {
  const states = reconstruction?.baseline.states ?? [];
  const inflow = states.find((item) => item.state === "underpass_inflow");
  const unsafe = states.find((item) => item.state === "unsafe_driving");
  const full = states.find((item) => item.state === "full_inundation");
  const intervention = reconstruction?.intervention;
  const current = reconstruction?.replay[time];
  const tone = STAGE_TONE[current?.state ?? ""] ?? "#38bdf8";

  if (!reconstruction || !intervention) {
    return <main className="dk-compare dk-compare-empty"><strong>Scenario 비교 데이터를 불러오지 못했습니다.</strong><button type="button" onClick={onBack}>관제 화면으로 돌아가기</button></main>;
  }

  return (
    <main className="dk-compare">
      <div className="dk-compare-head">
        <div>
          <p>Counterfactual response analysis</p>
          <h2>{eventData.focus_feature} 원시나리오 vs 개입 시나리오</h2>
          <span>같은 2023 오송 사건 조건에서 진입 차단 조치만 바꿔 대응 가능 시간을 비교합니다.</span>
        </div>
        <button type="button" className="dk-compare-back" onClick={onBack}>관제 화면으로</button>
      </div>

      <div className="dk-compare-replay">
        <div className="dk-compare-replay-label"><span>Incident replay</span><strong>{current ? `${clock(current.time)} · ${current.label}` : "재구성 단계 없음"}</strong></div>
        <button type="button" aria-label="이전 단계" title="이전 단계" disabled={time <= 0} onClick={() => { setPlaying(false); setTime((index) => Math.max(0, index - 1)); }}>‹</button>
        <button type="button" className="primary" disabled={!reconstruction.replay.length} onClick={onTogglePlayback}>{playing ? "❚❚ 일시정지" : "▶ 재생"}</button>
        <button type="button" aria-label="다음 단계" title="다음 단계" disabled={time >= reconstruction.replay.length - 1} onClick={() => { setPlaying(false); setTime((index) => Math.min(reconstruction.replay.length - 1, index + 1)); }}>›</button>
        <input type="range" min={0} max={Math.max(0, reconstruction.replay.length - 1)} value={time} onChange={(event) => { setPlaying(false); setTime(Number(event.target.value)); }} />
        <span>{reconstruction.replay.length ? `${time + 1} / ${reconstruction.replay.length}` : "—"}</span>
      </div>

      <section className="dk-compare-panel dk-compare-stage-panel">
        <div className="dk-compare-panel-head"><p>Spatial comparison</p><span>두 시나리오는 같은 사건 단계, 오른쪽 Evidence는 현재 단계를 고정 표시</span></div>
        <div className="dk-compare-stage-grid">
          <ScenarioMap layers={layers} reconstruction={reconstruction} time={time} mode="baseline" title="원시나리오" />
          <ScenarioMap layers={layers} reconstruction={reconstruction} time={time} mode="intervention" title="선택 시나리오" />
          <aside className="dk-compare-evidence">
            <EvidenceHandSection eventData={eventData} layers={layers} summary={summary} dataStatus={dataStatus} reconstruction={reconstruction} time={time} tone="#2dd4bf" compact />
          </aside>
        </div>
        <small className="dk-compare-map-note">두 지도는 같은 Replay 시점을 공유합니다. 선택 시나리오의 색상·차단 상태는 운영 규칙을 표현하며, 공식 침수범위나 수리모형 결과가 아닙니다.</small>
      </section>

      <div className="dk-compare-cards">
        <section className="dk-compare-card baseline">
          <div className="dk-compare-card-label"><i />원시나리오 · 관측 재현</div>
          <h3>{reconstruction.baseline.name}</h3>
          <p>{reconstruction.baseline.description}</p>
          <dl>
            <div><dt>유입 시작</dt><dd>{inflow ? `${clock(inflow.time)} · ${inflow.underpass_status}` : "—"}</dd></div>
            <div><dt>주행불능까지</dt><dd>{reconstruction.baseline.inflow_to_unsafe_min}분</dd></div>
            <div><dt>완전침수까지</dt><dd>{reconstruction.baseline.inflow_to_full_inundation_min}분</dd></div>
          </dl>
        </section>
        <section className="dk-compare-card intervention">
          <div className="dk-compare-card-label"><i />개입 시나리오 · 감지 자동차단</div>
          <h3>{intervention.name}</h3>
          <p>{intervention.closure_action}</p>
          <dl>
            <div><dt>개입 트리거</dt><dd>{clock(intervention.trigger_time)} · {intervention.trigger}</dd></div>
            <div><dt>확보 대응 여유</dt><dd>{intervention.available_response_window_min}분</dd></div>
            <div><dt>완전침수까지</dt><dd>{intervention.time_until_full_inundation_min}분</dd></div>
          </dl>
        </section>
      </div>

      <section className="dk-compare-panel">
        <div className="dk-compare-panel-head"><p>Comparison matrix</p><span>무엇이 바뀌고, 무엇이 바뀌지 않는가</span></div>
        <table className="dk-compare-table">
          <thead><tr><th>항목</th><th>원시나리오</th><th>개입 시나리오</th><th>판정</th></tr></thead>
          <tbody>
            <tr><th>사건 진행</th><td>{inflow ? `${clock(inflow.time)} 유입 → ${clock(unsafe?.time)} 주행불능 → ${clock(full?.time)} 완전침수` : "관측 재생"}</td><td>동일한 사건 timeline</td><td className="dk-compare-muted">위험 진행 자체는 변경하지 않음</td></tr>
            <tr><th>지하차도 상태</th><td>{inflow?.underpass_status ?? "open"} → {unsafe?.underpass_status ?? "unsafe"}</td><td>{clock(intervention.trigger_time)} 이후 신규 차량 진입 차단</td><td className="dk-compare-good">대응 상태 변경</td></tr>
            <tr><th>유입 후 주행불능</th><td>{reconstruction.baseline.inflow_to_unsafe_min}분</td><td>{reconstruction.baseline.inflow_to_unsafe_min}분</td><td className="dk-compare-muted">수리·유량 모델이 없어 동일</td></tr>
            <tr><th>유입 후 완전침수</th><td>{reconstruction.baseline.inflow_to_full_inundation_min}분</td><td>{intervention.time_until_full_inundation_min}분</td><td className="dk-compare-muted">침수 진행을 바꾼 결과가 아님</td></tr>
            <tr><th>근거 수준</th><td>관측/사건 재구성</td><td>{intervention.result_status}</td><td className="dk-compare-warn">물리 시뮬레이션 아님</td></tr>
          </tbody>
        </table>
      </section>

      <div className="dk-compare-callout">
        <strong>핵심 인사이트</strong>
        <span>이 개입은 물이 차오르는 속도나 침수범위를 줄였다고 말하는 모델이 아닙니다. {clock(intervention.trigger_time)}에 신규 진입을 막아, 같은 위험 진행 안에서 대응 상태를 바꾸는 규칙 기반 비교입니다.</span>
      </div>
      <small className="dk-compare-limit">근거: {intervention.trigger_basis} · {intervention.estimated_effect} · 공식 피해 감소율/사상자/실제 침수심은 산출하지 않습니다.</small>
    </main>
  );
}

/* ------------------------------------------------------------------ */
/* Agent — 자연어 → 계획 → 실행 → 결과. 수치는 전부 도구 결과다.               */
/* ------------------------------------------------------------------ */

function AgentDock({ eventId, compact = false }: { eventId: string; compact?: boolean }) {
  const [message, setMessage] = useState("");
  const [plan, setPlan] = useState<AgentIntentPlanResult | null>(null);
  const [result, setResult] = useState<AgentWorkflowResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const planIntent = async () => {
    if (!message.trim()) return;
    setBusy(true); setError(null); setResult(null);
    try { setPlan(await api.planAgentIntent(eventId, message.trim())); }
    catch { setError("Agent planner API를 호출하지 못했습니다."); }
    finally { setBusy(false); }
  };
  const run = async () => {
    if (!plan?.workflow) return;
    setBusy(true); setError(null);
    try {
      const { event_id: _ignored, ...parameters } = plan.parameters;
      void _ignored;
      setResult(await api.runAgentWorkflow(eventId, plan.workflow, parameters));
    } catch { setError("계획된 workflow를 실행하지 못했습니다."); }
    finally { setBusy(false); }
  };

  const status = busy ? "처리 중…" : result ? "다 됐습니다 — 결과와 근거를 아래에 표시했어요" : plan ? (plan.status === "READY" ? "계획이 준비됐습니다. 실행하세요" : plan.status === "UNSUPPORTED" ? "등록된 도구로 답할 수 없는 요청입니다" : "어느 분석인지 하나만 골라 다시 물어보세요") : "예: 08:25에 지하차도를 차단했으면?";

  return (
    <div className={`dk-agent${compact ? " dk-agent-compact" : ""}`}>
      <div className="dk-agent-head"><p>Agent workflow</p><span className={`dk-agent-badge ${plan?.planner_used ?? ""}`}>{plan ? (plan.planner_used === "llm" ? "LLM PLAN" : "DETERMINISTIC PLAN") : "READY"}</span></div>
      {!compact && <div className="dk-agent-intro">자연어 질문을 등록된 분석 도구로 연결합니다. 결과 수치는 API 도구가 계산합니다.</div>}
      {!compact && <div className="dk-agent-suggestions" aria-label="추천 질문">
        {QUICK_REQUESTS.map((item) => <button key={item.label} type="button" onClick={() => { setMessage(item.message); setPlan(null); setResult(null); setError(null); }}>{item.label}</button>)}
      </div>}
      <form className="dk-agent-bar" onSubmit={(event) => { event.preventDefault(); void planIntent(); }}>
        <input aria-label="Agent request" value={message} onChange={(event) => setMessage(event.target.value)} placeholder="예: 08:25에 지하차도를 차단했으면?" />
        <button type="submit" disabled={busy || !message.trim()}>계획</button>
        <button type="button" disabled={busy || plan?.status !== "READY" || !plan?.workflow} onClick={() => void run()}>실행</button>
      </form>
      <small className="dk-agent-status" aria-live="polite">{status}</small>
      {plan && (!compact || !result) && (
        <div className={`dk-plan ${plan.status.toLowerCase()}`}>
          <b>{plan.status} · {plan.workflow ?? "workflow 없음"}</b>
          <span>{plan.reason}</span>
          {plan.tool_names.length > 0 && <div className="dk-tools">{plan.tool_names.map((tool, index) => <em key={tool}>{index + 1}. {tool}</em>)}</div>}
          {plan.planner_note && <small>{plan.planner_note}</small>}
        </div>
      )}
      {result && (
        <div className="dk-result">
          <div className="dk-tools">{result.tool_calls.map((call) => <em key={call.order}>{call.order}. {call.tool_name}</em>)}</div>
          <Findings workflow={result.workflow} result={result.result} />
          {result.coverage_note && <small className="dk-note">coverage · {result.coverage_status} · {result.coverage_note}</small>}
          {Array.isArray(result.result.limitations) && (result.result.limitations as string[]).slice(0, 3).map((item) => <small key={item} className="dk-note">한계 · {item}</small>)}
        </div>
      )}
      {error && <small className="dk-error">{error}</small>}
    </div>
  );
}

const rows = (result: Record<string, unknown>, key: string) => (Array.isArray(result[key]) ? (result[key] as Array<Record<string, unknown>>) : []);

function Findings({ workflow, result }: { workflow: AgentWorkflowName; result: Record<string, unknown> }) {
  if (workflow === "closure_timing") {
    const scenarios = rows(result, "scenarios");
    return scenarios.length ? (
      <table className="dk-table">
        <thead><tr><th>차단</th><th>유입까지</th><th>주행불능</th><th>완전침수</th><th>감지차단 대비</th></tr></thead>
        <tbody>{scenarios.map((row) => (
          <tr key={String(row.closure_time)}><td>{clock(String(row.closure_time))}</td><td>{String(row.minutes_before_underpass_inflow)}분</td><td>{String(row.minutes_before_unsafe_driving)}분</td><td>{String(row.minutes_before_full_inundation)}분</td><td>{String(row.lead_time_vs_detection_trigger_min)}분</td></tr>
        ))}</tbody>
      </table>
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
