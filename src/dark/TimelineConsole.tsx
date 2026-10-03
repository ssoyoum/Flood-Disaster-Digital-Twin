import { useEffect, useRef, useState, type ReactNode } from "react";
import maplibregl, { type MapLayerMouseEvent } from "maplibre-gl";
import * as api from "../api";
import type { FloodEvent, LayersResponse, ResponseTimingResult, TimelineReconstructionResponse } from "../types";
import { FloodOpsLogo } from "./Landing";
import { CONFIDENCE_KO, ROLE_KO, localizeEvent, stageKo } from "./ko";
import "./dark.css";
import "./urban.css";

/*
 * 사건 시각 중심 관제 화면 (2022 포항, 2026 안동·의성).
 *
 * 이 사례들은 공식 침수범위·강우계 시계열이 아직 연결되지 않았다. 지도에는 사건일 OSM 스냅샷과
 * 보도된 지명(교량·마을 중심점)만 올리고, 시간축은 보도된 사건 시각으로 재생한다.
 * 반사실 비교는 대응 시각 하나를 옮겼을 때 이후 사건까지 남는 분을 백엔드에서 계산한 값 그대로 보여준다.
 */

type View = "console" | "compare";
type LayerKey = "roads" | "waterways" | "buildings" | "aoi";

const ESRI = "https://services.arcgisonline.com/ArcGIS/rest/services/Canvas";
const ATTRIBUTION = ["도로·하천·건축물 © OpenStreetMap contributors", "사건 시각: 언론 보도"];

const STAGE_TONE: Record<string, string> = {
  typhoon_landfall: "#60a5fa", first_notice: "#38bdf8", river_overflow: "#fbbf24", move_car_broadcast: "#fb923c",
  parking_inflow: "#f87171", parking_full: "#b91c1c", plant_outage: "#f97316", missing_report: "#ef4444",
  first_isolation: "#fbbf24", flood_warning: "#fb923c", camper_isolation: "#f97316", evacuation_order: "#2dd4bf",
  predicted_warning_level: "#ef4444", warning_lifted: "#60a5fa", national_landslide_alert: "#f87171",
};

const STAGE_NOTE_KO: Record<string, string> = {
  typhoon_landfall: "태풍 힌남노가 거제 부근에 상륙했습니다.",
  first_notice: "아파트 관리소장은 05:20경 차량을 지상으로 옮겨 달라고 다시 방송했다고 주장합니다. 독립 확인되지 않았습니다.",
  river_overflow: "06:00경 냉천이 범람하기 시작했습니다(포스코 발표).",
  move_car_broadcast: "지하주차장 차량을 옮기라는 안내방송이 나갔습니다(소방 신고 기록 기준 보도 시각).",
  parking_inflow: "지하주차장으로 물이 들어오기 시작했습니다(차량 블랙박스 기준).",
  parking_full: "유입 8분 만에 주차장이 완전히 잠겼고, 그 사이 차량 14대가 빠져나왔습니다.",
  plant_outage: "포스코 포항제철소의 전기·통신·용수 공급이 끊겼습니다.",
  missing_report: "지하주차장 실종 신고가 접수됐습니다.",
  first_isolation: "안동 신석리 교회 일대가 침수돼 3명이 고립됐습니다.",
  flood_warning: "낙동강홍수통제소가 미천 운산리 지점에 홍수경보를 냈습니다. 발령 당시 수위 3.5 m, 경보 기준 4.7 m.",
  camper_isolation: "광음리 유원지에서 캠핑카가 고립됐습니다.",
  evacuation_order: "대피명령이 나왔습니다. 매체에 따라 7/18 자정 또는 7/19 00:00으로 표기됩니다.",
  predicted_warning_level: "홍수통제소가 경보 발령 때 내놓은, 경보 기준 수위 도달 예측 시각입니다. 관측값이 아닙니다.",
  warning_lifted: "미천 홍수경보가 해제됐습니다.",
  national_landslide_alert: "산림청이 경북 산사태 위기경보를 '주의'에서 '경계'로 올렸습니다.",
};

const LIMITATION_KO: Record<string, string> = {
  "Incident times are press-reported and need official source pages.": "사건 시각은 언론 보도 기준이며 공식 원문 확인이 필요합니다.",
  "No official flood extent, gauge series, or building register is connected; the map shows an event-date OSM snapshot only.":
    "공식 침수범위·강우계 시계열·건축물대장이 연결되지 않았습니다. 지도는 사건일 OSM 스냅샷만 보여줍니다.",
  "Lead times are arithmetic between a response time and reported milestones. They do not estimate evacuation, casualties, or damage avoided.":
    "선행 시간은 대응 시각과 보도된 사건 시각의 차이입니다. 대피·인명·피해 감소를 추정하지 않습니다.",
  "Focus sites are village or bridge centre points, not the exact location of affected homes.":
    "초점 지점은 마을·교량 중심점이며 피해 주택의 정확한 위치가 아닙니다.",
};

