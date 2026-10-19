import { useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Bot, Gauge, GitCompare, History, ListChecks, Lock, ShieldCheck, Waves } from "lucide-react";
import { getFloodForecastSummary, getValidationCases, type ValidationCase, type ValidationSignal } from "../api";
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

// Schematic of the Osong case: breach on the Miho River, flood spreading to the underpass.
function ServiceSchematic() {
  const buildings = [
    [40, 30, 52, 30], [104, 26, 44, 38], [300, 24, 60, 30], [372, 22, 70, 34], [300, 70, 56, 26], [384, 70, 58, 28],
    [36, 196, 50, 34], [100, 200, 60, 28], [36, 250, 64, 30], [300, 196, 48, 30], [360, 200, 80, 26], [300, 246, 74, 32], [388, 244, 52, 34],
    [180, 196, 46, 30], [180, 248, 54, 30],
    [470, 24, 64, 30], [548, 20, 72, 36], [470, 72, 52, 28], [538, 70, 80, 26],
    [470, 196, 60, 30], [544, 200, 74, 28], [470, 246, 50, 34], [534, 244, 84, 32],
  ];
  return (
    <figure className="fo-schematic" aria-label="오송 지하차도 침수 모식도">
      <header>
        <div>
          <span className="fo-schematic-tag">검증 사례 · 257분의 공백</span>
          <strong>2023 오송 · 궁평2지하차도</strong>
        </div>
        <span className="fo-schematic-meta">근사 재구성 기준</span>
      </header>
      <div className="fo-schematic-map">
        <svg viewBox="0 0 640 300" role="img">
          <rect width="640" height="300" rx="10" fill="#121216" />
          {/* roads */}
          <rect x="0" y="150" width="640" height="26" fill="#1f1f23" />
          <line x1="0" y1="163" x2="640" y2="163" stroke="#52525b" strokeDasharray="7 7" />
          <rect x="258" y="0" width="24" height="300" fill="#1f1f23" />
          <line x1="270" y1="0" x2="270" y2="300" stroke="#52525b" strokeDasharray="7 7" />
          {/* flood envelope */}
          <path className="fo-flood" d="M150 118 C 188 104, 228 118, 252 140 C 300 150, 346 150, 372 176 C 396 206, 360 236, 318 232 C 280 230, 250 214, 222 196 C 190 176, 150 164, 138 144 C 132 132, 138 122, 150 118 Z" />
          {/* Miho River */}
          <path d="M-10 70 C 60 60, 110 110, 150 100 C 200 88, 220 40, 290 -10" fill="none" stroke="#12324d" strokeWidth="30" strokeLinecap="round" />
          <path d="M-10 70 C 60 60, 110 110, 150 100 C 200 88, 220 40, 290 -10" fill="none" stroke="#1f6fa3" strokeWidth="3" strokeDasharray="2 9" className="fo-river-flow" />
          {buildings.map(([x, y, w, h]) => (
            <rect key={`${x}-${y}`} x={x} y={y} width={w} height={h} rx="3" fill="#27272a" stroke="#3f3f46" />
          ))}
          {/* underpass */}
          <rect className="fo-underpass" x="296" y="148" width="64" height="30" rx="3" />
          {/* levee breach */}
          <g className="fo-breach" transform="translate(150 112)">
            <circle r="11" />
            <path d="M-4 -4 L4 4 M4 -4 L-4 4" />
          </g>
        </svg>
        <div className="fo-schematic-pop">
          <span className="fo-schematic-tag">선택 시설</span>
          <strong>궁평2지하차도</strong>
          <dl>
            <dt>공식 홍수경보</dt>
            <dd className="ok">04:10</dd>
            <dt>지하차도 유입</dt>
            <dd className="bad">08:27 · 통제 없음</dd>
          </dl>
        </div>
      </div>
      <footer>
        <span><i className="sw river" />미호천</span>
        <span><i className="sw flood" />침수 추정 범위</span>
        <span><i className="sw underpass" />지하차도</span>
        <span><i className="dot" />제방 붕괴 지점</span>
      </footer>
    </figure>
  );
}

