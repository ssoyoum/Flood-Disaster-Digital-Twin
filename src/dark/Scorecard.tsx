import { useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";
import * as api from "../api";
import type { ValidationCase, ValidationScorecard, ValidationSignal } from "../types";
import { FloodOpsLogo } from "./Landing";
import { AppNavigation } from "./Navigation";
import "./landing.css";
import "./compare.css";
import "./scorecard.css";

/*
 * 효과성 채점표: 국토부 지침 2.1.7(8)② 즉시 통제 조건이 실제 통제·유입보다 몇 분 먼저 충족됐는지.
 * ②의 «범람 우려 통보»를 홍수경보부터 볼지 주의보부터 볼지는 기관 확인 전이라 화면에서 고른다.
 * 값은 /api/watch/validation-cases(case_validation.scorecard)에서 그대로 가져오고 여기서 다시 계산하지 않는다.
 */

type Interp = "warning" | "advisory";
const INTERP: Record<Interp, string> = { warning: "홍수경보부터", advisory: "홍수주의보부터" };
const KEY_SIGNAL: Record<Interp, string> = { warning: "공식 홍수경보", advisory: "공식 홍수주의보" };

const clock = (iso: string | null) => (iso ? iso.slice(11, 16) : "—");
const day = (iso: string) => iso.slice(0, 10);

type Lead = { text: string; tone: "pos" | "neg" | "na" };

function lead(signal: ValidationSignal | undefined): Lead {
  if (!signal) return { text: "—", tone: "na" };
  if (signal.at === null || signal.lead_min === null) return { text: "구간 안에서 울리지 않음", tone: "na" };
  const sign = signal.lead_min >= 0 ? "+" : "−";
  return { text: `${clock(signal.at)} · ${sign}${Math.abs(signal.lead_min)}분`, tone: signal.lead_min >= 0 ? "pos" : "neg" };
}

const official = (item: ValidationCase, name: string) => item.signals.find((signal) => signal.signal === name);
const facilityRule = (item: ValidationCase) => item.signals.find((signal) => signal.facility_id && signal.signal.endsWith("주의 이상"));

// 숫자에서 바로 읽히는 한 줄. 판단은 하지 않고 채점표 값이 말하는 것만 적는다.
function reading(item: ValidationCase, interp: Interp) {
  const key = official(item, KEY_SIGNAL[interp]);
  const region = item.region_at_reference;
  if (key?.lead_min != null && key.lead_min < 0) return "② 조건이 실제 통제보다 늦게 충족 → 하천 수위 밖의 경로(강우·호우특보)가 필요";
  if (item.reference.kind === "inflow") return "② 조건은 먼저 충족됐고 시설 통제로 이어지지 않음";
  if (region.total && region.advisory_or_above / region.total >= 0.5) return `먼저 충족됐지만 같은 지역 ${region.total}곳 중 ${region.advisory_or_above}곳이 동시에 올라 선별력이 약함`;
  return "② 조건과 시설 규칙 모두 통제보다 먼저";
}

export default function ScorecardPage({ onBack, onOpenCase }: { onBack: () => void; onOpenCase: (item: ValidationCase) => void }) {
  const [data, setData] = useState<ValidationScorecard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [interp, setInterp] = useState<Interp>("warning");

  useEffect(() => {
    document.title = "효과성 채점표 | FloodOps";
    api.getValidationCases().then(setData).catch(() => setError("채점표를 불러오지 못했습니다. 백엔드 API 연결을 확인하세요."));
  }, []);

  const cases = data?.cases ?? [];
  const keyName = KEY_SIGNAL[interp], otherName = KEY_SIGNAL[interp === "warning" ? "advisory" : "warning"];
  const ahead = cases.filter((item) => (official(item, keyName)?.lead_min ?? -1) >= 0).length;
  const late = cases.filter((item) => { const value = official(item, keyName)?.lead_min; return value != null && value < 0; }).length;
  const osong = cases.find((item) => item.id === "osong-2023");
  const osongLead = osong ? official(osong, keyName)?.lead_min : null;

  return (
    <main className="fo-landing cc-page sc-page">
      <header className="cc-head">
        <button className="fo-ghost" type="button" onClick={onBack}><ArrowLeft size={16} /> 사례 검증</button>
        <div className="cc-brand"><FloodOpsLogo size={34} /><strong>FloodOps</strong></div>
        <AppNavigation active="compare" />
      </header>
      <section className="cc-intro">
        <p className="fo-eyebrow">EFFECTIVENESS</p>
        <h2>즉시 통제 조건 ②는 실제 통제·유입보다 몇 분 먼저 충족됐나</h2>
        <span>국토부 「도로터널 방재·환기시설 설치 및 관리지침」 2.1.7(8)② «홍수특보 발령 등으로 범람 우려 통보»를 {INTERP[interp]}로 읽었을 때입니다. + 는 먼저, − 는 늦음. 통제 시각은 보도 기준이며 분 단위 기록은 오송(감찰 결과)뿐입니다.</span>
      </section>
      <div className="sc-interp" role="group" aria-label="② 범람 우려 통보 해석">
        <span>② 해석</span>
        {(Object.keys(INTERP) as Interp[]).map((key) => <button key={key} type="button" aria-pressed={interp === key} onClick={() => setInterp(key)}>{INTERP[key]}</button>)}
        <small>기관 확인 전이라 두 해석을 모두 보여 줍니다.</small>
      </div>
      {error && <p className="cc-error">{error}</p>}
      {data && (
        <>
          <div className="sc-kpis" aria-label="요약">
            <div><strong>{cases.length}건</strong><span>채점한 지하차도·하천변 사건</span></div>
            <div><strong className="sc-pos">{ahead}건</strong><span>② 조건이 실제 통제·유입보다 먼저 충족</span></div>
            <div><strong className="sc-neg">{late}건</strong><span>② 조건이 실제 통제보다 늦게 충족</span></div>
            <div><strong className="sc-neg">{osongLead == null ? "—" : `+${osongLead}분`}</strong><span>오송: ② 충족 → 통제 없이 유입</span></div>
          </div>
          {osong?.official_events?.length ? (
            <section className="sc-strip" aria-label="오송 국조실 감찰 경과표">
              <p className="fo-eyebrow">오송 · 국무조정실 감찰 결과 경과표</p>
              <ol>{osong.official_events.map((event) => <li key={event.at} data-kind={event.kind}><b>{event.at.slice(5, 16).replace("T", " ")}</b><em>{event.label}</em><span>{event.note}</span></li>)}</ol>
              {osong.official_events_source && <a href={osong.official_events_source} target="_blank" rel="noreferrer">출처: 국무조정실 보도자료(2023-07-28)</a>}
            </section>
          ) : null}
          <table className="cc-table sc-table">
            <thead>
              <tr><th>사례</th><th>실제 통제·유입</th><th className="sc-key">② 충족 ({INTERP[interp]})</th><th>{otherName} (참고)</th><th>시설 규칙 · 주의 이상</th><th>같은 지역 동시 주의 이상</th><th>읽는 법</th><th /></tr>
            </thead>
            <tbody>
              {cases.map((item) => {
                const key = lead(official(item, keyName));
                const other = lead(official(item, otherName));
                const rule = facilityRule(item);
                const ruleLead = lead(rule);
                const region = item.region_at_reference;
                return (
                  <tr key={item.id}>
                    <td>{item.title}<small>{item.region} · 관측소 {item.gauge}</small></td>
                    <td>{day(item.reference.at)} {clock(item.reference.at)}<small>{item.reference.precision_ko} · {item.reference.label}</small></td>
                    <td className={`sc-key sc-${key.tone}`}>{key.text}</td>
                    <td className={`sc-${other.tone}`}>{other.text}</td>
                    <td className={`sc-${ruleLead.tone}`}>{ruleLead.text}<small>{rule?.signal ?? "시설 규칙 없음"}</small></td>
                    <td>{region.advisory_or_above} / {region.total}곳<small>경계 이상 {region.warning_or_above}곳 · {clock(region.at)} 기준</small></td>
                    <td>{reading(item, interp)}</td>
                    <td><button type="button" className="fo-ghost" onClick={() => onOpenCase(item)}>열기</button></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <section className="sc-pending" aria-label="자료 확보 뒤 추가할 열">
            <p className="fo-eyebrow">자료 확보 뒤 추가할 열</p>
            <ul className="cc-limits">
              <li>④ 호우특보 중 급격한 수위 증가: 기상청 특보 발표 이력 API 승인 뒤 사례마다 같은 방식으로 채점합니다.</li>
              <li>(7) 침수심 기준(15 cm, 하천 500 m 이내 등 5 cm): 현장 센서 자료가 공개되지 않아 과거 판정 시각을 복원할 수 없습니다.</li>
              <li>헛울림: 궁평2 2025-07-17(최고 8.5 m, 침수 없음)의 실제 통제 여부를 충북도로관리사업소에 확인 중입니다.</li>
            </ul>
          </section>
          <ul className="cc-limits sc-limits">{data.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
          <small className="sc-built">채점표 생성 {data.built_at} · {data.step_min}분 간격 재생</small>
        </>
      )}
    </main>
  );
}
