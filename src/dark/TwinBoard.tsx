import { useEffect, useMemo, useState } from "react";
import { Activity, AlertTriangle, ArrowLeft, Gauge, Radio, RotateCcw, TrendingUp } from "lucide-react";
import * as api from "../api";
import type { RiseForecast, TwinBacktest, TwinFacility, TwinStatus, WaterLevelReadiness } from "../types";
import { FloodOpsLogo } from "./Landing";
import "./dark.css";
import "./twin.css";

/*
 * 지하차도 통제 판단 보드.
 *
 * 시설(지하차도) 하나를 단위로, 연결된 수위관측소의 관측으로 지금 단계·계획홍수위까지 남은 분·통제 검토 권고를 보여준다.
 * 관측 소스는 백엔드가 고른다(홍수통제소 실시간 또는 저장된 2023년 재생). 같은 규칙을 2023년 사건에 적용한 백테스트를 함께 둔다.
 * 침수심은 재지 않으므로 공식 통제 기준(침수심)의 판단은 현장이 우선한다.
 */

const REPLAY_PRESETS: Array<{ at: string; label: string; note: string }> = [
  { at: "2023-07-15T04:10:00", label: "04:10", note: "홍수경보" },
  { at: "2023-07-15T06:40:00", label: "06:40", note: "국무조정실 통제 요건" },
  { at: "2023-07-15T06:50:00", label: "06:50", note: "계획홍수위(관측)" },
  { at: "2023-07-15T08:09:00", label: "08:09", note: "임시제방 붕괴" },
  { at: "2023-07-15T08:27:00", label: "08:27", note: "지하차도 유입" },
];

const RECO: Record<string, { label: string; tone: string; hint: string }> = {
  NORMAL: { label: "정상", tone: "#38bdf8", hint: "주의보 수위 미만" },
  MONITOR: { label: "감시", tone: "#fbbf24", hint: "상승 속도를 지켜봅니다" },
  CLOSURE_REVIEW: { label: "통제 검토", tone: "#f87171", hint: "담당자 판단·현장 확인이 우선" },
};

const STAGE_KO: Record<string, string> = { normal: "정상", attention: "관심", advisory: "주의보 수위", warning: "경보 수위", planned_flood: "계획홍수위 도달" };
const LEVEL_KO: Record<string, string> = { attention: "관심", advisory: "주의보", warning: "경보", planned_flood: "계획홍수위" };

const clock = (iso?: string | null) => (iso ? iso.slice(11, 16) : "—");
const dayClock = (iso?: string | null) => (iso ? `${iso.slice(5, 10).replace("-", ".")} ${iso.slice(11, 16)}` : "—");
const num = (value?: number | null, digits = 2) => (value === null || value === undefined ? "—" : value.toFixed(digits));

