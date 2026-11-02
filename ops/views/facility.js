import { API, arrow, cached, esc, get, STAGE_COLOR, STAGE_KO } from "../lib.js";
import { mountAgent } from "../agent.js";

// 장마 전 · 시설 기준. 업무 순서대로: 어떤 시설을 운영할지 → 기준 → 장마 중 지금 상태.
// 과거 사건에 규칙을 재생한 결과는 사례 재구성에서만 보여 준다.
const SUBTABS = [
  { id: "registry", label: "시설 등록" },
  { id: "criteria", label: "통제 기준 검토" },
  { id: "now", label: "지금 상태" },
];
const GATE_TONE = { CONFIRMED: "ok", PENDING: "wait", MISSING: "bad", UNKNOWN: "" };
const GATE_KO = { CONFIRMED: "확인", PENDING: "확인 대기", MISSING: "자료 없음", UNKNOWN: "미확인" };
const RECO_KO = { NORMAL: "정상", MONITOR: "감시", CLOSURE_REVIEW: "통제 검토" };
const CONFIRM_KO = { CONFIRMED: "통제 확인", NO_ACTION: "조치 없음", ESCALATE: "상급 보고" };
const DRIVER_KO ={ river_stage: "하천 수위형", unverified: "미검증", pluvial_hypothesis: "내수형 가설" };
// 하위 탭마다 시설 에이전트 추천 질문을 앞세우는 순서(workflow는 /api/agent/examples?facility_id= 의 값).
const AGENT_FLOWS = {
  registry: ["control_rule", "facility_backtest", "criteria_review", "facility_status", "rise_forecast"],
  criteria: ["criteria_review", "facility_backtest", "control_rule", "facility_status", "rise_forecast"],
  now: ["facility_status", "control_rule", "rise_forecast", "facility_backtest", "criteria_review"],
};

function gateChips(registry, f) {
  return `<div class="op-gates">${registry.gates.map((g) => {
    const gate = f.gates?.[g.id] ?? {};
    return `<span class="op-chip" data-tone="${GATE_TONE[gate.status] ?? ""}" title="${esc(g.question)}${gate.note ? `\n${esc(gate.note)}` : ""}">${esc(g.label)} · ${GATE_KO[gate.status] ?? "미확인"}</span>`;
  }).join("")}</div>`;
}

function registryView(registry) {
  const operationalNames = new Set(registry.operational.map((f) => f.name));
  const card = (f) => {
    const duplicate = f.status === "CANDIDATE" && operationalNames.has(f.name);
    return `<article class="op-card">
      <div class="op-card-head"><div><h3>${esc(f.name)}</h3><small>${esc(f.region ?? "지역 미상")}${f.road ? ` · ${esc(f.road)}` : ""}${f.managing_agency ? ` · ${esc(f.managing_agency)}` : ""}</small></div>
        <span class="op-chip" data-tone="${f.status === "OPERATIONAL" ? "ok" : ""}">${f.status === "OPERATIONAL" ? "운영" : "후보"}</span></div>
      <div class="op-kv">
        <div><span>잠김 원인</span><b>${esc(DRIVER_KO[f.driver] ?? f.driver)}</b></div>
        <div><span>대표 관측소</span><b>${esc(f.gauge?.name ?? "미연결")}</b></div>
      </div>
      ${gateChips(registry, f)}
      ${duplicate ? '<p class="op-note" style="color:var(--amber)">운영 시설과 이름이 같은 후보입니다. 같은 시설이 중복 등록됐는지 확인이 필요합니다.</p>' : ""}
      <a class="op-go" style="align-self:flex-start" href="#/facility/registry?facility=${encodeURIComponent(f.id)}&agent=open">${f.status === "OPERATIONAL" ? "이 시설 에이전트에게 묻기" : "에이전트 · 왜 답하지 않나"}</a>
    </article>`;
  };
  return `<section class="op-sec">
      <div class="op-sec-head"><h2>운영 등록 관문</h2><span>네 관문을 통과해야 시설별 통제 규칙을 붙입니다. 칩에 마우스를 올리면 확인 질문과 근거가 보입니다.</span></div>
      <div class="op-grid-4">${registry.gates.map((g, i) => `<div class="op-card"><span class="op-chip">${i + 1}</span><h3>${esc(g.label)}</h3><p class="op-note">${esc(g.question)}</p></div>`).join("")}</div>
    </section>
    <section class="op-sec">
      <div class="op-sec-head"><h2>운영 ${registry.counts.operational} · 후보 ${registry.counts.candidate}</h2><span>후보는 운영 규칙에 쓰지 않습니다</span></div>
      <div class="op-grid-2">${[...registry.operational, ...registry.candidates].map(card).join("")}</div>
    </section>`;
}

