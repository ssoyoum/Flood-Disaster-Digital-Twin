// 화면들이 같이 쓰는 API 호출·문자열·작은 그림.

export const API = new URLSearchParams(window.location.search).get("api") ?? "http://127.0.0.1:8091";

export async function get(path) {
  const response = await fetch(API + path);
  if (!response.ok) throw new Error(`${response.status} ${path}`);
  return response.json();
}

// 탭을 오갈 때 같은 요청을 다시 보내지 않는다. 실패한 요청은 기억하지 않는다.
const memo = new Map();
export function cached(path) {
  if (!memo.has(path)) memo.set(path, get(path).catch((error) => { memo.delete(path); throw error; }));
  return memo.get(path);
}

export const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
export const hhmm = (iso) => (iso ? String(iso).slice(11, 16) : "—");
export const ymd = (iso) => (iso ? String(iso).slice(0, 10).replaceAll("-", ".") : "");
export const num = (value) => (value == null ? "—" : Number(value).toLocaleString("ko-KR"));
export const minutes = (value) => (value == null ? "—" : `${value >= 0 ? "+" : "−"}${Math.abs(value)}분`);
export const arrow = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>';

export const STAGE_COLOR = { normal: "#38bdf8", attention: "#60a5fa", advisory: "#fbbf24", warning: "#fb923c", severe: "#f87171", planned_flood: "#f87171", unrated: "#52525b" };
export const STAGE_KO = { normal: "정상", attention: "관심", advisory: "주의보", warning: "경보", severe: "심각", planned_flood: "계획홍수위", unrated: "기준 없음" };
export const LEVEL_KO = { attention: "관심 수위", advisory: "주의보 수위", warning: "경보 수위", planned_flood: "계획홍수위" };

export const REFERENCE_KO = {
  official_requirement_met: "공식 통제 요건 충족",
  levee_failure: "임시제방 붕괴",
  underpass_inflow: "지하차도 유입",
  full_inundation: "완전 침수",
};

// 이 신호가 무엇을 위한 신호인지. 주의 단계는 대비 시작이지 통제 시점이 아니다.
export function tierOf(signal) {
  if (/주의보|주의 이상/.test(signal)) return "대비 시작";
  if (/경보|경계 이상/.test(signal)) return "통제 준비";
  return "기타";
}

export function leadBar(lead, span = 300) {
  if (lead == null) return '<span class="op-bar"></span>';
  const width = Math.min(50, (Math.abs(lead) / span) * 50);
  return lead >= 0
    ? `<span class="op-bar" aria-hidden="true"><i class="e" style="left:${50 - width}%;width:${width}%"></i></span>`
    : `<span class="op-bar" aria-hidden="true"><i class="l" style="left:50%;width:${width}%"></i></span>`;
}

// ---- 홈 주요 수치 아래 작은 그림 -------------------------------------------------------------
// 단위 그림: 시설 하나가 점 하나. 무리별로 진하기를 달리한다.
export function unitDots(groups, color) {
  const total = groups.reduce((sum, g) => sum + g.n, 0);
  const rows = 5, cols = Math.ceil(total / rows), size = 220 / cols;
  let i = 0, out = "";
  groups.forEach((group, gi) => {
    for (let k = 0; k < group.n; k += 1, i += 1) {
      const x = Math.floor(i / rows) * size, y = (i % rows) * 6.6;
      out += `<rect x="${x.toFixed(2)}" y="${y.toFixed(1)}" width="${Math.max(size - 0.6, 0.8).toFixed(2)}" height="5" fill="${color}" opacity="${gi === 0 ? 1 : 0.38}"/>`;
    }
  });
  return `<svg viewBox="0 0 220 34" preserveAspectRatio="none" role="img" aria-label="${groups.map((g) => `${g.label} ${g.n}`).join(", ")}">${out}</svg>`;
}

// 나눠진 막대: 비율만 보여준다.
export function splitBar(parts, color) {
  const total = parts.reduce((sum, p) => sum + p.n, 0) || 1;
  let x = 0;
  const rects = parts.map((p, i) => {
    const w = (p.n / total) * 220, r = `<rect x="${x.toFixed(1)}" y="8" width="${Math.max(w - 2, 0).toFixed(1)}" height="14" rx="2" fill="${color}" opacity="${[1, 0.45, 0.18][i] ?? 0.18}"/>`
      + (w > 34 ? `<text x="${(x + 6).toFixed(1)}" y="19" font-size="10" font-weight="700" fill="#09090b">${p.n}</text>` : "");
    x += w;
    return r;
  }).join("");
  return `<svg viewBox="0 0 220 34" preserveAspectRatio="none" role="img" aria-label="${parts.map((p) => `${p.label} ${p.n}`).join(", ")}">${rects}</svg>`;
}

// 연도별 막대.
export function yearBars(byYear, color) {
  const entries = Object.entries(byYear);
  const max = Math.max(1, ...entries.map(([, n]) => n));
  const w = 220 / entries.length;
  return `<svg viewBox="0 0 220 34" preserveAspectRatio="none" role="img" aria-label="연도별 발령">${entries.map(([year, n], i) => {
    const h = (n / max) * 26;
    return `<rect x="${(i * w + 1).toFixed(1)}" y="${(28 - h).toFixed(1)}" width="${(w - 3).toFixed(1)}" height="${h.toFixed(1)}" rx="1.5" fill="${color}" opacity="${year === "2023" ? 1 : 0.55}"><title>${year} ${n}건</title></rect>`;
  }).join("")}<line x1="0" x2="220" y1="28.5" y2="28.5" stroke="rgba(255,255,255,.15)"/></svg>`;
}