function readAt(): string | null {
  const match = window.location.hash.match(/[?&]at=([^&]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export default function TwinBoard({ onBack }: { onBack: () => void }) {
  const [facilities, setFacilities] = useState<TwinFacility[] | null>(null);
  const [facilityId, setFacilityId] = useState<string | null>(null);
  const [at, setAt] = useState<string | null>(readAt);
  const [status, setStatus] = useState<TwinStatus | null>(null);
  const [backtest, setBacktest] = useState<TwinBacktest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [waterInputs, setWaterInputs] = useState<WaterLevelReadiness | null>(null);
  const [waterInputError, setWaterInputError] = useState<string | null>(null);
  const [rise, setRise] = useState<RiseForecast | null>(null);
  const [riseError, setRiseError] = useState<string | null>(null);

  // 6시간 최대 상승 예측(연구 카드). 권고와 같은 시각을 보되 권고 계산에는 들어가지 않는다.
  useEffect(() => {
    if (!facilityId) return undefined;
    let active = true;
    let pending: AbortController | null = null;
    setRise(null); setRiseError(null);
    const refresh = () => {
      pending?.abort();
      const controller = new AbortController();
      pending = controller;
      api.getRiseForecast(facilityId, at ?? undefined, controller.signal)
        .then((data) => { if (active && !controller.signal.aborted) { setRise(data); setRiseError(null); } })
        .catch(() => { if (active && !controller.signal.aborted) setRiseError("상승 예측을 불러오지 못했습니다."); });
    };
    refresh();
    const timer = at ? null : window.setInterval(refresh, 5 * 60_000);
    return () => { active = false; pending?.abort(); if (timer !== null) window.clearInterval(timer); };
  }, [facilityId, at]);

  useEffect(() => {
    api.getTwinFacilities().then((list) => { setFacilities(list); setFacilityId((current) => current ?? list[0]?.id ?? null); }).catch((reason: Error) => setError(reason.message));
    // 뒤로가기나 주소 직접 수정으로 ?at= 가 바뀌면 같은 컴포넌트에서 다시 읽는다.
    const onHash = () => setAt(readAt());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    if (!facilityId) return undefined;
    let cancelled = false;
    setLoading(true);
    setStatus(null);
    setBacktest(null);
    setError(null);
    Promise.all([api.getTwinStatus(facilityId, at ?? undefined), api.getTwinBacktest(facilityId)])
      .then(([nextStatus, nextBacktest]) => { if (!cancelled) { setStatus(nextStatus); setBacktest(nextBacktest); } })
      .catch((reason: Error) => { if (!cancelled) setError(reason.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [facilityId, at]);

  useEffect(() => {
    if (!facilityId) return undefined;
    let active = true;
    let pending: AbortController | null = null;
    setWaterInputs(null); setWaterInputError(null);
    const refresh = () => {
      pending?.abort();
      const controller = new AbortController();
      pending = controller;
      api.getWaterLevelReadiness(facilityId, at ?? undefined, controller.signal)
        .then((data) => { if (active && !controller.signal.aborted) { setWaterInputs(data); setWaterInputError(null); } })
        .catch(() => { if (active && !controller.signal.aborted) setWaterInputError("수위 이력을 불러오지 못했습니다. 현재 관측과 연결 상태를 확인해 주세요."); });
    };
    refresh();
    const timer = at ? null : window.setInterval(refresh, 5 * 60_000);
    return () => { active = false; pending?.abort(); if (timer !== null) window.clearInterval(timer); };
  }, [facilityId, at]);

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
          <a className="dk-brand-mark" href="#" title="소개로 돌아가기" aria-label="소개로 돌아가기"><FloodOpsLogo size={30} /></a>
          <div>
            <h1>지하차도 통제 판단 트윈</h1>
            <p>FloodOps · 관측 수위로 지금 단계와 남은 시간을 보여주고, 과거 사건으로 규칙을 검증합니다</p>
          </div>
        </div>
        <nav className="dk-view-tabs" aria-label="FloodOps 화면">
          <button type="button" className="active">지금 상태</button>
          <a href="#event/osong-2023" className="tw-tab-link">통제 기준 검토</a>
          <a href="#compare" className="tw-tab-link">검증 사례</a>
        </nav>
        <div className="dk-status">
          <span className="dk-chip tw-mode" data-mode={viewingReplay ? "replay" : "live"}>
            {viewingReplay ? <RotateCcw size={12} /> : <Radio size={12} />}
            {viewingReplay ? "2023년 사건 재생" : "실시간 관측"}
            <small>{status?.mode === "live" ? "홍수통제소 OpenAPI" : "저장된 10분 수위"}</small>
          </span>
          <button type="button" className="fo-ghost tw-back" onClick={onBack}><ArrowLeft size={14} /> 사례 선택</button>
        </div>
      </header>

      <main className="tw-main">
        <section className="tw-col">
          <article className="tw-card tw-facility" aria-label="시설">
            <p className="tw-eyebrow">시설</p>
            <h2>{facility.name}</h2>
            <dl className="ub-gauge-table">
              <div><dt>노선</dt><dd>{facility.road}</dd></div>
              <div><dt>관리기관</dt><dd>{facility.managing_agency}</dd></div>
              <div><dt>구동 유형</dt><dd>{facility.driver === "river_stage" ? "하천 인접형 · 수위 기준" : facility.driver}</dd></div>
              <div><dt>연결 관측소</dt><dd>{facility.gauge.name} ({facility.gauge.station_id})</dd></div>
              <div><dt>검증 사건</dt><dd><a href={`#event/${facility.event_id}`}>{facility.event_id}</a></dd></div>
            </dl>
          </article>

          <article className="tw-card tw-reco" aria-label="통제 검토 권고">
            <p className="tw-eyebrow">권고 · {dayClock(status?.at)} 기준</p>
            {status?.status === "OK" && reco ? (
              <>
                <div className="tw-reco-badge"><Gauge size={22} />{reco.label}</div>
                <p className="tw-reco-reason">{status.reason}</p>
                <small>{reco.hint} · 단계 {status.stage_label}</small>
              </>
            ) : (
              <>
                <div className="tw-reco-badge is-empty">{loading ? "관측 확인 중" : "관측 없음"}</div>
                <p className="tw-reco-reason">{loading ? "선택한 시설과 시각의 관측을 불러오고 있습니다." : "이 시각에는 관측값이 없습니다. 실시간 모드에서는 10분 자료가 늦게 채워질 수 있어 1시간 자료로 대체합니다."}</p>
              </>
            )}
          </article>

          <article className="tw-card" aria-label="관측과 임계">
            <p className="tw-eyebrow">관측 · {status?.observation?.station ?? facility.gauge.name}</p>
            <div className="ub-kpis tw-kpis">
              <div><strong>{num(status?.observation?.water_level_m)} m</strong><span>현재 수위 (관측소 기준) · EL {num(status?.observation?.water_level_el_m, 3)} m</span></div>
              <div><strong>{num(status?.margin_to_planned_flood_m)} m</strong><span>계획홍수위까지 여유</span></div>
              <div><strong>{status?.rate_m_per_10min === null || status?.rate_m_per_10min === undefined ? "—" : `${status.rate_m_per_10min > 0 ? "+" : ""}${num(status.rate_m_per_10min, 3)}`} m/10분</strong><span>최근 30분 상승 속도</span></div>
              <div><strong>{status?.minutes_to_planned_flood === null || status?.minutes_to_planned_flood === undefined ? "—" : `${status.minutes_to_planned_flood}분`}</strong><span>현재 속도로 계획홍수위까지</span></div>
            </div>
            {status?.levels_m && <LevelBar level={status.observation?.water_level_m ?? null} levels={status.levels_m} />}
            <small className="ub-note">
              관측 {clock(status?.observation?.time)} · {status?.observation?.interval === "1H" ? "1시간 자료" : "10분 자료"} · {status?.observation?.age_min ?? "—"}분 전
              {status?.reference_minutes_to_inflow !== null && status?.reference_minutes_to_inflow !== undefined && ` · 2023년 실제 유입(08:27)까지 ${status.reference_minutes_to_inflow}분`}
            </small>
          </article>

          <RiseCard rise={rise} error={riseError} levels={status?.levels_m ?? null} />

          <article className="tw-card tw-water-history" aria-label="수위 이력과 예측 연결">
            <p className="tw-eyebrow">24시간 수위 이력 · 예측 모델 입력 연결</p>
            {waterInputs ? <>
              <p className="tw-water-context">{waterInputs.mode === "replay" ? "과거 재생" : "실시간 관측"} · {dayClock(waterInputs.as_of)} 기준</p>
              {waterInputs.observation_quality !== "fresh" && <p className="dk-error">{waterInputs.observation_quality === "missing" ? "연결된 수위 관측이 없습니다." : "관측이 오래돼 현재 판단에 사용할 수 없습니다."}</p>}
              <table className="ub-table tw-table">
                <thead><tr><th>입력 시점</th><th>관측 시각</th><th>수위</th></tr></thead>
                <tbody>{waterInputs.history.map((point) => <tr key={point.hours_ago}>
                  <td>{point.hours_ago === 0 ? "기준 시점" : `${point.hours_ago}시간 전`}</td>
                  <td>{dayClock(point.time)}</td><td>{point.water_level_m === null ? "관측 없음" : `${num(point.water_level_m)} m`}</td>
                </tr>)}</tbody>
              </table>
              <details className="tw-water-research">
                <summary>연구 모델 입력 연결 · 원본(익명 관측소) 검증 수치</summary>
                <p>수위 예측 프로젝트의 입력 {waterInputs.required_input_count}종 중 수위 {waterInputs.available_input_count}종을 연결했습니다. 강우·레이더·유역 조건과 실제 관측소 검증이 더 필요합니다.</p>
                <p>연구 모델의 내부 검증 오차는 {num(waterInputs.research.evaluation.global_rmse_m, 3)} m입니다. 1m 초과 상승 구간에서는 {num(waterInputs.research.evaluation.target_gt_1m_rmse_m, 3)} m이며, 이 시설의 예측 성능을 뜻하지 않습니다.</p>
                <small className="ub-note">원본의 관측소와 시각은 익명화돼 실제 시설과 직접 연결할 수 없습니다. 지금 표시한 값은 관측 이력이며, 모델 예측이나 통제 권고가 아닙니다.</small>
              </details>
            </> : !waterInputError && <small className="ub-note">수위 이력을 확인하는 중…</small>}
            {waterInputError && <p className="dk-error">{waterInputError}</p>}
          </article>
        </section>

        <section className="tw-col">
          <article className="tw-card" aria-label="시각 선택">
            <p className="tw-eyebrow">시각 선택</p>
            <div className="tw-presets">
              {status?.mode === "live" && <button type="button" className={!at ? "active" : ""} onClick={() => { setAt(null); window.location.hash = "twin"; }}><Radio size={12} /> 지금</button>}
              {REPLAY_PRESETS.map((preset) => (
                <button key={preset.at} type="button" className={at === preset.at ? "active" : ""} title={preset.note} onClick={() => { setAt(preset.at); window.location.hash = `twin?at=${encodeURIComponent(preset.at)}`; }}>
                  {preset.label} <small>{preset.note}</small>
                </button>
              ))}
            </div>
            <label className="tw-time">2023-07-15 직접 입력
              <input type="time" step={600} value={at?.slice(11, 16) ?? ""} onChange={(event) => { if (event.target.value) { const next = `2023-07-15T${event.target.value}:00`; setAt(next); window.location.hash = `twin?at=${encodeURIComponent(next)}`; } }} />
            </label>
            {loading && <small className="ub-note">불러오는 중…</small>}
            {error && <p className="dk-error">{error}</p>}
          </article>

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

          <article className="tw-card" aria-label="규칙과 한계">
            <p className="tw-eyebrow">규칙 · {status?.rule?.id ?? "—"}</p>
            <ul className="ub-list">
              {status?.rule && <li>{status.rule.review_when}</li>}
              {status?.rule && <li>{status.rule.basis}</li>}
              {status?.rule && <li>{status.rule.official_closure_trigger}</li>}
              {status?.limitations.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </article>
        </section>
      </main>
    </div>
  );
}

const RISE_REASON: Record<string, string> = {
  MODEL_NOT_AVAILABLE: "학습된 모델 파일이 서버에 없습니다.",
  MISSING_EXACT_LAGS: "24시간 전까지의 정시 관측이 모자라 예측하지 않습니다.",
  OBSERVATION_NOT_FRESH: "관측이 오래돼 예측하지 않습니다.",
};

/*
 * 6시간 최대 상승 예측 카드. 홍수통제소 실명 관측소 자료로 다시 학습한 LightGBM이 "앞으로 6시간 안의 최대 상승량"을 낸다.
 * 권고 배지는 수위 규칙만으로 계산되므로 이 카드는 참고 자료다. 도달 시각이나 침수심은 예측하지 않는다.
 */
function RiseCard({ rise, error, levels }: { rise: RiseForecast | null; error: string | null; levels: Record<string, number> | null }) {
  const model = rise?.model ?? null;
  const skill = model?.holdout_pfh_skill ?? null;
  const reaches = rise?.reaches_within_6h;
  const reachLabel = reaches?.planned_flood ? "계획홍수위 도달 예상" : reaches?.warning ? "경보 수위 도달 예상" : reaches?.advisory ? "주의보 수위 도달 예상" : "주의보 수위 미만 예상";
  const reachTone = reaches?.planned_flood ? "#f87171" : reaches?.warning ? "#fb923c" : reaches?.advisory ? "#fbbf24" : "#38bdf8";
  return (
    <article className="tw-card tw-rise" aria-label="6시간 최대 상승 예측" style={{ ["--rise-tone" as string]: reachTone }}>
      <p className="tw-eyebrow">6시간 최대 상승 예측 · 연구 카드 · 권고에 반영하지 않음</p>
      {rise?.prediction_available ? (
        <>
          <div className="tw-rise-head">
            <div className="tw-rise-badge"><TrendingUp size={20} />{rise.maxrise_6h_m !== undefined && rise.maxrise_6h_m > 0 ? "+" : ""}{num(rise.maxrise_6h_m)} m</div>
            <div>
              <strong className="tw-rise-reach">{reachLabel}</strong>
              <span className="tw-rise-sub">예상 최고 수위 {num(rise.forecast_level_m)} m{levels?.planned_flood !== undefined && ` · 계획홍수위 ${levels.planned_flood} m까지 ${num(rise.margin_after_rise_m)} m`}</span>
            </div>
          </div>
          <div className="ub-kpis tw-kpis tw-rise-kpis">
            <div><strong>{num(rise.linear_6h_m)} m</strong><span>단순 외삽(최근 1시간 상승 × 6)</span></div>
            <div><strong>{rise.inputs.rain.sfc_rain_6h === null ? "—" : `${num(rise.inputs.rain.sfc_rain_6h, 1)} mm`}</strong><span>최근 6시간 강우{rise.inputs.rain.station ? ` · ${rise.inputs.rain.station}` : " · 실시간 강우 미연결"}</span></div>
          </div>
          <small className="ub-note">기준 관측 {dayClock(rise.as_of)} · {rise.interval === "1H" ? "1시간 자료" : "10분 자료"}{rise.station_in_training === false && " · 이 관측소는 학습에 포함되지 않음"}</small>
        </>
      ) : (
        <>
          <div className="tw-reco-badge is-empty">{error ? "불러오기 실패" : rise ? "예측 없음" : "예측 확인 중"}</div>
          <p className="tw-reco-reason">{error ?? (rise ? RISE_REASON[rise.reason ?? ""] ?? rise.reason : "모델 입력을 모으는 중입니다.")}</p>
        </>
      )}
      {model && (
        <details className="tw-water-research">
          <summary>모델 근거 · 실명 관측소 {model.stations ?? "—"}곳 재학습 · 2023-07-15 오송 검증</summary>
          <p>
            홍수통제소 1시간 수위 {model.train_rows?.toLocaleString() ?? "—"}행(강우 입력 있는 행 {model.rows_with_rain?.toLocaleString() ?? "—"})으로 학습했고 {model.holdout_month} 한 달은 학습에서 뺐습니다.
            {model.cv_oof_rmse_m !== null && ` 월 단위 교차검증 오차 ${num(model.cv_oof_rmse_m, 3)} m (단순 외삽 ${num(model.cv_linear_rmse_m, 3)} m, 변화 없음 ${num(model.cv_no_change_rmse_m, 3)} m).`}
          </p>
          {skill && skill.model && skill.linear && (
            <p>
              제외한 달에서 «6시간 안 계획홍수위 도달»을 맞힌 횟수: 모델 {skill.model.hit}/{skill.hours_reaching_within_6h} (오경보 {skill.model.false_alarm}), 단순 외삽 {skill.linear.hit}/{skill.hours_reaching_within_6h} (오경보 {skill.linear.false_alarm}).
            </p>
          )}
          {model.osong_planned_flood_lead_min !== null && (
            <p>오송 2023-07-15: 모델은 계획홍수위 도달 {model.osong_planned_flood_lead_min}분 전에 «6시간 안 도달»을 냈습니다. 단순 외삽은 {model.osong_planned_flood_lead_min_linear}분 전이지만 전날 저녁부터 경보 수위 도달을 잘못 예고했습니다.</p>
          )}
          <small className="ub-note">{rise?.limitations.join(" ")}</small>
        </details>
      )}
    </article>
  );
}

function LevelBar({ level, levels }: { level: number | null; levels: Record<string, number> }) {
  const max = Math.max(levels.planned_flood * 1.15, (level ?? 0) * 1.05, 1);
  const pos = (value: number) => `${Math.min(100, Math.max(0, (value / max) * 100))}%`;
  const marks = (["attention", "advisory", "warning", "planned_flood"] as const).filter((key) => levels[key] !== undefined);
  // 관심·주의보·경보·계획홍수위를 같은 축에 두고 현재 수위를 표시한다. 수위는 관측소 기준면 위 높이(m)다.
  return (
    <div className="tw-levelbar" role="img" aria-label="현재 수위와 관측소 기준 수위">
      <div className="tw-levelbar-track">
        {level !== null && <div className="tw-levelbar-fill" style={{ width: pos(level) }} />}
        {marks.map((key) => <i key={key} className={`tw-levelbar-mark ${key}`} style={{ left: pos(levels[key]) }} title={`${LEVEL_KO[key]} ${levels[key]} m`} />)}
        {level !== null && <b className="tw-levelbar-now" style={{ left: pos(level) }}>{level.toFixed(2)}</b>}
      </div>
      <div className="tw-levelbar-labels">
        {marks.map((key) => <span key={key} style={{ left: pos(levels[key]) }}>{LEVEL_KO[key]} {levels[key]}</span>)}
      </div>
    </div>
  );
}