function criteriaView(review) {
  const lv = review.station.levels_m;
  const cur = review.current_rule;
  const maxCost = Math.max(1, ...review.sweep.map((r) => r.other_review_minutes ?? 0));
  const rows = review.sweep.map((r) => {
    const isCur = r.stage_floor === cur.stage_floor && r.lead_threshold_min === cur.lead_threshold_min;
    return `<tr class="${isCur ? "cur" : ""}">
      <td>${r.stage_floor === "warning" ? "경보" : "주의보"} 수위 ${lv[r.stage_floor]} m 이상</td>
      <td>${r.lead_threshold_min ? `계획홍수위까지 ${r.lead_threshold_min}분 이내` : "계획홍수위 도달"}${isCur ? ' <span class="op-chip" data-tone="ok">현재 규칙</span>' : ""}</td>
      <td><div class="op-cellbar"><i class="cost" style="width:${((r.other_review_minutes ?? 0) / maxCost) * 80}px"></i><b>${r.other_episode_count}회</b><span class="op-note">${r.other_review_minutes}분</span></div></td>
    </tr>`;
  }).join("");
  const maxYear = Math.max(lv.planned_flood, ...review.by_year.map((y) => y.max_water_level_m ?? 0));
  const years = review.by_year.map((y) => {
    const pct = (v) => `${(v / maxYear) * 100}%`;
    return `<tr><td>${y.year}</td>
      <td style="width:55%"><div style="position:relative;height:10px;border-radius:5px;background:rgba(255,255,255,.05)">
        <i style="position:absolute;left:0;top:0;bottom:0;width:${pct(y.max_water_level_m ?? 0)};border-radius:5px;background:${(y.max_water_level_m ?? 0) >= lv.warning ? "#fb923c" : "#38bdf8"}"></i>
        ${["advisory", "warning", "planned_flood"].map((k) => `<span title="${STAGE_KO[k]} ${lv[k]} m" style="position:absolute;left:${pct(lv[k])};top:-3px;bottom:-3px;width:1px;background:${STAGE_COLOR[k]}"></span>`).join("")}
      </div></td>
      <td class="op-num">${y.max_water_level_m ?? "—"} m</td><td class="op-num">${y.episodes}회 · ${y.review_minutes}분</td></tr>`;
  }).join("");
  return `<section class="op-sec">
      <div class="op-sec-head"><h2>기준 후보 비교</h2><span>${esc(review.station.name)} · 일찍 잡는 기준일수록 권고가 자주 납니다</span></div>
      <div class="op-card"><div class="op-table-wrap"><table class="op-table">
        <thead><tr><th>기준 단계</th><th>상승 속도 조건</th><th>저장된 해 권고</th></tr></thead>
        <tbody>${rows}</tbody></table></div>
        <p class="op-note">"계획홍수위까지 N분 이내"는 지금 상승 속도를 이어 그었을 때의 시간입니다. 권고 횟수는 통제·침수 기록과 대조하지 않은 후보이며 오경보로 확정하지 않습니다. 과거 사건 대비 몇 분 먼저였는지는 <a href="#/cases/osong-2023">사례 재구성 › 오송 ${arrow}</a>에서 봅니다.</p>
      </div>
    </section>
    <section class="op-sec">
      <div class="op-sec-head"><h2>해마다 최고 수위</h2><span>세로선은 주의보 ${lv.advisory} · 경보 ${lv.warning} · 계획홍수위 ${lv.planned_flood} m. 경보 수위를 넘고도 권고가 없던 해는 상승 속도가 조건에 못 미친 해입니다.</span></div>
      <div class="op-card"><div class="op-table-wrap"><table class="op-table"><thead><tr><th>연도</th><th>최고 수위</th><th></th><th>권고</th></tr></thead><tbody>${years}</tbody></table></div>
      <ul class="op-limits">${(review.limitations ?? []).map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
    </section>`;
}

async function nowView(facility) {
  const decisions = await get(`/api/twin/facilities/${facility.id}/decisions`).catch(() => ({ records: [] }));
  const src = `../public/twin-now-c.html?api=${encodeURIComponent(API)}&facility=${encodeURIComponent(facility.id)}`;
  return `<iframe class="op-frame" title="${esc(facility.name)} 지금 상태" src="${esc(src)}"></iframe>
    <section class="op-sec">
      <div class="op-sec-head"><h2>담당자 확인 기록</h2><span>${decisions.records.length}건 · 권고를 본 담당자가 남긴 확인·결과</span></div>
      ${decisions.records.length ? `<div class="op-card"><div class="op-table-wrap"><table class="op-table"><thead><tr><th>기록 시각</th><th>관측</th><th>권고</th><th>확인</th><th>확인자</th><th>메모</th></tr></thead><tbody>${decisions.records.map((r) => `<tr><td>${esc(String(r.recorded_at ?? "").slice(0, 16).replace("T", " "))}</td><td>${esc(r.stage_label ?? "")} · ${esc(r.water_level_m ?? "—")} m</td><td>${esc(RECO_KO[r.recommendation] ?? r.recommendation ?? "")}</td><td>${esc(CONFIRM_KO[r.confirmation] ?? r.confirmation ?? "")}</td><td>${esc(r.checked_by ?? "")}</td><td>${esc(r.note ?? "")}</td></tr>`).join("")}</tbody></table></div></div>` : '<p class="op-note">아직 기록이 없습니다. 위 화면에서 확인을 남기면 여기에 쌓입니다.</p>'}
    </section>`;
}

