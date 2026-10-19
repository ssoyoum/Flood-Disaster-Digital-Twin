import { arrow, cached, esc, hhmm, ymd } from "../lib.js";

// 근거 · 사례 재구성. 지난 홍수를 시각 단위로 다시 놓고, 통제·대피가 언제 가능했는지 본다.
const CASES = {
  "osong-2023": { name: "2023 오송 궁평2지하차도", place: "충북 청주시 흥덕구 오송읍", flow: "미호천 제방 붕괴 → 월류 → 지하차도 침수" },
  "seoul-2022": { name: "2022 서울 도림천 유역", place: "서울 관악·동작·영등포", flow: "집중호우 → 설계강우 초과 → 저지대·반지하 침수" },
  "pohang-2022": { name: "2022 포항 냉천(힌남노)", place: "경북 포항 냉천 하류·인덕동", flow: "태풍 → 냉천 범람 → 지하주차장 유입" },
  "andong-uiseong-2026": { name: "2026 안동·의성 복합재난", place: "안동 일직면 · 의성 단촌면", flow: "산불 이재민 임시주택 → 집중호우 → 미천 홍수경보 → 대피명령" },
};
const STEP_KO = {
  warning: "홍수경보 발령", hydraulic_warning: "미호천 계획홍수위 도달", overtopping: "월류 시작", levee_failure: "임시제방 붕괴",
  underpass_inflow: "지하차도 유입 시작", unsafe_driving: "차량 통행 위험", full_inundation: "지하차도 완전 침수",
  rain_warning: "호우경보 발령", heavy_rain: "시간당 50mm 도달", design_exceeded: "설계강우 95mm/h 초과", rescue_call: "첫 구조 신고(신림동)",
  public_alert: "첫 저지대 침수 문자", national_escalation: "중대본 2단계", responders_arrive: "소방 현장 도착",
  typhoon_landfall: "태풍 거제 상륙", first_notice: "관리사무소 재방송(주장)", river_overflow: "냉천 범람 시작", move_car_broadcast: "차량 이동 안내방송",
  parking_inflow: "지하주차장 침수 시작", parking_full: "지하주차장 완전 침수", plant_outage: "포스코 전기·용수 중단", missing_report: "실종 신고",
  first_isolation: "신석리 첫 고립", flood_warning: "미천 홍수경보", camper_isolation: "광음리 캠핑카 고립", evacuation_order: "대피명령",
  predicted_warning_level: "경보 수위 도달 예측", warning_lifted: "홍수경보 해제", national_landslide_alert: "산사태 위기경보 '경계'",
};
const CONF_KO = { NEEDS_SOURCE_PAGE: "출처 쪽수 확인 필요", OBSERVED: "관측", DERIVED: "파생", PRESS_REPORT: "언론 보도", FORECAST_REPORTED: "예측 보도", OFFICIAL_AMBIGUOUS: "공식(오전·오후 미표기)" };

let map = null, timer = null, handFeatures = [];
function cleanup() { if (timer) window.clearInterval(timer); timer = null; map?.remove(); map = null; }