// 0을 가운데 둔 선행(위)·지연(아래) 막대.
export function divergingTicks(values, color) {
  const span = Math.max(60, ...values.map((v) => Math.abs(v.lead ?? 0)));
  const w = 220 / Math.max(values.length, 1);
  return `<svg viewBox="0 0 220 34" preserveAspectRatio="none" role="img" aria-label="공식 경보 선행·지연">${values.map((v, i) => {
    if (v.lead == null) return "";
    const h = Math.max(2, (Math.abs(v.lead) / span) * 15);
    const y = v.lead >= 0 ? 17 - h : 17;
    return `<rect x="${(i * w + w * 0.25).toFixed(1)}" y="${y.toFixed(1)}" width="${(w * 0.5).toFixed(1)}" height="${h.toFixed(1)}" rx="1.5" fill="${v.lead >= 0 ? color : "#f87171"}"><title>${esc(v.label)} ${minutes(v.lead)}</title></rect>`;
  }).join("")}<line x1="0" x2="220" y1="17" y2="17" stroke="rgba(255,255,255,.2)"/></svg>`;
}

// ---- 수위 곡선 ---------------------------------------------------------------------------
// 규칙이 읽은 10분 수위 위에 기준선을 긋고, 권고 시각과 실제 사건 사이를 칠한다.
export function hydrograph({ points, levels, from, to, review, events }) {
  const W = 1000, H = 300, L = 46, R = 128, T = 14, B = 30;
  const t0 = Date.parse(from), t1 = Date.parse(to);
  const rows = points.filter(([t]) => { const v = Date.parse(t); return v >= t0 && v <= t1; });
  const ys = [...rows.map(([, v]) => v), levels.planned_flood ?? 0];
  const yMax = Math.ceil(Math.max(...ys) + 0.5), yMin = Math.max(0, Math.floor(Math.min(...rows.map(([, v]) => v)) - 0.5));
  const x = (iso) => L + ((Date.parse(iso) - t0) / (t1 - t0)) * (W - L - R);
  const y = (v) => T + (1 - (v - yMin) / (yMax - yMin)) * (H - T - B);
  const path = rows.map(([t, v], i) => `${i ? "L" : "M"}${x(t).toFixed(1)} ${y(v).toFixed(1)}`).join("");
  const area = rows.length ? `${path}L${x(rows[rows.length - 1][0]).toFixed(1)} ${H - B}L${x(rows[0][0]).toFixed(1)} ${H - B}Z` : "";
  let grid = "";
  for (let v = yMin; v <= yMax; v += 1) grid += `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/><text class="axis" x="${L - 8}" y="${y(v) + 4}" text-anchor="end">${v}</text>`;
  // 6시간 눈금을 한국 시각 00·06·12·18시에 맞춘다(시각 문자열은 모두 KST 기준이다).
  for (let t = Math.ceil((t0 + 32400000) / 21600000) * 21600000 - 32400000; t <= t1; t += 21600000) {
    const iso = new Date(t + 9 * 3600000).toISOString();
    grid += `<text class="axis" x="${x(iso.slice(0, 19))}" y="${H - 10}" text-anchor="middle">${iso.slice(5, 10).replace("-", ".")} ${iso.slice(11, 16)}</text>`;
  }
  const levelLines = Object.entries(LEVEL_KO).filter(([k]) => levels[k] != null && levels[k] >= yMin && levels[k] <= yMax).map(([k, label]) => {
    const color = STAGE_COLOR[k];
    return `<line class="lvl" x1="${L}" x2="${W - R}" y1="${y(levels[k])}" y2="${y(levels[k])}" stroke="${color}"/><text class="lvl-label" x="${W - R + 6}" y="${y(levels[k]) + 4}" fill="${color}">${label} ${levels[k]} m</text>`;
  }).join("");
  const gapEnd = events.find((e) => e.primary);
  const gap = review && gapEnd ? `<rect class="gap" x="${x(review.time)}" y="${T}" width="${Math.max(0, x(gapEnd.time) - x(review.time))}" height="${H - T - B}"/>
    <text class="mark-label" x="${(x(review.time) + x(gapEnd.time)) / 2}" y="${T + 16}" text-anchor="middle" fill="#34d399">${gapEnd.lead}분 먼저</text>` : "";
  // 사건 시각이 몇십 분 간격으로 몰려 있어 이름은 그래프 아래 범례로 뺀다.
  const marks = events.map((e) => `<line class="mark" x1="${x(e.time)}" x2="${x(e.time)}" y1="${T + 22}" y2="${H - B}" stroke="${e.color}"/>`).join("");
  const legend = `<div class="op-hydro-legend"><span><i style="background:#34d399"></i>통제 검토 권고 ${hhmm(review?.time)}</span>${events.map((e) => `<span><i style="background:${e.color}"></i>${esc(e.label)} ${hhmm(e.time)}${e.lead != null ? ` · 권고 ${e.lead}분 뒤` : ""}</span>`).join("")}</div>`;
  const reviewDot = review ? `<circle class="dot" cx="${x(review.time)}" cy="${y(review.water_level_m)}" r="6" fill="#34d399"/><text class="mark-label" x="${x(review.time) - 10}" y="${y(review.water_level_m) + 4}" text-anchor="end" fill="#34d399" paint-order="stroke" stroke="#18181b" stroke-width="4">권고 ${hhmm(review.time)} · ${review.water_level_m} m</text>` : "";
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="수위 곡선과 기준선">${grid}<path class="area" d="${area}"/>${gap}${levelLines}<path class="line" d="${path}"/>${marks}${reviewDot}</svg>${legend}`;
}
