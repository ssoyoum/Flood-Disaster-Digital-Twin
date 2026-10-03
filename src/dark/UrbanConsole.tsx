import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import maplibregl, { type MapLayerMouseEvent } from "maplibre-gl";
import * as api from "../api";
import type { AlertTimingResult, FloodEvent, LayersResponse, StorageCaptureResult, UrbanReconstructionResponse } from "../types";
import { AgentDock } from "./DarkConsole";
import { FloodOpsLogo } from "./Landing";
import { CONFIDENCE_KO, ROLE_KO, localizeEvent, stageKo } from "./ko";
import "./dark.css";
import "./urban.css";

/*
 * 강우형 도시 침수 관제 화면 (2022 서울 도림천 유역).
 *
 * 오송 화면과 달리 제방·지하차도·HAND 추정 범위가 없다. 지도에는 사건 뒤 조사된 공식 침수흔적을 그대로 올리고,
 * 시간축은 강우계 관측과 보도된 사건 시각으로 재생한다. 흔적에는 시각 정보가 없으므로 단계에 따라 넓히지 않는다.
 * 반사실 비교는 백엔드 계산(경보 시각 산술, 저류량 산술)을 그대로 보여준다.
 */

type View = "console" | "compare";
type LayerKey = "flood_extent" | "buildings" | "roads" | "waterways" | "aoi";

const ESRI = "https://services.arcgisonline.com/ArcGIS/rest/services/Canvas";
const DATA_ATTRIBUTION = [
  "침수흔적 © 서울특별시",
  "건축물 © 국토교통부 GIS건물통합정보",
  "도로·하천 © OpenStreetMap contributors",
];

const STAGE_TONE: Record<string, string> = {
  rain_warning: "#60a5fa",
  heavy_rain: "#38bdf8",
  design_exceeded: "#fbbf24",
  rescue_call: "#ef4444",
  public_alert: "#fb923c",
  national_escalation: "#f97316",
  responders_arrive: "#b91c1c",
};

// The API keeps English descriptions; the console shows these Korean ones.
const STAGE_NOTE_KO: Record<string, { description: string; source: string }> = {
  rain_warning: { description: "서울 서남권(관악·동작·영등포·구로 등) 호우주의보가 경보로 격상됐습니다.", source: "기상청 발표 (이데일리 2022-08-08 보도)" },
  heavy_rain: { description: "신림P 강우계의 60분 누적 강우가 처음 50 mm에 닿았습니다. 오후 한때의 집중호우입니다.", source: "서울시 10분 강우계 신림P(2302), 60분 이동합" },
  design_exceeded: { description: "신림P 60분 강우가 2022년 이전 서울 방재성능목표(시간당 95 mm, 30년 빈도)를 넘었습니다.", source: "서울시 10분 강우계 신림P · 방재성능목표는 서울시 발표(뉴시스 2022-08-10 보도)" },
  rescue_call: { description: "신림동 반지하 주택 침수로 112 신고 8건 중 첫 신고가 들어왔습니다. 신림P 60분 강우 최대값(121.5 mm)도 같은 시각에 끝납니다. 중대본 상황보고(8.9 06시)는 관악 반지하 사고를 '21:07경'으로 적었는데, 신고 시각인지 사망 시각인지는 밝히지 않았습니다.", source: "한국일보 2022-08-09 (구 단위 정보만 사용) · 중대본 상황보고 21:07경" },
  public_alert: { description: "서울시가 저지대 침수 관련 첫 재난문자를 보냈습니다. 관악구는 21:21부터 문자를 보냈습니다.", source: "한국일보 2022-08-09" },
  national_escalation: { description: "중앙재난안전대책본부가 비상 2단계로, 위기경보를 주의에서 경계로 올렸습니다. 행안부 보도자료 원문은 '9시 30분'으로 오전·오후를 적지 않았고, 같은 날 1단계는 오전 7시 30분에 가동됐습니다.", source: "행정안전부 보도자료 2022-08-08 · 경향신문" },
  responders_arrive: { description: "첫 신고 뒤 약 46분 만에 소방이 신림동 현장에 도착했습니다.", source: "한국일보 2022-08-09" },
};

const DEPTH_COLOR = ["step", ["get", "flood_depth_m"], "#7dd3fc", 0.3, "#38bdf8", 0.5, "#2563eb", 0.8, "#7c3aed"] as const;
const BUILDING_DEPTH_COLOR = ["step", ["get", "max_trace_depth_m"], "#94a3b8", 0.3, "#fbbf24", 0.5, "#f97316", 0.8, "#ef4444"] as const;

const clock = (iso?: string | null) => (iso ? iso.slice(11, 16) : "—");
const num = (value?: number | null) => (value === null || value === undefined ? "—" : value.toLocaleString("ko-KR"));
const escapeHtml = (value: unknown) =>
  String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char] ?? char);