type IntroProps = { onStart: () => void; onTwin?: () => void; onWatch?: () => void; onValidation?: () => void; onOsong?: () => void };

const FLOW_KPIS: Array<{ label: string; value: string; unit: string; tone: string }> = [
  { label: "감시 시설", value: "536", unit: "곳", tone: "#e4e4e7" },
  { label: "하천형 · 내수형", value: "142 · 394", unit: "곳", tone: "#38bdf8" },
  { label: "기상청 AWS 강우", value: "736", unit: "곳", tone: "#0ea5e9" },
  { label: "공식 홍수특보 이력", value: "1,151", unit: "건", tone: "#fb923c" },
  { label: "과거 홍수 채점", value: "4", unit: "건", tone: "#34d399" },
];

function leadBadge(signal?: ValidationSignal) {
  if (!signal || signal.lead_min === null) return <span className="fo-lead-badge none">—</span>;
  const early = signal.lead_min >= 0;
  return <span className={`fo-lead-badge ${early ? "early" : "late"}`}>{early ? "+" : "−"}{Math.abs(signal.lead_min)}분{signal.lead_is_lower_bound ? "↑" : ""}</span>;
}

export function IntroPage({ onStart, onTwin, onWatch, onValidation, onOsong }: IntroProps) {
  const [cases, setCases] = useState<ValidationCase[] | null>(null);
  const [official, setOfficial] = useState<{ warning: number; advisory: number } | null>(null);
  useEffect(() => {
    let live = true;
    getValidationCases().then((data) => { if (live) setCases(data.cases); }).catch(() => { if (live) setCases([]); });
    getFloodForecastSummary().then((data) => { if (live && !data.error) setOfficial(data.counts); }).catch(() => undefined);
    return () => { live = false; };
  }, []);
  const steps = [
    { icon: Gauge, no: "01", title: "넓게 선별", sub: "전국 관제 보드", href: "#watch", text: "지하차도 414곳·하천변 출입구 122곳을 잠기는 원인에 맞는 지표로 10분마다 0~4단계로 순위화합니다. 하천형은 수위 단계와 공식 홍수특보, 내수형은 강우 누적과 호우특보로 봅니다." },
    { icon: ListChecks, no: "02", title: "과거 홍수로 검증", sub: "검증 사례 채점", href: "#watch?tab=vc", text: "지금 규칙을 과거 홍수에 그대로 재생해 실제 통제(오송은 유입)보다 몇 분 먼저였는지 셉니다. 늦은 사례는 규칙을 고치는 근거입니다." },
    { icon: ShieldCheck, no: "03", title: "검증된 시설부터 운영", sub: "운영 시설 통제 판단", href: "#twin", text: "관문 4개를 통과한 시설만 «통제 검토» 규칙과 담당자 확인 기록을 붙입니다. 장마 뒤에는 시설별 통제 성적표로 남깁니다." },
  ];
  const more = [
    { icon: Waves, title: "오송 HAND 시뮬레이션", href: "#event/osong-2023", text: "관측 단계별 재구성 · 통제 시각 반사실" },
    { icon: History, title: "사례 라이브러리", href: "#cases", text: "서울 2022 · 포항 2022 · 안동·의성 2026" },
    { icon: GitCompare, title: "사례 간 비교", href: "#compare", text: "사건별 선행 시간을 한 표로" },
    { icon: Bot, title: "보드 운영 에이전트", href: "#watch", text: "“지금 홍수특보 내려진 곳 있어?”" },
  ];
  const total = official ? official.warning + official.advisory : 0;
  return (
    <main className="fo-landing fo-intro">
      <header className="fo-topnav">
        <Brand />
        <nav aria-label="FloodOps 화면">
          <a href="#watch">관제 보드</a>
          <a href="#watch?tab=vc">과거 홍수 검증</a>
          <a href="#event/osong-2023">오송 HAND 시뮬레이션</a>
          <a href="#twin">운영 시설</a>
          <a href="#cases">사례</a>
        </nav>
        <span className={`fo-live-pill ${total > 0 ? "hot" : ""}`}>
          <i />{official ? `지금 공식 홍수특보 ${total}곳 · 경보 ${official.warning}` : "공식 홍수특보 확인 중"}
        </span>
      </header>
      <section className="fo-hero">
        <div className="fo-hero-copy">
          <p className="fo-eyebrow">만약에 침수 · 하천 접점 시설 통제 판단 트윈</p>
          <h1>
            신호는 있었습니다.
            <br />
            어디를 먼저 막을지가 비어 있었습니다.
          </h1>
          <p className="fo-lead">
            2023 오송, 공식 홍수경보는 지하차도 유입보다 <b>257분</b> 먼저 나왔습니다.
            <br />
            FloodOps는 홍수통제소 수위·공식 홍수특보와 기상청 강우·호우특보를 전국 하천 접점 시설의
            <br />
            위험 단계로 10분마다 바꾸고, 그 기준을 과거 홍수의 실제 통제 시각으로 채점합니다.
          </p>
          <div className="fo-kpis" aria-label="주요 수치">
            {FLOW_KPIS.map((kpi) => (
              <div key={kpi.label} className="fo-kpi" style={{ ["--fo-c" as string]: kpi.tone }}>
                <span>{kpi.label}</span>
                <strong>{kpi.value}<small>{kpi.unit}</small></strong>
              </div>
            ))}
          </div>
          <div className="fo-intro-actions">
            {onWatch && <button className="fo-primary" type="button" onClick={onWatch}>전국 관제 보드 <ArrowRight size={18} /></button>}
            {onValidation && <button className="fo-ghost" type="button" onClick={onValidation}>과거 홍수 검증 <ArrowRight size={16} /></button>}
            {onOsong && <button className="fo-ghost" type="button" onClick={onOsong}>오송 HAND 시뮬레이션 <ArrowRight size={16} /></button>}
            {onTwin && <button className="fo-ghost" type="button" onClick={onTwin}>운영 시설 <ArrowRight size={16} /></button>}
          </div>
        </div>
        <ServiceSchematic />
      </section>
      <section className="fo-steps">
        {steps.map(({ icon: Icon, no, title, sub, href, text }) => (
          <a key={no} className="fo-step" href={href}>
            <header><span className="fo-step-no">{no}</span><Icon size={18} /><strong>{title}</strong><em>{sub} <ArrowRight size={13} /></em></header>
            <p>{text}</p>
            {no === "02" && (
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
            )}
          </a>
        ))}
      </section>
      <section className="fo-more" aria-label="다른 콘텐츠">
        {more.map(({ icon: Icon, title, href, text }) => (
          <a key={title} href={href}><Icon size={16} /><strong>{title}</strong><span>{text}</span></a>
        ))}
        <button type="button" onClick={onStart}><History size={16} /><strong>과거 사건 재생</strong><span>사례를 골라 관제 화면으로</span></button>
      </section>
      <p className="fo-footnote">순위·권고는 공개 관측과 공식 특보로 본 선행 지표이며, 통제 결정은 담당자 판단과 현장 기준이 우선합니다. 검증 사례의 통제 시각은 보도 기준(분 단위 기록은 오송뿐)이고, 침수 범위는 관측·지형 기반 근사 재구성이며 공식 침수범위가 아닙니다.</p>
    </main>
  );
}

export function CaseSelectPage({ events, onSelect, onBack, onCompare, onTwin }: { events: FloodEvent[]; onSelect: (id: string) => void; onBack: () => void; onCompare?: () => void; onTwin?: () => void }) {
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
          <ArrowLeft size={16} /> 소개
        </button>
        <div>
          <p className="fo-eyebrow">CASE LIBRARY</p>
          <h2>분석할 홍수 사례를 선택하세요</h2>
        </div>
        <div className="fo-cases-tools">
          {onTwin && <button className="fo-ghost" type="button" onClick={onTwin}><Gauge size={16} /> 통제 판단 보드</button>}
          {onCompare && <button className="fo-ghost" type="button" onClick={onCompare}><GitCompare size={16} /> 사례 간 비교</button>}
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