export async function renderFacility(view, route) {
  const sub = SUBTABS.some((t) => t.id === route.parts[0]) ? route.parts[0] : "registry";
  const registry = await cached("/api/twin/registry");
  const facility = registry.operational.find((f) => f.id === route.query.get("facility")) ?? registry.operational[0];
  // 에이전트는 등록 카드에서 고른 시설(후보 포함)을 따른다. 기준 검토·지금 상태 본문은 운영 시설만 그린다.
  const target = [...registry.operational, ...registry.candidates].find((f) => f.id === route.query.get("facility")) ?? facility;
  let body = "";
  if (sub === "registry") body = registryView(registry);
  else if (!facility) body = '<p class="op-note">운영 등록 시설이 없습니다.</p>';
  else if (sub === "criteria") body = criteriaView(await cached(`/api/twin/facilities/${facility.id}/criteria-review`));
  else body = await nowView(facility);

  view.innerHTML = `<div class="op-page">
    <header>
      <p class="op-eyebrow">장마 전 · 시설 기준</p>
      <h1 class="op-h1">이 시설은 어떤 신호로, 몇 분 전에 막나</h1>
      <p class="op-lead">${facility ? `${esc(facility.name)} · 대표 관측소 ${esc(facility.gauge?.name ?? "")}. ` : ""}관문을 통과한 시설에만 통제 규칙을 붙이고, 기준 후보마다 권고가 얼마나 자주 나는지 비교해 고릅니다.</p>
    </header>
    <nav class="op-subtabs" aria-label="시설 기준">${SUBTABS.map((t) => `<a href="#/facility/${t.id}${route.query.get("facility") ? `?facility=${encodeURIComponent(route.query.get("facility"))}` : ""}"${t.id === sub ? ' aria-current="page"' : ""}>${t.label}</a>`).join("")}</nav>
    ${body}
    ${sub === "criteria" ? `<p class="op-note">현재 규칙의 결과는 <a href="#/scorecard">기준 채점 ${arrow}</a>에서 장마 후 성적표로 봅니다.</p>` : ""}
  </div>`;
  if (target) mountAgent(view, facilityAgent(registry, target, facility, sub, route.query.get("agent") === "open"));
}

// 운영 시설은 시설 도구(관측 상태·통제 기준·백테스트·기준 비교·연구 모델)로 묻는다.
// 후보 시설에는 붙은 도구가 없으므로 질문을 받지 않고, 어떤 관문이 남았는지만 보여 준다.
function facilityAgent(registry, target, operational, sub, open) {
  const base = { key: `facility:${target.id}`, title: `${target.name} 에이전트`, open };
  if (target.status !== "OPERATIONAL") {
    const pending = registry.gates.filter((g) => target.gates?.[g.id]?.status !== "CONFIRMED").map((g) => `${esc(g.label)}(${GATE_KO[target.gates?.[g.id]?.status] ?? "미확인"})`);
    return {
      ...base,
      badge: "후보 · 도구 없음",
      intro: `${esc(target.name)}${target.region ? ` · ${esc(target.region)}` : ""} — 운영 등록 전 후보 시설입니다.`,
      gated: {
        html: `<p>시설별 에이전트 도구(관측 상태·통제 검토 기준·과거 수위 백테스트·기준 비교)는 <b>네 관문을 모두 통과해 운영 등록된 시설</b>에만 붙습니다. 이 시설에는 아직 붙은 도구가 없어 질문을 받지 않습니다. 근거 없는 답을 만들지 않기 위해서입니다.</p>
          ${gateChips(registry, target)}
          <p>${pending.length ? `남은 관문: ${pending.join(" · ")}` : "관문 기록은 모두 확인이지만 아직 운영 등록되지 않았습니다."}</p>
          ${operational ? `<p><a href="#/facility/${sub}?facility=${encodeURIComponent(operational.id)}&agent=open">운영 시설 ${esc(operational.name)} 에이전트로 ${arrow}</a></p>` : ""}`,
      },
    };
  }
  const eventId = target.event_id ?? "osong-2023";
  return {
    ...base,
    badge: "운영 · 시설 도구",
    intro: `${esc(target.name)} · 대표 관측소 ${esc(target.gauge?.name ?? "")}. 관측 상태, 통제 검토 기준과 근거, 과거 수위 백테스트, 기준을 바꿨을 때의 비교를 물어보세요. 실제 침수심·피해 감소·통제 실행은 계산하거나 수행하지 않습니다.`,
    scope: { event_id: eventId, facility_id: target.id },
    examples: `/api/agent/examples?event_id=${encodeURIComponent(eventId)}&facility_id=${encodeURIComponent(target.id)}`,
    workflows: AGENT_FLOWS[sub] ?? AGENT_FLOWS.registry,
    placeholder: "예: 기준을 경보+60분으로 바꾸면 몇 분 먼저 검토하나요?",
  };
}