function cardHtml(title: string, rows: Array<[string, unknown]>, tone = "#38bdf8") {
  const body = rows.map(([key, value]) => `<div><dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value ?? "—")}</dd></div>`).join("");
  return `<div class="dk-card" style="--tone:${tone}"><b>${escapeHtml(title)}</b><dl>${body}</dl></div>`;
}

function minutesLabel(minutes: number | null | undefined) {
  if (minutes === null || minutes === undefined) return "—";
  const sign = minutes < 0 ? "-" : "";
  const abs = Math.abs(minutes);
  return abs >= 60 ? `${sign}${Math.floor(abs / 60)}시간 ${abs % 60}분` : `${sign}${abs}분`;
}

export default function UrbanConsole({ eventId }: { eventId: string }) {
  const [eventData, setEventData] = useState<FloodEvent | null>(null);
  const [layers, setLayers] = useState<LayersResponse | null>(null);
  const [reconstruction, setReconstruction] = useState<UrbanReconstructionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.getEvent(eventId), api.getLayers(eventId, 2022), api.getUrbanReconstruction(eventId)])
      .then(([nextEvent, nextLayers, nextReconstruction]) => {
        if (cancelled) return;
        const localized = localizeEvent(nextEvent);
        document.title = `${localized.name} | FloodOps`;
        setEventData(localized);
        setLayers(nextLayers);
        setReconstruction({
          ...nextReconstruction,
          replay: nextReconstruction.replay.map((step) => ({
            ...step,
            label: stageKo(step.state, step.label),
            role: ROLE_KO[step.role] ?? step.role,
            confidence: CONFIDENCE_KO[step.confidence] ?? step.confidence,
          })),
        });
      })
      .catch(() => setError("이 사례의 관제 데이터를 불러오지 못했습니다. 백엔드 API 연결을 확인하세요."));
    return () => { cancelled = true; };
  }, [eventId]);

  if (error) return <div className="app-state error-state"><strong>FloodOps를 불러오지 못했습니다</strong><span>{error}</span></div>;
  if (!eventData || !layers || !reconstruction) return <div className="app-state"><strong>관제 화면을 준비하는 중</strong></div>;
  return <UrbanConsoleView eventData={eventData} layers={layers} reconstruction={reconstruction} />;
}

