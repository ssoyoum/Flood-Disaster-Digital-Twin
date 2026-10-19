import { useEffect, useState } from "react";
import { ArrowRight } from "lucide-react";
import {
  getFacilityScorecard, getFloodForecastHistory, getTwinRegistry, getValidationCases,
  type FacilityScorecard, type FloodForecastHistory, type ValidationCase, type ValidationSignal,
} from "../api";
import { FloodOpsLogo } from "./Landing";
import { AppNavigation } from "./Navigation";
import "./scorecard.css";

// 장마 후 화면: 지금 규칙과 공식 특보가 실제 통제보다 몇 분 먼저였는지 센다. 수치는 모두 서버 계산값이다.

const LEAD_KEYS: Array<[string, string]> = [
  ["official_requirement_met", "공식 통제 요건 충족"],
  ["levee_failure", "제방 붕괴"],
  ["underpass_inflow", "지하차도 유입"],
  ["full_inundation", "완전 침수"],
];

const hhmm = (iso?: string | null) => (iso ? iso.slice(11, 16) : "—");
const day = (iso?: string | null) => (iso ? iso.slice(0, 10).replaceAll("-", ".") : "");

function Lead({ signal }: { signal: ValidationSignal }) {
  if (signal.lead_min === null) return <span className="sc-lead none">없음</span>;
  const early = signal.lead_min >= 0;
  return <span className={`sc-lead ${early ? "early" : "late"}`}>{early ? "+" : "−"}{Math.abs(signal.lead_min)}분{signal.lead_is_lower_bound ? "↑" : ""}</span>;
}

function LeadBar({ signal, span }: { signal: ValidationSignal; span: number }) {
  if (signal.lead_min === null) return <span className="sc-bar" />;
  const width = Math.min(50, (Math.abs(signal.lead_min) / span) * 50);
  const early = signal.lead_min >= 0;
  return (
    <span className="sc-bar" aria-hidden="true">
      <i className={early ? "early" : "late"} style={early ? { left: `${50 - width}%`, width: `${width}%` } : { left: "50%", width: `${width}%` }} />
    </span>
  );
}

function CaseCard({ item, span }: { item: ValidationCase; span: number }) {
  const ref = item.reference;
  const near = item.region_at_reference;
  return (
    <article className="sc-card sc-case">
      <header>
        <div>
          <strong>{item.title.replace(/ \d{4}-\d{2}-\d{2}$/, "")}</strong>
          <span>{day(ref.at)} · 기준 <b>{hhmm(ref.at)}</b> {ref.label}</span>
        </div>
        <a className="sc-go" href={`#watch?at=${encodeURIComponent(`${ref.at}:00`)}&rain=replay`}>그날 {hhmm(ref.at)} 보드로 <ArrowRight size={13} /></a>
      </header>
      <p className="sc-precision">기준 시각 정밀도: {ref.precision_ko}</p>
      <ul className="sc-signals">
        {item.signals.map((signal) => (
          <li key={signal.signal}>
            <span className="sc-signal-name">{signal.signal}</span>
            <span className="sc-signal-at">{signal.at ? hhmm(signal.at) : "—"}</span>
            <LeadBar signal={signal} span={span} />
            <Lead signal={signal} />
          </li>
        ))}
      </ul>
      {near && <p className="sc-foot">기준 시각에 {item.region} 시설 {near.total}곳 중 주의 이상 <b>{near.advisory_or_above}</b>곳 · 경계 이상 {near.warning_or_above}곳</p>}
    </article>
  );
}

