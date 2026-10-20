import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Gauge, GitCompare, History, Scale } from "lucide-react";
import { getTwinFacilities, getValidationCases } from "../api";
import type { FloodEvent, ValidationCase } from "../types";
import { AppNavigation, type FloodOpsRoute } from "./Navigation";
import "./landing.css";
import "./cases.css";

type CaseText = { name: string; place: string; flow: string };

// The catalog API returns English labels; the landing shows Korean ones.
const CASE_TEXT: Record<string, CaseText> = {
  "osong-2023": { name: "2023 오송 궁평2지하차도 침수", place: "충북 청주시 흥덕구 오송읍", flow: "미호천 제방 붕괴 → 월류 → 지하차도 침수 → 차량·통행자" },
  "seoul-2022": { name: "2022 서울 도림천 유역 침수", place: "서울 관악·동작·영등포 (도림천 유역)", flow: "집중호우 → 설계강우 초과 → 저지대 침수 → 구조 신고 → 경보 · 빗물터널" },
  "pohang-2022": { name: "2022 포항 태풍 힌남노 침수", place: "경북 포항 냉천 하류·인덕동", flow: "태풍 → 냉천 범람 → 지하주차장 유입 → 완전 침수 · 진입 금지 시각 비교" },
  "andong-uiseong-2026": { name: "2026 안동·의성 복합재난", place: "안동 일직면 귀미리 · 의성 단촌면 구계리", flow: "산불 이재민 임시주택 → 집중호우 → 미천 홍수경보 → 대피명령 시각 비교" },
};

export const READY_EVENTS = new Set(["osong-2023", "seoul-2022", "pohang-2022", "andong-uiseong-2026"]);

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

function Brand({ active }: { active: FloodOpsRoute }) {
  return (
    <header className="fo-brand fo-app-header">
      <FloodOpsLogo />
      <div>
        <strong>FloodOps</strong>
        <span>홍수 대응 의사결정 디지털 트윈</span>
      </div>
      <AppNavigation active={active} />
    </header>
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
          <span className="fo-schematic-tag">검증 사건 모식도</span>
          <strong>2023 오송 · 궁평2지하차도</strong>
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
        <a className="fo-schematic-link" href="#event/osong-2023">오송 사건 값 보기 <ArrowRight size={13} /></a>
      </footer>
    </figure>
  );
}