function UrbanConsoleView({ eventData, layers, reconstruction }: { eventData: FloodEvent; layers: LayersResponse; reconstruction: UrbanReconstructionResponse }) {
  const [view, setView] = useState<View>("console");
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const stages = reconstruction.replay;
  const current = stages[time];
  const tone = STAGE_TONE[current?.state ?? ""] ?? "#38bdf8";

  useEffect(() => {
    if (!playing) return undefined;
    const timer = window.setInterval(() => {
      setTime((index) => {
        if (index + 1 >= stages.length) { setPlaying(false); return index; }
        return index + 1;
      });
    }, 1100);
    return () => window.clearInterval(timer);
  }, [playing, stages.length]);

  const step = (delta: number) => { setPlaying(false); setTime((index) => Math.min(stages.length - 1, Math.max(0, index + delta))); };
  const togglePlayback = () => {
    if (!playing && time >= stages.length - 1) setTime(0);
    setPlaying((value) => !value);
  };

  useEffect(() => {
    if (view !== "console") return undefined;
    const onKey = (event: KeyboardEvent) => {
      if ((event.target as HTMLElement | null)?.closest?.("input, select, textarea")) return;
      if (event.key === "ArrowRight") step(1);
      if (event.key === "ArrowLeft") step(-1);
      if (event.key === " ") { event.preventDefault(); togglePlayback(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, playing, time, stages.length]);

  return (
    <div className="dk-root ub-root" style={{ ["--tone" as string]: tone }}>
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
          <button type="button" className={view === "compare" ? "active" : ""} onClick={() => { setPlaying(false); setView("compare"); }}>반사실 비교</button>
        </nav>
        <div className="dk-header-agent">
          <div className="dk-header-agent-title"><span><strong>대응 에이전트</strong><small>근거 기반 조치 질의</small></span></div>
          <AgentDock eventId={eventData.id} compact />
        </div>
        <div className="dk-status">
          <span className="dk-chip dk-chip-stage"><i />{current ? `${clock(current.time)} ${current.label}` : "—"}</span>
          <span className="dk-chip">침수흔적 <small>{num(reconstruction.exposure.traces.count)}건</small></span>
          <span className="dk-chip">흔적 위 건축물 <small>{num(reconstruction.exposure.buildings.trace_intersecting)}동</small></span>
        </div>
      </header>

      {view === "console" ? (
        <div className="dk-body ub-body">
          <aside className="dk-side">
            <div className="dk-side-head"><p>사건 재생</p><h2>사건 단계 · {stages.length}단계</h2></div>
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
            {current && (
              <section className="ub-stage-note" aria-label="현재 단계 근거">
                <p>{STAGE_NOTE_KO[current.state]?.description ?? current.description}</p>
                <small>
                  출처: {current.source_url
                    ? <a href={current.source_url} target="_blank" rel="noreferrer">{STAGE_NOTE_KO[current.state]?.source ?? current.source}</a>
                    : STAGE_NOTE_KO[current.state]?.source ?? current.source}
                </small>
              </section>
            )}
          </aside>

          <UrbanMap layers={layers} tone={tone}>
            <div className="dk-replay ub-replay">
              <button type="button" onClick={() => step(-1)} aria-label="이전 단계">‹</button>
              <button type="button" onClick={togglePlayback}>{playing ? "❚❚ 일시정지" : "▶ 재생"}</button>
              <button type="button" onClick={() => step(1)} aria-label="다음 단계">›</button>
              <input type="range" min={0} max={Math.max(0, stages.length - 1)} value={time} onChange={(event) => { setPlaying(false); setTime(Number(event.target.value)); }} />
              <span>{current ? `${clock(current.time)} · ${current.label}` : ""}</span>
            </div>
          </UrbanMap>

          <aside className="dk-detail">
            <div className="dk-detail-head"><p>관측 근거</p><h2>강우 · 공식 침수흔적</h2></div>
            <div className="dk-detail-body">
              <Hyetograph reconstruction={reconstruction} currentTime={current?.time} tone={tone} />
              <ExposurePanel reconstruction={reconstruction} />
              <Limitations reconstruction={reconstruction} />
            </div>
          </aside>
        </div>
      ) : (
        <ComparePage eventData={eventData} reconstruction={reconstruction} onBack={() => setView("console")} />
      )}
    </div>
  );
}

function UrbanMap({ layers, tone, children }: { layers: LayersResponse; tone: string; children?: ReactNode }) {
  const elementRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [ready, setReady] = useState(false);
  const [visible, setVisible] = useState<Record<LayerKey, boolean>>({ flood_extent: true, buildings: true, roads: true, waterways: true, aoi: true });

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
          { id: "esri-dark-ref", type: "raster", source: "esri-dark-ref", paint: { "raster-opacity": 0.7 } },
        ],
      },
      center: [126.9225, 37.4875],
      zoom: 13.4,
      maxZoom: 17,
    });
    map.addControl(new maplibregl.AttributionControl({ compact: false, customAttribution: DATA_ATTRIBUTION }), "bottom-right");
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-left");

    map.on("load", () => {
      const add = (key: LayerKey) => map.addSource(key, { type: "geojson", data: layers[key].data as never });
      add("aoi"); add("roads"); add("waterways"); add("flood_extent"); add("buildings");
      map.addLayer({ id: "aoi-line", type: "line", source: "aoi", paint: { "line-color": "#22d3ee", "line-width": 1.2, "line-dasharray": [3, 3], "line-opacity": 0.55 } });
      map.addLayer({ id: "roads-line", type: "line", source: "roads", paint: { "line-color": "#64748b", "line-width": 0.8, "line-opacity": 0.4 } });
      map.addLayer({ id: "waterways-line", type: "line", source: "waterways", paint: { "line-color": "#7dd3fc", "line-width": 2.2, "line-opacity": 0.9 } });
      map.addLayer({ id: "traces-fill", type: "fill", source: "flood_extent", paint: { "fill-color": DEPTH_COLOR as never, "fill-opacity": 0.55 } });
      map.addLayer({ id: "buildings-line", type: "line", source: "buildings", minzoom: 14, paint: { "line-color": BUILDING_DEPTH_COLOR as never, "line-width": 1, "line-opacity": 0.85 } });

      map.on("click", "traces-fill", (event: MapLayerMouseEvent) => {
        const props = event.features?.[0]?.properties ?? {};
        new maplibregl.Popup({ offset: 12, className: "dk-popup" })
          .setLngLat(event.lngLat)
          .setHTML(cardHtml("공식 침수흔적", [
            ["침수심", `${props.flood_depth_m ?? "?"} m`], ["유형", props.damage_type], ["자치구", props.district],
            ["기간", `${props.start_date ?? ""}~${props.end_date ?? ""}`], ["출처", "서울시 침수흔적도 2022"],
          ], "#38bdf8"))
          .addTo(map);
      });
      map.on("click", "buildings-line", (event: MapLayerMouseEvent) => {
        const props = event.features?.[0]?.properties ?? {};
        new maplibregl.Popup({ offset: 12, className: "dk-popup" })
          .setLngLat(event.lngLat)
          .setHTML(cardHtml("흔적과 겹친 건축물", [
            ["행정동", props.dong], ["주용도", props.main_use], ["지상/지하", `${props.above_ground_floors ?? "?"} / ${props.underground_floors ?? "?"}층`],
            ["흔적 최대 침수심", `${props.max_trace_depth_m ?? "?"} m`], ["사용승인", props.use_approval_date],
          ], "#fbbf24"))
          .addTo(map);
      });
      for (const id of ["traces-fill", "buildings-line"]) {
        map.on("mouseenter", id, () => { map.getCanvas().style.cursor = "pointer"; });
        map.on("mouseleave", id, () => { map.getCanvas().style.cursor = ""; });
      }
      setReady(true);
    });
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; };
    // 최초 1회만 만든다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const groups: Record<LayerKey, string[]> = {
      flood_extent: ["traces-fill"], buildings: ["buildings-line"], roads: ["roads-line"], waterways: ["waterways-line"], aoi: ["aoi-line"],
    };
    (Object.keys(groups) as LayerKey[]).forEach((key) => {
      groups[key].forEach((id) => { if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", visible[key] ? "visible" : "none"); });
    });
  }, [ready, visible]);

  const names: Record<LayerKey, string> = {
    flood_extent: "공식 침수흔적", buildings: "흔적과 겹친 건축물", roads: "도로", waterways: "하천(도림천 등)", aoi: "분석 범위",
  };

  return (
    <section className="dk-map-wrap ub-map-wrap" aria-label="지도" style={{ ["--tone" as string]: tone }}>
      <div ref={elementRef} className="dk-map" />
      {children}
      <div className="dk-legend ub-legend">
        <p>공식 침수흔적 · 침수심</p>
        <span><i style={{ background: "#7dd3fc" }} />0.3 m 미만</span>
        <span><i style={{ background: "#38bdf8" }} />0.3–0.5 m</span>
        <span><i style={{ background: "#2563eb" }} />0.5–0.8 m</span>
        <span><i style={{ background: "#7c3aed" }} />0.8 m 이상</span>
        <small>사건 뒤 조사한 기록이라 시각 정보가 없습니다. 단계를 바꿔도 범위는 그대로입니다.</small>
        <div className="ub-layer-toggles">
          {(Object.keys(names) as LayerKey[]).map((key) => (
            <label key={key}>
              <input type="checkbox" checked={visible[key]} onChange={(event) => setVisible((state) => ({ ...state, [key]: event.target.checked }))} />
              {names[key]} <small>{num(layers[key].feature_count)}</small>
            </label>
          ))}
        </div>
      </div>
    </section>
  );
}

