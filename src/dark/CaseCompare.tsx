import { useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";
import * as api from "../api";
import type { CaseLeadTimes } from "../types";
import { FloodOpsLogo } from "./Landing";
import "./landing.css";
import "./compare.css";

/*
 * 사례 간 비교: 사례마다 실제 대응 시각과 등록된 반사실 시각이 기준 사건보다 몇 분 앞섰는지.
 * 덤벨 차트 하나(한 축, 분 단위)와 같은 값의 표. 값은 /api/cases/lead-times 가 각 사례 계산 함수에서 가져온다.
 * 색: 실제 #d97014(원), 반사실 #109c8e(마름모) — 다크 배경 #111a2b 기준 팔레트 검증 통과, 모양으로도 구분.
 */

const ACTUAL = "#d97014";
const WHATIF = "#109c8e";

function minutes(value: number | null) {
  if (value === null) return "—";
  const abs = Math.abs(value);
  const text = abs >= 60 ? `${Math.floor(abs / 60)}시간 ${abs % 60}분` : `${abs}분`;
  return value < 0 ? `${text} 늦음` : `${text} 전`;
}

export default function CaseComparePage({ onBack, onOpen }: { onBack: () => void; onOpen: (id: string) => void }) {
  const [data, setData] = useState<CaseLeadTimes | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hover, setHover] = useState<{ x: number; y: number; text: string } | null>(null);

  useEffect(() => {
    document.title = "사례 간 비교 | FloodOps";
    api.getCaseLeadTimes().then(setData).catch(() => setError("사례 비교 데이터를 불러오지 못했습니다. 백엔드 API 연결을 확인하세요."));
  }, []);

  const cases = data?.cases ?? [];
  const values = cases.flatMap((item) => [item.actual.lead_min, item.counterfactual.lead_min]).filter((value): value is number => value !== null);
  const minX = Math.min(-30, ...values);
  const maxX = Math.max(60, ...values) + 10;
  const width = 980;
  const rowHeight = 76;
  const pad = { left: 310, right: 40, top: 30, bottom: 36 };
  const height = pad.top + pad.bottom + rowHeight * cases.length;
  const x = (value: number) => pad.left + ((value - minX) / (maxX - minX)) * (width - pad.left - pad.right);
  const ticks: number[] = [];
  for (let tick = Math.ceil(minX / 30) * 30; tick <= maxX; tick += 30) ticks.push(tick);

  return (
    <main className="fo-landing cc-page">
      <header className="cc-head">
        <button className="fo-ghost" type="button" onClick={onBack}><ArrowLeft size={16} /> 사례 선택</button>
        <div className="cc-brand"><FloodOpsLogo size={34} /><strong>FloodOps</strong></div>
      </header>
      <section className="cc-intro">
        <p className="fo-eyebrow">CROSS-CASE</p>
        <h2>대응이 기준 사건보다 몇 분 앞섰나</h2>
        <span>사례마다 실제 대응 시각과, 기록된 관측·사건 시각에서 고른 반사실 시각 하나를 같은 축에 놓았습니다. 0은 각 사례의 기준 사건이고 왼쪽은 그 뒤입니다.</span>
      </section>
      {error && <p className="cc-error">{error}</p>}
      {data && (
        <>
          <div className="cc-legend" aria-label="범례">
            <span><svg width="14" height="14" aria-hidden="true"><circle cx="7" cy="7" r="5" fill={ACTUAL} /></svg>실제 대응</span>
            <span><svg width="14" height="14" aria-hidden="true"><rect x="2.5" y="2.5" width="9" height="9" fill={WHATIF} transform="rotate(45 7 7)" /></svg>반사실 대응</span>
          </div>
          <figure className="cc-chart" onMouseLeave={() => setHover(null)}>
            <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="사례별 실제 대응과 반사실 대응의 선행 시간">
              {ticks.map((tick) => (
                <g key={tick}>
                  <line x1={x(tick)} x2={x(tick)} y1={pad.top - 8} y2={height - pad.bottom} className={tick === 0 ? "cc-zero" : "cc-grid"} />
                  <text x={x(tick)} y={height - pad.bottom + 18} textAnchor="middle" className="cc-axis">{tick === 0 ? "기준 사건" : `${tick}분`}</text>
                </g>
              ))}
              {cases.map((item, index) => {
                const y = pad.top + rowHeight * index + rowHeight / 2;
                const actual = item.actual.lead_min;
                const whatif = item.counterfactual.lead_min;
                const show = (event: React.MouseEvent, text: string) => {
                  const box = (event.currentTarget as SVGElement).ownerSVGElement?.getBoundingClientRect();
                  // 오른쪽 끝 점의 툴팁이 차트 밖으로 나가지 않도록 왼쪽으로 뒤집는다.
                  if (box) setHover({ x: event.clientX - box.left > box.width - 340 ? event.clientX - box.left - 344 : event.clientX - box.left + 12, y: event.clientY - box.top + 12, text });
                };
                return (
                  <g key={item.event_id}>
                    <text x={12} y={y - 10} className="cc-case">{item.case}</text>
                    <text x={12} y={y + 7} className="cc-sub">{item.response}</text>
                    <text x={12} y={y + 22} className="cc-sub">기준: {item.milestone}</text>
                    {actual !== null && whatif !== null && <line x1={x(actual)} x2={x(whatif)} y1={y} y2={y} className="cc-connector" />}
                    {actual !== null ? (
                      <g onMouseMove={(event) => show(event, `실제 ${item.actual.time} · ${item.actual.label} · ${minutes(actual)}`)}>
                        <circle cx={x(actual)} cy={y} r={14} fill="transparent" />
                        <circle cx={x(actual)} cy={y} r={6} fill={ACTUAL} stroke="#111a2b" strokeWidth={2} />
                        <text x={x(actual)} y={y - 12} textAnchor="middle" className="cc-value">{actual}</text>
                      </g>
                    ) : (
                      <text x={x(minX) + 8} y={y + 4} className="cc-note">실제: {item.actual.label}</text>
                    )}
                    {whatif !== null && (
                      <g onMouseMove={(event) => show(event, `반사실 ${item.counterfactual.time} · ${item.counterfactual.label} · ${minutes(whatif)}`)}>
                        <circle cx={x(whatif)} cy={y} r={14} fill="transparent" />
                        <rect x={x(whatif) - 5} y={y - 5} width={10} height={10} fill={WHATIF} stroke="#111a2b" strokeWidth={2} transform={`rotate(45 ${x(whatif)} ${y})`} />
                        <text x={x(whatif)} y={y - 12} textAnchor="middle" className="cc-value">{whatif}</text>
                      </g>
                    )}
                  </g>
                );
              })}
            </svg>
            {hover && <div className="cc-tooltip" style={{ left: hover.x, top: hover.y }}>{hover.text}</div>}
          </figure>
          <table className="cc-table">
            <thead><tr><th>사례</th><th>기준 사건</th><th>실제 대응</th><th>반사실 대응</th><th>근거</th><th /></tr></thead>
            <tbody>
              {cases.map((item) => (
                <tr key={item.event_id}>
                  <td>{item.case}<small>{item.response}</small></td>
                  <td>{item.milestone}</td>
                  <td>{item.actual.time ? `${item.actual.time} · ${minutes(item.actual.lead_min)}` : "—"}<small>{item.actual.label}</small></td>
                  <td>{item.counterfactual.time} · {minutes(item.counterfactual.lead_min)}<small>{item.counterfactual.label}</small></td>
                  <td>{item.evidence}</td>
                  <td><button type="button" className="fo-ghost" onClick={() => onOpen(item.event_id)}>열기</button></td>
                </tr>
              ))}
            </tbody>
          </table>
          <ul className="cc-limits">{data.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
        </>
      )}
    </main>
  );
}
