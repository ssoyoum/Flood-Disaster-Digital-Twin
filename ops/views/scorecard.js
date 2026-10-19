import { arrow, cached, esc, hhmm, hydrograph, leadBar, minutes, num, REFERENCE_KO, tierOf, ymd } from "../lib.js";

// 장마 후 · 기준 채점.
// "일찍 알렸다"는 숫자는 혼자 쓰지 않는다. 언제나 울리는 경보도 일찍 알리기 때문이다.
// 그래서 선행 분 옆에 ① 무엇을 넘었나 ② 다른 해에 몇 번 울렸나 ③ 같은 시각 몇 곳이 같이 올랐나를 둔다.

const LEVEL_NAME = { advisory: "주의보 수위", warning: "경보 수위" };

function why3({ rule, lead, cost }) {
  return `<dl class="op-why">
    <div><dt><b>1</b>무엇을 넘었나</dt><dd>${rule}</dd></div>
    <div><dt><b>2</b>얼마나 먼저</dt><dd>${lead}</dd></div>
    <div><dt><b>3</b>헛경보는</dt><dd>${cost}</dd></div>
  </dl>`;
}

async function facilityBlock(facility) {
  const [card, review, backtest] = await Promise.all([
    cached(`/api/twin/facilities/${facility.id}/scorecard`),
    cached(`/api/twin/facilities/${facility.id}/criteria-review`),
    cached(`/api/twin/facilities/${facility.id}/backtest?points=true`),
  ]);
  const levels = review.station.levels_m;
  const first = backtest.first_closure_review;
  const ref = card.reference_event ?? {};
  const lead = card.lead_minutes ?? {};
  const s = card.scorecard;
  const years = review.by_year ?? [];
  const closeCalls = s.close_call_years.map((year) => {
    const row = years.find((r) => r.year === year);
    return `${year}년 최고 ${row?.max_water_level_m ?? "—"} m`;
  });
  const floor = LEVEL_NAME[card.rule?.stage_floor] ?? "경보 수위";

  const ruleText = first
    ? `${floor} ${levels[card.rule.stage_floor]} m 이상이고, 지금 상승 속도로 계획홍수위 ${levels.planned_flood} m까지 ${card.rule.lead_threshold_min}분 이내
       <small>첫 권고 ${hhmm(first.time)} · 수위 ${first.water_level_m} m · ${esc(first.reason)}</small>`
    : "등록된 규칙이 이 사건에서 권고를 내지 않았습니다.";
  const leadText = lead.underpass_inflow != null
    ? `<strong class="op-early">${lead.underpass_inflow}분</strong> 먼저 <small>지하차도 유입 ${hhmm(ref.underpass_inflow)} 기준 · 공식 통제 요건(${hhmm(ref.official_requirement_met)})보다 ${lead.official_requirement_met}분 · 제방 붕괴보다 ${lead.levee_failure}분</small>`
    : "—";
  // 더 일찍 잡은 기준 후보가 무엇을 대가로 치르는지 한 줄로 붙인다.
  const earlier = (review.sweep ?? []).filter((r) => r.stage_floor === card.rule?.stage_floor && r.lead_to_inflow_min > (lead.underpass_inflow ?? Infinity))
    .sort((a, b) => a.lead_to_inflow_min - b.lead_to_inflow_min)[0];
  const tradeoff = earlier ? ` 기준을 계획홍수위 ${earlier.lead_threshold_min}분 전으로 당기면 ${earlier.lead_to_inflow_min}분 먼저지만 다른 해 권고가 ${earlier.other_episode_count}회(${earlier.other_review_minutes}분) 생깁니다.` : "";
  const costText = `<strong>${s.false_alarm_candidates}회</strong> 다른 해 권고 <small>${s.years_covered[0]}–${s.years_covered[s.years_covered.length - 1]}년 ${s.years_covered.length}개 해에 같은 규칙을 돌린 결과${closeCalls.length ? ` · 근접(권고 없이 경보 수위): ${closeCalls.join(", ")}` : ""}.${tradeoff}</small>`;

  const events = [
    { key: "official_requirement_met", color: "#fbbf24" },
    { key: "levee_failure", color: "#fb923c" },
    { key: "underpass_inflow", color: "#f87171", primary: true },
    { key: "full_inundation", color: "#f87171" },
  ].filter((e) => ref[e.key]).map((e) => ({ ...e, time: ref[e.key], label: REFERENCE_KO[e.key], lead: lead[e.key] }));
  const chart = backtest.points?.length ? hydrograph({ points: backtest.points, levels, from: "2023-07-14T12:00", to: "2023-07-15T10:00", review: first, events }) : "";

  return `<article class="op-card">
    <div class="op-card-head"><div><h3>${esc(card.facility)}</h3><small>대표 관측소 ${esc(review.station.name)} · 기준 사건 ${ymd(ref.underpass_inflow)} · 저장된 10분 수위 ${num(backtest.series.records)}개</small></div>
      <a class="op-go" href="#/facility/criteria">기준 후보 비교 ${arrow}</a></div>
    ${why3({ rule: ruleText, lead: leadText, cost: costText })}
    <div class="op-hydro">${chart}</div>
    <p class="op-note">초록 구간이 권고와 유입 사이의 시간입니다. 점선은 관측소 기준 수위이고, 권고는 경보 수위를 넘은 뒤 상승 속도까지 맞아야 나옵니다(경보 수위만 넘은 시각은 ${esc(hhmm(backtest.stage_transitions.find((t) => t.stage === "warning")?.time))}). ${esc(backtest.note)}</p>
  </article>`;
}