// 신림P 10분 강우 막대와 60분 누적 선, 설계강우 기준선, 현재 단계 시각 표시.
function Hyetograph({ reconstruction, currentTime, tone }: { reconstruction: UrbanReconstructionResponse; currentTime?: string; tone: string }) {
  const series = reconstruction.rainfall_series;
  const design = reconstruction.design_rainfall_mm_per_hour;
  const width = 320;
  const height = 150;
  const pad = { left: 30, right: 8, top: 10, bottom: 20 };
  const start = series.length ? Date.parse(series[0].time) : 0;
  const end = series.length ? Date.parse(series[series.length - 1].time) : 1;
  const x = (iso: string) => pad.left + ((Date.parse(iso) - start) / Math.max(1, end - start)) * (width - pad.left - pad.right);
  const yMax = Math.max(130, ...series.map((row) => row.rainfall_60min_mm ?? 0));
  const y = (value: number) => height - pad.bottom - (value / yMax) * (height - pad.top - pad.bottom);
  const barWidth = Math.max(0.8, (width - pad.left - pad.right) / Math.max(1, series.length) - 0.4);
  const line = series.filter((row) => row.rainfall_60min_mm !== null).map((row) => `${x(row.time).toFixed(1)},${y(row.rainfall_60min_mm ?? 0).toFixed(1)}`).join(" ");
  const peak = reconstruction.rainfall_peaks[reconstruction.primary_gauge];
  const hours = [6, 9, 12, 15, 18, 21];

  return (
    <section className="ub-panel" aria-label="강우 관측">
      <header><p>강우 관측 · {reconstruction.primary_gauge}</p><b>최대 60분 {peak?.max_60min_mm ?? "—"} mm ({clock(peak?.max_60min_end)})</b></header>
      <svg viewBox={`0 0 ${width} ${height}`} className="ub-hyeto" role="img" aria-label="10분 강우와 60분 누적 강우">
        {[0, 50, 100].map((value) => (
          <g key={value}>
            <line x1={pad.left} x2={width - pad.right} y1={y(value)} y2={y(value)} stroke="#22304a" />
            <text x={pad.left - 4} y={y(value) + 3} textAnchor="end">{value}</text>
          </g>
        ))}
        {series.map((row) => (
          <rect key={row.time} x={x(row.time) - barWidth / 2} y={y(row.rainfall_10min_mm)} width={barWidth} height={Math.max(0, height - pad.bottom - y(row.rainfall_10min_mm))} fill="#38bdf8" opacity={0.55} />
        ))}
        <polyline points={line} fill="none" stroke="#fbbf24" strokeWidth={1.6} />
        <line x1={pad.left} x2={width - pad.right} y1={y(design)} y2={y(design)} stroke="#f87171" strokeDasharray="4 3" />
        <text x={width - pad.right} y={y(design) - 3} textAnchor="end" className="ub-hyeto-design">설계강우 {design} mm/h</text>
        {hours.map((hour) => {
          const iso = `2022-08-08T${String(hour).padStart(2, "0")}:00:00+09:00`;
          return <text key={hour} x={x(iso)} y={height - 6} textAnchor="middle">{hour}시</text>;
        })}
        {currentTime && Date.parse(currentTime) >= start && Date.parse(currentTime) <= end && (
          <line x1={x(currentTime)} x2={x(currentTime)} y1={pad.top} y2={height - pad.bottom} stroke={tone} strokeWidth={2} />
        )}
      </svg>
      <div className="ub-hyeto-legend">
        <span><i style={{ background: "#38bdf8" }} />10분 강우</span>
        <span><i style={{ background: "#fbbf24" }} />60분 누적</span>
        <span><i style={{ background: "#f87171" }} />기존 방재성능목표</span>
      </div>
      <dl className="ub-gauge-table">
        {Object.entries(reconstruction.rainfall_peaks).map(([name, value]) => (
          <div key={name}><dt>{name} <small>{value.district}</small></dt><dd>{value.max_60min_mm} mm · {clock(value.max_60min_end)} · 일 {value.total_0808_mm} mm</dd></div>
        ))}
      </dl>
    </section>
  );
}