function FacilityCard({ card }: { card: FacilityScorecard }) {
  const s = card.scorecard;
  const cells: Array<[string, string, string]> = [
    ["적중", String(s.hit), "기준 사건 전에 검토 권고"],
    ["누락", String(s.miss), "기준 사건까지 권고 없음"],
    ["오경보 후보", String(s.false_alarm_candidates), "다른 해 권고 구간(통제 기록 미대조)"],
    ["근접", s.close_call_years.length ? s.close_call_years.join("·") : "0", "권고 없이 경보 수위에 닿은 해"],
  ];
  return (
    <article className="sc-card sc-facility">
      <header>
        <div>
          <strong>{card.facility}</strong>
          <span>
            규칙 {card.rule ? `${card.rule.stage_floor === "warning" ? "홍수경보" : "홍수주의보"} 단계 이상 · 계획홍수위 도달 ${card.rule.lead_threshold_min}분 전이면 통제 검토` : "등록 규칙 없음"}
          </span>
        </div>
        <a className="sc-go" href="#twin">시설 기준에서 열기 <ArrowRight size={13} /></a>
      </header>
      <div className="sc-cells">
        {cells.map(([label, value, hint]) => (
          <div key={label} className="sc-cell">
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{hint}</small>
          </div>
        ))}
      </div>
      {card.lead_minutes && (
        <div className="sc-leads">
          <p>첫 검토 권고 {hhmm(card.first_review?.time)}{card.first_review ? ` (수위 ${card.first_review.water_level_m.toFixed(2)} m)` : ""}가 앞선 시간</p>
          <ul>
            {LEAD_KEYS.filter(([key]) => card.lead_minutes?.[key] != null).map(([key, label]) => (
              <li key={key}><span>{label} {hhmm(card.reference_event?.[key])}</span><b>{card.lead_minutes?.[key]}분 전</b></li>
            ))}
          </ul>
        </div>
      )}
      <p className="sc-foot">재생한 해 {s.years_covered.length ? `${s.years_covered[0]}–${s.years_covered[s.years_covered.length - 1]}` : "없음"} · {card.method}</p>
      <ul className="sc-limits">{card.limitations.map((line) => <li key={line}>{line}</li>)}</ul>
    </article>
  );
}

function HistoryCard({ history }: { history: FloodForecastHistory }) {
  const years = Object.entries(history.issuances.by_year);
  const max = Math.max(1, ...years.map(([, n]) => n));
  const warn = history.official_vs_observed["경보"];
  const adv = history.official_vs_observed["주의보"];
  const range = (s: { p25_min: number | null; p75_min: number | null }) => (s.p25_min != null && s.p75_min != null ? `${s.p25_min}–${s.p75_min}분` : "—");
  return (
    <article className="sc-card sc-history">
      <div className="sc-history-main">
        <p className="sc-big"><strong>{history.issuances.issuances.toLocaleString("ko-KR")}</strong>건 <span>{history.issuances.years} · {history.issuances.months}월 · 관측소 {history.issuances.stations}곳</span></p>
        <div className="sc-years" role="img" aria-label="연도별 발령 건수">
          {years.map(([year, n]) => (
            <div key={year}><i style={{ height: `${(n / max) * 100}%` }} /><b>{n}</b><span>{year.slice(2)}</span></div>
          ))}
        </div>
      </div>
      <dl className="sc-history-stats">
        <div><dt>홍수경보가 관측 도달보다 먼저</dt><dd>중앙값 <b>{warn.issue_lead_over_crossing.median_min}분</b><small>{range(warn.issue_lead_over_crossing)} · {warn.issue_lead_over_crossing.n}건</small></dd></div>
        <div><dt>홍수주의보가 관측 도달보다 먼저</dt><dd>중앙값 <b>{adv.issue_lead_over_crossing.median_min}분</b><small>{range(adv.issue_lead_over_crossing)} · {adv.issue_lead_over_crossing.n}건</small></dd></div>
        <div><dt>관측만 보는 규칙이 경보보다 늦음</dt><dd>중앙값 <b>{warn.rule_minus_issue.median_min}분</b><small>{range(warn.rule_minus_issue)} · {warn.rule_minus_issue.n}건</small></dd></div>
      </dl>
      <p className="sc-foot">그래서 공식 특보를 시설 단계의 하한으로 씁니다. 관측 규칙은 특보를 이기는 신호가 아니라 특보가 없는 시설을 보완하는 신호입니다.</p>
      <ul className="sc-limits">{history.limitations.map((line) => <li key={line}>{line}</li>)}</ul>
    </article>
  );
}

