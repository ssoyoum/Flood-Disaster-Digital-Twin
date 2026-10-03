import type { FloodEvent, ReconstructionResponse } from "../types";

// The API and processed data keep English codes; the console shows Korean labels.
export const STAGE_KO: Record<string, string> = {
  warning: "홍수경보 발령",
  hydraulic_warning: "미호천 계획홍수위 도달",
  overtopping: "월류 시작",
  levee_failure: "임시제방 붕괴",
  underpass_inflow: "지하차도 유입 시작",
  unsafe_driving: "차량 통행 위험",
  full_inundation: "지하차도 완전 침수",
  rain_warning: "호우경보 발령",
  heavy_rain: "시간당 50mm 도달",
  design_exceeded: "설계강우 95mm/h 초과",
  rescue_call: "첫 구조 신고 (신림동)",
  public_alert: "첫 저지대 침수 문자",
  national_escalation: "중대본 2단계",
  responders_arrive: "소방 현장 도착",
};

export const ROLE_KO: Record<string, string> = {
  "Incident Record": "사건 기록",
  "Hydromet Threshold": "수문 기준",
  "Baseline Event": "기준 사건",
  "Validation Target": "검증 대상",
};

export const CONFIDENCE_KO: Record<string, string> = {
  NEEDS_SOURCE_PAGE: "출처 쪽수 확인 필요",
  OBSERVED: "관측",
  DERIVED: "파생",
  PRESS_REPORT: "언론 보도",
};

export const STATUS_KO: Record<string, string> = {
  VERIFIED: "검증",
  DERIVED: "파생",
  TEMPORARY: "임시",
  PENDING: "확보 전",
};

const EVENT_KO: Record<string, Pick<FloodEvent, "name" | "location" | "focus_feature">> = {
  "osong-2023": { name: "2023 오송 궁평2지하차도 침수", location: "충북 청주시 흥덕구 오송읍", focus_feature: "궁평2지하차도" },
  "seoul-2022": { name: "2022 서울 도림천 유역 침수", location: "서울 관악·동작·영등포 (도림천 유역)", focus_feature: "도림천 유역 저지대" },
};

export const stageKo = (state: unknown, fallback: unknown) => STAGE_KO[String(state)] ?? String(fallback ?? state ?? "");
export const statusKo = (status: unknown) => STATUS_KO[String(status)] ?? String(status ?? "");

export function localizeEvent(event: FloodEvent): FloodEvent {
  return { ...event, ...EVENT_KO[event.id] };
}

const TEXT_KO: Record<string, string> = {
  "2023 Osong observed event reconstruction": "2023 오송 관측 사건 재구성",
  "Baseline: 2023 observed incident sequence": "원시나리오: 2023 관측 사건 경과",
  "Observed rainfall, water-level context, and official incident timing are replayed as a rule-based state sequence.":
    "관측 강우·수위와 공식 사건 시각을 규칙에 따라 단계별로 재생합니다.",
  "Intervention: underpass entrance closure": "개입: 지하차도 입구 통제",
  "Not provided: no validated underpass-depth trigger is connected": "미제공: 검증된 지하차도 수심 기준이 연결되지 않음",
  "The closure time is anchored to the observed inflow timestamp for timeline comparison; no sensor threshold is provided.":
    "타임라인 비교를 위해 통제 시각을 관측된 유입 시각에 맞췄습니다. 센서 기준값은 없습니다.",
  "Close underpass entrances and block new vehicle entry.": "지하차도 입구를 닫고 신규 차량 진입을 막습니다.",
  "If the assumed closure is fully enforced, new entry stops; vehicle and casualty effects are not calculated.":
    "가정한 통제가 완전히 지켜지면 신규 진입이 멈춥니다. 차량·인명 피해 효과는 계산하지 않습니다.",
  "TEMPORARY HAND-like reconstruction, not official Flood Extent or a calibrated hydraulic model.":
    "임시 HAND 방식 재구성이며 공식 침수범위나 보정된 수리모형 결과가 아닙니다.",
};
export const textKo = <T,>(value: T): T => (typeof value === "string" && TEXT_KO[value] ? (TEXT_KO[value] as T) : value);
const localizeStrings = <T extends object>(obj: T): T =>
  Object.fromEntries(Object.entries(obj).map(([key, value]) => [key, textKo(value)])) as T;

export function localizeReconstruction(reconstruction: ReconstructionResponse): ReconstructionResponse {
  return {
    ...reconstruction,
    title: textKo(reconstruction.title),
    baseline: localizeStrings(reconstruction.baseline),
    ...(reconstruction.intervention ? { intervention: localizeStrings(reconstruction.intervention) } : {}),
    replay: reconstruction.replay.map((step) => ({
      ...step,
      label: stageKo(step.state, step.label),
      role: ROLE_KO[step.role] ?? step.role,
      confidence: CONFIDENCE_KO[step.confidence] ?? step.confidence,
    })),
  };
}