export function IntroPage({ onStart, onTwin, onWatch }: { onStart: () => void; onTwin?: () => void; onWatch?: () => void }) {
  const [operational, setOperational] = useState<string[] | null>(null);
  const [facilityLoadError, setFacilityLoadError] = useState(false);
  useEffect(() => {
    let live = true;
    getTwinFacilities().then((items) => { if (live) setOperational(items.map((item) => item.name)); }).catch(() => { if (live) { setOperational([]); setFacilityLoadError(true); } });
    return () => { live = false; };
  }, []);
  const features = [
    { icon: Gauge, title: "전국 감시 보드", href: "#watch", text: "홍수통제소 관측소 1,400여 곳을 각 관측소의 공식 기준 수위로 판정하고, 연결된 시설과 함께 지도에 올립니다. 에이전트에게 \"충북 보여줘\"라고 말하면 이동합니다." },
    { icon: Scale, title: "운영 시설 · 통제 기준 검토", href: "#twin?tab=criteria", text: "검증된 시설은 시설별 규칙으로 통제 검토를 권고하고, 기준을 바꾸면 과거 사건에서 몇 분 먼저 알렸을지와 다른 해 권고 횟수를 함께 봅니다." },
    { icon: History, title: "사건으로 검증", href: "#cases", text: "과거 사건을 관측 단계별로 재생하고 통제·대피 시각을 바꿔 남는 시간을 비교합니다. 규칙과 에이전트의 검증용입니다." },
  ];
  const scope = [
    { title: "지하차도", state: facilityLoadError ? "연결 확인 필요" : operational ? `운영 ${operational.length}` : "시설 확인 중", tone: "live", href: "#twin", detail: facilityLoadError ? "운영 시설 API를 불러오지 못했습니다" : operational?.length ? operational.join("·") : "운영 시설 목록을 불러오는 중" },
    { title: "저지대 마을 대피", state: "사례 검증", tone: "case", href: "#event/andong-uiseong-2026", detail: "2026 안동·의성 대피 시각" },
  ];
  return (
    <main className="fo-landing fo-intro">
      <Brand active="intro" />
      <section className="fo-hero">
        <div className="fo-hero-copy">
          <p className="fo-eyebrow">하천 접점 시설 통제·대피 판단 트윈</p>
          <h1>
            강물이 넘치기 전에,
            <br />
            어디를 언제 막을까
          </h1>
          <p className="fo-lead">
            FloodOps는 하천 수위를 지하차도·하천변 출입구·저지대 마을의 단계와 통제까지 남은 시간으로 바꿔 보여주고,
            <br />
            그 기준이 과거 홍수에서 몇 분 먼저 알렸을지, 평소에는 얼마나 자주 울렸을지
            <br />
            담당자가 직접 검증해 보는 판단 보조 도구입니다.
          </p>
          <ul className="fo-scope" aria-label="적용 시설">
            {scope.map((item) => {
              const body = <><span className={`fo-scope-state ${item.tone}`}>{item.state}</span><strong>{item.title}</strong><small>{item.detail}</small></>;
              return <li key={item.title}>{item.href ? <a href={item.href}>{body}</a> : <div aria-disabled="true">{body}</div>}</li>;
            })}
          </ul>
          <div className="fo-intro-actions">
            {onWatch && (
              <button className="fo-primary" type="button" onClick={onWatch}>
                전국 감시 보드 <ArrowRight size={18} />
              </button>
            )}
            {onTwin && (
              <button className="fo-ghost" type="button" onClick={onTwin}>
                운영 시설 통제 판단 <ArrowRight size={16} />
              </button>
            )}
            <button className="fo-ghost" type="button" onClick={onStart}>
              과거 사건 재생 <ArrowRight size={16} />
            </button>
          </div>
        </div>
        <ServiceSchematic />
      </section>
      <section className="fo-features">
        {features.map(({ icon: Icon, title, text, href }, index) => (
          <a key={title} className="fo-feature" href={href} style={{ animationDelay: `${index * -2}s` }}>
            <Icon size={20} />
            <strong>{title} <ArrowRight size={14} /></strong>
            <p>{text}</p>
          </a>
        ))}
      </section>
      <p className="fo-footnote">권고는 하천 수위로 본 선행 지표이며, 통제 결정은 담당자 판단과 현장 기준(침수심)이 우선합니다. 침수 범위는 관측·지형 기반 근사 재구성이며 공식 침수범위가 아닙니다.</p>
    </main>
  );
}

const MAIN_CASE = "osong-2023";
const leadText = (lead: number | null | undefined, label: string) => (lead == null ? `${label} 울리지 않음` : `${label} ${lead >= 0 ? "+" : "−"}${Math.abs(lead)}분`);

/*
 * 사례 검증: 본편은 기준 채점에 쓰는 지하차도·하천변 통제 사건(오송 재현 + 채점표의 대전 사건),
 * 확장 사례는 원인이 달라 기준 검증에 쓰지 않는 관제 화면만 둔다.
 */
