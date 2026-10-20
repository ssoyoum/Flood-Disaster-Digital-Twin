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
 * 효과성 채점표: 공식 홍수특보와 시설 규칙이 실제 통제·유입보다 몇 분 먼저 울렸는지.
 * 값은 /api/watch/validation-cases(case_validation.scorecard)에서 그대로 가져오고 여기서 다시 계산하지 않는다.
 */

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
function reading(item: ValidationCase) {
  const advisory = official(item, "공식 홍수주의보");
  const region = item.region_at_reference;
  if (advisory?.lead_min != null && advisory.lead_min < 0) return "공식 기준이 실제 통제보다 늦음 → 하천 수위 밖의 경로(강우·호우특보)가 필요";
  if (item.reference.kind === "inflow") return "신호는 먼저 있었고 시설 통제로 이어지지 않음";
  if (region.total && region.advisory_or_above / region.total >= 0.5) return `먼저 울렸지만 같은 지역 ${region.total}곳 중 ${region.advisory_or_above}곳이 동시에 올라 선별력이 약함`;
  return "공식 기준과 시설 규칙 모두 통제보다 먼저";
}

export default function ScorecardPage({ onBack, onOpenCase }: { onBack: () => void; onOpenCase: (item: ValidationCase) => void }) {
  const [data, setData] = useState<ValidationScorecard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    document.title = "효과성 채점표 | FloodOps";
    api.getValidationCases().then(setData).catch(() => setError("채점표를 불러오지 못했습니다. 백엔드 API 연결을 확인하세요."));
  }, []);

  const cases = data?.cases ?? [];
  const ahead = (name: string) => cases.filter((item) => (official(item, name)?.lead_min ?? -1) >= 0).length;
  const late = cases.filter((item) => { const value = official(item, "공식 홍수주의보")?.lead_min; return value != null && value < 0; }).length;

  return (
    <main className="fo-landing cc-page sc-page">
      <header className="cc-head">
        <button className="fo-ghost" type="button" onClick={onBack}><ArrowLeft size={16} /> 사례 검증</button>
        <div className="cc-brand"><FloodOpsLogo size={34} /><strong>FloodOps</strong></div>
        <AppNavigation active="compare" />
      </header>
      <section className="cc-intro">
        <p className="fo-eyebrow">EFFECTIVENESS</p>
        <h2>공식 기준은 실제 통제·유입보다 몇 분 먼저 울렸나</h2>
        <span>사례마다 공식 홍수주의보·홍수경보와 시설 규칙이 처음 올라간 시각을 실제 통제(보도) 또는 유입 시각과 비교합니다. + 는 먼저, − 는 늦음. {data ? `채점 규칙: ${data.rule}` : ""}</span>
      </section>
      {error && <p className="cc-error">{error}</p>}
      {data && (
        <>
          <div className="sc-kpis" aria-label="요약">
            <div><strong>{cases.length}건</strong><span>채점한 지하차도·하천변 사건</span></div>
            <div><strong className="sc-pos">{ahead("공식 홍수주의보")}건</strong><span>공식 홍수주의보가 통제·유입보다 먼저</span></div>
            <div><strong className="sc-pos">{ahead("공식 홍수경보")}건</strong><span>공식 홍수경보가 통제·유입보다 먼저</span></div>
            <div><strong className="sc-neg">{late}건</strong><span>공식 주의보가 통제보다 늦음</span></div>
          </div>
          <table className="cc-table sc-table">
            <thead>
              <tr><th>사례</th><th>기준 사건</th><th>공식 홍수주의보</th><th>공식 홍수경보</th><th>시설 규칙 · 주의 이상</th><th>같은 지역 동시 주의 이상</th><th>읽는 법</th><th /></tr>
            </thead>
            <tbody>
              {cases.map((item) => {
                const advisory = lead(official(item, "공식 홍수주의보"));
                const warning = lead(official(item, "공식 홍수경보"));
                const rule = facilityRule(item);
                const ruleLead = lead(rule);
                const region = item.region_at_reference;
                return (
                  <tr key={item.id}>
                    <td>{item.title}<small>{item.region} · 관측소 {item.gauge}</small></td>
                    <td>{day(item.reference.at)} {clock(item.reference.at)}<small>{item.reference.precision_ko} · {item.reference.label}</small></td>
                    <td className={`sc-${advisory.tone}`}>{advisory.text}</td>
                    <td className={`sc-${warning.tone}`}>{warning.text}</td>
                    <td className={`sc-${ruleLead.tone}`}>{ruleLead.text}<small>{rule?.signal ?? "시설 규칙 없음"}</small></td>
                    <td>{region.advisory_or_above} / {region.total}곳<small>경계 이상 {region.warning_or_above}곳 · {clock(region.at)} 기준</small></td>
                    <td>{reading(item)}</td>
                    <td><button type="button" className="fo-ghost" onClick={() => onOpenCase(item)}>열기</button></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <section className="sc-pending" aria-label="자료 확보 뒤 추가할 열">
            <p className="fo-eyebrow">자료 확보 뒤 추가할 열</p>
            <ul className="cc-limits">
              <li>기상청 호우특보: 특보 발표 이력 API 승인 뒤 사례마다 발표 시각을 같은 방식으로 채점합니다.</li>
              <li>행정안전부 침수심 통제기준: 현장 센서 자료가 공개되지 않아 과거 사건에서 판정 시각을 복원할 수 없습니다. 기준 원문은 확인 중입니다.</li>
              <li>헛울림: 궁평2 2025-07-17(최고 8.5 m, 침수 없음)에서 120분 후보 기준만 울렸습니다. 실제 통제 여부는 충북도로관리사업소에 확인 중이며, 운영 시설 보드의 «통제 기준 검토» 탭에서 볼 수 있습니다.</li>
            </ul>
          </section>
          <ul className="cc-limits sc-limits">{data.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
          <small className="sc-built">채점표 생성 {data.built_at} · {data.step_min}분 간격 재생</small>
        </>
      )}
    </main>
  );
}
