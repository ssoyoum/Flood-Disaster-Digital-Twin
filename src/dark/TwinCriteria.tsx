import { useEffect, useState } from "react";
import { Scale } from "lucide-react";
import * as api from "../api";
import type { CriteriaFloor, TwinCriteriaReview } from "../types";

/*
 * 통제 기준 검토 탭.
 * 같은 규칙을 2019~2026년 연중 10분 수위 전체에 적용해, 2023년 사건에서 얻는 선행 시간과
 * 다른 해에 생기는 통제 검토 구간(실제 침수 기록 미확인)을 함께 보여준다. 기준을 바꾸는 쪽은 담당자다.
 */

const FLOORS: Array<{ id: CriteriaFloor; label: string }> = [
  { id: "advisory", label: "주의보 수위부터" },
  { id: "warning", label: "경보 수위부터" },
];
const LEADS = [0, 60, 120, 180];
const STAGE_KO: Record<string, string> = { normal: "정상", attention: "관심", advisory: "주의보", warning: "경보", planned_flood: "계획홍수위" };

const clock = (iso?: string | null) => (iso ? iso.slice(11, 16) : "—");
const day = (iso: string) => iso.slice(0, 10).replace(/-/g, ".");
const leadLabel = (minutes: number) => (minutes === 0 ? "계획홍수위 도달만" : `${minutes}분 이내 도달 예상`);
const ahead = (minutes: number | null | undefined) => (minutes === null || minutes === undefined ? "—" : minutes > 0 ? `${minutes}분 전` : minutes < 0 ? `${-minutes}분 늦음` : "같은 시각");
const duration = (minutes: number) => (minutes >= 60 ? `${Math.floor(minutes / 60)}시간${minutes % 60 ? ` ${minutes % 60}분` : ""}` : `${minutes}분`);