// 사례 간 비교: 실제 대응과 "기준대로 했다면"의 선행 분을 한 축에 놓는다.
function leadChart(cases) {
  const max = Math.max(60, ...cases.flatMap((c) => [c.actual?.lead_min ?? 0, c.counterfactual?.lead_min ?? 0].map(Math.abs)));
  const W = 1000, rowH = 54, L = 300, R = 40, H = cases.length * rowH + 30;
  const x = (v) => L + ((v + max) / (2 * max)) * (W - L - R);
  const rows = cases.map((c, i) => {
    const y = 20 + i * rowH;
    const dot = (v, fill, label, dy) => v == null ? "" : `<circle cx="${x(v)}" cy="${y + 14}" r="6" fill="${fill}"/><text x="${x(v)}" y="${y + 14 + dy}" text-anchor="middle" font-size="11" font-weight="700" fill="${fill}">${label} ${v >= 0 ? "+" : "−"}${Math.abs(v)}분</text>`;
    return `<text x="0" y="${y + 10}" font-size="13" font-weight="700" fill="#f4f4f5">${esc(c.case)}</text>
      <text x="0" y="${y + 28}" font-size="11.5" fill="#71717a">${esc(c.response)} · 기준 ${esc(c.milestone)}</text>
      <line x1="${L}" x2="${W - R}" y1="${y + 14}" y2="${y + 14}" stroke="rgba(255,255,255,.08)"/>
      ${c.actual?.lead_min != null && c.counterfactual?.lead_min != null ? `<line x1="${x(c.actual.lead_min)}" x2="${x(c.counterfactual.lead_min)}" y1="${y + 14}" y2="${y + 14}" stroke="#34d399" stroke-width="2"/>` : ""}
      ${dot(c.actual?.lead_min, "#a1a1aa", "실제", -12)}${c.actual?.lead_min == null ? `<text x="${x(0) - 10}" y="${y + 18}" text-anchor="end" font-size="11" fill="#f87171">실제: ${esc(c.actual?.label ?? "없음")}</text>` : ""}
      ${dot(c.counterfactual?.lead_min, "#34d399", "기준대로", 24)}`;
  }).join("");
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="사례별 실제 대응과 기준대로 했을 때의 선행 분">
    <line x1="${x(0)}" x2="${x(0)}" y1="6" y2="${H - 10}" stroke="#52525b"/><text x="${x(0)}" y="${H}" text-anchor="middle" font-size="11" fill="#71717a">기준 사건 시각</text>
    <text x="${W - R}" y="${H}" text-anchor="end" font-size="11" fill="#71717a">← 늦음 · 먼저 →</text>${rows}</svg>`;
}

async function listView(view) {
  const [events, leads] = await Promise.all([cached("/api/events"), cached("/api/cases/lead-times").catch(() => null)]);
  const ready = events.filter((e) => CASES[e.id]);
  view.innerHTML = `<div class="op-page">
    <header>
      <p class="op-eyebrow">근거 · 사례 재구성</p>
      <h1 class="op-h1">왜 필요한가: 지난 홍수를 시각 단위로 다시 봅니다</h1>
      <p class="op-lead">신호가 언제 있었고, 통제·대피가 언제 가능했는지 기록된 시각만으로 맞춰 놓습니다. 기준 채점의 근거 자료입니다.</p>
    </header>
    <section class="op-doors">${ready.map((e) => {
      const c = CASES[e.id];
      return `<article class="op-door"><a class="op-door-head" href="#/cases/${e.id}"><span class="op-chip">${ymd(e.started_at).slice(0, 4)}</span><b>${esc(c.name)}${arrow}</b><em>${esc(c.place)}</em></a><ul><li>${esc(c.flow)}</li></ul></article>`;
    }).join("")}</section>
    ${leads ? `<section class="op-sec"><div class="op-sec-head"><h2>사례 간 비교</h2><span>대응 시각과 기준 사건 사이의 분 · 음수는 기준 사건 뒤 · 사례마다 기준 사건이 달라 순위로 읽지 않습니다</span></div>
      <div class="op-card"><div class="op-lead-chart">${leadChart(leads.cases)}</div>
      <ul class="op-limits">${leads.cases.map((c) => `<li>${esc(c.case)}: ${esc(c.counterfactual?.label ?? "")} · ${esc(c.evidence ?? "")}</li>`).join("")}${leads.limitations.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div></section>` : ""}
  </div>`;
}

function mountHandMap(container, layers, replay, onReady) {
  const ESRI = "https://services.arcgisonline.com/ArcGIS/rest/services/Canvas";
  map = new maplibregl.Map({ container, attributionControl: { compact: true },
    style: { version: 8, sources: { base: { type: "raster", tiles: [`${ESRI}/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}`], tileSize: 256, maxzoom: 16, attribution: "Esri" } },
      layers: [{ id: "bg", type: "background", paint: { "background-color": "#0b0b0e" } }, { id: "base", type: "raster", source: "base", paint: { "raster-brightness-max": 0.75 } }] } });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
  map.on("load", () => {
    const add = (key) => map.addSource(key, { type: "geojson", data: layers[key]?.data ?? { type: "FeatureCollection", features: [] } });
    ["aoi", "waterways", "roads", "hand_reconstruction", "underpass"].forEach(add);
    map.addLayer({ id: "water", type: "fill", source: "waterways", paint: { "fill-color": "#1f6fa3", "fill-opacity": 0.55 } });
    map.addLayer({ id: "roads", type: "line", source: "roads", paint: { "line-color": "#3f3f46", "line-width": 0.8 } });
    map.addLayer({ id: "aoi", type: "line", source: "aoi", paint: { "line-color": "#71717a", "line-width": 1, "line-dasharray": [3, 3] } });
    map.addLayer({ id: "hand", type: "fill", source: "hand_reconstruction", filter: ["all", ["==", ["geometry-type"], "Polygon"], ["==", ["get", "stage_index"], -1]],
      paint: { "fill-color": "#f87171", "fill-opacity": ["interpolate", ["linear"], ["get", "hand_threshold_m"], 0, 0.2, 6, 0.45] } });
    map.addLayer({ id: "hand-line", type: "line", source: "hand_reconstruction", filter: ["all", ["==", ["geometry-type"], "Polygon"], ["==", ["get", "stage_index"], -1]], paint: { "line-color": "#f87171", "line-width": 0.6 } });
    map.addLayer({ id: "underpass", type: "line", source: "underpass", paint: { "line-color": "#fbbf24", "line-width": 4 } });
    const coords = (layers.aoi?.data?.features ?? []).flatMap((f) => f.geometry.type === "Polygon" ? f.geometry.coordinates.flat() : f.geometry.coordinates.flat(2));
    if (coords.length) {
      const lons = coords.map((c) => c[0]), lats = coords.map((c) => c[1]);
      map.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], { padding: 30, duration: 0 });
    }
    onReady();
  });
}

async function detailView(view, id) {
  const c = CASES[id];
  if (!c) { view.innerHTML = '<div class="op-page"><p class="op-err">알 수 없는 사례입니다.</p></div>'; return; }
  const [recon, leads] = await Promise.all([cached(`/api/events/${id}/reconstruction`), cached("/api/cases/lead-times").catch(() => null)]);
  const steps = recon.replay ?? [];
  const lead = leads?.cases.find((x) => x.event_id === id);
  const isOsong = id === "osong-2023";
  view.innerHTML = `<div class="op-page">
    <header>
      <p class="op-eyebrow"><a href="#/cases">사례 재구성</a> · ${esc(c.place)}</p>
      <h1 class="op-h1">${esc(c.name)}</h1>
      <p class="op-lead">${esc(c.flow)}</p>
    </header>
    ${lead ? `<dl class="op-why">
      <div><dt><b>1</b>기준 사건</dt><dd>${esc(lead.milestone)}<small>${esc(lead.response)}</small></dd></div>
      <div><dt><b>2</b>실제 대응</dt><dd>${lead.actual?.lead_min != null ? `<strong class="${lead.actual.lead_min >= 0 ? "op-early" : "op-late"}">${lead.actual.lead_min >= 0 ? "+" : "−"}${Math.abs(lead.actual.lead_min)}분</strong>` : '<strong class="op-late">없음</strong>'}<small>${esc(lead.actual?.time ?? "")} ${esc(lead.actual?.label ?? "")}</small></dd></div>
      <div><dt><b>3</b>기준대로 했다면</dt><dd>${lead.counterfactual?.lead_min != null ? `<strong class="op-early">+${lead.counterfactual.lead_min}분</strong>` : "—"}<small>${esc(lead.counterfactual?.time ?? "")} ${esc(lead.counterfactual?.label ?? "")} · ${esc(lead.evidence ?? "")}</small></dd></div>
    </dl>` : ""}
    <div class="op-replay" role="group" aria-label="사건 재생">
      <div class="op-replay-label"><span>사건 재생</span><strong id="op-replay-now">—</strong></div>
      <button type="button" id="op-prev" aria-label="이전 단계" title="이전 단계">‹</button>
      <button type="button" id="op-play" class="primary">▶ 재생</button>
      <button type="button" id="op-next" aria-label="다음 단계" title="다음 단계">›</button>
      <div class="op-replay-track">
        <input type="range" id="op-range" min="0" max="${Math.max(0, steps.length - 1)}" value="0" aria-label="재구성 단계">
        <div class="op-replay-ticks">${steps.map((s) => `<span>${hhmm(s.time)}</span>`).join("")}</div>
      </div>
    </div>
    <div class="op-case-layout">
      <div class="op-card">
        <div class="op-card-head"><h3>재구성 단계 ${steps.length}개</h3></div>
        <ol class="op-steps" id="op-steps">${steps.map((s, i) => `<li data-i="${i}"><time>${hhmm(s.time)}</time><i></i><span><b>${esc(STEP_KO[s.state] ?? s.label)}</b><small>${esc(CONF_KO[s.confidence] ?? s.confidence ?? "")}</small></span></li>`).join("")}</ol>
      </div>
      ${isOsong
        ? `<div class="op-map" id="op-map"><div class="op-map-wait" id="op-map-wait">지형·HAND 레이어를 불러오는 중(약 10 MB)</div>
            <div class="op-map-legend"><span><i style="background:#f87171"></i>침수 추정 범위(HAND 근사)</span><span><i style="background:#1f6fa3"></i>하천</span><span><i style="background:#fbbf24"></i>궁평2지하차도</span><span id="op-hand-count"></span></div></div>`
        : `<div class="op-card"><h3 id="op-step-title">단계를 고르세요</h3><p class="op-note" id="op-step-body">왼쪽 단계를 누르면 출처와 확인 수준이 보입니다. 이 사례는 지도 없이 시각 기록만 재구성했습니다.</p></div>`}
    </div>
    <p class="op-note">침수 범위는 관측·지형(HAND) 기반 근사이며 공식 침수범위가 아닙니다. 시각은 보도·공식 발표 기준이고 확인 수준을 단계마다 표시합니다.</p>
  </div>`;

  let current = 0;
  const select = (i) => {
    current = i;
    view.querySelectorAll("#op-steps li").forEach((li) => { const k = Number(li.dataset.i); li.classList.toggle("on", k === i); li.classList.toggle("past", k < i); });
    const step = steps[i];
    view.querySelector("#op-replay-now").textContent = step ? `${hhmm(step.time)} · ${STEP_KO[step.state] ?? step.label}` : "재구성 단계 없음";
    view.querySelector("#op-range").value = String(i);
    view.querySelector("#op-prev").disabled = i <= 0;
    view.querySelector("#op-next").disabled = i >= steps.length - 1;
    if (!isOsong) {
      view.querySelector("#op-step-title").textContent = `${hhmm(step.time)} ${STEP_KO[step.state] ?? step.label}`;
      view.querySelector("#op-step-body").textContent = `출처: ${step.source ?? "—"} · 확인 수준: ${CONF_KO[step.confidence] ?? step.confidence ?? "—"}`;
    }
    if (map?.getLayer("hand")) {
      const filter = ["all", ["==", ["geometry-type"], "Polygon"], ["==", ["get", "stage_index"], i]];
      map.setFilter("hand", filter); map.setFilter("hand-line", filter);
      const cells = handFeatures.filter((f) => f.properties?.stage_index === i && f.geometry?.type === "Polygon");
      const el = view.querySelector("#op-hand-count");
      if (el) el.textContent = `이 단계 추정 셀 ${cells.length}개`;
    }
  };
  // 예전 사건 콘솔과 같은 재생 막대: ‹ ▶ › 와 시간 막대. 손으로 움직이면 재생을 멈춘다.
  const playButton = view.querySelector("#op-play");
  const stop = () => { if (timer) window.clearInterval(timer); timer = null; playButton.textContent = "▶ 재생"; };
  const manual = (i) => { stop(); select(Math.max(0, Math.min(steps.length - 1, i))); };
  view.querySelectorAll("#op-steps li").forEach((li) => li.addEventListener("click", () => manual(Number(li.dataset.i))));
  view.querySelector("#op-prev").addEventListener("click", () => manual(current - 1));
  view.querySelector("#op-next").addEventListener("click", () => manual(current + 1));
  view.querySelector("#op-range").addEventListener("input", (e) => manual(Number(e.target.value)));
  playButton.disabled = !steps.length;
  playButton.addEventListener("click", () => {
    if (timer) { stop(); return; }
    if (current >= steps.length - 1) select(0);
    playButton.textContent = "❚❚ 일시정지";
    timer = window.setInterval(() => { if (current + 1 >= steps.length) { stop(); return; } select(current + 1); }, 1200);
  });
  select(0);

  if (isOsong) {
    const layers = await cached("/api/events/osong-2023/layers?year=2023");
    if (!document.getElementById("op-map")) return;  // 그사이 다른 화면으로 옮겼다
    handFeatures = layers.hand_reconstruction?.data?.features ?? [];
    mountHandMap(document.getElementById("op-map"), layers, steps, () => { document.getElementById("op-map-wait")?.remove(); select(current); });
  }
}

export async function renderCases(view, route) {
  cleanup();
  if (route.parts[0]) return detailView(view, route.parts[0]);
  return listView(view);
}
window.addEventListener("hashchange", () => { if (!window.location.hash.startsWith("#/cases/")) cleanup(); });