function caseCard(item) {
  const ref = item.reference;
  const near = item.region_at_reference;
  const share = near && near.total ? near.advisory_or_above / near.total : null;
  const select = near ? `<div class="op-select" title="기준 시각에 같은 지역에서 함께 주의 이상이던 시설 비율. 높을수록 이 시설만 골라낸 신호가 아닙니다.">
      <span>같은 시각 ${esc(item.region)} ${near.total}곳 중 주의 이상 <b>${near.advisory_or_above}</b> · 경계 이상 ${near.warning_or_above}</span>
      <span class="track"><i style="width:${(near.warning_or_above / near.total) * 100}%;background:#fb923c"></i><i style="width:${((near.advisory_or_above - near.warning_or_above) / near.total) * 100}%;background:#fbbf24"></i></span>
      <span class="op-num">${share == null ? "—" : `${Math.round(share * 100)}%`}</span></div>` : "";
  const rows = item.signals.map((s) => `<li>
      <span class="tier">${tierOf(s.signal)}</span>
      <span class="name"><b>${esc(s.signal)}</b>${s.why ? `<small>${esc(s.why)}</small>` : s.source ? `<small>${esc(s.source)}</small>` : ""}</span>
      <span class="at">${s.at ? hhmm(s.at) : "—"}</span>
      ${leadBar(s.lead_min)}
      <span class="lead ${s.lead_min == null ? "" : s.lead_min >= 0 ? "op-early" : "op-late"}">${s.lead_min == null ? "없음" : `${minutes(s.lead_min)}${s.lead_is_lower_bound ? "↑" : ""}`}</span>
    </li>`).join("");
  return `<article class="op-card">
    <div class="op-card-head"><div><h3>${esc(item.title.replace(/ \d{4}-\d{2}-\d{2}$/, ""))}</h3>
      <small>${ymd(ref.at)} · 기준 <b>${hhmm(ref.at)}</b> ${esc(ref.label)} · ${esc(ref.precision_ko)}</small></div>
      <a class="op-go" href="#/watch?at=${encodeURIComponent(`${ref.at}:00`)}&rain=replay">그날 ${hhmm(ref.at)} 보드로 ${arrow}</a></div>
    ${select}
    <ul class="op-sig">${rows}</ul>
  </article>`;
}