export default function TwinCriteria({ facilityId }: { facilityId: string }) {
  const [floor, setFloor] = useState<CriteriaFloor | null>(null);
  const [lead, setLead] = useState<number | null>(null);
  const [review, setReview] = useState<TwinCriteriaReview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      api.getTwinCriteriaReview(facilityId, floor ?? "warning", lead ?? 60, controller.signal)
        .then((data) => {
          setReview(data); setError(null);
          // 처음에는 시설에 등록된 현재 규칙을 그대로 보여준다.
          if (floor === null) setFloor(data.current_rule.stage_floor);
          if (lead === null) setLead(data.current_rule.lead_threshold_min);
        })
        .catch(() => { if (!controller.signal.aborted) setError("기준 검토 결과를 불러오지 못했습니다."); });
    }, 150);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [facilityId, floor, lead]);

  const current = review?.current_rule;
  const isCurrent = (f: CriteriaFloor, l: number) => current?.stage_floor === f && current?.lead_threshold_min === l;
  const others = review?.episodes.filter((item) => !item.reference_event) ?? [];
  const years = review ? `${review.coverage.years[0]}~${review.coverage.years[review.coverage.years.length - 1]}` : "";
  const levels = review?.station.levels_m;

  return (
    <main className="tw-main">
      <section className="tw-col">
        <article className="tw-card" aria-label="통제 기준 선택">
          <p className="tw-eyebrow">통제 기준 검토 · {review?.station.name ?? "연결 관측소"}</p>
          <h2 className="tw-section-title">어느 시점에 통제 검토를 권고할까요?</h2>
          <p className="tw-section-lead">계획홍수위에 닿으면 항상 권고합니다. 그 전에 «현재 상승 속도로 계획홍수위까지 몇 분 안»이면 미리 권고할지 정합니다. 기준을 앞당길수록 2023년에는 일찍 알리지만, 다른 해에도 권고가 생깁니다.</p>
          <div className="tw-choice-group" role="group" aria-label="미리 권고를 시작할 단계">
            <span>미리 권고를 시작할 단계</span>
            {FLOORS.map((item) => (
              <button key={item.id} type="button" className={floor === item.id ? "active" : ""} aria-pressed={floor === item.id} onClick={() => setFloor(item.id)}>
                {item.label}{levels && <small>{levels[item.id]} m</small>}
              </button>
            ))}
          </div>
          <div className="tw-choice-group" role="group" aria-label="계획홍수위 도달 예상 시간">
            <span>계획홍수위 도달 예상 시간</span>
            {LEADS.map((value) => (
              <button key={value} type="button" className={lead === value ? "active" : ""} aria-pressed={lead === value} onClick={() => setLead(value)}>
                {value === 0 ? "도달만" : `${value}분`}{floor && isCurrent(floor, value) && <small>현재 규칙</small>}
              </button>
            ))}
          </div>
          <label className="tw-range">직접 조정 <strong>{lead === null ? "—" : leadLabel(lead)}</strong>
            <input type="range" min={0} max={360} step={10} value={lead ?? 60} onChange={(event) => setLead(Number(event.target.value))} />
          </label>
        </article>

        <article className="tw-card tw-criteria-result" aria-label="기준 검토 결과">
          <p className="tw-eyebrow">결과 · {review ? `${review.params.stage_floor_label} 이상 · ${leadLabel(review.params.lead_threshold_min)}` : "계산 중"}{review?.is_current_rule && " · 현재 규칙"}</p>
          {error && <p className="dk-error">{error}</p>}
          {review && (
            <>
              <div className="ub-kpis tw-kpis">
                <div><strong>{clock(review.first_review?.time)}</strong><span>2023-07-15 첫 «통제 검토» 권고</span></div>
                <div><strong>{ahead(review.lead_minutes?.underpass_inflow)}</strong><span>지하차도 유입(08:27) 기준</span></div>
                <div><strong>{ahead(review.lead_minutes?.official_requirement_met)}</strong><span>국무조정실 통제 요건(06:40) 기준</span></div>
                <div className={review.other_episode_count ? "tw-kpi-cost" : ""}><strong>{review.other_episode_count}건{review.other_episode_count > 0 && <small> · {duration(review.other_review_minutes)}</small>}</strong><span>{years}년 다른 시기 권고 구간</span></div>
              </div>
              <p className="tw-criteria-sentence">
                이 기준이면 2023년에는 <b>{clock(review.first_review?.time)}</b>에 통제 검토를 권고해 지하차도 유입 <b>{ahead(review.lead_minutes?.underpass_inflow)}</b>이었습니다.{" "}
                {review.other_episode_count === 0
                  ? `${years}년 다른 시기에는 권고가 없었습니다.`
                  : `대신 ${others.map((item) => `${day(item.start)} ${clock(item.start)}~${clock(item.end)}(최고 ${item.peak_water_level_m.toFixed(2)} m${item.quality_review_required ? ", 자료 확인 필요" : ""})`).join(", ")}에도 권고가 나왔습니다. 그때 지하차도 침수·통제 기록은 확인하지 않았습니다.`}
              </p>
            </>
          )}
        </article>

        <article className="tw-card" aria-label="연도별 권고">
          <p className="tw-eyebrow">연도별 · {review?.coverage.season === "매년 6~9월" ? "홍수기(6~9월)" : "연중"} 10분 수위 {review?.coverage.rows.toLocaleString() ?? "—"}개</p>
          {review ? (
            <table className="ub-table tw-table">
              <thead><tr><th>연도</th><th>최고 수위</th><th>최고 단계</th><th>권고 구간</th></tr></thead>
              <tbody>{review.by_year.map((row) => (
                <tr key={row.year} className={row.reference_event ? "tl-actual-row" : row.episodes ? "tw-row-cost" : ""}>
                  <td>{row.year}</td>
                  <td>{row.max_water_level_m.toFixed(2)} m</td>
                  <td>{STAGE_KO[stageOf(row.max_water_level_m, levels)] ?? "—"}</td>
                  <td>{row.reference_event ? "검증 사건(오송)" : row.episodes ? `${row.episodes}건 · ${duration(row.review_minutes)}` : "없음"}</td>
                </tr>
              ))}</tbody>
            </table>
          ) : <small className="ub-note">불러오는 중…</small>}
          {review && (
            <small className="ub-note">
              자료 점검: 10분 칸 {review.quality.expected_slots.toLocaleString()}개 중 빠진 칸 {review.quality.missing_slots.toLocaleString()}개({review.quality.gap_count}곳),
              10분 사이 {review.quality.step_review_threshold_m} m 이상 변화 {review.quality.step_review_count}건. 지우지 않고 표시만 하며, 권고 구간과 겹친 표시는 {review.quality.episodes_with_flags}건입니다.
              {review.quality.quarantines.map((item) => ` 연구 격리 ${item.start.slice(0, 10)} ${item.start.slice(11, 16)}~${item.end.slice(11, 16)}(${item.readings_excluded}개 값)는 규칙에서 뺐습니다(원출처 확인 전).`).join("")}
            </small>
          )}
        </article>
      </section>

      <section className="tw-col">
        <article className="tw-card" aria-label="기준 비교표">
          <p className="tw-eyebrow">기준 비교표 · 행을 누르면 그 기준으로 바뀝니다</p>
          {review ? (
            <table className="ub-table tw-table tw-sweep">
              <thead><tr><th>미리 권고 기준</th><th>2023 첫 권고</th><th>유입 전</th><th>다른 해 권고</th></tr></thead>
              <tbody>{review.sweep.filter((row) => !(row.lead_threshold_min === 0 && row.stage_floor === "advisory")).map((row) => {
                // 계획홍수위 도달만 보는 기준은 단계와 무관해 한 행으로 합친다.
                const selected = row.lead_threshold_min === 0 ? lead === 0 : row.stage_floor === floor && row.lead_threshold_min === lead;
                return (
                  <tr key={`${row.stage_floor}-${row.lead_threshold_min}`} className={selected ? "is-selected" : ""} aria-selected={selected} tabIndex={0}
                    onClick={() => { setFloor(row.stage_floor); setLead(row.lead_threshold_min); }}
                    onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setFloor(row.stage_floor); setLead(row.lead_threshold_min); } }}>
                    <td>{row.lead_threshold_min === 0 ? "계획홍수위 도달만" : `${FLOORS.find((item) => item.id === row.stage_floor)?.label} · ${row.lead_threshold_min}분`}{isCurrent(row.stage_floor, row.lead_threshold_min) && <span className="tw-tag">현재</span>}</td>
                    <td>{clock(row.first_review_time)}</td>
                    <td>{row.lead_to_inflow_min === null ? "—" : `${row.lead_to_inflow_min}분`}</td>
                    <td>{row.other_episode_count ? `${row.other_episode_count}건 · ${duration(row.other_review_minutes)}` : "없음"}</td>
                  </tr>
                );
              })}</tbody>
            </table>
          ) : <small className="ub-note">불러오는 중…</small>}
          <small className="ub-note">앞당긴 선행 시간과 다른 해의 권고 구간을 함께 보고 기준을 고르세요.</small>
        </article>

        <article className="tw-card tw-criteria-note" aria-label="기준 검토 한계">
          <p className="tw-eyebrow"><Scale size={12} /> 읽는 법과 한계</p>
          <ul className="ub-list">{review?.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
        </article>
      </section>
    </main>
  );
}

function stageOf(level: number, levels?: Record<string, number>) {
  if (!levels) return "";
  let stage = "normal";
  for (const key of ["attention", "advisory", "warning", "planned_flood"]) if (level >= levels[key]) stage = key;
  return stage;
}
