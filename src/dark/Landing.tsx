import { useEffect, useRef, useState, type ReactNode } from "react";
import { ArrowLeft, ArrowRight, Gauge, GitCompare, History, ListChecks, Lock, ShieldCheck } from "lucide-react";
import { getFacilityScorecard, getFloodForecastSummary, getTwinRegistry, getValidationCases, type ValidationCase, type ValidationSignal } from "../api";
import { AppNavigation } from "./Navigation";
import type { FloodEvent } from "../types";
import "./landing.css";

type CaseText = { name: string; place: string; flow: string };

// The catalog API returns English labels; the landing shows Korean ones.
const CASE_TEXT: Record<string, CaseText> = {
  "osong-2023": { name: "2023 오송 궁평2지하차도 침수", place: "충북 청주시 흥덕구 오송읍", flow: "미호천 제방 붕괴 → 월류 → 지하차도 침수 → 차량·통행자" },
  "seoul-2022": { name: "2022 서울 도림천 유역 침수", place: "서울 관악·동작·영등포 (도림천 유역)", flow: "집중호우 → 설계강우 초과 → 저지대 침수 → 구조 신고 → 경보 · 빗물터널" },
  "pohang-2022": { name: "2022 포항 태풍 힌남노 침수", place: "경북 포항 냉천 하류·인덕동", flow: "태풍 → 냉천 범람 → 지하주차장 유입 → 완전 침수 · 진입 금지 시각 비교" },
  "iksan-2024": { name: "2024 익산 극한호우 침수", place: "전북 익산 산북천 유역(낭산·망성)", flow: "극한호우 → 배수·소하천 용량 초과 → 농가·농경지·도로" },
  "andong-uiseong-2026": { name: "2026 안동·의성 복합재난", place: "안동 일직면 귀미리 · 의성 단촌면 구계리", flow: "산불 이재민 임시주택 → 집중호우 → 미천 홍수경보 → 대피명령 시각 비교" },
};

const READY_EVENTS = new Set(["osong-2023", "seoul-2022", "pohang-2022", "andong-uiseong-2026"]);

export function caseText(event: FloodEvent): CaseText {
  return CASE_TEXT[event.id] ?? { name: event.name, place: event.location, flow: event.analysis_flow };
}

export function FloodOpsLogo({ size = 44 }: { size?: number }) {
  return (
    <svg className="fo-logo" width={size} height={size} viewBox="0 0 48 48" aria-hidden="true">
      <rect x="1.5" y="1.5" width="45" height="45" rx="11" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M24 9c-6 8-10 13.5-10 18.5a10 10 0 0 0 20 0C34 22.5 30 17 24 9Z" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinejoin="round" />
      <path d="M17.5 29c2.2 1.6 4.3 1.6 6.5 0s4.3-1.6 6.5 0" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      <circle cx="24" cy="22" r="1.9" fill="currentColor" />
    </svg>
  );
}

function Brand() {
  return (
    <div className="fo-brand">
      <FloodOpsLogo />
      <div>
        <strong>FloodOps</strong>
        <span>홍수 대응 의사결정 디지털 트윈</span>
      </div>
    </div>
  );
}

// 장마 전 → 중 → 후가 한 바퀴로 이어지고, 채점 결과가 다음 해 기준으로 돌아간다.
function SeasonCycle() {
  const nodes = [
    { x: 30, y: 196, season: "장마 전", title: "시설 기준", sub: "어떤 신호로 몇 분 전에", href: "#twin" },
    { x: 150, y: 24, season: "장마 중", title: "관제 보드", sub: "지금 어디를 먼저", href: "#watch" },
    { x: 270, y: 196, season: "장마 후", title: "기준 채점", sub: "실제 통제보다 빨랐나", href: "#scorecard" },
  ];
  return (
    <figure className="fo-cycle" aria-label="장마 전·중·후 업무 순환">
      <svg viewBox="0 0 460 330" role="img">
        <defs>
          <marker id="fo-cycle-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0 0 L10 5 L0 10 z" fill="#71717a" />
          </marker>
        </defs>
        <path d="M110 192 L178 112" className="fo-cycle-edge" markerEnd="url(#fo-cycle-arrow)" />
        <path d="M282 112 L350 192" className="fo-cycle-edge" markerEnd="url(#fo-cycle-arrow)" />
        <path d="M268 262 C 240 300, 220 300, 192 262" className="fo-cycle-edge back" markerEnd="url(#fo-cycle-arrow)" />
        <text x="230" y="316" textAnchor="middle" className="fo-cycle-back">다음 해 기준 수정</text>
        {nodes.map((node) => (
          <a key={node.title} href={node.href}>
            <g className="fo-cycle-node" transform={`translate(${node.x} ${node.y})`}>
              <rect width="160" height="84" rx="12" />
              <text x="16" y="26" className="fo-cycle-season">{node.season}</text>
              <text x="16" y="52" className="fo-cycle-title">{node.title}</text>
              <text x="16" y="72" className="fo-cycle-sub">{node.sub}</text>
            </g>
          </a>
        ))}
      </svg>
      <figcaption><a href="#cases">사례 재구성</a>은 세 시기를 뒷받침하는 근거 자료입니다.</figcaption>
    </figure>
  );
}