export function CaseSelectPage({ events, onSelect, onBack, onCompare, onTwin }: { events: FloodEvent[]; onSelect: (id: string) => void; onBack: () => void; onCompare?: () => void; onTwin?: () => void }) {
  const [scored, setScored] = useState<ValidationCase[] | null>(null);
  useEffect(() => {
    getValidationCases().then((data) => setScored(data.cases)).catch(() => setScored([]));
  }, []);

  const osong = events.find((event) => event.id === MAIN_CASE);
  const extras = events.filter((event) => event.id !== MAIN_CASE && READY_EVENTS.has(event.id));
  const osongScore = scored?.find((item) => item.id === MAIN_CASE);
  const osongWarning = osongScore?.signals.find((signal) => signal.signal === "공식 홍수경보")?.lead_min;
  const scoredOthers = (scored ?? []).filter((item) => item.id !== MAIN_CASE);

  return (
    <main className="fo-landing fo-cases-page">
      <Brand active="cases" />
      <header className="fo-cases-head">
        <button className="fo-ghost" type="button" onClick={onBack}>
          <ArrowLeft size={16} /> 소개
        </button>
        <div>
          <p className="fo-eyebrow">VALIDATION</p>
          <h2>기준을 검증한 사건</h2>
        </div>
        <div className="fo-cases-tools">
          {onTwin && <button className="fo-ghost" type="button" onClick={onTwin}><Gauge size={16} /> 통제 판단 보드</button>}
          {onCompare && <button className="fo-ghost" type="button" onClick={onCompare}><Scale size={16} /> 효과성 채점표</button>}
        </div>
      </header>
      <section className="fo-case-sets" aria-label="검증 사건">
        <div className="fo-case-set">
          <p className="fo-eyebrow">본편 · 지하차도·하천변 통제 사건 — 기준 채점에 쓰는 사건</p>
          <div className="fo-case-grid">
            {osong && (
              <button type="button" className="fo-case is-ready" onClick={() => onSelect(osong.id)}>
                <span className="fo-case-status ready">깊은 재현 · 관제 가능</span>
                <strong>{caseText(osong).name}</strong>
                <span className="fo-case-place">{caseText(osong).place}</span>
                <span className="fo-case-flow">{caseText(osong).flow}</span>
                {osongWarning != null && <span className="fo-case-lead">{leadText(osongWarning, "공식 홍수경보")} · 유입 {osongScore?.reference.at.slice(11, 16)}</span>}
                <span className="fo-case-go">관제 화면 열기 <ArrowRight size={15} /></span>
              </button>
            )}
            {scoredOthers.map((item) => {
              const advisory = item.signals.find((signal) => signal.signal === "공식 홍수주의보")?.lead_min ?? null;
              return (
                <button key={item.id} type="button" className="fo-case is-ready" onClick={onCompare}>
                  <span className="fo-case-status ready">채점 · 보도 통제 시각 대조</span>
                  <strong>{item.title}</strong>
                  <span className="fo-case-place">{item.region} · 관측소 {item.gauge}</span>
                  <span className="fo-case-flow">{item.reference.label}</span>
                  <span className={`fo-case-lead ${advisory != null && advisory < 0 ? "late" : ""}`}>{leadText(advisory, "공식 홍수주의보")}</span>
                  <span className="fo-case-go">채점표 보기 <ArrowRight size={15} /></span>
                </button>
              );
            })}
            {scored === null && <p className="fo-case-empty-note">채점 사건을 불러오는 중</p>}
            {scored?.length === 0 && <p className="fo-case-empty-note">채점표를 불러오지 못했습니다. 백엔드 API 연결을 확인하세요.</p>}
          </div>
        </div>
        <div className="fo-case-set fo-case-set-extra">
          <p className="fo-eyebrow">확장 사례 · 원인이 다름 — 기준 검증에 쓰지 않음</p>
          <div className="fo-case-grid">
            {extras.map((event) => {
              const text = caseText(event);
              return (
                <button key={event.id} type="button" className="fo-case is-ready" onClick={() => onSelect(event.id)}>
                  <span className="fo-case-status ready">관제 가능</span>
                  <strong>{text.name}</strong>
                  <span className="fo-case-place">{text.place}</span>
                  <span className="fo-case-flow">{text.flow}</span>
                  <span className="fo-case-go">관제 화면 열기 <ArrowRight size={15} /></span>
                </button>
              );
            })}
          </div>
        </div>
      </section>
    </main>
  );
}
