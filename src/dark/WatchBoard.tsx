import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import maplibregl, { type GeoJSONSource, type MapLayerMouseEvent } from "maplibre-gl";
import { Activity, ArrowRight, CloudRain, Gauge, Radio, RotateCcw, TrendingUp, X } from "lucide-react";
import * as api from "../api";
import type { AgentView, WatchChanges, WatchOverview, WatchRainIntensity, WatchRainNearby, WatchRainReading, WatchStage, WatchStation, WatchStationDetail } from "../types";
import { AgentDock } from "./DarkConsole";
import { FloodOpsLogo } from "./Landing";
import "./dark.css";
import "./twin.css";
import "./watch.css";

/*
 * 전국 감시 보드. 단위는 관측소이고, 각 관측소를 그 관측소의 공식 기준 수위로 판정한다.
 * 관측소에 연결된 시설(지하차도 등)은 "감시 등급"으로만 보여주고, 운영 등록 시설만 시설별 규칙(#twin)으로 이어진다.
 * 에이전트 답에 화면 이동(view)이 실리면 지도와 선택이 따라간다.
 */

const STAGE_COLOR: Record<WatchStage, string> = { unrated: "#3a4a63", normal: "#38bdf8", attention: "#60a5fa", advisory: "#fbbf24", warning: "#f97316", planned_flood: "#f87171" };
const STAGE_KO: Record<WatchStage, string> = { unrated: "기준 없음", normal: "정상", attention: "관심", advisory: "주의보", warning: "경보", planned_flood: "계획홍수위" };
const STAGE_ORDER: WatchStage[] = ["unrated", "normal", "attention", "advisory", "warning", "planned_flood"];
// Rain uses a violet scale so it never reads as a gauge stage colour.
const RAIN_COLOR: Record<WatchRainIntensity, string> = { none: "#3a4a63", light: "#a5b4fc", moderate: "#818cf8", heavy: "#a855f7", very_heavy: "#e879f9" };
const REGION_CENTER: Record<string, [number, number]> = {
  서울: [126.98, 37.56], 부산: [129.05, 35.18], 대구: [128.6, 35.87], 인천: [126.7, 37.46], 광주: [126.85, 35.16], 대전: [127.38, 36.35], 울산: [129.31, 35.54],
  세종: [127.29, 36.48], 경기: [127.2, 37.45], 강원: [128.3, 37.6], 충북: [127.7, 36.75], 충남: [126.9, 36.5], 전북: [127.1, 35.75], 전남: [126.9, 34.85],
  경북: [128.75, 36.4], 경남: [128.3, 35.35], 제주: [126.55, 33.4],
};
const ESRI = "https://services.arcgisonline.com/ArcGIS/rest/services/Canvas";
const REPLAY_PRESET = { at: "2023-07-15T06:00:00", label: "2023.07.15 06:00", note: "오송 사건 아침" };

const clock = (iso?: string | null) => (iso ? `${iso.slice(5, 10).replace("-", ".")} ${iso.slice(11, 16)}` : "—");
const num = (value: number | null | undefined, digits = 2) => (value === null || value === undefined ? "—" : value.toFixed(digits));

function readParam(key: string): string | null {
  const match = window.location.hash.match(new RegExp(`[?&]${key}=([^&]+)`));
  return match ? decodeURIComponent(match[1]) : null;
}

function writeParams(params: Record<string, string | null>) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => { if (value) search.set(key, value); });
  const text = search.toString();
  window.location.hash = text ? `watch?${text}` : "watch";
}

