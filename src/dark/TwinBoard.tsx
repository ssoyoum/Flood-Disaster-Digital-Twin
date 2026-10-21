import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, AlertTriangle, ArrowLeft, ArrowRight, Radio, RotateCcw } from "lucide-react";
import * as api from "../api";
import type { TwinBacktest, TwinFacility, TwinGateId, TwinRegistry, TwinRegistryFacility, TwinStatus } from "../types";
import { AgentDock } from "./DarkConsole";
import { FloodOpsLogo } from "./Landing";
import { AppNavigation } from "./Navigation";
import TwinCriteria from "./TwinCriteria";
import "./dark.css";
import "./navigation.css";
import "./twin.css";

type BoardTab = "now" | "criteria" | "backtest" | "registry";
const TABS: Array<{ id: BoardTab; label: string }> = [
  { id: "now", label: "지금 상태" },
  { id: "criteria", label: "통제 기준 검토" },
  { id: "backtest", label: "백테스트" },
  { id: "registry", label: "시설 등록" },
];

const GATE_IDS: TwinGateId[] = ["inflow_path", "representative_gauge", "site_instrumentation", "validation_event"];
const GATE_LABELS: Record<TwinGateId, string> = {
  inflow_path: "유입 경로", representative_gauge: "대표 관측소", site_instrumentation: "현장 계측", validation_event: "검증 사건",
};
const GATE_STATUS_LABELS: Record<string, string> = {
  CONFIRMED: "확인", PENDING: "확인 대기", MISSING: "자료 없음", UNKNOWN: "미확인",
};
const DRIVER_LABELS: Record<string, string> = { river: "하천형", pluvial: "내수형" };

/*
 * 지하차도 통제 판단 보드.
 *
 * 시설(지하차도) 하나를 단위로, 연결된 수위관측소의 관측으로 지금 단계·계획홍수위까지 남은 분·통제 검토 권고를 보여준다.
 * 관측 소스는 백엔드가 고른다(홍수통제소 실시간 또는 저장된 2023년 재생). 같은 규칙을 2023년 사건에 적용한 백테스트를 함께 둔다.
 * 침수심은 재지 않으므로 공식 통제 기준(침수심)의 판단은 현장이 우선한다.
 */

const RECO: Record<string, { label: string; tone: string; hint: string }> = {
  NORMAL: { label: "정상", tone: "#38bdf8", hint: "주의보 수위 미만" },
  MONITOR: { label: "감시", tone: "#fbbf24", hint: "상승 속도를 지켜봅니다" },
  CLOSURE_REVIEW: { label: "통제 검토", tone: "#f87171", hint: "담당자 판단·현장 확인이 우선" },
};
const STAGE_KO: Record<string, string> = { normal: "정상", attention: "관심", advisory: "주의보 수위", warning: "경보 수위", planned_flood: "계획홍수위 도달" };
const clock = (iso?: string | null) => (iso ? iso.slice(11, 16) : "—");
const dayClock = (iso?: string | null) => (iso ? `${iso.slice(5, 10).replace("-", ".")} ${iso.slice(11, 16)}` : "—");
const num = (value?: number | null, digits = 2) => (value === null || value === undefined ? "—" : value.toFixed(digits));