export default function ScorecardPage() {
  const [cases, setCases] = useState<ValidationCase[] | null>(null);
  const [caseLimits, setCaseLimits] = useState<string[]>([]);
  const [facilities, setFacilities] = useState<FacilityScorecard[] | null>(null);
  const [history, setHistory] = useState<FloodForecastHistory | null>(null);
  const [failed, setFailed] = useState<string[]>([]);

  useEffect(() => {
    let live = true;
    const fail = (part: string) => () => { if (live) setFailed((list) => [...list, part]); };
    getValidationCases().then((data) => { if (live) { setCases(data.cases); setCaseLimits(data.limitations ?? []); } }).catch(fail("과거 홍수 채점"));
    getTwinRegistry()
      .then((registry) => Promise.all(registry.operational.map((facility) => getFacilityScorecard(facility.id))))
      .then((cards) => { if (live) setFacilities(cards); })
      .catch(fail("시설 성적표"));
    getFloodForecastHistory().then((data) => { if (live) setHistory(data); }).catch(fail("특보 이력"));
    return () => { live = false; };
  }, []);

  // 오송 특보는 900분 넘게 앞서 막대를 그대로 그리면 나머지가 점이 된다. 300분에서 끊고 숫자로 읽게 한다.
  const span = 300;

  return (
    <main className="sc-page">
      <header className="sc-head">
        <a className="sc-brand" href="#"><FloodOpsLogo size={34} /><span><strong>FloodOps</strong><small>기준 채점 · 장마 후</small></span></a>
        <AppNavigation active="scorecard" />
      </header>

      <section className="sc-intro">
        <p className="sc-eyebrow">장마 후 · 기준 채점</p>
        <h1>기준이 실제 통제보다 빨랐나</h1>
        <p>지금 규칙을 과거 홍수에 10분 간격으로 그대로 재생해, 공식 특보와 시설 단계가 실제 통제(오송은 유입)보다 몇 분 먼저였는지 셉니다. 늦은 사례는 다음 해 기준을 고치는 근거입니다.</p>
      </section>

      {failed.length > 0 && <p className="sc-error">불러오지 못한 항목: {failed.join(", ")}. 백엔드 연결을 확인하세요.</p>}

      <section className="sc-section">
        <header><h2>과거 홍수 채점</h2><span>{cases ? `${cases.length}건` : "불러오는 중"} · 막대는 기준 시각보다 앞(초록)·뒤(빨강), 300분에서 끊음</span></header>
        <div className="sc-case-grid">
          {(cases ?? []).map((item) => <CaseCard key={item.id} item={item} span={span} />)}
        </div>
        {caseLimits.length > 0 && <ul className="sc-limits">{caseLimits.map((line) => <li key={line}>{line}</li>)}</ul>}
      </section>

      <section className="sc-section">
        <header><h2>시설별 통제 성적표</h2><span>운영 등록 시설만 · Barnes et al. 2007 네 분류</span></header>
        {facilities === null && !failed.includes("시설 성적표") && <p className="sc-wait">성적표를 계산하는 중</p>}
        {(facilities ?? []).map((card) => <FacilityCard key={card.facility_id} card={card} />)}
      </section>

      <section className="sc-section">
        <header><h2>공식 홍수특보 이력</h2><span>홍수통제소 fldfct 발령 이력과 관측 수위 비교</span></header>
        {history ? <HistoryCard history={history} /> : !failed.includes("특보 이력") && <p className="sc-wait">이력을 불러오는 중</p>}
      </section>

      <p className="sc-note">채점은 공개 관측과 공식 특보로 본 선행 지표입니다. 통제 시각은 보도 기준이며 분 단위 기록은 오송뿐입니다. 통제 결정은 담당자 판단과 현장 기준이 우선합니다.</p>
    </main>
  );
}
