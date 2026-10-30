import { cached, esc, hhmm, minutes, num, ymd } from "../lib.js";

// 장마 후 · 기준 채점. 이번 시즌 담당자가 남긴 통제 기록과 규칙의 권고를 맞춘다.
// 과거 홍수에 규칙을 재생한 검증은 사례 재구성에서만 보여 준다.

const LEVEL_NAME = { advisory: "주의보 수위", warning: "경보 수위" };
const OUTCOME = {
  hit: { label: "적중", tone: "ok", note: "권고 구간 앞뒤로 통제 기록이 있음" },
  not_closed: { label: "막지 않음", tone: "", note: "권고를 보고 막지 않기로 기록함" },
  unrecorded: { label: "기록 없음", tone: "wait", note: "권고는 났지만 통제 기록이 없음(오경보로 세지 않음)" },
  miss: { label: "누락", tone: "bad", note: "권고 없이 통제한 기록" },
  quiet: { label: "조용", tone: "", note: "권고도 통제 기록도 없음" },
};

function countsBlock(counts) {
  return `<div class="op-grid-4">${["hit", "not_closed", "unrecorded", "miss"].map((k) => `<div class="op-card">
      <span class="op-chip" data-tone="${OUTCOME[k].tone}">${OUTCOME[k].label}</span>
      <h3 class="op-num">${num(counts?.[k] ?? 0)}<small>건</small></h3>
      <p class="op-note">${OUTCOME[k].note}</p></div>`).join("")}</div>`;
}

function rowsTable(rows) {
  if (!rows.length) return '<p class="op-note">이 시즌에는 규칙 권고도, 담당자 통제 기록도 없었습니다.</p>';
  return `<div class="op-table-wrap"><table class="op-table">
    <thead><tr><th>권고 구간</th><th>최고 수위</th><th>통제 기록</th><th>결과</th><th>권고 → 통제</th></tr></thead>
    <tbody>${rows.map((r) => {
      const ep = r.episode;
      const recs = (r.records ?? []).map((x) => `${esc(String(x.started_at ?? "").slice(5, 16).replace("T", " "))} ${esc(x.checked_by ?? "")}`).join("<br>") || "—";
      const o = OUTCOME[r.outcome] ?? { label: r.outcome, tone: "" };
      return `<tr><td>${ep ? `${esc(ep.start.slice(5, 16).replace("T", " "))} ~ ${hhmm(ep.end)} <span class="op-note">${ep.review_minutes}분</span>` : "권고 없음"}</td>
        <td class="op-num">${ep?.peak_water_level_m ?? "—"} m</td><td>${recs}</td>
        <td><span class="op-chip" data-tone="${o.tone}">${o.label}</span></td>
        <td class="op-num">${r.lead_min == null ? "—" : minutes(r.lead_min)}</td></tr>`;
    }).join("")}</tbody></table></div>`;
}

function candidatesTable(card) {
  const lv = card.levels_m;
  return `<div class="op-table-wrap"><table class="op-table">
    <thead><tr><th>기준 단계</th><th>상승 속도 조건</th><th>권고 구간</th><th>적중</th><th>기록 없음</th><th>누락</th></tr></thead>
    <tbody>${card.candidates.map((c) => `<tr class="${c.is_current_rule ? "cur" : ""}">
      <td>${LEVEL_NAME[c.stage_floor] ?? c.stage_floor} ${lv[c.stage_floor]} m 이상</td>
      <td>${c.lead_threshold_min ? `계획홍수위까지 ${c.lead_threshold_min}분 이내` : "계획홍수위 도달"}${c.is_current_rule ? ' <span class="op-chip" data-tone="ok">현재 규칙</span>' : ""}</td>
      <td class="op-num">${c.episodes}</td><td class="op-num">${c.counts.hit}</td><td class="op-num">${c.counts.unrecorded}</td><td class="op-num">${c.counts.miss}</td></tr>`).join("")}</tbody>
  </table></div>`;
}

async function facilityBlock(facility, season) {
  const card = await cached(`/api/twin/facilities/${facility.id}/season-scorecard?season=${season}`);
  const w = card.window;
  const seasons = card.available_seasons.map((y) => `<a class="op-chip" href="#/scorecard?season=${y}"${y === card.season ? ' data-tone="ok" aria-current="true"' : ""}>${y}</a>`).join(" ");
  return `<article class="op-card">
    <div class="op-card-head"><div><h3>${esc(card.facility)} · ${card.season} 장마</h3>
      <small>${ymd(w.start)} – ${ymd(w.end)} · 저장된 10분 수위 ${num(w.readings)}개 · 시즌 최고 ${w.max_water_level_m ?? "—"} m · 통제 기록 ${num(card.records)}건</small></div>
      <div>${seasons}</div></div>
    ${countsBlock(card.counts)}
    <h3>권고와 통제 기록</h3>
    ${rowsTable(card.rows)}
    <p class="op-note">권고 → 통제 중앙값 ${card.median_lead_min == null ? "—" : minutes(card.median_lead_min)} · ${esc(card.method)}</p>
    <h3>같은 기록으로 본 기준 후보 ${card.candidates.length}개</h3>
    ${candidatesTable(card)}
    <ul class="op-limits">${(card.limitations ?? []).map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
  </article>`;
}