function readAt(): string | null {
  const match = window.location.hash.match(/[?&]at=([^&]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

function readTab(): BoardTab {
  const match = window.location.hash.match(/[?&]tab=([^&]+)/);
  return TABS.find((item) => item.id === match?.[1])?.id ?? "now";
}

export default function TwinBoard({ onBack }: { onBack: () => void }) {
  const [facilities, setFacilities] = useState<TwinFacility[] | null>(null);
  const [registry, setRegistry] = useState<TwinRegistry | null>(null);
  const [registryError, setRegistryError] = useState<string | null>(null);
  const [facilityId, setFacilityId] = useState<string | null>(null);
  const [at, setAt] = useState<string | null>(readAt);
  const [initialAt] = useState(readAt);
  const frameRef = useRef<HTMLIFrameElement>(null);
  const [status, setStatus] = useState<TwinStatus | null>(null);
  const [backtest, setBacktest] = useState<TwinBacktest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<BoardTab>(readTab);

  useEffect(() => {
    api.getTwinFacilities().then((list) => { setFacilities(list); setFacilityId((current) => current ?? list[0]?.id ?? null); }).catch((reason: Error) => setError(reason.message));
    api.getTwinRegistry().then(setRegistry).catch((reason: Error) => setRegistryError(reason.message));
    // 뒤로가기나 주소 직접 수정으로 ?at= 가 바뀌면 같은 컴포넌트에서 다시 읽는다.
    const onHash = () => {
      const next = readAt();
      setAt(next);
      frameRef.current?.contentWindow?.postMessage({ type: "floodops-twin-set-time", at: next }, window.location.origin);
    };
    const onMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin || event.source !== frameRef.current?.contentWindow) return;
      if (event.data?.type !== "floodops-twin-time" || typeof event.data.at !== "string" || !/^2023-07-15T\d{2}:\d{2}:00$/.test(event.data.at)) return;
      setAt(event.data.at);
      const params = new URLSearchParams(window.location.hash.split("?")[1] ?? "");
      params.set("at", event.data.at);
      window.history.replaceState(null, "", `#twin?${params}`);
    };
    window.addEventListener("hashchange", onHash);
    window.addEventListener("message", onMessage);
    return () => { window.removeEventListener("hashchange", onHash); window.removeEventListener("message", onMessage); };
  }, []);

  useEffect(() => {
    if (!facilityId) return undefined;
    let cancelled = false;
    setStatus(null);
    setBacktest(null);
    setError(null);
    Promise.all([api.getTwinStatus(facilityId, at ?? undefined), tab === "backtest" ? api.getTwinBacktest(facilityId) : Promise.resolve(null)])
      .then(([nextStatus, nextBacktest]) => { if (!cancelled) { setStatus(nextStatus); if (nextBacktest) setBacktest(nextBacktest); } })
      .catch((reason: Error) => { if (!cancelled) setError(reason.message); });
    return () => { cancelled = true; };
  }, [facilityId, at, tab]);

  // 실시간 모드에서는 5분마다 다시 읽는다(관측은 10분 간격).
  useEffect(() => {
    if (!facilityId || at || status?.mode !== "live") return undefined;
    const timer = window.setInterval(() => { api.getTwinStatus(facilityId).then(setStatus).catch(() => undefined); }, 5 * 60_000);
    return () => window.clearInterval(timer);
  }, [facilityId, at, status?.mode]);

  const facility = useMemo(() => facilities?.find((item) => item.id === facilityId) ?? null, [facilities, facilityId]);
  const reco = status?.recommendation ? RECO[status.recommendation] : null;
  const tone = reco?.tone ?? "#38bdf8";
  const viewingReplay = Boolean(at) || status?.mode === "replay";

  if (error && !status) return <div className="app-state error-state"><AlertTriangle /><strong>보드를 불러오지 못했습니다</strong><span>{error}</span></div>;
  if (!facilities || !facility) return <div className="app-state"><Activity className="spin" /><strong>시설 목록을 불러오는 중</strong></div>;

  return (
    <div className="dk-root tw-root" style={{ ["--tone" as string]: tone }}>
      <header className="dk-topbar">
        <div className="dk-brand">
          <a className="dk-brand-mark" href="#watch" title="감시 보드로 돌아가기" aria-label="감시 보드로 돌아가기"><FloodOpsLogo size={30} /></a>
          <div>
            <h1>운영 시설 통제 판단</h1>
            <p>FloodOps · 공식 기준을 시설에 대입해 지금 단계와 남은 시간을 보여주고, 과거 사건으로 검증합니다</p>
          </div>
        </div>
        <nav className="dk-view-tabs" aria-label="FloodOps 화면">
          {TABS.map((item) => (
            <button key={item.id} type="button" className={tab === item.id ? "active" : ""} aria-pressed={tab === item.id} onClick={() => setTab(item.id)}>{item.label}</button>
          ))}
        </nav>
        <div className="dk-header-agent">
          <div className="dk-header-agent-title"><span><strong>대응 에이전트</strong><small>시설 판단 근거 질의</small></span></div>
          <AgentDock eventId={facility.event_id} compact initialFacility={facility.id} facilityAt={at} />
        </div>
        <div className="dk-status">
          <span className="dk-chip tw-mode" data-mode={viewingReplay ? "replay" : "live"}>
            {viewingReplay ? <RotateCcw size={12} /> : <Radio size={12} />}
            {viewingReplay ? "2023년 사건 재생" : "실시간 관측"}
            <small>{tab === "now" || status?.mode !== "live" ? "저장된 10분 수위" : "홍수통제소 OpenAPI"}</small>
          </span>
          <AppNavigation active="twin" />
          <button type="button" className="fo-ghost tw-back" onClick={onBack}><ArrowLeft size={14} /> 감시 보드</button>
        </div>
      </header>

      {tab === "now" && <main className="tw-now-frame">
        <iframe
          ref={frameRef}
          title="현재 지하차도 통제 판단 트윈"
          src={`/twin-now-c.html?api=${encodeURIComponent(import.meta.env.VITE_API_BASE === "same-origin" ? "" : import.meta.env.VITE_API_BASE ?? (import.meta.env.PROD ? "" : "http://localhost:8033"))}&facility=${encodeURIComponent(facility.id)}${initialAt ? `&at=${encodeURIComponent(initialAt)}` : ""}`}
        />
      </main>}

      {tab === "criteria" && <TwinCriteria facilityId={facility.id} />}

      {tab === "registry" && <main className="tw-main tw-registry-page" aria-label="시설 등록 현황">
        <header className="tw-registry-summary">
          <div>
            <p className="tw-eyebrow">시설 유형 · 등록 게이트</p>
            <h2 className="tw-section-title">운영 시설과 확장 후보</h2>
            <p className="tw-section-lead">하천형 운영 시설과 내수형 가설 후보를 같은 등록 항목으로 보여줍니다. 후보 가설은 운영 규칙으로 사용하지 않습니다.</p>
          </div>
          {registry && <strong>{registry.counts.operational} 운영 · {registry.counts.candidate} 후보</strong>}
        </header>
        {registry ? <div className="tw-registry-list">
          {[...registry.operational, ...registry.candidates].map((row: TwinRegistryFacility) => {
            const rainGauge = row.nearby_rain_gauges?.[0];
            const stageGauge = row.nearby_gauges?.[0];
            const gateCount = row.unmet_gates?.length ?? GATE_IDS.filter((id) => row.gates[id].status !== "CONFIRMED").length;
            return <article className="tw-card tw-registry-item" key={row.id}>
              <div className="tw-registry-item-head">
                <div>
                  <span className="tw-registry-status" data-status={row.status}>{row.status === "OPERATIONAL" ? "운영" : "후보"}</span>
                  {row.driver_hypothesis && <span className="tw-registry-hypothesis">가설 · {row.driver_hypothesis}</span>}
                  <h3>{row.name}</h3>
                  <p>{row.region ?? "지역 미등록"}</p>
                </div>
                <small>{gateCount === 0 ? "등록 게이트 완료" : `미확인 게이트 ${gateCount}`}</small>
              </div>
              <dl className="tw-registry-details">
                <div><dt>분류</dt><dd>{row.driver_hypothesis ? `${DRIVER_LABELS[row.driver_hypothesis]} 가설 · 미검증` : DRIVER_LABELS[row.driver] ?? row.driver}</dd></div>
                <div><dt>위치</dt><dd>{row.location ? `${row.location[1].toFixed(6)}, ${row.location[0].toFixed(6)}` : "좌표 없음"}</dd></div>
                <div><dt>수위계</dt><dd>{row.gauge?.name ?? (stageGauge ? `${stageGauge.name} · ${stageGauge.distance_km.toFixed(2)} km` : "미연결")}</dd></div>
                <div><dt>강우계</dt><dd>{rainGauge ? `${rainGauge.name} · ${rainGauge.distance_km.toFixed(2)} km` : "미연결"}</dd></div>
                <div><dt>운영 판정</dt><dd>{row.status === "OPERATIONAL" ? "운영 기준 적용" : "운영 기준 미등록"}</dd></div>
                <div><dt>출처</dt><dd>{row.source?.source_record_id ?? row.event_id ?? "시설 레지스트리"}</dd></div>
              </dl>
              <div className="tw-gates tw-registry-gates">
                {GATE_IDS.map((id) => <span className="tw-gate" data-status={row.gates[id].status} title={row.gates[id].note} key={id}>{GATE_LABELS[id]} · {GATE_STATUS_LABELS[row.gates[id].status]}</span>)}
              </div>
              {row.driver_hypothesis_note && <p className="tw-registry-note">{row.driver_hypothesis_note}</p>}
              {row.status === "CANDIDATE" && <p className="tw-registry-candidate-note">후보 자료이며 시설별 운영 기준과 검증 사건은 등록되지 않았습니다.</p>}
            </article>;
          })}
        </div> : <div className="tw-card tw-registry-empty">
          <strong>{registryError ? "시설 등록 정보를 불러오지 못했습니다." : "시설 등록 정보를 불러오는 중입니다."}</strong>
          {registryError && <small>{registryError}</small>}
        </div>}
      </main>}

      {tab === "backtest" && <main className="tw-main">
        <section className="tw-col">
          <article className="tw-card" aria-label="백테스트">
            <p className="tw-eyebrow">백테스트 · 2023년 관측에 같은 규칙 적용</p>
            {backtest ? (
              <>
                <div className="ub-kpis tw-kpis">
                  <div><strong>{clock(backtest.first_closure_review?.time)}</strong><span>첫 «통제 검토» 권고</span></div>
                  <div><strong>{backtest.lead_minutes ? `${backtest.lead_minutes.underpass_inflow}분` : "—"}</strong><span>지하차도 유입(08:27) 전</span></div>
                  <div><strong>{backtest.lead_minutes ? `${backtest.lead_minutes.levee_failure}분` : "—"}</strong><span>임시제방 붕괴(08:09) 전</span></div>
                </div>
                <table className="ub-table tw-table">
                  <thead><tr><th>시각</th><th>단계</th><th>수위</th></tr></thead>
                  <tbody>
                    {backtest.stage_transitions.map((row) => (
                      <tr key={row.time} className={row.stage === "planned_flood" ? "tl-actual-row" : ""}>
                        <td>{dayClock(row.time)}</td><td>{STAGE_KO[row.stage] ?? row.stage}</td><td>{num(row.water_level_m)} m</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <small className="ub-note">{backtest.note}</small>
              </>
            ) : <small className="ub-note">불러오는 중…</small>}
          </article>
        </section>

        <section className="tw-col">
          <article className="tw-card tw-links" aria-label="사건으로 검증">
            <p className="tw-eyebrow">사건으로 검증</p>
            <a href={`#event/${facility.event_id}`}>
              <strong>2023 오송 사건 재생 · 통제 시각 비교 <ArrowRight size={14} /></strong>
              <span>관측 단계별 공간 재구성을 재생하고, 통제 시각을 바꿨을 때 유입까지 남는 시간을 비교합니다.</span>
            </a>
            <a href="#compare">
              <strong>다른 사례의 대응 시간 <ArrowRight size={14} /></strong>
              <span>서울·포항·안동 사건의 실제 대응과 한 가지 가정 대응의 시간 차이입니다. 시설 운영 등록은 아닙니다.</span>
            </a>
          </article>
          <article className="tw-card" aria-label="백테스트 범위">
            <p className="tw-eyebrow">이 백테스트가 말하는 것</p>
            <ul className="ub-list">
              <li>저장된 2023년 10분 수위에 지금 보드와 같은 규칙({status?.rule?.id ?? backtest?.rule?.id ?? "—"})을 적용했을 때 언제 권고가 나왔는지입니다.</li>
              <li>다른 해 홍수기까지 넓힌 비교와 기준 변경은 «통제 기준 검토» 탭에서 봅니다.</li>
              <li>권고가 났다고 실제 통제가 가능했다는 뜻은 아닙니다. 현장 확인·진입 차단 설비·인력은 반영하지 않습니다.</li>
            </ul>
          </article>
        </section>
      </main>}
    </div>
  );
}
