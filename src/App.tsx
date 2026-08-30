import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl, { type Map as MapLibreMap } from "maplibre-gl";
import { Activity, AlertTriangle, ArrowDownRight, Building2, Check, CheckCircle2, ChevronDown, CircleHelp, Clock3, Droplets, ExternalLink, KeyRound, Layers3, MapPin, Play, Route, Settings2, Shield, SlidersHorizontal, Waves, X } from "lucide-react";
import * as api from "./api";
import type { ExposureMetrics, FloodEvent, GeoJson, InterventionType, Observation, ScenarioResult } from "./types";

const interventionOptions: { value: InterventionType; label: string; hint: string }[] = [
  { value: "SHELTER_OPEN", label: "추가 대피소 개방", hint: "대피 수용력을 늘립니다" },
  { value: "ROAD_CLOSURE", label: "침수 도로 통제", hint: "2차 노출을 줄입니다" },
  { value: "EVACUATION", label: "대피 우선 배치", hint: "위험 인구를 우선 이동합니다" },
  { value: "TEMPORARY_BARRIER", label: "임시 방어시설", hint: "침수 범위 감소를 추정합니다" },
  { value: "INFRASTRUCTURE_PROTECTION", label: "핵심 시설 보호", hint: "주요 시설 위험을 낮춥니다" },
];

const emptyGeoJson: GeoJson = { type: "FeatureCollection", features: [] };

function formatNumber(value: number) {
  return new Intl.NumberFormat("ko-KR").format(value);
}

function originLabel(origin: string) {
  return origin === "SIMULATED" ? "SIMULATED" : origin;
}

function Metric({ icon: Icon, label, value, unit, tone = "neutral" }: { icon: typeof Activity; label: string; value: string; unit?: string; tone?: "neutral" | "risk" | "safe" }) {
  return (
    <div className="metric-card">
      <div className={`metric-icon ${tone}`}><Icon size={16} /></div>
      <div className="metric-copy">
        <span>{label}</span>
        <strong>{value}{unit && <small>{unit}</small>}</strong>
      </div>
    </div>
  );
}

function DataBadge({ origin }: { origin: string }) {
  return <span className={`data-badge ${origin.toLowerCase()}`}><span />{originLabel(origin)}</span>;
}

function MapPanel({ flood, roads, buildings, infrastructure, shelters, showLayers, eventLabel }: { flood: GeoJson; roads: GeoJson; buildings: GeoJson; infrastructure: GeoJson; shelters: GeoJson; showLayers: Record<string, boolean>; eventLabel: string }) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: { version: 8, sources: {}, layers: [{ id: "background", type: "background", paint: { "background-color": "#e8f0f0" } }] },
      center: [127.33, 36.63],
      zoom: 12.8,
      attributionControl: false,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.on("load", () => {
      map.addSource("flood", { type: "geojson", data: flood as never });
      map.addLayer({ id: "flood-fill", type: "fill", source: "flood", paint: { "fill-color": "#ef6b5b", "fill-opacity": 0.28 } });
      map.addLayer({ id: "flood-line", type: "line", source: "flood", paint: { "line-color": "#c8453b", "line-width": 2, "line-dasharray": [2, 1] } });
      map.addSource("roads", { type: "geojson", data: roads as never });
      map.addLayer({ id: "roads-line", type: "line", source: "roads", paint: { "line-color": "#677580", "line-width": 3, "line-opacity": 0.7 } });
      map.addSource("buildings", { type: "geojson", data: buildings as never });
      map.addLayer({ id: "buildings-point", type: "circle", source: "buildings", paint: { "circle-color": "#315c73", "circle-radius": 6, "circle-stroke-width": 2, "circle-stroke-color": "#fff" } });
      map.addSource("infrastructure", { type: "geojson", data: infrastructure as never });
      map.addLayer({ id: "infrastructure-point", type: "circle", source: "infrastructure", paint: { "circle-color": "#efae42", "circle-radius": 7, "circle-stroke-width": 2, "circle-stroke-color": "#fff" } });
      map.addSource("shelters", { type: "geojson", data: shelters as never });
      map.addLayer({ id: "shelters-point", type: "circle", source: "shelters", paint: { "circle-color": "#2e9d76", "circle-radius": 7, "circle-stroke-width": 2, "circle-stroke-color": "#fff" } });
      const bounds = new maplibregl.LngLatBounds();
      flood.features.forEach((feature) => {
        const coordinates = feature.geometry.coordinates as number[][][];
        coordinates[0]?.forEach(([lng, lat]) => bounds.extend([lng, lat]));
      });
      if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: 80, duration: 0 });
    });
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; };
  }, [flood, roads, buildings, infrastructure, shelters]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    Object.entries(showLayers).forEach(([key, visible]) => {
      const layerId = `${key}-${key === "flood" ? "fill" : key === "roads" ? "line" : "point"}`;
      if (map.getLayer(layerId)) map.setLayoutProperty(layerId, "visibility", visible ? "visible" : "none");
      if (key === "flood" && map.getLayer("flood-line")) map.setLayoutProperty("flood-line", "visibility", visible ? "visible" : "none");
    });
  }, [showLayers]);

  return <div className="map-panel"><div ref={mapContainer} className="map-canvas" /><div className="map-label"><span className="pulse-dot" /> {eventLabel}</div><div className="map-legend"><div><i className="legend-flood" />Flood Extent</div><div><i className="legend-road" />Road</div><div><i className="legend-infra" />Critical Facility</div><div><i className="legend-shelter" />Shelter</div></div></div>;
}