const FLOW_KPIS: Array<{ label: string; value: string; unit: string }> = [
  { label: "감시 시설", value: "536", unit: "곳" },
  { label: "하천형 · 내수형", value: "142 · 394", unit: "곳" },
  { label: "기상청 AWS 강우", value: "736", unit: "곳" },
  { label: "공식 홍수특보 이력", value: "1,151", unit: "건" },
  { label: "과거 홍수 채점", value: "4", unit: "건" },
];

function leadBadge(signal?: ValidationSignal) {
  if (!signal || signal.lead_min === null) return <span className="fo-lead-badge none">—</span>;
  const early = signal.lead_min >= 0;
  return <span className={`fo-lead-badge ${early ? "early" : "late"}`}>{early ? "+" : "−"}{Math.abs(signal.lead_min)}분{signal.lead_is_lower_bound ? "↑" : ""}</span>;
}

type Door = { id: string; season: string; title: string; question: string; href: string; icon: typeof Gauge; points: string[] };

// 네 화면. 순서는 메뉴(Navigation.SCREENS)와 같다.
const DOORS: Door[] = [
  { id: "watch", season: "장마 중", title: "관제 보드", question: "지금 어디를 먼저 볼까", href: "#watch", icon: Gauge,
    points: ["시설 536곳 원인별 위험 순위(10분)", "공식 홍수특보·호우특보를 단계 하한으로", "시설 상세에서 «그날과 비교»", "오른쪽 드로어에 보드 운영 에이전트"] },
  { id: "scorecard", season: "장마 후", title: "기준 채점", question: "기준이 실제 통제보다 빨랐나", href: "#scorecard", icon: ListChecks,
    points: ["지금 규칙을 과거 홍수에 10분 간격으로 재생", "시설별 통제 성적표(적중·누락·오경보 후보·근접)", "공식 특보 이력 1,151건의 선행 분"] },
  { id: "twin", season: "장마 전", title: "시설 기준", question: "이 시설은 어떤 신호로, 몇 분 전에 막나", href: "#twin", icon: ShieldCheck,
    points: ["운영 등록 관문 4개(유입 경로·관측소·현장 계측·검증 사건)", "통제 기준 검토와 백테스트", "담당자 확인 기록"] },
  { id: "cases", season: "근거", title: "사례 재구성", question: "왜 필요한가", href: "#cases", icon: History, points: [] },
];

const CASE_LINKS = [
  { title: "오송 HAND 시뮬레이션", sub: "2023 · 붕괴 시각 시나리오", href: "#event/osong-2023" },
  { title: "서울 도림천", sub: "2022 · 내수 침수", href: "#event/seoul-2022" },
  { title: "포항 냉천", sub: "2022 · 진입 금지 시각", href: "#event/pohang-2022" },
  { title: "안동·의성", sub: "2026 · 대피명령 시각", href: "#event/andong-uiseong-2026" },
  { title: "사례 간 비교", sub: "선행 시간을 한 표로", href: "#compare" },
];

