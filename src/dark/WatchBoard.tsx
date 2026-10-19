import { useEffect, useRef, useState } from "react";
import { getSeoulRiverStages } from "../api";
import type { SeoulRiverStageFeed } from "../types";
import "./watch.css";

type WatchView = { at: string | null; region: string | null; stage: string | null; station: string | null; driver: string | null };

function readWatchView(): WatchView {
  const query = new URLSearchParams(window.location.hash.split("?")[1] ?? "");
  return { at: query.get("at"), region: query.get("region"), stage: query.get("stage"), station: query.get("facility") ?? query.get("station"), driver: query.get("driver") };
}

function buildFrameUrl() {
  const params = new URLSearchParams();
  params.set("api", import.meta.env.VITE_API_BASE === "same-origin" ? "" : import.meta.env.VITE_API_BASE ?? (import.meta.env.PROD ? "" : "http://localhost:8033"));
  Object.entries(readWatchView()).forEach(([key, value]) => { if (value) params.set(key, value); });
  const query = new URLSearchParams(window.location.hash.split("?")[1] ?? "");
  const tab = query.get("tab");
  if (tab) params.set("tab", tab);  // e.g. #watch?tab=vc opens the validation cases
  if (query.get("rain") === "replay") params.set("rain", "replay");  // #scorecard "그날 보드로" replays that day's rain
  return `/watch-board-integration.html?${params.toString()}`;
}

function viewHash(view: WatchView) {
  const params = new URLSearchParams();
  Object.entries(view).forEach(([key, value]) => { if (value) params.set(key, value); });
  const query = params.toString();
  return `#watch${query ? `?${query}` : ""}`;
}

function formatSeoulTime(value: string | null) {
  if (!value) return "시간 정보 없음";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
}

function controlStatusLabel(status: SeoulRiverStageFeed["stations"][number]["control_status"]) {
  if (status === "at_or_above") return "기준 이상";
  if (status === "below") return "기준 미만";
  if (status === "no_reading") return "수위 미수신";
  return "기준 미제공";
}