export default function App() {
  const [events, setEvents] = useState<FloodEvent[]>([]);
  const [event, setEvent] = useState<FloodEvent | null>(null);
  const [flood, setFlood] = useState<GeoJson>(emptyGeoJson);
  const [roads, setRoads] = useState<GeoJson>(emptyGeoJson);
  const [buildings, setBuildings] = useState<GeoJson>(emptyGeoJson);
  const [infrastructure, setInfrastructure] = useState<GeoJson>(emptyGeoJson);
  const [shelters, setShelters] = useState<GeoJson>(emptyGeoJson);
  const [timeline, setTimeline] = useState<Observation[]>([]);
  const [baseline, setBaseline] = useState<ExposureMetrics | null>(null);
  const [scenario, setScenario] = useState<ScenarioResult | null>(null);
  const [interventionType, setInterventionType] = useState<InterventionType>("SHELTER_OPEN");
  const [scenarioName, setScenarioName] = useState("대피소 추가 개방안");
  const [timeIndex, setTimeIndex] = useState(2);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showLayers, setShowLayers] = useState({ flood: true, roads: true, buildings: true, infrastructure: true, shelters: true });
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [safetyApiKey, setSafetyApiKey] = useState(() => localStorage.getItem("floodops.safetyDataApiKey") ?? "");
  const [apiTestState, setApiTestState] = useState<"idle" | "testing" | "success" | "error">("idle");
  const [apiTestMessage, setApiTestMessage] = useState("");

  useEffect(() => {
    api.getEvents()
      .then(async (events) => {
        const nextEvent = events[0];
        setEvents(events);
        const [nextFlood, nextTimeline, nextLayers, nextBaseline] = await Promise.all([api.getFlood(nextEvent.id), api.getTimeline(nextEvent.id), api.getLayers(nextEvent.id), api.getBaseline(nextEvent.id)]);
        setEvent(nextEvent); setFlood(nextFlood); setTimeline(nextTimeline); setBuildings(nextLayers.buildings); setRoads(nextLayers.roads); setInfrastructure(nextLayers.infrastructure); setShelters(nextLayers.shelters); setBaseline(nextBaseline.result); setTimeIndex(nextTimeline.length - 1);
      })
      .catch(() => setError("API에 연결할 수 없습니다. backend를 먼저 실행해 주세요."))
      .finally(() => setLoading(false));
  }, []);

  async function selectEvent(eventId: string) {
    const nextEvent = events.find((item) => item.id === eventId);
    if (!nextEvent) return;
    setLoading(true);
    setError(null);
    try {
      const [nextFlood, nextTimeline, nextLayers, nextBaseline] = await Promise.all([api.getFlood(nextEvent.id), api.getTimeline(nextEvent.id), api.getLayers(nextEvent.id), api.getBaseline(nextEvent.id)]);
      setEvent(nextEvent); setFlood(nextFlood); setTimeline(nextTimeline); setBuildings(nextLayers.buildings); setRoads(nextLayers.roads); setInfrastructure(nextLayers.infrastructure); setShelters(nextLayers.shelters); setBaseline(nextBaseline.result); setScenario(null); setTimeIndex(Math.max(0, nextTimeline.length - 1));
    } catch {
      setError("사건 데이터를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }

  function saveSafetyApiKey() {
    localStorage.setItem("floodops.safetyDataApiKey", safetyApiKey.trim());
    setApiTestState("idle");
    setApiTestMessage("키가 이 브라우저에 저장되었습니다.");
  }

  async function testSafetyApiKey() {
    if (!safetyApiKey.trim()) {
      setApiTestState("error");
      setApiTestMessage("서비스 키를 입력하세요.");
      return;
    }
    setApiTestState("testing");
    try {
      const result = await api.testSafetyDataApi(safetyApiKey.trim());
      setApiTestState(result.connected ? "success" : "error");
      setApiTestMessage(`${result.message} (${result.result_code || "no code"})`);
    } catch {
      setApiTestState("error");
      setApiTestMessage("API 연결 요청에 실패했습니다.");
    }
  }

  const currentObservation = timeline[timeIndex];
  const currentRainfall = useMemo(() => timeline.filter((item) => item.observation_type === "rainfall").at(-1), [timeline]);
  const currentWaterLevel = useMemo(() => timeline.filter((item) => item.observation_type === "water_level").at(-1), [timeline]);

  async function handleScenario() {
    setScenario(null);
    try { if (event) setScenario(await api.createScenario(scenarioName, interventionType, event.id)); } catch { setError("시나리오를 생성하지 못했습니다."); }
  }

  if (loading) return <div className="app-state"><Activity className="spin" /><strong>FloodOps를 준비하는 중입니다</strong><span>사건과 공간 레이어를 불러오고 있습니다.</span></div>;
  if (error && !event) return <div className="app-state error-state"><AlertTriangle /><strong>연결이 필요합니다</strong><span>{error}</span><button onClick={() => window.location.reload()}>다시 시도</button></div>;

  const displayMetrics = scenario?.result ?? baseline;
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><div className="brand-mark"><Waves size={19} /></div><div><strong>FloodOps</strong><span>DECISION DIGITAL TWIN</span></div></div>
        <div className="topbar-context"><span className="status-dot" /> Demo workspace <span className="divider" /> <span>Last sync 08:42:16</span></div>
        <button className="icon-button" title="도움말"><CircleHelp size={18} /></button>
        <div className="topbar-actions"><button className="icon-button" title="API 설정" onClick={() => setSettingsOpen(true)}><Settings2 size={18} /></button><button className="icon-button" title="도움말"><CircleHelp size={18} /></button></div>
      </header>
      <main className="workspace">
        <aside className="sidebar">
          <div className="sidebar-scroll">
            <section className="section-block event-block">
              <div className="eyebrow">EVENT / INCIDENT</div>
              <button className="event-select"><span className="event-pin"><MapPin size={15} /></span><span><strong>{event?.name}</strong><small>{event?.location}</small></span><ChevronDown size={15} /></button>
              <div className="event-picker"><span className="event-pin"><MapPin size={15} /></span><select value={event?.id ?? ""} onChange={(e) => void selectEvent(e.target.value)} aria-label="사건 선택">{events.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.location}</option>)}</select><ChevronDown size={15} /></div>
              <div className="event-meta"><span><Clock3 size={13} /> {event?.started_at.slice(0, 10)}</span><DataBadge origin={event?.origin ?? "SIMULATED"} /></div>
              <p className="data-note">{event?.data_status}</p>
              <p className="event-analysis"><strong>{event?.data_year} · {event?.theme}</strong><span>{event?.analysis_flow}</span><small>분석 대상: {event?.focus_feature}</small><small>{event?.source}</small></p>
            </section>
            <section className="section-block">
              <div className="section-heading"><div><div className="eyebrow">LIVE CONDITIONS</div><h2>현재 상황</h2></div><span className="live-tag"><span />LIVE</span></div>
              <div className="condition-grid"><div><span>강우량</span><strong>{currentRainfall?.value.toFixed(1) ?? "--"} <em>mm/h</em></strong></div><div><span>수위</span><strong>{currentWaterLevel?.value.toFixed(1) ?? "--"} <em>m</em></strong></div><div><span>경보 단계</span><strong className="warning-text">주의</strong></div><div><span>관측 품질</span><strong className="good-text">{currentObservation?.quality_flag === "SIMULATED" ? "추정" : "양호"}</strong></div></div>
            </section>
            <section className="section-block layers-block">
              <div className="section-heading"><div><div className="eyebrow">MAP LAYERS</div><h2>분석 레이어</h2></div><Layers3 size={16} className="muted-icon" /></div>
              {([['flood', 'Flood Extent', '홍수 범위'], ['roads', 'Road Network', '도로 네트워크'], ['buildings', 'Buildings', '건물'], ['infrastructure', 'Critical Facilities', '핵심 시설'], ['shelters', 'Shelters', '대피소']] as const).map(([key, label, sub]) => <label className="layer-row" key={key}><input type="checkbox" checked={showLayers[key]} onChange={(e) => setShowLayers((state) => ({ ...state, [key]: e.target.checked }))} /><span className={`layer-swatch ${key}`} /><span><strong>{label}</strong><small>{sub}</small></span><Check size={14} className="check-icon" /></label>)}
            </section>
            <section className="section-block replay-block">
              <div className="section-heading"><div><div className="eyebrow">TIME WINDOW</div><h2>관측 타임라인</h2></div><span className="history-tag"><Clock3 size={12} /> HISTORY</span></div>
              <div className="timeline-readout"><strong>{currentObservation?.timestamp.slice(11, 16) ?? "--:--"}</strong><span>{currentObservation?.observation_type === "rainfall" ? "강우 관측" : "수위 관측"}</span></div>
              <input className="range-input" type="range" min="0" max={Math.max(0, timeline.length - 1)} value={timeIndex} onChange={(e) => setTimeIndex(Number(e.target.value))} />
              <div className="timeline-labels"><span>{timeline[0]?.timestamp.slice(11, 16)}</span><span>{timeline.at(-1)?.timestamp.slice(11, 16)}</span></div>
              <button className="secondary-button" disabled><Play size={14} /> Historical Replay · Portfolio V1</button>
            </section>
          </div>
          <div className="sidebar-footer"><div className="footer-lock"><Shield size={14} /><span>Decision workspace</span></div><span>v0.1 MVP</span></div>
        </aside>
        <section className="main-canvas">
          <div className="map-wrap"><MapPanel flood={flood} roads={roads} buildings={buildings} infrastructure={infrastructure} shelters={shelters} showLayers={showLayers} eventLabel={`${event?.data_year} ${event?.name} · ${event?.location}`} /><div className="map-toolbar"><button className="tool-button active" title="레이어"><Layers3 size={16} /></button><button className="tool-button" title="분석 설정"><SlidersHorizontal size={16} /></button></div></div>
          <div className="analysis-panel">
            <div className="analysis-head"><div><div className="eyebrow">EXPOSURE ANALYSIS <span className="inline-dot" /> DERIVED</div><h1>침수 영향 요약</h1><p>현재 Flood Extent와 공간 데이터의 교차 분석 결과입니다.</p></div><div className="analysis-actions"><DataBadge origin="DERIVED" /><button className="ghost-button" title="분석 새로고침"><Activity size={15} /> 새로고침</button></div></div>
            <div className="metrics-grid"><Metric icon={Droplets} label="침수 면적" value={displayMetrics ? displayMetrics.flooded_area_km2.toFixed(2) : "--"} unit="km²" tone="risk" /><Metric icon={Building2} label="노출 인구" value={displayMetrics ? formatNumber(displayMetrics.exposed_population) : "--"} unit="명" tone="risk" /><Metric icon={Route} label="영향 도로" value={displayMetrics ? displayMetrics.affected_road_length_km.toFixed(1) : "--"} unit="km" /><Metric icon={AlertTriangle} label="핵심 시설" value={displayMetrics ? String(displayMetrics.critical_infrastructure) : "--"} unit="곳" tone="risk" /></div>
            <div className="scenario-section"><div className="scenario-title"><div><div className="eyebrow">WHAT-IF SCENARIO</div><h2>방재 개입 비교</h2><p>Baseline과 선택한 개입의 예상 차이를 비교합니다.</p></div>{scenario && <span className="scenario-created"><Check size={13} /> 비교 완료</span>}</div><div className="scenario-form"><label className="field"><span>시나리오 이름</span><input value={scenarioName} onChange={(e) => setScenarioName(e.target.value)} /></label><label className="field"><span>개입 유형</span><select value={interventionType} onChange={(e) => setInterventionType(e.target.value as InterventionType)}>{interventionOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label><button className="primary-button" onClick={handleScenario}><ArrowDownRight size={16} /> 결과 계산</button></div><div className="selected-intervention"><span className="intervention-icon"><Shield size={15} /></span><span><strong>{interventionOptions.find((option) => option.value === interventionType)?.label}</strong><small>{interventionOptions.find((option) => option.value === interventionType)?.hint}</small></span><DataBadge origin="SIMULATED" /></div>{scenario && <div className="comparison"><div className="comparison-head"><div><span>BASELINE</span><strong>{scenario.baseline.exposed_population.toLocaleString()}명</strong></div><div className="comparison-arrow"><ArrowDownRight size={18} /></div><div className="comparison-result"><span>INTERVENTION</span><strong>{scenario.result.exposed_population.toLocaleString()}명</strong></div><div className="reduction"><strong>-{scenario.reduction_percent}%</strong><span>노출 인구 감소</span></div></div><div className="comparison-bar"><span style={{ width: `${Math.max(12, 100 - scenario.reduction_percent)}%` }} /></div><div className="assumption-note"><AlertTriangle size={14} /><span>{scenario.assumptions[0]} · {scenario.assumptions[1]}</span></div></div>}</div>
          </div>
        </section>
      </main>
      {settingsOpen && <div className="modal-backdrop" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) setSettingsOpen(false); }}><section className="settings-modal" role="dialog" aria-modal="true" aria-labelledby="settings-title"><div className="settings-head"><div><div className="eyebrow">DATA INTEGRATION</div><h2 id="settings-title">재난안전데이터공유플랫폼</h2></div><button className="icon-button light" title="닫기" onClick={() => setSettingsOpen(false)}><X size={18} /></button></div><p className="settings-copy">수위·침수흔적도 API 서비스 키를 입력합니다. 키는 이 브라우저의 localStorage에만 저장됩니다.</p><label className="settings-field"><span><KeyRound size={13} /> 서비스 키</span><input type="password" value={safetyApiKey} onChange={(e) => setSafetyApiKey(e.target.value)} placeholder="서비스 키 입력" autoComplete="off" /></label><div className="settings-links"><a href="https://www.safetydata.go.kr/" target="_blank" rel="noreferrer">발급 페이지 <ExternalLink size={12} /></a><span>대상: DSSP-IF-00007 수위자료 10분</span></div>{apiTestMessage && <div className={`api-test-message ${apiTestState}`}><span>{apiTestState === "success" ? <CheckCircle2 size={15} /> : <AlertTriangle size={15} />}</span>{apiTestMessage}</div>}<div className="settings-actions"><button className="secondary-button" onClick={saveSafetyApiKey}><Check size={14} /> 저장</button><button className="primary-button" onClick={() => void testSafetyApiKey()} disabled={apiTestState === "testing"}>{apiTestState === "testing" ? "확인 중..." : "연결 테스트"}</button></div></section></div>}
    </div>
  );
}