function historyBlock(h) {
  const cmp = h.official_vs_observed;
  const row = (name, d) => {
    const crossed = d.target_crossed, never = d.issuances - d.target_crossed;
    const l = d.issue_lead_over_crossing;
    return `<tr><td><b>${name}</b></td><td class="op-num">${num(d.issuances)}</td>
      <td><div class="op-cellbar"><i style="width:${(crossed / d.issuances) * 140}px"></i><span class="op-num">${num(crossed)}</span></div></td>
      <td><div class="op-cellbar"><i class="cost" style="width:${(never / d.issuances) * 140}px"></i><span class="op-num">${num(never)}</span></div></td>
      <td class="op-num"><b>${l.median_min}분</b> <span class="op-note">(${l.p25_min}–${l.p75_min}분, ${l.n}건)</span></td></tr>`;
  };
  const w = cmp["경보"];
  return `<div class="op-card">
    <div class="op-table-wrap"><table class="op-table">
      <thead><tr><th>공식 특보</th><th>발령</th><th>해당 수위에 닿음</th><th>닿지 않음(헛경보 후보)</th><th>닿은 경우 먼저 나온 시간(중앙값)</th></tr></thead>
      <tbody>${row("홍수경보", w)}${row("홍수주의보", cmp["주의보"])}</tbody>
    </table></div>
    <p class="op-note">관측만 보는 통제 검토 규칙은 경보 ${num(w.issuances)}건 가운데 ${num(w.rule_fired)}건에서만 발동했고, 발동한 경우 경보보다 중앙값 ${w.rule_minus_issue.median_min}분 늦었습니다(경보보다 먼저 ${w.rule_before_issue}건). 그래서 공식 특보를 시설 단계의 하한으로 쓰고, 관측 규칙은 특보가 없는 시설을 보완하는 데 씁니다.</p>
    <ul class="op-limits">${h.limitations.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
  </div>`;
}

export async function renderScorecard(view) {
  const [registry, validation, history] = await Promise.all([
    cached("/api/twin/registry"),
    cached("/api/watch/validation-cases").catch(() => null),
    cached("/api/watch/flood-forecast-history").catch(() => null),
  ]);
  const facilityHtml = (await Promise.all(registry.operational.map((f) => facilityBlock(f).catch((e) => `<p class="op-err">${esc(f.name)} 성적표를 불러오지 못했습니다: ${esc(e.message)}</p>`)))).join("");

  view.innerHTML = `<div class="op-page">
    <header>
      <p class="op-eyebrow">장마 후 · 기준 채점</p>
      <h1 class="op-h1">기준이 실제 통제보다 빨랐나</h1>
      <p class="op-lead">언제나 울리는 경보도 "일찍" 알립니다. 그래서 선행 분은 혼자 보지 않고 세 가지와 같이 봅니다. <b>무엇을 넘었나</b>(기준), <b>다른 해에 몇 번 울렸나</b>(헛경보), <b>같은 시각 몇 곳이 같이 올랐나</b>(선별력). 늦은 사례와 헛경보가 많은 기준은 다음 해에 고칩니다.</p>
    </header>

    <section class="op-sec">
      <div class="op-sec-head"><h2>운영 시설 통제 검토 규칙</h2><span>운영 등록 ${registry.counts.operational}곳 · 저장된 사건 수위에 규칙을 그대로 재생</span></div>
      ${facilityHtml}
    </section>

    <section class="op-sec">
      <div class="op-sec-head"><h2>과거 홍수 단계·특보 신호</h2><span>${validation ? `${validation.cases.length}건` : "불러오지 못함"} · 대비 시작(주의) 신호와 통제 준비(경보·경계) 신호를 나눠 봄 · 막대는 300분에서 끊음</span></div>
      <div class="op-grid-2">${(validation?.cases ?? []).map(caseCard).join("")}</div>
      ${validation ? `<ul class="op-limits">${validation.limitations.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
    </section>

    <section class="op-sec">
      <div class="op-sec-head"><h2>공식 홍수특보 이력</h2><span>${history ? `${num(history.issuances.issuances)}건 · ${esc(history.issuances.years)} · ${esc(history.issuances.months)}월 · 관측소 ${history.issuances.stations}곳` : "불러오지 못함"}</span></div>
      ${history ? historyBlock(history) : ""}
    </section>
  </div>`;
}