function ExposurePanel({ reconstruction }: { reconstruction: UrbanReconstructionResponse }) {
  const { traces, buildings, roads } = reconstruction.exposure;
  const uses = Object.entries(buildings.trace_intersecting_by_use).slice(0, 4);
  return (
    <section className="ub-panel" aria-label="공식 침수흔적 노출">
      <header><p>공식 침수흔적 기준 노출</p><b>관측된 침수 · 추정 아님</b></header>
      <div className="ub-kpis">
        <div><b>{num(traces.count)}</b><span>침수흔적 (건)</span></div>
        <div><b>{traces.union_area_in_aoi_km2}</b><span>흔적 면적 (km²)</span></div>
        <div><b>{num(buildings.trace_intersecting)}</b><span>흔적과 겹친 건축물 (동)</span></div>
        <div><b>{roads.osm_road_km_in_traces}</b><span>흔적 안 도로 (km)</span></div>
      </div>
      <dl className="ub-gauge-table">
        <div><dt>침수심</dt><dd>중앙값 {traces.depth_m.median} m · 상위 10% {traces.depth_m.p90} m · 최대 {traces.depth_m.max} m</dd></div>
        <div><dt>0.5 m 이상 흔적</dt><dd>{num(traces.depth_ge_0_5m)}건 · 겹친 건축물 {num(buildings.trace_intersecting_depth_ge_0_5m)}동</dd></div>
        <div><dt>건축물 재고</dt><dd>범위 안 {num(buildings.stock_at_event)}동 중 {(buildings.trace_intersecting / buildings.stock_at_event * 100).toFixed(1)}%</dd></div>
        <div><dt>주용도</dt><dd>{uses.map(([use, count]) => `${use} ${num(count)}`).join(" · ")}</dd></div>
        <div><dt>지하층 있음</dt><dd>{num(buildings.trace_intersecting_with_underground_floors)}동</dd></div>
      </dl>
      <small className="ub-note">건축물은 {buildings.snapshot} 스냅샷에서 사용승인일 2022-08-08 이후 {num(buildings.excluded_approved_after_event)}동을 뺀 값입니다. 사용승인일이 빈 {num(buildings.stock_missing_approval_date)}동은 포함했습니다.</small>
    </section>
  );
}

function Limitations({ reconstruction }: { reconstruction: UrbanReconstructionResponse }) {
  return (
    <section className="ub-panel" aria-label="출처와 한계">
      <header><p>출처 · 한계</p><b>무엇을 계산하지 않는가</b></header>
      <ul className="ub-list">
        {reconstruction.provenance.map((item) => <li key={item.source}><b>{item.source}</b> · {item.data_vintage} · {item.role}</li>)}
      </ul>
      <ul className="ub-list ub-muted">
        {reconstruction.limitations.map((item) => <li key={item}>{LIMITATION_KO[item] ?? item}</li>)}
      </ul>
    </section>
  );
}