const clock = (iso?: string | null) => (iso ? iso.slice(11, 16) : "—");
const dayClock = (iso?: string | null) => (iso ? `${Number(iso.slice(8, 10))}일 ${iso.slice(11, 16)}` : "—");
const num = (value?: number | null) => (value === null || value === undefined ? "—" : value.toLocaleString("ko-KR"));
const escapeHtml = (value: unknown) =>
  String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char] ?? char);

function minutesLabel(minutes: number | null | undefined) {
  if (minutes === null || minutes === undefined) return "—";
  const abs = Math.abs(minutes);
  const text = abs >= 60 ? `${Math.floor(abs / 60)}시간 ${abs % 60}분` : `${abs}분`;
  return minutes < 0 ? `${text} 지남` : text;
}

export default function TimelineConsole({ eventId }: { eventId: string }) {
  const [eventData, setEventData] = useState<FloodEvent | null>(null);
  const [layers, setLayers] = useState<LayersResponse | null>(null);
  const [reconstruction, setReconstruction] = useState<TimelineReconstructionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.getEvent(eventId)
      .then((nextEvent) => Promise.all([nextEvent, api.getLayers(eventId, nextEvent.data_year), api.getTimelineReconstruction(eventId)]))
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
  return <TimelineConsoleView eventData={eventData} layers={layers} reconstruction={reconstruction} />;
}

function TimelineConsoleView({ eventData, layers, reconstruction }: { eventData: FloodEvent; layers: LayersResponse; reconstruction: TimelineReconstructionResponse }) {
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
        <div className="dk-status">
          <span className="dk-chip dk-chip-stage"><i />{current ? `${dayClock(current.time)} ${current.label}` : "—"}</span>
          <span className="dk-chip">근거 <small>언론 보도 시각</small></span>
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
                <p>{STAGE_NOTE_KO[current.state] ?? current.description}</p>
                <small>출처: {current.source_url ? <a href={current.source_url} target="_blank" rel="noreferrer">{current.source}</a> : current.source}</small>
              </section>
            )}
          </aside>

          <TimelineMap layers={layers} center={reconstruction.map_center} tone={tone}>
            <div className="dk-replay ub-replay">
              <button type="button" onClick={() => step(-1)} aria-label="이전 단계">‹</button>
              <button type="button" onClick={togglePlayback}>{playing ? "❚❚ 일시정지" : "▶ 재생"}</button>
              <button type="button" onClick={() => step(1)} aria-label="다음 단계">›</button>
              <input type="range" min={0} max={Math.max(0, stages.length - 1)} value={time} onChange={(event) => { setPlaying(false); setTime(Number(event.target.value)); }} />
              <span>{current ? `${dayClock(current.time)} · ${current.label}` : ""}</span>
            </div>
          </TimelineMap>

          <aside className="dk-detail">
            <div className="dk-detail-head"><p>보도된 사실</p><h2>피해·조치 수치와 출처</h2></div>
            <div className="dk-detail-body">
              <section className="ub-panel" aria-label="보도된 수치">
                <header><p>보도된 수치</p><b>모델 계산이 아님</b></header>
                <dl className="ub-gauge-table">
                  {reconstruction.reported_facts.map((fact) => (
                    <div key={fact.label}><dt>{fact.label}</dt><dd>{fact.value} <small><a href={fact.url} target="_blank" rel="noreferrer">{fact.source}</a></small></dd></div>
                  ))}
                </dl>
              </section>
              <section className="ub-panel" aria-label="반사실 질문">
                <header><p>반사실 질문</p><b>{reconstruction.interventions.length}개</b></header>
                <ul className="ub-list">{reconstruction.interventions.map((item) => <li key={item.id}><b>{item.name}</b> · {item.question}</li>)}</ul>
                <button type="button" className="dk-compare-back" onClick={() => setView("compare")}>반사실 비교 열기</button>
              </section>
              <section className="ub-panel" aria-label="출처와 한계">
                <header><p>출처 · 한계</p><b>무엇을 계산하지 않는가</b></header>
                <ul className="ub-list ub-muted">{reconstruction.limitations.map((item) => <li key={item}>{LIMITATION_KO[item] ?? item}</li>)}</ul>
              </section>
            </div>
          </aside>
        </div>
      ) : (
        <main className="dk-compare ub-compare">
          <div className="dk-compare-head">
            <div>
              <p>반사실 비교</p>
              <h2>이 대응을 더 일찍 했다면?</h2>
              <span>보도된 사건 시각은 그대로 두고, 대응 시각 하나만 옮겨 이후 사건까지 남는 시간을 계산합니다. 대피 성공이나 인명·피해 감소는 계산하지 않습니다.</span>
            </div>
            <button type="button" className="dk-compare-back" onClick={() => setView("console")}>관제 화면으로</button>
          </div>
          {reconstruction.interventions.map((intervention) => (
            <ResponseTimingPanel key={intervention.id} eventId={eventData.id} reconstruction={reconstruction} intervention={intervention} />
          ))}
        </main>
      )}
    </div>
  );
}

