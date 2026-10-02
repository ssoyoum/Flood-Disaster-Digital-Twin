import { useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Bot, GitCompare, History, Lock } from "lucide-react";
import type { FloodEvent } from "../types";
import "./landing.css";

type CaseText = { name: string; place: string; flow: string };

// The catalog API returns English labels; the landing shows Korean ones.
const CASE_TEXT: Record<string, CaseText> = {
  "osong-2023": { name: "2023 오송 궁평2지하차도 침수", place: "충북 청주시 흥덕구 오송읍", flow: "미호천 제방 붕괴 → 월류 → 지하차도 침수 → 차량·통행자" },
  "seoul-2022": { name: "2022 서울 도시 침수", place: "서울 강남·신림", flow: "집중호우 → 배수 한계 초과 → 저지대 침수 → 반지하·지하공간" },
  "pohang-2022": { name: "2022 포항 태풍 힌남노 침수", place: "경북 포항 냉천 일대", flow: "태풍 → 냉천 범람 → 아파트 지하주차장·산업시설" },
  "iksan-2024": { name: "2024 익산 극한호우 침수", place: "전북 익산 함라면", flow: "극한호우 → 배수·소하천 용량 초과 → 농가·농경지·도로" },
  "andong-uiseong-2026": { name: "2026 안동·의성 복합재난", place: "경북 안동·의성 산불 피해지", flow: "산불 피해지 → 강우 → 임시주거·도로·상수도" },
};

const READY_EVENTS = new Set(["osong-2023"]);

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
          <span className="fo-schematic-tag">시나리오 모식도</span>
          <strong>2023 오송 · 지하차도 통제 비교</strong>
        </div>
        <span className="fo-schematic-meta">근사 재구성 기준</span>
      </header>
      <div className="fo-schematic-map">
        <svg viewBox="0 0 640 300" role="img">
          <rect width="640" height="300" rx="10" fill="#0c1422" />
          {/* roads */}
          <rect x="0" y="150" width="640" height="26" fill="#1a2740" />
          <line x1="0" y1="163" x2="640" y2="163" stroke="#3a4d6e" strokeDasharray="7 7" />
          <rect x="258" y="0" width="24" height="300" fill="#1a2740" />
          <line x1="270" y1="0" x2="270" y2="300" stroke="#3a4d6e" strokeDasharray="7 7" />
          {/* flood envelope */}
          <path className="fo-flood" d="M150 118 C 188 104, 228 118, 252 140 C 300 150, 346 150, 372 176 C 396 206, 360 236, 318 232 C 280 230, 250 214, 222 196 C 190 176, 150 164, 138 144 C 132 132, 138 122, 150 118 Z" />
          {/* Miho River */}
          <path d="M-10 70 C 60 60, 110 110, 150 100 C 200 88, 220 40, 290 -10" fill="none" stroke="#12324d" strokeWidth="30" strokeLinecap="round" />
          <path d="M-10 70 C 60 60, 110 110, 150 100 C 200 88, 220 40, 290 -10" fill="none" stroke="#1f6fa3" strokeWidth="3" strokeDasharray="2 9" className="fo-river-flow" />
          {buildings.map(([x, y, w, h]) => (
            <rect key={`${x}-${y}`} x={x} y={y} width={w} height={h} rx="3" fill="#16213a" stroke="#34466a" />
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
            <dt>원상태</dt>
            <dd className="bad">차량 진입 계속</dd>
            <dt>개입</dt>
            <dd className="ok">통제 시각 조정</dd>
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

export function IntroPage({ onStart }: { onStart: () => void }) {
  const features = [
    { icon: History, title: "사건 재구성", text: "수위·강우 관측과 지형으로 과거 홍수를 시간대별로 다시 재생합니다." },
    { icon: GitCompare, title: "개입 비교", text: "지하차도 통제 시각을 바꿔 원상태와 개입 결과를 나란히 비교합니다." },
    { icon: Bot, title: "에이전트 질의", text: "질문을 분석 계획으로 바꾸고, 담당자 승인 후에만 도구를 실행합니다." },
  ];
  return (
    <main className="fo-landing fo-intro">
      <Brand />
      <section className="fo-hero">
        <div className="fo-hero-copy">
          <p className="fo-eyebrow">홍수 대응 의사결정 디지털 트윈</p>
          <h1>
            그때 먼저 통제했다면
            <br />
            무엇이 달라졌을까
          </h1>
          <p className="fo-lead">
            FloodOps는 실제 홍수 사건을 공공 관측자료로 재구성하고,
            <br />
            통제·대피 같은 대응 조치를 가정했을 때 피해가 어떻게 달라지는지
            <br />
            담당자가 직접 비교해 보는 관제 서비스입니다.
          </p>
          <button className="fo-primary" type="button" onClick={onStart}>
            사례 선택 <ArrowRight size={18} />
          </button>
        </div>
        <ServiceSchematic />
      </section>
      <section className="fo-features">
        {features.map(({ icon: Icon, title, text }, index) => (
          <article key={title} style={{ animationDelay: `${index * -2}s` }}>
            <Icon size={20} />
            <strong>{title}</strong>
            <p>{text}</p>
          </article>
        ))}
      </section>
      <p className="fo-footnote">침수 범위는 관측·지형 기반 근사 재구성이며 공식 침수범위가 아닙니다. 각 화면에 출처와 한계를 함께 표시합니다.</p>
    </main>
  );
}

export function CaseSelectPage({ events, onSelect, onBack }: { events: FloodEvent[]; onSelect: (id: string) => void; onBack: () => void }) {
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
