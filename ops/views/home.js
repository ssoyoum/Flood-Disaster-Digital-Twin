import { arrow, cached, esc, num, splitBar, unitDots, yearBars } from "../lib.js";

// 장마 전 → 중 → 후가 한 바퀴로 이어지고, 채점 결과가 다음 해 기준으로 돌아간다.
const CYCLE = `<figure class="op-cycle" aria-label="장마 전·중·후 업무 순환">
  <svg viewBox="0 0 460 330" role="img">
    <defs><marker id="op-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#71717a"/></marker></defs>
    <path class="edge flow" d="M110 192 L178 112" marker-end="url(#op-arrow)"/>
    <path class="edge flow" d="M282 112 L350 192" marker-end="url(#op-arrow)"/>
    <path class="edge back flow" d="M268 262 C 240 300, 220 300, 192 262" marker-end="url(#op-arrow)"/>
    <text class="backlabel" x="230" y="316" text-anchor="middle">다음 해 기준 수정</text>
    ${[
      { x: 30, y: 196, season: "장마 전", title: "시설 기준", sub: "어떤 신호로 몇 분 전에", href: "#/facility" },
      { x: 150, y: 24, season: "장마 중", title: "관제 보드", sub: "지금 어디를 먼저", href: "#/watch" },
      { x: 270, y: 196, season: "장마 후", title: "기준 채점", sub: "실제 통제보다 빨랐나", href: "#/scorecard" },
    ].map((n, i) => `<a href="${n.href}" aria-label="${n.season} ${n.title} 화면 열기"><g class="node" transform="translate(${n.x} ${n.y})" style="--i:${i}">
      <rect class="ring" width="160" height="84" rx="12"/><rect class="card" width="160" height="84" rx="12"/>
      <text class="season" x="16" y="26">${n.season}</text><text class="title" x="16" y="52">${n.title}</text><text class="sub" x="16" y="72">${n.sub}</text>
      <text class="go" x="146" y="26" text-anchor="end">열기 →</text></g></a>`).join("")}
  </svg>
  <figcaption>상자를 누르면 그 시기의 화면으로 갑니다 · <a href="#/cases">사례 재구성</a>은 세 시기를 뒷받침하는 근거 자료입니다.</figcaption>
</figure>`;