export function IntroPage() {
  const [cases, setCases] = useState<ValidationCase[] | null>(null);
  const [official, setOfficial] = useState<{ warning: number; advisory: number } | null>(null);
  const [registry, setRegistry] = useState<{ operational: number; candidate: number } | null>(null);
  const [inflowLead, setInflowLead] = useState<number | null>(null);
  useEffect(() => {
    let live = true;
    getValidationCases().then((data) => { if (live) setCases(data.cases); }).catch(() => { if (live) setCases([]); });
    getFloodForecastSummary().then((data) => { if (live && !data.error) setOfficial(data.counts); }).catch(() => undefined);
    getTwinRegistry().then((data) => {
      if (!live) return;
      setRegistry(data.counts);
      const first = data.operational[0];
      if (first) getFacilityScorecard(first.id).then((card) => { if (live) setInflowLead(card.lead_minutes?.underpass_inflow ?? null); }).catch(() => undefined);
    }).catch(() => undefined);
    return () => { live = false; };
  }, []);
  const total = official ? official.warning + official.advisory : 0;

  const extra: Record<string, ReactNode> = {
    watch: <p className="fo-door-live"><i className={total > 0 ? "hot" : ""} />{official ? `지금 공식 홍수특보 ${total}곳 · 경보 ${official.warning}` : "공식 홍수특보 확인 중"}</p>,
    scorecard: (
      <ul className="fo-val-list">
        {(cases ?? []).map((item) => {
          const officialSignal = item.signals.find((s) => s.signal === "공식 홍수경보" && s.at) ?? item.signals.find((s) => s.signal === "공식 홍수주의보");
          const rule = item.signals.find((s) => s.signal.endsWith("첫 주의 이상"));
          return (
            <li key={item.id}>
              <b>{item.title.replace(/ \d{4}-\d{2}-\d{2}$/, "")}</b>
              <span className="fo-val-cell">특보 {leadBadge(officialSignal)}</span>
              <span className="fo-val-cell">규칙 {leadBadge(rule)}</span>
            </li>
          );
        })}
        {cases === null && <li className="fo-val-wait">채점표를 불러오는 중</li>}
      </ul>
    ),
    twin: (
      <div className="fo-door-figures">
        <span><b>{registry ? registry.operational : "—"}</b>운영</span>
        <span><b>{registry ? registry.candidate : "—"}</b>후보</span>
        <span><b>{inflowLead != null ? `${inflowLead}분` : "—"}</b>궁평2 규칙이 유입보다 먼저</span>
      </div>
    ),
    cases: (
      <ul className="fo-door-links">
        {CASE_LINKS.map((link) => (
          <li key={link.href}><a href={link.href}><strong>{link.title}</strong><span>{link.sub}</span><ArrowRight size={13} /></a></li>
        ))}
      </ul>
    ),
  };

  return (
    <main className="fo-landing fo-intro">
      <header className="fo-topnav">
        <Brand />
        <nav aria-label="FloodOps 화면">
          {DOORS.map((door) => <a key={door.id} href={door.href}>{door.title}<small>{door.season}</small></a>)}
        </nav>
        <span className={`fo-live-pill ${total > 0 ? "hot" : ""}`}>
          <i />{official ? `지금 공식 홍수특보 ${total}곳 · 경보 ${official.warning}` : "공식 홍수특보 확인 중"}
        </span>
      </header>
      <section className="fo-hero">
        <div className="fo-hero-copy">
          <p className="fo-eyebrow">만약에 침수 · 하천 접점 시설 통제 판단 트윈</p>
          <h1>
            하천 시설의 통제 기준을 세우고,
            <br />
            장마 중에 쓰고, 장마 뒤에 채점합니다.
          </h1>
          <p className="fo-lead">
            지하차도·하천변 출입구 536곳을 홍수통제소 수위·공식 홍수특보와 기상청 강우·호우특보로 10분마다 단계화합니다.
            <br />
            같은 데이터로 장마 전에는 시설별 통제 기준을, 장마 중에는 먼저 볼 시설을, 장마 뒤에는 그 기준의 성적표를 냅니다.
          </p>
          <div className="fo-kpis" aria-label="주요 수치">
            {FLOW_KPIS.map((kpi) => (
              <div key={kpi.label} className="fo-kpi">
                <span>{kpi.label}</span>
                <strong>{kpi.value}<small>{kpi.unit}</small></strong>
              </div>
            ))}
          </div>
        </div>
        <SeasonCycle />
      </section>
      <section className="fo-doors" aria-label="네 화면">
        {DOORS.map(({ id, season, title, question, href, icon: Icon, points }) => (
          <article key={id} className={`fo-door fo-door-${id}`}>
            <a className="fo-door-head" href={href}>
              <span className="fo-door-season">{season}</span>
              <span className="fo-door-title"><Icon size={18} /><strong>{title}</strong><ArrowRight size={15} /></span>
              <em>{question}</em>
            </a>
            {points.length > 0 && <ul className="fo-door-points">{points.map((point) => <li key={point}>{point}</li>)}</ul>}
            {extra[id]}
          </article>
        ))}
      </section>
      <p className="fo-footnote">순위·권고는 공개 관측과 공식 특보로 본 선행 지표이며, 통제 결정은 담당자 판단과 현장 기준이 우선합니다. 검증 사례의 통제 시각은 보도 기준(분 단위 기록은 오송뿐)이고, 침수 범위는 관측·지형 기반 근사 재구성이며 공식 침수범위가 아닙니다.</p>
    </main>
  );
}