export default function WatchBoard() {
  const frameRef = useRef<HTMLIFrameElement>(null);
  const [frameUrl] = useState(buildFrameUrl);
  const [riverPanelOpen, setRiverPanelOpen] = useState(false);
  const [riverFeed, setRiverFeed] = useState<SeoulRiverStageFeed | null>(null);
  const [riverLoading, setRiverLoading] = useState(false);
  const [riverError, setRiverError] = useState<string | null>(null);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin || event.source !== frameRef.current?.contentWindow) return;
      if (event.data?.type !== "floodops-watch-view") return;
      const incoming = event.data.view ?? {};
      const nextHash = viewHash({ at: incoming.at ?? null, region: incoming.region ?? null, stage: incoming.stage ?? null,
        station: incoming.facility_id ?? incoming.station ?? null, driver: incoming.driver ?? null });
      if (window.location.hash !== nextHash) window.location.hash = nextHash;
    };
    const onHashChange = () => {
      frameRef.current?.contentWindow?.postMessage({ type: "floodops-watch-set-view", view: readWatchView() }, window.location.origin);
    };
    window.addEventListener("message", onMessage);
    window.addEventListener("hashchange", onHashChange);
    return () => {
      window.removeEventListener("message", onMessage);
      window.removeEventListener("hashchange", onHashChange);
    };
  }, []);

  useEffect(() => {
    if (!riverPanelOpen) return;
    let active = true;
    const controller = new AbortController();
    const load = async () => {
      setRiverLoading(true);
      try {
        const result = await getSeoulRiverStages(controller.signal);
        if (active) {
          setRiverFeed(result);
          setRiverError(null);
        }
      } catch (error) {
        if (active && !(error instanceof DOMException && error.name === "AbortError")) {
          setRiverError(error instanceof Error ? error.message : "서울시 하천 수위 자료를 불러오지 못했습니다.");
        }
      } finally {
        if (active) setRiverLoading(false);
      }
    };
    void load();
    const refresh = window.setInterval(() => void load(), 5 * 60 * 1000);
    return () => {
      active = false;
      controller.abort();
      window.clearInterval(refresh);
    };
  }, [riverPanelOpen]);

  return (
    <main className="wb-root" aria-label="FloodOps 감시 보드">
      <iframe ref={frameRef} title="FloodOps 전국 하천 감시 보드" src={frameUrl} />
      <button
        className="wb-river-toggle"
        type="button"
        aria-expanded={riverPanelOpen}
        aria-controls="wb-river-panel"
        onClick={() => setRiverPanelOpen((open) => !open)}
      >
        서울시 하천 수위
      </button>
      {riverPanelOpen && (
        <section className="wb-river-panel" id="wb-river-panel" role="dialog" aria-labelledby="wb-river-title">
          <header className="wb-river-header">
            <div>
              <p className="wb-river-eyebrow">서울 열린데이터광장 · 10분 갱신 자료</p>
              <h2 id="wb-river-title">서울시 하천 수위·통제수위</h2>
            </div>
            <button className="wb-river-close" type="button" aria-label="서울시 하천 수위 닫기" onClick={() => setRiverPanelOpen(false)}>닫기</button>
          </header>
          {riverLoading && <p className="wb-river-message" role="status">자료를 불러오는 중입니다…</p>}
          {riverError && <p className="wb-river-message wb-river-error" role="alert">{riverError}</p>}
          {riverFeed?.error && <p className="wb-river-message wb-river-note" role="status">{riverFeed.error}</p>}
          {riverFeed && (
            <>
              <div className="wb-river-summary">
                <span className={`wb-river-mode wb-river-mode-${riverFeed.mode}`}>
                  {riverFeed.mode === "live" ? "실시간 연결" : "저장 자료"}
                </span>
                <span>관측소 {riverFeed.stations_total}곳</span>
                <span>통제수위 제공 {riverFeed.stations_with_control_level}곳</span>
                <strong>기준 이상 {riverFeed.at_or_above_control}곳</strong>
              </div>
              <p className="wb-river-fetched">조회 {formatSeoulTime(riverFeed.fetched_at)} · 5분마다 자동 갱신</p>
              {!riverFeed.available && <p className="wb-river-message">표시할 관측 자료가 없습니다.</p>}
              {riverFeed.available && (
                <div className="wb-river-table-wrap">
                  <table className="wb-river-table">
                    <thead>
                      <tr><th scope="col">관측소</th><th scope="col">현재 수위</th><th scope="col">통제수위</th><th scope="col">자료 시각</th></tr>
                    </thead>
                    <tbody>
                      {riverFeed.stations.map((station) => (
                        <tr key={station.gauge_code}>
                          <th scope="row">
                            <span className="wb-river-station-name">{station.gauge_name || station.gauge_code}</span>
                            <span className="wb-river-station-meta">{[station.river, station.district].filter(Boolean).join(" · ") || "하천 정보 없음"}</span>
                          </th>
                          <td>{station.level_m == null ? "—" : `${station.level_m.toFixed(2)} m`}</td>
                          <td>
                            {station.control_level_m == null ? <span className="wb-river-muted">미제공</span> : <>
                              <span>{station.control_level_m.toFixed(2)} m</span>
                              <span className={`wb-river-status wb-river-status-${station.control_status}`}>{controlStatusLabel(station.control_status)}</span>
                            </>}
                          </td>
                          <td>
                            <span>{formatSeoulTime(station.collected_at)}</span>
                            <span className={`wb-river-freshness wb-river-freshness-${station.freshness}`}>
                              {station.freshness === "fresh" ? `${station.age_minutes}분 전` : station.freshness === "stale" ? `${station.age_minutes}분 전 · 지연` : "시각 미상"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <div className="wb-river-limitations">
                {riverFeed.limitations.map((limitation) => <p key={limitation}>{limitation}</p>)}
                <a href={riverFeed.source_url} target="_blank" rel="noreferrer">자료 출처 열기</a>
              </div>
            </>
          )}
        </section>
      )}
    </main>
  );
}
