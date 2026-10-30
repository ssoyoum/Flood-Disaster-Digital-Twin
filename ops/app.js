import { API, cached, esc } from "./lib.js";
import { renderHome } from "./views/home.js";
import { renderScorecard } from "./views/scorecard.js";
import { renderFacility } from "./views/facility.js";
import { renderCases } from "./views/cases.js";

// 홈 아래 네 화면. 메뉴 이름은 업무 시기로 붙인다.
export const TABS = [
  { id: "watch", label: "관제 보드", season: "장마 중" },
  { id: "scorecard", label: "기준 채점", season: "장마 후" },
  { id: "facility", label: "시설 기준", season: "장마 전" },
  { id: "cases", label: "사례 재구성", season: "근거" },
];
const VIEWS = { home: renderHome, scorecard: renderScorecard, facility: renderFacility, cases: renderCases };

const view = document.getElementById("op-view");
const watch = document.getElementById("op-watch");
const status = document.getElementById("op-status");
let watchSrc = null, watchStatus = null, official = null;

function readRoute() {
  const raw = window.location.hash.replace(/^#\/?/, "");
  const [path, query = ""] = raw.split("?");
  const parts = path.split("/").filter(Boolean);
  return { view: parts[0] || "home", parts: parts.slice(1), query: new URLSearchParams(query) };
}

function renderTabs(active) {
  document.getElementById("op-tabs").innerHTML = TABS.map((t) =>
    `<a href="#/${t.id}"${active === t.id ? ' aria-current="page"' : ""}>${t.label}<small>${t.season}</small></a>`).join("");
}

function renderStatus(active) {
  const pills = [];
  if (active === "watch" && watchStatus?.mode === "simulation") {
    pills.push(`<span class="op-pill hot"><i></i>가상 강우 테스트 · ${esc(watchStatus.simulation?.label ?? "")} · 실제 관측 아님</span>`);
  } else if (active === "watch" && watchStatus) {
    const replay = watchStatus.mode === "replay";
    pills.push(`<span class="op-pill${replay ? " replay" : ""}"><i></i>${replay ? "수위 재생" : "수위 실시간"} · ${esc(watchStatus.stations)}곳</span>`);
    const rain = watchStatus.rain;
    const rainClass = !rain?.available ? " off" : rain.mode === "replay" ? " replay" : "";
    pills.push(`<span class="op-pill${rainClass}"><i></i>${!rain?.available ? "강우 자료 없음" : rain.mode === "replay" ? "강우 재생" : "강우 실시간"}${rain?.observed_at ? ` · ${esc(rain.observed_at.slice(5, 16).replace("T", " "))}` : ""}</span>`);
  }
  if (official) {
    const total = official.warning + official.advisory;
    pills.push(`<span class="op-pill${total ? " hot" : ""}" title="홍수통제소 홍수예보 발령(최근 72시간 유효분)"><i></i>지금 공식 홍수특보 ${total}곳 · 경보 ${official.warning}</span>`);
  } else {
    pills.push('<span class="op-pill"><i></i>공식 홍수특보 확인 중</span>');
  }
  status.innerHTML = pills.join("");
}

// 관제 보드는 지도를 다시 띄우지 않도록 한 번 만든 iframe을 숨겼다 보였다 한다.
function showWatch(query) {
  const params = new URLSearchParams({ api: API, shell: "ops", twin_href: `${window.location.pathname}#/facility/now` });
  ["facility", "region", "stage"].forEach((key) => { if (query.get(key)) params.set(key, query.get(key)); });
  const src = `../public/watch-board-integration.html?${params}`;
  if (src !== watchSrc) {
    watchSrc = src;
    watch.innerHTML = `<iframe title="FloodOps 관제 보드" src="${esc(src)}"></iframe>`;
  }
  watch.hidden = false;
  view.hidden = true;
}

async function route() {
  const r = readRoute();
  const active = TABS.some((t) => t.id === r.view) ? r.view : "home";
  renderTabs(active);
  renderStatus(active);
  if (active === "watch") { showWatch(r.query); document.title = "관제 보드 · FloodOps"; return; }
  watch.hidden = true;
  view.hidden = false;
  view.scrollTop = 0;
  const render = VIEWS[active] ?? renderHome;
  document.title = `${active === "home" ? "FloodOps 운영" : `${TABS.find((t) => t.id === active).label} · FloodOps`}`;
  view.innerHTML = '<div class="op-page"><p class="op-wait">불러오는 중</p></div>';
  try {
    await render(view, r);
  } catch (error) {
    view.innerHTML = `<div class="op-page"><p class="op-err">화면을 그리지 못했습니다: ${esc(error.message)} · API ${esc(API)} 연결을 확인하세요.</p></div>`;
  }
}

window.addEventListener("message", (event) => {
  if (event.origin !== window.location.origin || event.data?.type !== "floodops-watch-status") return;
  watchStatus = event.data;
  if (readRoute().view === "watch") renderStatus("watch");
});
window.addEventListener("hashchange", route);

cached("/api/watch/flood-forecasts").then((data) => { if (!data.error) { official = data.counts; renderStatus(readRoute().view); } }).catch(() => undefined);
route();