export default function WatchBoard() {
  const [at, setAt] = useState<string | null>(() => readParam("at"));
  const [region, setRegion] = useState<string | null>(() => readParam("region"));
  const [minStage, setMinStage] = useState<WatchStage | null>(() => (readParam("stage") as WatchStage | null));
  const [overview, setOverview] = useState<WatchOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(() => readParam("station"));
  const [detail, setDetail] = useState<WatchStationDetail | null>(null);
  const [changes, setChanges] = useState<WatchChanges | null>(null);
  const [flyTo, setFlyTo] = useState<{ center: [number, number]; zoom: number } | null>(null);
  const [showRain, setShowRain] = useState(true);

  useEffect(() => {
    const onHash = () => { setAt(readParam("at")); setRegion(readParam("region")); setMinStage(readParam("stage") as WatchStage | null); setSelected(readParam("station")); };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // 전체 관측소는 지도에 다 올리고(필터는 화면에서), 목록은 서버 정렬을 쓴다.
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const load = () => {
      api.getWatchOverview({ at, limit: 2000 }, controller.signal)
        .then((data) => { if (active) { setOverview(data); setError(null); } })
        .catch((reason: Error) => { if (active && !controller.signal.aborted) setError(reason.message); });
      api.getWatchChanges({ at, since_min: 60 }, controller.signal).then((data) => { if (active) setChanges(data); }).catch(() => undefined);
    };
    load();
    const timer = at ? null : window.setInterval(load, 5 * 60_000);
    return () => { active = false; controller.abort(); if (timer !== null) window.clearInterval(timer); };
  }, [at]);

  useEffect(() => {
    if (!selected) { setDetail(null); return undefined; }
    let active = true;
    api.getWatchStation(selected, at).then((data) => { if (active) setDetail(data); }).catch(() => { if (active) setDetail(null); });
    return () => { active = false; };
  }, [selected, at]);

  // A link that already names a station or region (shared URL, agent view) should open on it, not on the whole country.
  const framed = useRef(false);
  useEffect(() => {
    if (!overview || framed.current) return;
    framed.current = true;
    const row = selected ? overview.stations.find((item) => item.code === selected) : null;
    if (row) setFlyTo({ center: [row.lon, row.lat], zoom: 12 });
    else if (region && REGION_CENTER[region]) setFlyTo({ center: REGION_CENTER[region], zoom: 8 });
  }, [overview, selected, region]);

  // Every count on the side card is over the chosen region only; the stage filter narrows the list and the map, not the counts.
  const scoped = useMemo(() => (overview ? overview.stations.filter((row) => !region || row.region === region) : []), [overview, region]);
  const visible = useMemo(() => {
    const floor = minStage ? STAGE_ORDER.indexOf(minStage) : -1;
    return scoped.filter((row) => floor < 0 || (row.stage && STAGE_ORDER.indexOf(row.stage) >= floor));
  }, [scoped, minStage]);
  const counts = useMemo(() => {
    const atLeast: Record<WatchStage, number> = { unrated: 0, normal: 0, attention: 0, advisory: 0, warning: 0, planned_flood: 0 };
    let rising = 0;
    let facilities = 0;
    let operational = 0;
    let underHeavyRain = 0;
    scoped.forEach((row) => {
      if (row.stage) STAGE_ORDER.forEach((stage, index) => { if (index > 1 && STAGE_ORDER.indexOf(row.stage as WatchStage) >= index) atLeast[stage] += 1; });
      if ((row.rate_m_per_10min ?? 0) >= 0.02) rising += 1;
      facilities += row.facilities.length;
      operational += row.facilities.filter((item) => item.tier === "operational").length;
      if ((row.rain_nearby?.intensity_mm_h ?? 0) >= 15) underHeavyRain += 1;
    });
    return { atLeast, rising, facilities, operational, underHeavyRain };
  }, [scoped]);
  const rain = overview?.rain ?? null;
  const rainScoped = useMemo(() => (rain ? rain.stations.filter((row) => !region || row.region === region) : []), [rain, region]);
  const heavyRain = rainScoped.filter((row) => (row.intensity_mm_h ?? 0) >= 15).length;
  const priority = useMemo(() => visible.filter((row) => row.stage && row.stage !== "unrated" && row.stage !== "normal").slice(0, 12), [visible]);

  const select = useCallback((code: string | null, fly = true) => {
    setSelected(code);
    writeParams({ at, region, stage: minStage, station: code });
    const row = code ? overview?.stations.find((item) => item.code === code) : null;
    if (row && fly) setFlyTo({ center: [row.lon, row.lat], zoom: 12 });
  }, [at, region, minStage, overview]);

  const applyView = useCallback((view: AgentView) => {
    const nextRegion = view.region ?? (view.station_code ? region : null);
    setRegion(nextRegion);
    setMinStage(view.min_stage ?? null);
    setSelected(view.station_code ?? null);
    if (view.layer === "rain") setShowRain(true);
    writeParams({ at, region: nextRegion, stage: view.min_stage ?? null, station: view.station_code ?? null });
    if (view.center) setFlyTo({ center: view.center, zoom: view.zoom ?? 12 });
    else if (view.region && REGION_CENTER[view.region]) setFlyTo({ center: REGION_CENTER[view.region], zoom: 8 });
    else if (!view.region) setFlyTo({ center: [127.8, 36.3], zoom: 6.4 });
  }, [at, region]);

  const changeRegion = (next: string | null) => { setRegion(next); writeParams({ at, region: next, stage: minStage, station: selected }); if (next && REGION_CENTER[next]) setFlyTo({ center: REGION_CENTER[next], zoom: 8 }); else if (!next) setFlyTo({ center: [127.8, 36.3], zoom: 6.4 }); };
  const changeStage = (next: WatchStage | null) => { setMinStage(next); writeParams({ at, region, stage: next, station: selected }); };
  const changeAt = (next: string | null) => { setAt(next); writeParams({ at: next, region, stage: minStage, station: selected }); };

  const replay = Boolean(at) || overview?.mode === "replay";
  const stationKey = selected ?? "";

  return (
    <div className="dk-root wb-root">
      <header className="dk-topbar">
        <div className="dk-brand">
          <a className="dk-brand-mark" href="#intro" title="소개" aria-label="소개"><FloodOpsLogo size={30} /></a>
          <div>
            <h1>하천 접점 시설 감시 보드</h1>
            <p>FloodOps · 관측소마다 공식 기준 수위로 지금 단계와 남은 시간을 보고, 연결 시설을 함께 봅니다</p>
          </div>
        </div>
        <nav className="dk-view-tabs" aria-label="FloodOps 화면">
          <a className="active" href="#watch" aria-current="page">감시 보드</a>
          <a href="#twin">운영 시설</a>
          <a href="#cases">검증</a>
          <a href="#intro">소개</a>
        </nav>
        <div className="dk-status">
          <span className="dk-chip tw-mode" data-mode={replay ? "replay" : "live"}>
            {replay ? <RotateCcw size={12} /> : <Radio size={12} />}
            {replay ? "저장 자료 재생" : "실시간 관측"}
            <small>{overview ? (replay ? `${overview.stations_total}곳` : `${overview.stations_observed}곳 · ${clock(overview.observed_at)}`) : "불러오는 중"}</small>
          </span>
        </div>
      </header>

      <main className="wb-main">
        <aside className="wb-side" aria-label="현황">
          <section className="tw-card">
            <p className="tw-eyebrow">지금 · {overview ? clock(overview.observed_at ?? overview.at) : "—"} 관측 기준{region ? ` · ${region}` : " · 전국"}</p>
            <div className="wb-counts" role="list">
              {(["planned_flood", "warning", "advisory", "attention"] as WatchStage[]).map((stage) => (
                <button key={stage} type="button" role="listitem" className={minStage === stage ? "active" : ""} style={{ ["--c" as string]: STAGE_COLOR[stage] }} onClick={() => changeStage(minStage === stage ? null : stage)}>
                  <strong>{counts.atLeast[stage]}</strong><span>{STAGE_KO[stage]} 이상</span>
                </button>
              ))}
            </div>
            <div className="wb-meta">
              <span><TrendingUp size={12} /> 상승 중 {counts.rising}곳</span>
              <span><Gauge size={12} /> 연결 시설 {counts.facilities}곳 · 운영 {counts.operational}</span>
            </div>
            {rain && (
              <button type="button" className={`wb-rain-toggle${showRain ? " active" : ""}`} aria-pressed={showRain} onClick={() => setShowRain((value) => !value)}
                title={`${rain.basis} · 지도에 강우 ${showRain ? "숨기기" : "보이기"}`}>
                <CloudRain size={13} />
                {!rain.available ? <span>강우 자료 없음</span> : (
                  <span>강우 중 <b>{rainScoped.length}</b>곳 · 강한 비 이상 <b>{heavyRain}</b>곳 · 강한 비 아래 하천 관측소 <b>{counts.underHeavyRain}</b>곳</span>
                )}
              </button>
            )}
            <div className="wb-filters">
              <label>지역
                <select value={region ?? ""} onChange={(event) => changeRegion(event.target.value || null)}>
                  <option value="">전국</option>
                  {overview?.regions.map((item) => <option key={item.region} value={item.region}>{item.region} · {item.stations}</option>)}
                </select>
              </label>
              <label>시각
                <select value={at ?? ""} onChange={(event) => changeAt(event.target.value || null)}>
                  <option value="">지금 (실시간)</option>
                  <option value={REPLAY_PRESET.at}>{REPLAY_PRESET.label} · {REPLAY_PRESET.note}</option>
                </select>
              </label>
            </div>
            {overview?.error && <small className="dk-error">{overview.error}</small>}
            {error && <small className="dk-error">{error}</small>}
          </section>

          <section className="tw-card wb-priority" aria-label="우선순위">
            <p className="tw-eyebrow">우선순위 · 단계 → 계획홍수위까지 남은 분</p>
            {!overview && <p className="ub-note"><Activity className="spin" size={14} /> 관측을 불러오는 중…</p>}
            {overview && !priority.length && <p className="ub-note">{minStage || region ? "조건에 맞는 관측소가 없습니다." : "관심 수위 이상인 관측소가 없습니다. 모두 정상 범위입니다."}</p>}
            <ol>
              {priority.map((row, index) => (
                <li key={row.code} className={row.code === selected ? "is-selected" : ""}>
                  <button type="button" onClick={() => select(row.code)} style={{ ["--c" as string]: STAGE_COLOR[row.stage ?? "unrated"] }}>
                    <b>{index + 1}</b>
                    <span className="wb-pri-name">{row.name}<small>{row.region}{row.facilities.length ? ` · 시설 ${row.facilities.length}` : ""}</small></span>
                    <span className="wb-pri-stage">{STAGE_KO[row.stage ?? "unrated"]}</span>
                    <span className="wb-pri-min">{row.minutes_to_planned_flood === null ? "—" : row.minutes_to_planned_flood === 0 ? "도달" : `${row.minutes_to_planned_flood}분`}</span>
                  </button>
                </li>
              ))}
            </ol>
          </section>

          {rain?.available && (
            <section className="tw-card wb-changes wb-rain" aria-label="비 많이 오는 곳">
              <p className="tw-eyebrow">비 많이 오는 곳 · {clock(rain.observed_at)} · {rain.mode === "live" ? "10분 강우" : "1시간 강우"}</p>
              {!rainScoped.length ? <p className="ub-note">{region ? `${region}에는` : "지금"} 비가 관측된 강우 관측소가 없습니다.</p> : (
                <ul>
                  {rainScoped.slice(0, 5).map((row) => (
                    <li key={row.code}>
                      <button type="button" onClick={() => { setShowRain(true); setFlyTo({ center: [row.lon, row.lat], zoom: 10 }); }} style={{ ["--c" as string]: RAIN_COLOR[row.intensity] }}>
                        <i className="wb-rain-dot" /> {row.name} <small>{rainAmount(row)} · {row.intensity_label}</small>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              <small className="ub-note">{rain.basis}. 비는 시간차를 두고 하천 수위에 반영되며, 강우만으로 단계를 바꾸지 않습니다.</small>
            </section>
          )}

          {changes && (
            <section className="tw-card wb-changes" aria-label="최근 변화">
              <p className="tw-eyebrow">최근 {changes.since_min}분 변화{changes.compared_to ? ` · ${clock(changes.compared_to)} 대비` : ""}</p>
              {!changes.available ? <p className="ub-note">{changes.note}</p> : (
                <ul>
                  {changes.stage_up.slice(0, 5).map((item) => <li key={`u${item.code}`}><button type="button" onClick={() => select(item.code)}>▲ {item.name} <small>{STAGE_KO[item.from]}→{STAGE_KO[item.to]} · {item.delta_m > 0 ? "+" : ""}{item.delta_m} m</small></button></li>)}
                  {changes.new_rising.slice(0, 3).map((item) => <li key={`r${item.code}`}><button type="button" onClick={() => select(item.code)}>↗ {item.name} <small>{item.rate_m_per_10min > 0 ? "+" : ""}{item.rate_m_per_10min} m/10분</small></button></li>)}
                  {!changes.stage_up.length && !changes.new_rising.length && <li><small className="ub-note">단계가 오른 관측소가 없습니다.</small></li>}
                </ul>
              )}
            </section>
          )}
        </aside>

        <section className="wb-map-wrap" aria-label="전국 지도">
          <WatchMap stations={overview?.stations ?? []} visible={visible} selected={selected} onSelect={(code) => select(code, false)} flyTo={flyTo} rain={showRain ? rain?.stations ?? [] : []} />
          {selected && (
            <aside className="wb-overlay" aria-label="선택 관측소">
              <button type="button" className="wb-overlay-close" aria-label="닫기" onClick={() => select(null, false)}><X size={14} /></button>
              {!detail ? <section className="tw-card"><p className="ub-note"><Activity className="spin" size={14} /> {stationKey} 불러오는 중…</p></section> : <StationCard detail={detail} />}
            </aside>
          )}
          <div className="wb-legend">
            {(["planned_flood", "warning", "advisory", "attention", "normal", "unrated"] as WatchStage[]).map((stage) => <span key={stage}><i style={{ background: STAGE_COLOR[stage] }} />{STAGE_KO[stage]}</span>)}
            <span><i className="wb-legend-facility" />연결 시설</span>
            {rain && <button type="button" className={`wb-legend-rain${showRain ? " active" : ""}`} aria-pressed={showRain} onClick={() => setShowRain((value) => !value)}><i />강우</button>}
          </div>
        </section>

        <aside className="wb-agent-panel" aria-label="대응 에이전트">
          <div className="wb-agent-head">
            <p className="tw-eyebrow">대응 에이전트 · 보드 운영</p>
            <h2>물어보면 화면이 따라갑니다</h2>
            <p className="ub-note">"충북 보여줘", "가장 위험한 곳 5곳", "지금 비 많이 오는 곳", "상황 보고 초안". 수치는 서버 도구가 계산하고 AI는 설명만 합니다. 지역·관측소·단계는 질문에 쓴 단어만 조건으로 씁니다.</p>
          </div>
          <AgentDock eventId="osong-2023" board="watch" facilityAt={at} onView={applyView} />
        </aside>
      </main>
    </div>
  );
}

function StationCard({ detail }: { detail: WatchStationDetail }) {
  const stage = detail.stage ?? "unrated";
  const tone = STAGE_COLOR[stage];
  const levels = detail.levels_m;
  const operational = detail.facilities.filter((item) => item.tier === "operational");
  const watch = detail.facilities.filter((item) => item.tier === "watch");
  return (
    <>
      <section className="tw-card wb-station" style={{ ["--tone" as string]: tone }}>
        <p className="tw-eyebrow">관측소 · {detail.region} · {detail.flood_forecast ? "홍수예보 지점" : "일반 관측소"}</p>
        <h2>{detail.name}</h2>
        <div className="wb-stage-badge" style={{ color: tone, borderColor: tone }}>{STAGE_KO[stage]}</div>
        {detail.observation ? (
          <div className="ub-kpis tw-kpis">
            <div><strong>{num(detail.observation.water_level_m)} m</strong><span>수위 · {clock(detail.observation.time)} · {detail.observation.interval === "1H" ? "1시간" : "10분"} 자료</span></div>
            <div><strong>{detail.margin_to_planned_flood_m === null ? "—" : `${num(detail.margin_to_planned_flood_m)} m`}</strong><span>계획홍수위까지 여유</span></div>
            <div><strong>{detail.rate_m_per_10min === null ? "—" : `${detail.rate_m_per_10min > 0 ? "+" : ""}${num(detail.rate_m_per_10min, 3)}`}</strong><span>m/10분 · {detail.rise_label}{detail.rate_window_min ? ` · 최근 ${detail.rate_window_min}분` : ""}</span></div>
            <div><strong>{detail.minutes_to_planned_flood === null ? "—" : detail.minutes_to_planned_flood === 0 ? "도달" : `${detail.minutes_to_planned_flood}분`}</strong><span>현재 속도 기준선 · 예보 아님</span></div>
          </div>
        ) : <p className="ub-note">이 시각에는 관측값이 없습니다.</p>}
        {detail.observation && Object.keys(levels).length > 0 && <LevelBar level={detail.observation.water_level_m} levels={levels} />}
        {detail.quality !== "fresh" && <small className="dk-error">관측 품질: {detail.quality === "stale" ? `오래된 자료(${detail.observation?.age_min}분 전)` : detail.quality === "suspect" ? "급변(정합성 확인 필요)" : "관측 없음"}</small>}
        {detail.recent.length > 1 && <Sparkline points={detail.recent} levels={levels} tone={tone} />}
        <RainLine rain={detail.rain_nearby ?? null} />
      </section>
      <section className="tw-card wb-facilities" aria-label="연결 시설">
        <p className="tw-eyebrow">연결 시설 · 운영 {operational.length} · 감시 {watch.length}</p>
        {!detail.facilities.length && <p className="ub-note">이 관측소에 연결된 시설이 아직 없습니다.</p>}
        <ul>
          {operational.map((item) => (
            <li key={item.facility_id} className="is-operational">
              <a href="#twin"><span className="wb-tier operational">운영</span><strong>{item.name}</strong><small>시설별 규칙·백테스트 검증됨 → 통제 판단 보드</small><ArrowRight size={14} /></a>
            </li>
          ))}
          {watch.map((item) => (
            <li key={item.facility_id}>
              <span className="wb-tier watch">감시</span><strong>{item.name}</strong><small>{item.sgg ? `${item.sgg} · ` : ""}{item.distance_km !== null ? `관측소까지 ${item.distance_km} km` : ""} · 대표성 미검증</small>
            </li>
          ))}
        </ul>
        <small className="ub-note">감시 등급은 5 km 안 가장 가까운 관측소에 묶은 것이고, 그 관측소가 시설 유입을 대표하는지는 확인하지 않았습니다. 운영 등록은 유입 경로·대표 관측소·현장 계측·검증 사건 네 관문을 거칩니다.</small>
      </section>
    </>
  );
}

function rainAmount(row: Pick<WatchRainReading, "rain_10m_mm" | "rain_1h_mm" | "rain_1h_basis">) {
  const parts = [];
  if (row.rain_10m_mm !== null) parts.push(`10분 ${row.rain_10m_mm} mm`);
  // The last whole hour can read 0 mm while it is pouring now, so only a rolling or stored hour is shown.
  if (row.rain_1h_mm !== null && row.rain_1h_basis !== "last_hour") parts.push(`1시간 ${row.rain_1h_mm} mm`);
  return parts.join(" · ") || "—";
}

function RainLine({ rain }: { rain: WatchRainNearby | null }) {
  if (!rain) return <p className="wb-rainline ub-note"><CloudRain size={13} /> 10 km 안에 강우 관측값이 있는 관측소가 없습니다.</p>;
  return (
    <p className="wb-rainline" style={{ ["--c" as string]: RAIN_COLOR[rain.intensity] }}>
      <CloudRain size={13} />
      <span><span><b>{rain.intensity_label}</b>{rain.intensity !== "none" ? ` · ${rainAmount(rain)}` : ""}</span><small>근처 강우 {rain.name} · {rain.distance_km} km · {clock(rain.time)}</small></span>
    </p>
  );
}

function LevelBar({ level, levels }: { level: number; levels: Record<string, number> }) {
  const keys = ["attention", "advisory", "warning", "planned_flood"].filter((key) => key in levels);
  const max = Math.max(level, ...keys.map((key) => levels[key])) * 1.08 || 1;
  const pos = (value: number) => `${Math.min(100, Math.max(0, (value / max) * 100))}%`;
  // The side card is narrow, so the bar carries only the end marks and the thresholds are listed below it.
  const ends = keys.filter((key, index) => index === 0 || index === keys.length - 1);
  return (
    <div className="tw-levelbar wb-levelbar" role="img" aria-label="현재 수위와 관측소 기준 수위">
      <div className="tw-levelbar-track">
        <div className="tw-levelbar-fill" style={{ width: pos(level) }} />
        {keys.map((key) => <i key={key} className={`tw-levelbar-mark ${key}`} style={{ left: pos(levels[key]) }} title={`${STAGE_KO[key as WatchStage]} ${levels[key]} m`} />)}
        <b className="tw-levelbar-now" style={{ left: pos(level) }}>{level.toFixed(2)}</b>
      </div>
      <div className="tw-levelbar-labels">{ends.map((key) => <span key={key} style={{ left: pos(levels[key]) }}>{STAGE_KO[key as WatchStage]} {levels[key]}</span>)}</div>
      <small className="wb-thresholds">{keys.map((key) => `${STAGE_KO[key as WatchStage]} ${levels[key]}`).join(" · ")} m</small>
    </div>
  );
}

function Sparkline({ points, levels, tone }: { points: Array<{ time: string; water_level_m: number }>; levels: Record<string, number>; tone: string }) {
  const width = 300;
  const height = 70;
  const values = points.map((point) => point.water_level_m);
  const marks = ["advisory", "warning", "planned_flood"].filter((key) => key in levels).map((key) => levels[key]);
  const min = Math.min(...values, ...marks) - 0.2;
  const max = Math.max(...values, ...marks) + 0.2;
  const x = (index: number) => (index / Math.max(1, points.length - 1)) * width;
  const y = (value: number) => height - ((value - min) / (max - min || 1)) * height;
  const path = points.map((point, index) => `${index ? "L" : "M"}${x(index).toFixed(1)},${y(point.water_level_m).toFixed(1)}`).join(" ");
  return (
    <figure className="wb-spark">
      <figcaption className="tw-eyebrow">최근 {points.length}개 관측 · {clock(points[0].time)} → {clock(points[points.length - 1].time)}</figcaption>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="최근 수위 추이">
        {marks.map((mark) => <line key={mark} x1={0} x2={width} y1={y(mark)} y2={y(mark)} stroke="#3a4a63" strokeDasharray="3 4" />)}
        <path d={path} fill="none" stroke={tone} strokeWidth={2} />
        <circle cx={x(points.length - 1)} cy={y(values[values.length - 1])} r={3} fill={tone} />
      </svg>
    </figure>
  );
}

function WatchMap({ stations, visible, selected, onSelect, flyTo, rain }: { stations: WatchStation[]; visible: WatchStation[]; selected: string | null; onSelect: (code: string) => void; flyTo: { center: [number, number]; zoom: number } | null; rain: WatchRainReading[] }) {
  const elementRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const readyRef = useRef(false);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  // The latest data writer; the map calls it once its layers exist, whatever arrived first.
  const applyRef = useRef<() => void>(() => undefined);

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
          { id: "esri-dark", type: "raster", source: "esri-dark", paint: { "raster-opacity": 0.9 } },
          { id: "esri-dark-ref", type: "raster", source: "esri-dark-ref", paint: { "raster-opacity": 0.6 } },
        ],
      },
      center: [127.8, 36.3],
      zoom: 6.4,
      maxZoom: 15,
    });
    map.addControl(new maplibregl.AttributionControl({ compact: false, customAttribution: ["관측 © 한강홍수통제소 OpenAPI", "시설 © 국토교통부 · OSM"] }), "bottom-right");
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-left");
    const rainPopup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10 });
    // Layers go in as soon as the style is ready; waiting for "load" also waits on basemap tiles,
    // and a failed Esri tile can hold it back so the gauges never appear.
    const setup = () => {
      if (readyRef.current || mapRef.current !== map) return;
      map.addSource("stations", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addSource("facilities", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addSource("rain", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      // Rain sits under the gauges as soft violet halos sized by intensity (mm/h).
      map.addLayer({ id: "rain", type: "circle", source: "rain", paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 5, ["interpolate", ["linear"], ["get", "rate"], 0, 3, 15, 7, 60, 12], 11, ["interpolate", ["linear"], ["get", "rate"], 0, 10, 15, 22, 60, 36]],
        "circle-color": ["get", "color"], "circle-opacity": 0.42, "circle-blur": 0.35,
      } });
      map.on("mousemove", "rain", (event: MapLayerMouseEvent) => {
        const props = event.features?.[0]?.properties;
        if (props && !map.queryRenderedFeatures(event.point, { layers: ["stations"] }).length) rainPopup.setLngLat(event.lngLat).setHTML(`<strong>${props.name}</strong><br/>${props.label} · ${props.amount}`).addTo(map);
      });
      map.on("mouseleave", "rain", () => rainPopup.remove());
      map.addLayer({ id: "facilities", type: "circle", source: "facilities", paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 6, 2, 12, 5], "circle-color": "#0b1220", "circle-stroke-color": ["case", ["==", ["get", "tier"], "operational"], "#34d399", "#9aa9c2"], "circle-stroke-width": 1.5, "circle-opacity": 0.9 } });
      map.addLayer({ id: "stations", type: "circle", source: "stations", paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 5, ["case", [">=", ["get", "rank"], 3], 5, 3], 12, ["case", [">=", ["get", "rank"], 3], 10, 6]],
        "circle-color": ["get", "color"], "circle-opacity": ["case", ["boolean", ["get", "dim"], false], 0.25, 0.95],
        "circle-stroke-color": ["case", ["boolean", ["get", "selected"], false], "#ffffff", "#0b1220"], "circle-stroke-width": ["case", ["boolean", ["get", "selected"], false], 2.5, 0.8],
      } });
      map.on("click", "stations", (event: MapLayerMouseEvent) => { const code = event.features?.[0]?.properties?.code; if (code) onSelectRef.current(String(code)); });
      map.on("mouseenter", "stations", () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", "stations", () => { map.getCanvas().style.cursor = ""; });
      const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10 });
      map.on("mousemove", "stations", (event: MapLayerMouseEvent) => {
        const props = event.features?.[0]?.properties;
        if (!props) return;
        popup.setLngLat(event.lngLat).setHTML(`<strong>${props.name}</strong><br/>${props.stage_label} · ${props.level ?? "—"} m${props.minutes !== undefined && props.minutes !== null && props.minutes !== "" ? ` · ${props.minutes === 0 ? "계획홍수위 도달" : `${props.minutes}분`}` : ""}${Number(props.facilities) ? `<br/>연결 시설 ${props.facilities}` : ""}`).addTo(map);
      });
      map.on("mouseleave", "stations", () => popup.remove());
      readyRef.current = true;
      applyRef.current();
    };
    mapRef.current = map;
    if (map.isStyleLoaded()) setup();
    else { map.once("style.load", setup); map.once("load", setup); }
    return () => { map.remove(); mapRef.current = null; readyRef.current = false; };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return undefined;
    const visibleCodes = new Set(visible.map((row) => row.code));
    const apply = () => {
      const stationSource = map.getSource("stations") as GeoJSONSource | undefined;
      const facilitySource = map.getSource("facilities") as GeoJSONSource | undefined;
      const rainSource = map.getSource("rain") as GeoJSONSource | undefined;
      if (!stationSource || !facilitySource || !rainSource) return;
      rainSource.setData({
        type: "FeatureCollection",
        features: rain.filter((row) => (row.intensity_mm_h ?? 0) > 0).map((row) => ({
          type: "Feature" as const, geometry: { type: "Point" as const, coordinates: [row.lon, row.lat] },
          properties: { name: row.name, rate: row.intensity_mm_h ?? 0, color: RAIN_COLOR[row.intensity], label: row.intensity_label, amount: rainAmount(row) },
        })),
      });
      stationSource.setData({
        type: "FeatureCollection",
        features: stations.map((row) => ({
          type: "Feature", geometry: { type: "Point", coordinates: [row.lon, row.lat] },
          properties: { code: row.code, name: row.name, color: STAGE_COLOR[row.stage ?? "unrated"], rank: STAGE_ORDER.indexOf(row.stage ?? "unrated"), stage_label: STAGE_KO[row.stage ?? "unrated"],
            level: row.observation?.water_level_m ?? null, minutes: row.minutes_to_planned_flood, facilities: row.facilities.length, selected: row.code === selected, dim: !visibleCodes.has(row.code) },
        })),
      });
      facilitySource.setData({
        type: "FeatureCollection",
        features: stations.flatMap((row) => row.facilities.map((item) => ({ type: "Feature" as const, geometry: { type: "Point" as const, coordinates: [item.lon, item.lat] }, properties: { tier: item.tier, name: item.name } }))),
      });
    };
    applyRef.current = apply;
    if (readyRef.current) apply();
    return undefined;
  }, [stations, visible, selected, rain]);

  useEffect(() => {
    if (!flyTo || !mapRef.current) return;
    mapRef.current.flyTo({ center: flyTo.center, zoom: flyTo.zoom, duration: 900 });
  }, [flyTo]);

  return <div ref={elementRef} className="wb-map" />;
}