function TimelineMap({ layers, center, tone, children }: { layers: LayersResponse; center: [number, number]; tone: string; children?: ReactNode }) {
  const elementRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [ready, setReady] = useState(false);
  const [visible, setVisible] = useState<Record<LayerKey, boolean>>({ roads: true, waterways: true, buildings: true, aoi: true });

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
      center,
      zoom: 13,
      maxZoom: 17,
    });
    map.addControl(new maplibregl.AttributionControl({ compact: false, customAttribution: ATTRIBUTION }), "bottom-right");
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-left");
    map.on("load", () => {
      const add = (key: keyof LayersResponse) => map.addSource(key, { type: "geojson", data: layers[key].data as never });
      add("aoi"); add("roads"); add("waterways"); add("buildings"); add("facilities");
      map.addLayer({ id: "aoi-line", type: "line", source: "aoi", paint: { "line-color": "#22d3ee", "line-width": 1.2, "line-dasharray": [3, 3], "line-opacity": 0.55 } });
      map.addLayer({ id: "roads-line", type: "line", source: "roads", paint: { "line-color": "#64748b", "line-width": 0.9, "line-opacity": 0.5 } });
      map.addLayer({ id: "waterways-line", type: "line", source: "waterways", paint: { "line-color": "#7dd3fc", "line-width": 2.6, "line-opacity": 0.9 } });
      map.addLayer({ id: "buildings-fill", type: "fill", source: "buildings", paint: { "fill-color": "#3b4a63", "fill-opacity": 0.6 } });
      map.addLayer({ id: "sites-halo", type: "circle", source: "facilities", paint: { "circle-radius": 14, "circle-color": "#fbbf24", "circle-opacity": 0.18 } });
      map.addLayer({ id: "sites-dot", type: "circle", source: "facilities", paint: { "circle-radius": 5, "circle-color": "#fbbf24", "circle-stroke-color": "#0b1220", "circle-stroke-width": 2 } });
      // 글리프를 쓰지 않으므로 지명은 HTML 마커로 올린다.
      for (const site of layers.facilities.data.features) {
        const label = document.createElement("div");
        label.className = "tl-site-label";
        label.textContent = String(site.properties?.name ?? "");
        new maplibregl.Marker({ element: label, anchor: "left", offset: [10, 0] }).setLngLat(site.geometry.coordinates as [number, number]).addTo(map);
      }
      map.on("click", "sites-dot", (event: MapLayerMouseEvent) => {
        const props = event.features?.[0]?.properties ?? {};
        new maplibregl.Popup({ offset: 12, className: "dk-popup" })
          .setLngLat(event.lngLat)
          .setHTML(`<div class="dk-card"><b>${escapeHtml(props.name)}</b><dl><div><dt>설명</dt><dd>${escapeHtml(props.note)}</dd></div></dl></div>`)
          .addTo(map);
      });
      const ring = (layers.aoi.data.features[0]?.geometry.coordinates as number[][][] | undefined)?.[0];
      if (ring?.length) {
        const lons = ring.map((point) => point[0]);
        const lats = ring.map((point) => point[1]);
        map.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], { padding: { top: 40, bottom: 90, left: 40, right: 280 }, duration: 0 });
      }
      map.on("mouseenter", "sites-dot", () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", "sites-dot", () => { map.getCanvas().style.cursor = ""; });
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
    const groups: Record<LayerKey, string[]> = { roads: ["roads-line"], waterways: ["waterways-line"], buildings: ["buildings-fill"], aoi: ["aoi-line"] };
    (Object.keys(groups) as LayerKey[]).forEach((key) => {
      groups[key].forEach((id) => { if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", visible[key] ? "visible" : "none"); });
    });
  }, [ready, visible]);

  const names: Record<LayerKey, string> = { waterways: "하천", roads: "도로", buildings: "건축물(OSM, 부분)", aoi: "분석 범위" };
  return (
    <section className="dk-map-wrap ub-map-wrap" aria-label="지도" style={{ ["--tone" as string]: tone }}>
      <div ref={elementRef} className="dk-map" />
      {children}
      <div className="dk-legend ub-legend">
        <p>지도</p>
        <span><i style={{ background: "#fbbf24" }} />보도된 지점 (마을·교량 중심점)</span>
        <span><i style={{ background: "#7dd3fc" }} />하천</span>
        <small>공식 침수범위가 연결되지 않아 침수 영역을 그리지 않습니다. 건축물은 사건일 OSM에 있는 것만 보입니다.</small>
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

function ResponseTimingPanel({
  eventId,
  reconstruction,
  intervention,
}: {
  eventId: string;
  reconstruction: TimelineReconstructionResponse;
  intervention: TimelineReconstructionResponse["interventions"][number];
}) {
  const [selected, setSelected] = useState<string[]>(intervention.presets.slice(-1));
  const [manual, setManual] = useState("");
  const [result, setResult] = useState<ResponseTimingResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    const times = [...selected, ...(manual ? [manual] : [])];
    api.getResponseTiming(eventId, intervention.id, times)
      .then((next) => { if (!cancelled) setResult(next); })
      .catch((reason: Error) => { if (!cancelled) setError(reason.message); });
    return () => { cancelled = true; };
  }, [eventId, intervention.id, selected, manual]);

  const stages = reconstruction.replay;
  const axisStart = Date.parse(stages[0].time) - 30 * 60_000;
  const axisEnd = Date.parse(stages[stages.length - 1].time) + 30 * 60_000;
  const pos = (iso: string) => `${Math.min(100, Math.max(0, ((Date.parse(iso) - axisStart) / (axisEnd - axisStart)) * 100))}%`;

  return (
    <section className="dk-compare-panel ub-whatif">
      <div className="dk-compare-panel-head">
        <p>개입 · {intervention.name}</p>
        <h3>{intervention.question}</h3>
        <span>{intervention.actual_label}</span>
      </div>
      <div className="ub-controls">
        <fieldset>
          <legend>가정한 대응 시각</legend>
          {intervention.presets.map((value) => {
            const stage = stages.find((item) => item.time.slice(11, 16) === value);
            return (
              <label key={value} className="ub-chip-toggle">
                <input
                  type="checkbox"
                  checked={selected.includes(value)}
                  onChange={(event) => setSelected((list) => (event.target.checked ? [...list, value] : list.filter((item) => item !== value)))}
                />
                {value}{stage ? ` · ${stage.label}` : ""}
              </label>
            );
          })}
        </fieldset>
        <label>직접 입력
          <input type="time" value={manual} onChange={(event) => setManual(event.target.value)} />
        </label>
      </div>
      {error && <p className="dk-error">{error}</p>}
      {result && (
        <>
          <div className="ub-timeline tl-timeline" aria-label="대응 시각 비교 시간축">
            {stages.map((stage) => (
              <i key={stage.state} className="tl-tick" style={{ left: pos(stage.time) }} title={`${clock(stage.time)} ${stage.label}`} />
            ))}
            {result.milestones.map((milestone, index) => (
              // 기준 사건이 몇 분 차이로 붙어 있으면 라벨이 겹치므로 높이를 엇갈린다.
              <i key={milestone.state} className="ub-mark rescue" style={{ left: pos(milestone.time), height: `${52 + index * 22}px` }}><em>{stageKo(milestone.state, milestone.label)} {clock(milestone.time)}</em></i>
            ))}
            {result.scenarios.map((row) => (
              <i key={row.action_time} className={`ub-mark ${row.is_actual ? "actual" : "whatif"}`} style={{ left: pos(row.action_time) }}>
                <em>{row.is_actual ? `실제 ${clock(row.action_time)}` : clock(row.action_time)}</em>
              </i>
            ))}
          </div>
          <table className="ub-table">
            <thead>
              <tr>
                <th>대응 시각</th>
                <th>실제보다</th>
                {result.milestones.map((milestone) => <th key={milestone.state}>{stageKo(milestone.state, milestone.label)}까지</th>)}
              </tr>
            </thead>
            <tbody>
              {result.scenarios.map((row) => (
                <tr key={row.action_time} className={row.is_actual ? "tl-actual-row" : ""}>
                  <td>{dayClock(row.action_time)}{row.is_actual ? " (실제)" : ""}</td>
                  <td>{row.is_actual ? "—" : row.minutes_earlier_than_actual >= 0 ? `${minutesLabel(row.minutes_earlier_than_actual)} 빠름` : `${minutesLabel(-row.minutes_earlier_than_actual)} 늦음`}</td>
                  {result.milestones.map((milestone) => <td key={milestone.state}>{minutesLabel(row.minutes_before_milestones[milestone.state])}</td>)}
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
