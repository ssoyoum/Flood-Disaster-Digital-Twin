import { API, esc, get } from "./lib.js";

// 화면마다 붙는 에이전트 패널. 관제 보드 서랍(watch-board-integration.html)과 같은 문법으로
// POST /api/agent/ask 에 화면이 정한 범위(event_id · board · facility_id)만 실어 보낸다.
// 수치는 서버 도구가 계산하고, 답의 [n]은 그 도구 호출 번호다.
//
// mountAgent(host, {
//   key,          대화를 기억할 이름(탭을 오가도 같은 범위면 이어진다)
//   title, badge, intro,
//   scope,        요청에 그대로 싣는 범위 { event_id, board?, facility_id? }
//   examples,     추천 질문을 받을 경로(/api/agent/examples?...). 실패하면 fallback
//   workflows,    추천 질문 가운데 이 화면에 맞는 workflow만(순서대로). 없으면 전부
//   fallback,     [{ label, question }]
//   placeholder,
//   gated,        { html } 이면 질문을 받지 않고 이유만 보여 준다(도구가 없는 범위)
//   open,         처음부터 펼칠지
// })

const conversations = new Map();
const STATE_KO = { NEEDS_DATA: "분석 근거 부족", UNAVAILABLE: "응답 실패 · 다시 시도할 수 있습니다" };
const ICON = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12Z"/><path d="M8.5 11h.01M12 11h.01M15.5 11h.01"/></svg>';

const withCites = (text) => esc(text).replace(/\[(\d+)\]/g, '<span class="op-ag-cite">[$1]</span>');

function conversation(key) {
  if (!conversations.has(key)) conversations.set(key, { turns: [], open: false, draft: "" });
  return conversations.get(key);
}

async function loadExamples(cfg) {
  let raw = [];
  if (cfg.examples) {
    try { raw = await get(cfg.examples); } catch { raw = []; }
  }
  let items = raw;
  if (cfg.workflows) {
    const order = cfg.workflows;
    items = raw.filter((i) => order.includes(i.workflow)).sort((a, b) => order.indexOf(a.workflow) - order.indexOf(b.workflow));
  }
  if (!items.length) items = cfg.fallback ?? [];
  // 서버 추천 가운데 이 화면에서 고르지 않은 질문(관제 보드의 지역 이동 등)
  const kept = new Set(items.map((i) => i.question));
  return { items, offTopic: new Set(raw.map((i) => i.question).filter((q) => !kept.has(q))) };
}

function errorText(status, body) {
  let detail = body;
  try { detail = JSON.parse(body).detail ?? body; } catch { /* 본문이 JSON이 아님 */ }
  if (status === 429) return typeof detail === "string" ? detail : "질문이 잠시 많습니다. 조금 뒤에 다시 물어보세요.";
  if (status === 422) return "질문 형식이 API 조건과 맞지 않습니다.";
  if (status === 404) return "이 범위의 에이전트 도구를 서버가 찾지 못했습니다.";
  return `Agent API 오류 (${status}).`;
}