export function CaseSelectPage({ events, onSelect, onBack, onCompare }: { events: FloodEvent[]; onSelect: (id: string) => void; onBack: () => void; onCompare?: () => void }) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const activeIndex = events.length ? selectedIndex % events.length : 0;
  const move = (step: number) => {
    if (events.length < 2) return;
    setSelectedIndex((index) => (index + step + events.length) % events.length);
  };

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport || events.length < 2) return;
    let waiting = false;
    let timer: number | undefined;
    const onWheel = (event: WheelEvent) => {
      if (!event.deltaY) return;
      event.preventDefault();
      if (waiting) return;
      waiting = true;
      setSelectedIndex((index) => (index + (event.deltaY > 0 ? 1 : -1) + events.length) % events.length);
      timer = window.setTimeout(() => { waiting = false; }, 380);
    };
    viewport.addEventListener("wheel", onWheel, { passive: false });
    return () => {
      viewport.removeEventListener("wheel", onWheel);
      window.clearTimeout(timer);
    };
  }, [events.length]);

  return (
    <main className="fo-landing fo-cases-page">
      <Brand />
      <header className="fo-cases-head">
        <button className="fo-ghost" type="button" onClick={onBack}>
          <ArrowLeft size={16} /> 홈
        </button>
        <div>
          <p className="fo-eyebrow">근거 · 사례 재구성</p>
          <h2>왜 필요한가: 지난 홍수를 시각 단위로 다시 봅니다</h2>
        </div>
        <div className="fo-cases-tools">
          {onCompare && <button className="fo-ghost" type="button" onClick={onCompare}><GitCompare size={16} /> 사례 간 비교</button>}
          <AppNavigation active="cases" />
        </div>
      </header>
      <section className="fo-case-library" aria-label="홍수 사례 목록">
        <div
          ref={viewportRef}
          className="fo-case-viewport"
          role="region"
          aria-roledescription="carousel"
          aria-label="홍수 사례를 휠이나 방향키로 탐색"
          tabIndex={0}
          onKeyDown={(event) => {
            if (event.key === "ArrowRight" || event.key === "ArrowDown") { event.preventDefault(); move(1); }
            if (event.key === "ArrowLeft" || event.key === "ArrowUp") { event.preventDefault(); move(-1); }
          }}
        >
          {events.map((event, index) => {
            const text = caseText(event);
            const ready = READY_EVENTS.has(event.id);
            const forward = (index - activeIndex + events.length) % events.length;
            const offset = forward > Math.floor(events.length / 2) ? forward - events.length : forward;
            const visible = Math.abs(offset) <= 1;
            return (
              <div key={event.id} className={`fo-case-slide ${offset === 0 ? "is-center" : offset === -1 ? "is-before" : offset === 1 ? "is-after" : offset < 0 ? "is-hidden is-hidden-before" : "is-hidden is-hidden-after"}`} aria-hidden={!visible}>
                <button type="button" className={`fo-case ${ready ? "is-ready" : "is-locked"}`} disabled={!ready} tabIndex={visible ? 0 : -1} onClick={() => onSelect(event.id)}>
                  <span className={`fo-case-status ${ready ? "ready" : "locked"}`}>{ready ? "관제 가능" : <><Lock size={12} /> 데이터 연결 예정</>}</span>
                  <strong>{text.name}</strong>
                  <span className="fo-case-place">{text.place}</span>
                  <span className="fo-case-flow">{text.flow}</span>
                  {ready && <span className="fo-case-go">관제 화면 열기 <ArrowRight size={15} /></span>}
                </button>
              </div>
            );
          })}
          {!events.length && <p className="fo-case-empty">표시할 사례가 없습니다.</p>}
        </div>
        <div className="fo-case-controls">
          <button type="button" aria-label="이전 사례" disabled={events.length < 2} onClick={() => move(-1)}><ArrowLeft size={18} /></button>
          <span aria-live="polite">{events.length ? `${String(activeIndex + 1).padStart(2, "0")} / ${String(events.length).padStart(2, "0")}` : "00 / 00"}</span>
          <button type="button" aria-label="다음 사례" disabled={events.length < 2} onClick={() => move(1)}><ArrowRight size={18} /></button>
        </div>
        <p className="fo-case-help">마우스 휠을 내리거나 방향키로 사례를 넘겨 보세요. 마지막 다음에는 첫 사례로 돌아갑니다.</p>
      </section>
    </main>
  );
}