// 전체 시설: 서버가 10분마다 기록한 실시간 보드로 채점한다. 과거 이력을 받지 않으므로 기록 시작 이후만 있다.
function boardBlock(b) {
  const cov = b.coverage;
  const c = b.counts;
  const since = cov.from ? `${cov.from.slice(0, 16).replace("T", " ")}부터 ${cov.to.slice(5, 16).replace("T", " ")}까지 ${num(cov.snapshots)}회 기록` : "아직 기록 없음 · 서버가 실시간으로 돌면 10분마다 쌓입니다";
  const tiles = [
    ["주의 이상 도달", c.reached["주의"], "곳", "#fbbf24"], ["경계 이상 도달", c.reached["경계"], "곳", "#fb923c"],
    ["경보 구간", c.episodes, "회", "#e4e4e7"], ["특보 없이 혼자 울림", c.episodes_alone, "회", "#a1a1aa"],
  ].map(([label, value, unit, color]) => `<div class="op-card"><span class="op-note">${label}</span><h3 class="op-num" style="color:${color}">${num(value)}<small>${unit}</small></h3></div>`).join("");
  const rows = b.facilities.filter((r) => r.episodes > 0).slice(0, 50);
  const table = rows.length ? `<div class="op-table-wrap"><table class="op-table">
      <thead><tr><th>시설</th><th>유형 · 지역</th><th>최고 단계</th><th>경보 구간</th><th>특보 동반 / 혼자</th><th>주의·경계·심각 시간</th><th>마지막 구간</th></tr></thead>
      <tbody>${rows.map((r) => {
        const m = r.minutes_by_level;
        const last = r.last_episode;
        return `<tr><td><b>${esc(r.name)}</b></td><td>${esc(r.kind_ko ?? "")} · ${esc(r.region ?? "")}</td><td>${esc(r.peak_label ?? "—")}</td>
          <td class="op-num">${r.episodes}</td><td class="op-num">${r.episodes_with_official} / ${r.episodes_alone}</td>
          <td class="op-num">${Math.round(m["주의"] / 60)} · ${Math.round(m["경계"] / 60)} · ${Math.round(m["심각"] / 60)}시간</td>
          <td>${last ? `${esc(last.start.slice(5, 16).replace("T", " "))} ~ ${hhmm(last.end)}` : "—"}</td></tr>`;
      }).join("")}</tbody></table></div>`
    : '<p class="op-note">기록 기간 동안 주의 이상에 든 시설이 없습니다. 비가 오면 여기에 시설별 경보 구간이 쌓입니다. 화면을 시험하려면 관제 보드의 «가상 강우»를 쓰세요(가상 강우는 기록하지 않음).</p>';
  return `<div class="op-card">
    <div class="op-card-head"><div><h3>전체 ${num(c.facilities)}곳 · ${b.season}년 기록</h3><small>${since}</small></div></div>
    <div class="op-grid-4">${tiles}</div>
    ${table}
    <p class="op-note">${esc(b.method)}</p>
    <ul class="op-limits">${b.limitations.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>
  </div>`;
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

export async function renderScorecard(view, route) {
  const season = Number(route.query.get("season")) || new Date().getFullYear();
  const [registry, history, board] = await Promise.all([
    cached("/api/twin/registry"),
    cached("/api/watch/flood-forecast-history").catch(() => null),
    cached(`/api/watch/season-board?season=${Math.max(2026, season)}`).catch(() => null),
  ]);
  const facilityHtml = (await Promise.all(registry.operational.map((f) => facilityBlock(f, season).catch((e) => `<p class="op-err">${esc(f.name)} 성적표를 불러오지 못했습니다: ${esc(e.message)}</p>`)))).join("");

  view.innerHTML = `<div class="op-page">
    <header>
      <p class="op-eyebrow">장마 후 · 기준 채점</p>
      <h1 class="op-h1">이번 장마, 기준이 실제 통제보다 빨랐나</h1>
      <p class="op-lead">담당자가 남긴 통제 기록과 규칙의 권고를 시즌 단위로 맞춥니다. 권고만 나고 기록이 없으면 오경보로 세지 않고 «기록 없음»으로 둡니다. 과거 홍수에 규칙을 재생한 검증은 <a href="#/cases">사례 재구성</a>에서 봅니다.</p>
    </header>

    <section class="op-sec">
      <div class="op-sec-head"><h2>전체 시설 시즌 기록</h2><span>과거 이력 없이, 서버가 10분마다 남긴 실시간 판정으로 채점 · 새로 넣은 시설도 넣은 때부터 자동으로 채점</span></div>
      ${board ? boardBlock(board) : '<p class="op-err">시즌 기록을 불러오지 못했습니다.</p>'}
    </section>

    <section class="op-sec">
      <div class="op-sec-head"><h2>운영 시설 시즌 성적표</h2><span>운영 등록 ${registry.counts.operational}곳 · 시즌 5/15–10/15 · 통제 기록은 시설 기준 › 지금 상태에서 남김</span></div>
      ${facilityHtml}
    </section>

    <section class="op-sec">
      <div class="op-sec-head"><h2>공식 홍수특보 이력</h2><span>${history ? `${num(history.issuances.issuances)}건 · ${esc(history.issuances.years)} · ${esc(history.issuances.months)}월 · 관측소 ${history.issuances.stations}곳` : "불러오지 못함"}</span></div>
      ${history ? historyBlock(history) : ""}
    </section>
  </div>`;
}