export function mountAgent(host, cfg) {
  const conv = conversation(cfg.key);
  if (cfg.open) conv.open = true;
  host.querySelector(".op-ag-fab")?.remove();
  host.querySelector(".op-ag")?.remove();

  const fab = document.createElement("button");
  fab.type = "button";
  fab.className = "op-ag-fab";
  fab.innerHTML = `${ICON}<span>에이전트에게 묻기</span>`;
  const panel = document.createElement("aside");
  panel.className = "op-ag";
  panel.setAttribute("aria-label", cfg.title);
  panel.innerHTML = `<header class="op-ag-head">
      <span class="op-ag-av">AI</span>
      <div><h2>${esc(cfg.title)}</h2>${cfg.badge ? `<span class="op-chip" data-tone="ok">${esc(cfg.badge)}</span>` : ""}</div>
      <button type="button" class="op-ag-close" aria-label="닫기" title="닫기">×</button>
    </header>
    <div class="op-ag-body">
      <p class="op-ag-intro">${cfg.intro}</p>
      ${cfg.gated ? `<div class="op-ag-gated">${cfg.gated.html}</div>` : '<div class="op-ag-sugs" aria-label="추천 질문"><p class="op-wait">추천 질문을 불러오는 중</p></div>'}
      <div class="op-ag-thread" aria-live="polite"></div>
    </div>
    ${cfg.gated ? "" : `<footer class="op-ag-foot">
      <p class="op-ag-error" hidden></p>
      <form class="op-ag-ask"><input type="text" maxlength="1000" placeholder="${esc(cfg.placeholder ?? "질문을 입력하세요")}" aria-label="질문"><button type="submit">질문</button></form>
      <small class="op-ag-status"></small>
    </footer>`}`;
  host.append(fab, panel);

  const $ = (sel) => panel.querySelector(sel);
  const thread = $(".op-ag-thread");
  const input = $(".op-ag-ask input");
  let busy = false, examples = { items: [], offTopic: new Set() };

  const setOpen = (open) => {
    conv.open = open;
    panel.classList.toggle("on", open);
    fab.hidden = open;
    host.classList.toggle("op-ag-push", open);
    if (open) input?.focus({ preventScroll: true });
  };

  // 관제 보드용 후속 질문(지역 이동 등)은 이 화면에서 쓸 수 없으니, 화면에 맞는 추천으로 바꾼다.
  const followUps = (response) => {
    const asked = new Set(conv.turns.map((t) => t.question));
    let items = (response.follow_ups ?? []).filter((f) => !examples.offTopic.has(f) && !asked.has(f));
    if (!items.length) items = examples.items.map((i) => i.question).filter((q) => !asked.has(q));
    return items.slice(0, 3);
  };

  const renderSugs = () => {
    const box = $(".op-ag-sugs");
    if (!box) return;
    box.hidden = conv.turns.length > 0;
    box.innerHTML = examples.items.length
      ? examples.items.map((i) => `<button type="button" data-q="${esc(i.question)}"><b>${esc(i.label)}</b><span>${esc(i.question)}</span></button>`).join("")
      : '<p class="op-note">추천 질문을 받지 못했습니다. 아래에 직접 물어보세요.</p>';
    box.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => ask(b.dataset.q)));
  };

  const renderTurns = () => {
    thread.innerHTML = conv.turns.map((t, i) => {
      const r = t.response, latest = i === conv.turns.length - 1;
      const state = r.status === "ANSWERED" ? "" : `<span class="op-ag-state" data-s="${esc(r.status)}">${esc(STATE_KO[r.status] ?? r.status)}</span>`;
      const tools = r.tool_calls?.length ? `<div class="op-ag-tools">${r.tool_calls.map((c) => `<em>[${c.order}] ${esc(c.tool_name)}</em>`).join("")}</div>` : "";
      const evidence = (r.tool_calls ?? []).map((c) => `<details class="op-ag-evi"><summary>[${c.order}] ${esc(c.tool_name)} · 호출 결과 보기</summary>${c.reason ? `<small>선택 이유 · ${esc(c.reason)}</small>` : ""}${Object.keys(c.parameters ?? {}).length ? `<small>입력 · ${esc(JSON.stringify(c.parameters))}</small>` : ""}<pre>${esc(JSON.stringify(c.result, null, 2))}</pre></details>`).join("");
      const limits = (r.limitations ?? []).map((l) => `<span class="op-ag-limit">제한 · ${esc(l)}</span>`).join("");
      const follow = latest && t.follow.length ? `<div class="op-ag-follow">${t.follow.map((f) => `<button type="button" data-q="${esc(f)}">${esc(f)}</button>`).join("")}</div>` : "";
      return `<div class="op-ag-me">${esc(t.question)}</div>
        <div class="op-ag-ai" data-s="${esc(r.status)}"><span class="op-ag-av">AI</span><div class="op-ag-ai-body">${state}<p class="op-ag-answer">${withCites(r.answer)}</p>${tools}${evidence}${limits}${follow}</div></div>`;
    }).join("");
    thread.querySelectorAll(".op-ag-follow button").forEach((b) => b.addEventListener("click", () => ask(b.dataset.q)));
    renderSugs();
    thread.lastElementChild?.scrollIntoView({ block: "nearest" });
  };

  const setBusy = (on) => {
    busy = on;
    panel.querySelectorAll(".op-ag-ask button, .op-ag-ask input, .op-ag-sugs button, .op-ag-follow button").forEach((el) => { el.disabled = on; });
    const status = $(".op-ag-status");
    if (!status) return;
    status.classList.toggle("busy", on);
    status.textContent = on ? "자료를 확인하고 다음 도구를 고르는 중…" : conv.turns.length ? "후속 질문을 이어서 물어보세요. 실제 통제·대피 판단은 담당자가 합니다." : "수치는 서버 도구가 계산하고 AI는 설명만 합니다.";
  };

  async function ask(question) {
    const text = (question ?? "").trim();
    if (!text || busy || cfg.gated) return;
    setOpen(true);
    const error = $(".op-ag-error");
    error.hidden = true;
    setBusy(true);
    // 서버는 이전 대화를 6개까지, 한 마디 1500자까지 받는다.
    const history = conv.turns.flatMap((t) => [{ role: "user", content: t.question }, { role: "assistant", content: t.response.answer.slice(0, 1500) }]).slice(-6);
    try {
      const res = await fetch(`${API}/api/agent/ask`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...cfg.scope, message: text, history }) });
      if (!res.ok) throw Object.assign(new Error("api"), { status: res.status, body: await res.text() });
      const response = await res.json();
      conv.turns.push({ question: text, response, follow: [] });
      conv.turns[conv.turns.length - 1].follow = followUps(response);
      input.value = response.status === "UNAVAILABLE" ? text : "";
      renderTurns();
    } catch (e) {
      input.value = text;
      error.hidden = false;
      error.textContent = e.status ? errorText(e.status, e.body) : `Agent API(${API || "같은 주소"})에 연결하지 못했습니다. 서버 실행 상태를 확인해 주세요.`;
    } finally {
      setBusy(false);
    }
  }

  fab.addEventListener("click", () => setOpen(true));
  $(".op-ag-close").addEventListener("click", () => setOpen(false));
  panel.addEventListener("keydown", (e) => { if (e.key === "Escape") setOpen(false); });
  $(".op-ag-ask")?.addEventListener("submit", (e) => { e.preventDefault(); ask(input.value); });
  input?.addEventListener("input", () => { conv.draft = input.value; });
  if (input) input.value = conv.draft;

  setOpen(conv.open);
  if (!cfg.gated) {
    setBusy(false);
    renderTurns();
    loadExamples(cfg).then((loaded) => { examples = loaded; renderSugs(); });
  }
  return { ask, open: () => setOpen(true) };
}
