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
    cached("/api/watch/facility-risk?limit=2000").catch(() => null),
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
        <img src="previews/${d.id}.jpg" alt="" loading="lazy" width="720" height="450">
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