const LIMITATION_KO: Record<string, string> = {
  "Official flood traces record where flooding happened after the event; they carry no timestamps, so the map cannot animate flood growth.":
    "공식 침수흔적은 사건 뒤 조사한 결과라 시각이 없습니다. 지도에서 침수 확산을 재생하지 않습니다.",
  "Rainfall thresholds use one gauge (신림P) as the trigger; other gauges in the corridor peaked at different minutes.":
    "강우 임계는 신림P 한 곳 기준입니다. 유역 안 다른 강우계는 정점 시각이 다릅니다.",
  "Lead times are arithmetic between an alert time and recorded incident times. They do not estimate evacuation, casualties, or damage avoided.":
    "선행 시간은 경보 시각과 기록된 사건 시각의 차이입니다. 대피·인명·피해 감소를 추정하지 않습니다.",
  "Storage capture is rain volume arithmetic over the Dorimcheon catchment area (40.96 km2, literature value) and an assumed runoff coefficient. It is not a sewer or tunnel hydraulic model.":
    "저류 계산은 도림천 유역면적(40.96 km², 문헌값)과 가정한 유출계수에 대한 강우 부피 산술이며 하수관·터널 수리모형이 아닙니다.",
  "Building stock comes from a 2026-08-09 register snapshot filtered to use-approval dates on or before 2022-08-08; buildings demolished before 2026 are missing.":
    "건축물은 2026-08-09 스냅샷을 사용승인일로 거른 값이라, 2026년 전에 철거된 건물은 빠져 있습니다.",
  "Incident times other than gauge thresholds come from press coverage and need official source pages.":
    "강우 임계 외의 사건 시각은 언론 보도 기준이며 공식 원문 확인이 필요합니다.",
};

function ComparePage({ eventData, reconstruction, onBack }: { eventData: FloodEvent; reconstruction: UrbanReconstructionResponse; onBack: () => void }) {
  return (
    <main className="dk-compare ub-compare">
      <div className="dk-compare-head">
        <div>
          <p>반사실 비교</p>
          <h2>이 조치가 있었다면?</h2>
          <span>관측 기록은 그대로 두고, 경보 시각과 저류 시설만 바꿔 시각과 부피를 계산합니다. 인명·피해 감소는 계산하지 않습니다.</span>
        </div>
        <button type="button" className="dk-compare-back" onClick={onBack}>관제 화면으로</button>
      </div>
      <AlertTimingPanel eventId={eventData.id} reconstruction={reconstruction} />
      <StoragePanel eventId={eventData.id} reconstruction={reconstruction} />
    </main>
  );
}

const THRESHOLD_OPTIONS = [30, 50, 70, 95];