// 화면 카드 위 도식: 누르면 어떤 화면이 나오는지 구성만 단순하게 그린다(실제 캡처 아님).
const SKETCH = {
  watch: `<svg viewBox="0 0 320 200" role="img" aria-label="관제 보드 도식: 왼쪽 위험 순위 목록과 지도 위 시설 점">
    <rect width="320" height="200" fill="#0d1117"/>
    <path d="M196 22 C226 18 250 34 252 58 C262 74 258 96 246 112 C252 132 240 150 226 160 C214 176 192 182 178 172 C166 160 170 140 162 126 C150 110 156 92 168 80 C172 58 176 30 196 22Z" fill="#1c2430" stroke="#2f3b4b"/>
    ${[[190, 48, "#f87171", 6], [204, 60, "#fb923c", 5], [184, 70, "#fbbf24", 4], [214, 92, "#38bdf8", 3], [200, 118, "#38bdf8", 3], [226, 132, "#fbbf24", 4], [190, 150, "#38bdf8", 3], [236, 74, "#38bdf8", 3], [172, 104, "#38bdf8", 3], [210, 160, "#38bdf8", 3]]
      .map(([x, y, c, r], i) => `<circle cx="${x}" cy="${y}" r="${r}" fill="${c}"${i < 2 ? ` class="pulse"` : ""}/>`).join("")}
    <rect x="12" y="14" width="118" height="172" rx="8" fill="#16181d" stroke="#2a2d34"/>
    <rect x="22" y="24" width="60" height="7" rx="3" fill="#e4e4e7"/>
    ${[["#f87171", 92], ["#fb923c", 80], ["#fbbf24", 70], ["#38bdf8", 58], ["#38bdf8", 50]].map(([c, w], i) => `<rect x="22" y="${44 + i * 27}" width="3" height="18" rx="1.5" fill="${c}"/><rect x="30" y="${46 + i * 27}" width="${w}" height="5" rx="2.5" fill="#a1a1aa"/><rect x="30" y="${55 + i * 27}" width="${w - 22}" height="4" rx="2" fill="#52525b"/>`).join("")}
    <rect x="262" y="14" width="46" height="14" rx="7" fill="none" stroke="#34d399"/><circle cx="271" cy="21" r="2.5" fill="#34d399"/><rect x="277" y="19" width="24" height="4" rx="2" fill="#34d399"/>
  </svg>`,
  scorecard: `<svg viewBox="0 0 320 200" role="img" aria-label="기준 채점 도식: 적중·막지 않음·기록 없음·누락 칸과 권고-통제 시간축">
    <rect width="320" height="200" fill="#0d1117"/>
    ${[["#34d399", "적중"], ["#a1a1aa", "막지 않음"], ["#fbbf24", "기록 없음"], ["#f87171", "누락"]].map(([c, t], i) => `<rect x="${14 + i * 74}" y="16" width="66" height="44" rx="7" fill="#16181d" stroke="#2a2d34"/><text x="${22 + i * 74}" y="32" font-size="9" font-weight="700" fill="${c}">${t}</text><rect x="${22 + i * 74}" y="40" width="${18 + (3 - i) * 4}" height="10" rx="2" fill="#e4e4e7"/>`).join("")}
    <rect x="14" y="74" width="292" height="112" rx="8" fill="#16181d" stroke="#2a2d34"/>
    <line x1="28" x2="292" y1="150" y2="150" stroke="#3f3f46"/>
    <rect x="70" y="108" width="120" height="30" rx="4" fill="rgba(52,211,153,.18)" stroke="#34d399"/>
    <text x="76" y="102" font-size="9" fill="#34d399" font-weight="700">권고 구간</text>
    <line x1="160" x2="160" y1="96" y2="150" stroke="#f87171" stroke-width="2"/><text x="164" y="94" font-size="9" fill="#f87171" font-weight="700">통제 기록</text>
    <path d="M28 146 C70 144 90 130 120 118 C150 104 170 100 200 112 C230 124 260 140 292 144" fill="none" stroke="#38bdf8" stroke-width="2"/>
    <text x="28" y="172" font-size="9" fill="#71717a">5/15</text><text x="270" y="172" font-size="9" fill="#71717a">10/15</text>
  </svg>`,
  facility: `<svg viewBox="0 0 320 200" role="img" aria-label="시설 기준 도식: 등록 관문 4단계와 기준 후보 비교표">
    <rect width="320" height="200" fill="#0d1117"/>
    ${["유입 경로", "대표 관측소", "현장 계측", "검증 사건"].map((t, i) => `<rect x="${12 + i * 76}" y="18" width="66" height="40" rx="7" fill="#16181d" stroke="${i < 2 ? "#34d399" : "#2a2d34"}"/><circle cx="${24 + i * 76}" cy="30" r="6" fill="${i < 2 ? "#34d399" : "#3f3f46"}"/><text x="${21.5 + i * 76}" y="33" font-size="8" font-weight="800" fill="#09090b">${i + 1}</text><text x="${18 + i * 76}" y="50" font-size="9" fill="#d4d4d8" font-weight="700">${t}</text>${i < 3 ? `<path d="M${80 + i * 76} 38 l6 0" stroke="#52525b" stroke-width="1.5"/>` : ""}`).join("")}
    <rect x="12" y="72" width="296" height="114" rx="8" fill="#16181d" stroke="#2a2d34"/>
    ${[0, 1, 2, 3, 4].map((i) => `<rect x="24" y="${86 + i * 19}" width="${70 + (i % 2) * 14}" height="6" rx="3" fill="#a1a1aa"/><rect x="128" y="${86 + i * 19}" width="80" height="6" rx="3" fill="#52525b"/><rect x="226" y="${85 + i * 19}" width="${10 + i * 12}" height="8" rx="2" fill="#fb923c" opacity=".8"/>${i === 2 ? `<rect x="18" y="${80 + i * 19}" width="284" height="18" rx="4" fill="none" stroke="#34d399"/>` : ""}`).join("")}
  </svg>`,
  cases: `<svg viewBox="0 0 320 200" role="img" aria-label="사례 재구성 도식: 사건 단계 시간축과 침수 추정 범위 지도">
    <rect width="320" height="200" fill="#0d1117"/>
    <rect x="12" y="14" width="132" height="172" rx="8" fill="#16181d" stroke="#2a2d34"/>
    <line x1="30" x2="30" y1="30" y2="172" stroke="#3f3f46" stroke-width="2"/>
    ${["#fbbf24", "#fb923c", "#f87171", "#f87171", "#f87171"].map((c, i) => `<circle cx="30" cy="${36 + i * 32}" r="5" fill="${c}"/><rect x="42" y="${32 + i * 32}" width="${74 - i * 6}" height="5" rx="2.5" fill="#d4d4d8"/><rect x="42" y="${41 + i * 32}" width="40" height="4" rx="2" fill="#52525b"/>`).join("")}
    <rect x="154" y="14" width="154" height="172" rx="8" fill="#141a22" stroke="#2a2d34"/>
    <path d="M150 60 C190 50 210 90 240 80 C270 70 290 40 320 30" fill="none" stroke="#1f6fa3" stroke-width="10" opacity=".7"/>
    <path d="M196 96 C220 84 250 92 262 110 C276 130 254 150 228 146 C204 142 186 120 196 96Z" fill="rgba(248,113,113,.35)" stroke="#f87171"/>
    <rect x="232" y="118" width="22" height="6" rx="1" fill="#fbbf24"/>
    <rect x="164" y="166" width="134" height="10" rx="5" fill="#27272a"/><rect x="164" y="166" width="78" height="10" rx="5" fill="#34d399"/>
  </svg>`,
};

function kpi({ label, value, unit, color, chart, caption }) {
  return `<div class="op-kpi" style="--c:${color}">
    <span class="op-kpi-label"><i></i>${label}</span>
    <strong>${value}<small>${unit}</small></strong>
    ${chart}
    <span class="op-kpi-cap">${caption}</span>
  </div>`;
}

export async function renderHome(view) {
  const [risk, history, registry] = await Promise.all([
    cached("/api/watch/facility-risk?limit=10000").catch(() => null),
    cached("/api/watch/flood-forecast-history").catch(() => null),
    cached("/api/twin/registry").catch(() => null),
  ]);
  const facilities = risk?.facilities ?? [];
  const count = (pred) => facilities.filter(pred).length;
  const underpass = count((f) => f.group === "underpass"), riverside = count((f) => f.group === "riverside");
  const river = count((f) => f.driver === "river"), pluvial = count((f) => f.driver === "pluvial");
  const fromAws = count((f) => f.rain?.source === "KMA AWS"), fromHrfco = count((f) => f.rain?.source === "HRFCO"), noRain = facilities.length - fromAws - fromHrfco;
  const aws = (risk?.rain_gauges ?? []).filter((g) => String(g.code).startsWith("kma:")).length;
  const byLevel = risk?.counts?.by_level ?? {};
  const watchLevels = ["주의", "경계", "심각"].map((label) => ({ label, n: byLevel[label] ?? 0 }));
  const watching = watchLevels.reduce((sum, p) => sum + p.n, 0);
  const lastYear = history ? Object.keys(history.issuances.by_year).slice(-1)[0] : null;

  const kpis = [
    kpi({ label: "감시 시설", value: num(facilities.length || null), unit: "곳", color: "#e4e4e7",
      chart: facilities.length ? unitDots([{ label: "지하차도", n: underpass }, { label: "하천변 출입구", n: riverside }], "#e4e4e7") : "",
      caption: `점 하나가 시설 하나 · 지하차도 ${underpass} · 하천변 ${riverside}` }),
    kpi({ label: "하천형 · 내수형", value: `${river} · ${pluvial}`, unit: "곳", color: "#38bdf8",
      chart: splitBar([{ label: "하천형", n: river }, { label: "내수형", n: pluvial }], "#38bdf8"),
      caption: "하천형은 수위·홍수특보, 내수형은 강우·호우특보로 판단" }),
    kpi({ label: "기상청 AWS 강우", value: num(aws || null), unit: "곳", color: "#0ea5e9",
      chart: splitBar([{ label: "AWS", n: fromAws }, { label: "홍수통제소", n: fromHrfco }, { label: "없음", n: noRain }], "#0ea5e9"),
      caption: aws ? `시설별 강우 출처 · AWS ${fromAws} · 홍수통제소 ${fromHrfco} · 없음 ${noRain}` : `지금 기상청 AWS 응답 없음 · 홍수통제소 강우로 대신 ${fromHrfco}곳` }),
    kpi({ label: "공식 홍수특보 이력", value: num(history?.issuances?.issuances), unit: "건", color: "#fb923c",
      chart: history ? yearBars(history.issuances.by_year, "#fb923c") : "",
      caption: history ? `${history.issuances.years} 연도별 발령 · 진한 막대 ${lastYear}` : "이력을 불러오지 못함" }),
    kpi({ label: risk?.mode === "replay" ? "주의 이상 시설(재생)" : "지금 주의 이상 시설", value: num(risk ? watching : null), unit: "곳", color: "#fbbf24",
      chart: watching ? splitBar(watchLevels, "#fbbf24") : "",
      caption: risk ? `${String(risk.observed_at ?? risk.at ?? "").slice(5, 16).replace("T", " ")} 관측 · ${watchLevels.map((p) => `${p.label} ${p.n}`).join(" · ")}` : "불러오지 못함" }),
  ].join("");

  const total = registry?.counts;
  const doors = [
    { id: "watch", season: "장마 중", title: "관제 보드", q: "지금 어디를 먼저 볼까",
      points: [`시설 ${num(facilities.length || null)}곳 원인별 위험 순위(10분)`, "공식 홍수특보·호우특보를 단계 하한으로", "보드 운영 에이전트"] },
    { id: "scorecard", season: "장마 후", title: "기준 채점", q: "이번 장마, 기준이 실제 통제보다 빨랐나",
      points: ["담당자 통제 기록과 권고를 시즌 단위로 맞춤", "기준 후보를 같은 기록으로 비교", `공식 특보 이력 ${num(history?.issuances?.issuances)}건`] },
    { id: "facility", season: "장마 전", title: "시설 기준", q: "이 시설은 어떤 신호로, 몇 분 전에 막나",
      points: ["운영 등록 관문 4개", "기준 후보별 권고 횟수 비교", "지금 상태 · 담당자 확인 기록"],
      foot: `<div class="op-mini-row"><b>운영 ${total ? total.operational : "—"} · 후보 ${total ? total.candidate : "—"}</b><span>등록</span><span></span></div>` },
    { id: "cases", season: "근거", title: "사례 재구성", q: "왜 필요한가",
      points: ["과거 사건 재구성과 규칙 재생은 이 화면에서만"],
      foot: [["오송 HAND 시뮬레이션", "2023 · 붕괴 시각까지 단계별 범위", "osong-2023"], ["서울 도림천", "2022 · 내수 침수", "seoul-2022"], ["포항 냉천", "2022 · 지하주차장", "pohang-2022"], ["안동·의성", "2026 · 대피명령", "andong-uiseong-2026"]]
        .map(([t, s, id]) => `<a class="op-mini-link" href="#/cases/${id}"><b>${t}</b><span>${arrow}</span><small>${s}</small></a>`).join("") },
  ].map((d) => `<article class="op-door">
      <a class="op-door-shot" href="#/${d.id}" tabindex="-1" aria-hidden="true">
        ${SKETCH[d.id]}
        <span>화면 열기 ${arrow}</span>
      </a>
      <a class="op-door-head" href="#/${d.id}"><span class="op-chip">${d.season}</span><b>${d.title}${arrow}</b><em>${d.q}</em></a>
      ${d.points.length ? `<ul>${d.points.map((p) => `<li>${p}</li>`).join("")}</ul>` : ""}
      ${d.foot ? `<div class="op-door-foot">${d.foot}</div>` : ""}
    </article>`).join("");

  view.innerHTML = `<div class="op-page">
    <section class="op-hero">
      <div>
        <p class="op-eyebrow">만약에 침수 · 하천 접점 시설 통제 판단 트윈</p>
        <h1>하천 시설의 통제 기준을 세우고,<br>장마 중에 쓰고, 장마 뒤에 채점합니다.</h1>
        <p class="op-lead">지하차도·하천변 출입구를 홍수통제소 수위·공식 홍수특보와 기상청 강우·호우특보로 10분마다 단계화합니다. 같은 데이터로 장마 전에는 시설별 통제 기준을, 장마 중에는 먼저 볼 시설을, 장마 뒤에는 그 기준의 성적표를 냅니다.</p>
      </div>
      ${CYCLE}
    </section>
    <section class="op-kpis" aria-label="주요 수치">${kpis}</section>
    <section class="op-doors" aria-label="네 화면">${doors}</section>
    <p class="op-note">순위·권고는 공개 관측과 공식 특보로 본 선행 지표이며, 통제 결정은 담당자 판단과 현장 기준이 우선합니다. 과거 사건의 통제 시각·침수 범위는 사례 재구성에서 출처와 확인 수준을 함께 표시합니다.</p>
  </div>`;
}