function AlertTimingPanel({ eventId, reconstruction }: { eventId: string; reconstruction: UrbanReconstructionResponse }) {
  const [station, setStation] = useState(reconstruction.primary_gauge);
  const [thresholds, setThresholds] = useState<number[]>([50, 95]);
  const [manual, setManual] = useState("12:50");
  const [result, setResult] = useState<AlertTimingResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    api.getAlertTiming(eventId, { station, thresholds_mm_per_hour: thresholds, alert_times: manual ? [manual] : [] })
      .then((next) => { if (!cancelled) setResult(next); })
      .catch((reason: Error) => { if (!cancelled) setError(reason.message); });
    return () => { cancelled = true; };
  }, [eventId, station, thresholds, manual]);

  const axisStart = Date.parse("2022-08-08T12:00:00+09:00");
  const axisEnd = Date.parse("2022-08-08T22:00:00+09:00");
  const pos = (iso: string) => `${((Date.parse(iso) - axisStart) / (axisEnd - axisStart)) * 100}%`;

  return (
    <section className="dk-compare-panel ub-whatif">
      <div className="dk-compare-panel-head">
        <p>개입 1 · 경보 시각</p>
        <h3>강우계가 임계를 넘은 순간 저지대 경보를 보냈다면</h3>
        <span>실제 첫 저지대 침수 문자는 21:19로, 첫 구조 신고(20:59)보다 {result?.actual_alert_after_rescue_call_min ?? 20}분 늦었습니다.</span>
      </div>
      <div className="ub-controls">
        <label>강우계
          <select value={station} onChange={(event) => setStation(event.target.value)}>
            {reconstruction.gauges.map((name) => <option key={name} value={name}>{name}</option>)}
          </select>
        </label>
        <fieldset>
          <legend>60분 강우 임계 (mm)</legend>
          {THRESHOLD_OPTIONS.map((value) => (
            <label key={value} className="ub-chip-toggle">
              <input
                type="checkbox"
                checked={thresholds.includes(value)}
                onChange={(event) => setThresholds((list) => (event.target.checked ? [...list, value].sort((a, b) => a - b) : list.filter((item) => item !== value)))}
              />
              {value}
            </label>
          ))}
        </fieldset>
        <label>수동 경보 시각
          <input type="time" value={manual} onChange={(event) => setManual(event.target.value)} />
        </label>
      </div>
      {error && <p className="dk-error">{error}</p>}
      {result && (
        <>
          <div className="ub-timeline" aria-label="경보 시각 비교 시간축">
            <div className="ub-timeline-axis">
              {[12, 14, 16, 18, 20, 22].map((hour) => <span key={hour} style={{ left: pos(`2022-08-08T${hour}:00:00+09:00`) }}>{hour}시</span>)}
            </div>
            <i className="ub-mark rescue" style={{ left: pos(result.first_rescue_call) }} title="첫 구조 신고 20:59"><em>첫 구조 신고 20:59</em></i>
            <i className="ub-mark actual" style={{ left: pos(result.actual_first_alert) }} title="실제 첫 문자 21:19"><em>실제 문자 21:19</em></i>
            {result.scenarios.filter((row) => row.alert_time).map((row) => (
              <i key={row.label} className="ub-mark whatif" style={{ left: pos(row.alert_time as string) }} title={row.label}><em>{clock(row.alert_time)}</em></i>
            ))}
          </div>
          <table className="ub-table">
            <thead><tr><th>가정한 경보</th><th>경보 시각</th><th>첫 구조 신고까지</th><th>실제 문자보다</th></tr></thead>
            <tbody>
              {result.scenarios.map((row) => (
                <tr key={row.label}>
                  <td>{row.label}</td>
                  <td>{row.reached ? clock(row.alert_time) : "도달 안 함"}</td>
                  <td>{minutesLabel(row.minutes_before_first_rescue_call)}</td>
                  <td>{row.minutes_earlier_than_actual_alert === null ? "—" : `${minutesLabel(row.minutes_earlier_than_actual_alert)} 빠름`}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <ul className="ub-list ub-muted">{result.assumptions.map((item) => <li key={item}>{item}</li>)}</ul>
        </>
      )}
    </section>
  );
}

const STORAGE_PRESETS = [
  { label: "도림천 터널 계획 40만 m³", value: 400_000 },
  { label: "신월 저류시설 32만 m³", value: 320_000 },
];

function StoragePanel({ eventId, reconstruction }: { eventId: string; reconstruction: UrbanReconstructionResponse }) {
  const [storage, setStorage] = useState(400_000);
  const [capacity, setCapacity] = useState(95);
  const [runoff, setRunoff] = useState(1);
  const [useAoiArea, setUseAoiArea] = useState(false);
  const [result, setResult] = useState<StorageCaptureResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    const timer = window.setTimeout(() => {
      api.getStorageCapture(eventId, {
        station: reconstruction.primary_gauge,
        storage_m3: storage,
        capacity_mm_per_hour: capacity,
        runoff_coefficient: runoff,
        ...(useAoiArea ? { catchment_area_km2: reconstruction.exposure.aoi_area_km2 } : {}),
      })
        .then((next) => { if (!cancelled) setResult(next); })
        .catch((reason: Error) => { if (!cancelled) setError(reason.message); });
    }, 200);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [eventId, reconstruction.primary_gauge, reconstruction.exposure.aoi_area_km2, storage, capacity, runoff, useAoiArea]);

  const chart = useMemo(() => {
    if (!result || !result.excess_timeline.length) return null;
    const rows = result.excess_timeline;
    const width = 520;
    const height = 150;
    const pad = { left: 46, right: 10, top: 12, bottom: 22 };
    const maxValue = Math.max(result.storage_m3, result.excess_volume_m3) * 1.08;
    const x = (index: number) => pad.left + (index / Math.max(1, rows.length - 1)) * (width - pad.left - pad.right);
    const y = (value: number) => height - pad.bottom - (value / maxValue) * (height - pad.top - pad.bottom);
    return { rows, width, height, pad, x, y };
  }, [result]);

  return (
    <section className="dk-compare-panel ub-whatif">
      <div className="dk-compare-panel-head">
        <p>개입 2 · 대심도 빗물터널</p>
        <h3>도림천 빗물터널이 있었다면, 처리 능력을 넘은 비를 얼마나 담았나</h3>
        <span>2011년 계획된 대심도 터널 가운데 신월만 지어졌습니다. 도림천 터널은 2022년 이후 다시 추진돼 2030년 준공 목표입니다.</span>
      </div>
      <div className="ub-controls">
        <fieldset>
          <legend>저류량</legend>
          {STORAGE_PRESETS.map((preset) => (
            <label key={preset.value} className="ub-chip-toggle">
              <input type="radio" name="storage" checked={storage === preset.value} onChange={() => setStorage(preset.value)} />
              {preset.label}
            </label>
          ))}
        </fieldset>
        <fieldset>
          <legend>처리 능력 (mm/h)</legend>
          {[95, 100, 110].map((value) => (
            <label key={value} className="ub-chip-toggle">
              <input type="radio" name="capacity" checked={capacity === value} onChange={() => setCapacity(value)} />
              {value}
            </label>
          ))}
        </fieldset>
        <fieldset>
          <legend>면적</legend>
          <label className="ub-chip-toggle">
            <input type="radio" name="area" checked={!useAoiArea} onChange={() => setUseAoiArea(false)} />
            도림천 유역 40.96 km²
          </label>
          <label className="ub-chip-toggle">
            <input type="radio" name="area" checked={useAoiArea} onChange={() => setUseAoiArea(true)} />
            분석 범위 {reconstruction.exposure.aoi_area_km2} km²
          </label>
        </fieldset>
        <label>유출계수 {runoff.toFixed(2)}
          <input type="range" min={0.3} max={1} step={0.05} value={runoff} onChange={(event) => setRunoff(Number(event.target.value))} />
        </label>
      </div>
      {error && <p className="dk-error">{error}</p>}
      {result && (
        <>
          <div className="dk-compare-cards">
            <article className="dk-compare-card baseline">
              <div className="dk-compare-card-label"><i />원시나리오 · 터널 없음</div>
              <h3>처리 능력 초과 빗물 {num(result.excess_volume_m3)} m³</h3>
              <p>{reconstruction.primary_gauge} 10분 강우 중 시간당 {result.capacity_mm_per_hour} mm를 넘은 몫을 면적 {result.catchment_area_km2} km²·유출계수 {result.runoff_coefficient}로 부피화했습니다.</p>
              <dl>
                <div><dt>초과 시작</dt><dd>{clock(result.first_excess_time)}</dd></div>
                <div><dt>첫 구조 신고</dt><dd>20:59</dd></div>
              </dl>
            </article>
            <article className="dk-compare-card intervention">
              <div className="dk-compare-card-label"><i />개입 · 저류 {num(result.storage_m3)} m³</div>
              <h3>초과량의 {result.captured_share_pct ?? "—"}% 저류</h3>
              <p>{result.storage_full_time ? `${clock(result.storage_full_time)}에 가득 찹니다. 첫 구조 신고보다 ${minutesLabel(result.storage_full_minutes_before_first_rescue_call)} 앞입니다.` : "이 가정에서는 초과량 전부를 담고도 남습니다."}</p>
              <dl>
                <div><dt>저류한 부피</dt><dd>{num(result.captured_volume_m3)} m³</dd></div>
                <div><dt>남은 초과량</dt><dd>{num(Math.max(0, result.excess_volume_m3 - result.captured_volume_m3))} m³</dd></div>
              </dl>
            </article>
          </div>
          {chart && (
            <svg viewBox={`0 0 ${chart.width} ${chart.height}`} className="ub-storage-chart" role="img" aria-label="누적 초과량과 저류량">
              <line x1={chart.pad.left} x2={chart.width - chart.pad.right} y1={chart.y(result.storage_m3)} y2={chart.y(result.storage_m3)} stroke="#2dd4bf" strokeDasharray="5 4" />
              <text x={chart.width - chart.pad.right} y={chart.y(result.storage_m3) - 4} textAnchor="end" fill="#2dd4bf">저류량 {num(result.storage_m3)} m³</text>
              <polyline
                points={chart.rows.map((row, index) => `${chart.x(index).toFixed(1)},${chart.y(row.cumulative_excess_m3).toFixed(1)}`).join(" ")}
                fill="none" stroke="#f87171" strokeWidth={2}
              />
              {chart.rows.map((row, index) => (
                <g key={row.time}>
                  <circle cx={chart.x(index)} cy={chart.y(row.cumulative_excess_m3)} r={2.6} fill="#f87171" />
                  <text x={chart.x(index)} y={chart.height - 6} textAnchor="middle">{clock(row.time)}</text>
                </g>
              ))}
              <text x={chart.pad.left - 6} y={chart.y(0) + 3} textAnchor="end">0</text>
            </svg>
          )}
          <section className="ub-panel ub-reference" aria-label="참고 사례">
            <header><p>참고 사례 · 실제로 지어진 터널</p><b>{result.reference_case.name}</b></header>
            <dl className="ub-gauge-table">
              <div><dt>저류량</dt><dd>{num(result.reference_case.storage_m3)} m³ · {result.reference_case.design} <small><a href={result.reference_case.storage_url} target="_blank" rel="noreferrer">{result.reference_case.storage_source}</a></small></dd></div>
              <div><dt>8.8 유입</dt><dd>{num(result.reference_case.inflow_2022_08_08_m3)} m³ <small><a href={result.reference_case.inflow_url} target="_blank" rel="noreferrer">{result.reference_case.inflow_source}</a></small></dd></div>
              <div><dt>결과</dt><dd>{result.reference_case.outcome}</dd></div>
            </dl>
            <small className="ub-note">{result.reference_case.note}</small>
          </section>
          <ul className="ub-list ub-muted">{result.assumptions.map((item) => <li key={item}>{item}</li>)}</ul>
        </>
      )}
    </section>
  );
}
