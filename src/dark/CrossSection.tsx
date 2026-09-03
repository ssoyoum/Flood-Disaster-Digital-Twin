import { useMemo } from "react";
import type { GeoJson } from "../types";

/*
 * 지하차도가 놓인 HAND 셀의 단면.
 *
 * HAND 재구성이 셀을 고르는 규칙을 그대로 그림으로 옮긴 것이다.
 *   셀이 선택됨  ⇔  셀의 HAND(배수 기준면 위 높이) ≤ 그 단계의 임계(관측 수위 상승분 + 붕괴 가중)
 * 그래서 파란 물은 "배수 기준면에서 관측 수위가 얼마나 올라왔는가"이고, 점선은 그 단계의 선택 임계다.
 * 물이 셀 표면(HAND)을 넘으면 그 단계 envelope 에 이 셀이 들어간다.
 *
 * 값은 전부 hand_reconstruction 레이어 속성에서 읽는다. 여기서 만든 숫자는 없다.
 * 이것은 실제 침수심·수면고가 아니다. 관측 수위는 DEM 절대 표고로 변환되지 않았다(DQ-007).
 */

type StageRow = {
  stage_index: number;
  state: string;
  label: string;
  relative_rise: number;
  threshold: number;
  observed_wl: number | null;
  wl_ts: string | null;
  rain: number | null;
};

type Cell = {
  grid_id: string;
  hand_m: number;
  mean_elevation_m: number | null;
  local_drainage_elevation_m: number | null;
  distance_to_river_m: number | null;
};

const asNumber = (value: unknown) => (typeof value === "number" && Number.isFinite(value) ? value : null);

/** 광선 투사. 셀 폴리곤은 사각형이라 단순하다. */
function contains(ring: number[][], [x, y]: [number, number]) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i]; const [xj, yj] = ring[j];
    const crosses = yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;
    if (crosses) inside = !inside;
  }
  return inside;
}

export function buildProfile(hand: GeoJson, center: [number, number] | null) {
  const byStage = new Map<number, StageRow>();
  let cell: Cell | null = null;
  const included = new Set<number>();
  for (const feature of hand.features) {
    if (feature.geometry.type !== "Polygon") continue;
    const p = feature.properties;
    const si = asNumber(p.stage_index);
    if (si === null) continue;
    if (!byStage.has(si)) {
      byStage.set(si, {
        stage_index: si,
        state: String(p.state ?? ""),
        label: String(p.label ?? ""),
        relative_rise: asNumber(p.relative_water_level_rise_m) ?? 0,
        threshold: asNumber(p.hand_threshold_m) ?? 0,
        observed_wl: asNumber(p.observed_water_level_m),
        wl_ts: p.water_level_timestamp_kst ? String(p.water_level_timestamp_kst) : null,
        rain: asNumber(p.stage_hourly_rainfall_mm),
      });
    }
    if (center && !included.has(si)) {
      const ring = (feature.geometry.coordinates as number[][][])[0];
      if (ring && contains(ring, center)) {
        included.add(si);
        cell ??= {
          grid_id: String(p.grid_id ?? "?"),
          hand_m: asNumber(p.hand_m) ?? 0,
          mean_elevation_m: asNumber(p.mean_elevation_m),
          local_drainage_elevation_m: asNumber(p.local_drainage_elevation_m),
          distance_to_river_m: asNumber(p.distance_to_river_m),
        };
      }
    }
  }
  return { byStage, cell, included };
}

export default function CrossSection({
  hand,
  center,
  stageIndex,
  stageLabel,
  stageTime,
  tone,
  focusName,
}: {
  hand: GeoJson;
  center: [number, number] | null;
  stageIndex: number;
  stageLabel: string;
  stageTime: string;
  tone: string;
  focusName: string;
}) {
  const profile = useMemo(() => buildProfile(hand, center), [hand, center]);
  const row = profile.byStage.get(stageIndex) ?? null;
  const cell = profile.cell;
  const maxThreshold = Math.max(0, ...[...profile.byStage.values()].map((r) => r.threshold));
  const top = Math.max(3, maxThreshold, cell?.hand_m ?? 0) + 0.8; // 세로 축 최대(m)

  // 그림 좌표. 아래쪽 y=BASE 가 배수 기준면 0 m.
  const W = 330; const H = 190; const BASE = 158; const TOP = 18;
  const y = (m: number) => BASE - (Math.min(Math.max(m, 0), top) / top) * (BASE - TOP);
  const rise = row?.relative_rise ?? 0;
  const threshold = row?.threshold ?? 0;
  const derivedMargin = Math.max(0, threshold - rise);
  const handM = cell?.hand_m ?? 0;
  const selected = profile.included.has(stageIndex);
  const groundX = 150; // 이 오른쪽이 셀(지하차도가 놓인 땅)

  return (
    <div className="dk-xs" style={{ ["--tone" as string]: tone }}>
      <div className="dk-xs-head">
        <p>Cell cross-section</p>
        <h3>{focusName} 셀 단면 · {stageTime} {stageLabel}</h3>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="배수 기준면 대비 관측 수위 상승과 셀 HAND 비교">
        <defs>
          <linearGradient id="dk-water" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="#38bdf8" stopOpacity=".85" />
            <stop offset="1" stopColor="#0ea5e9" stopOpacity=".55" />
          </linearGradient>
        </defs>
        {/* 눈금 */}
        {Array.from({ length: Math.floor(top) + 1 }, (_, m) => (
          <g key={m}>
            <line x1="34" x2={W - 8} y1={y(m)} y2={y(m)} stroke="#22304a" strokeWidth=".6" />
            <text x="30" y={y(m) + 3} textAnchor="end" fontSize="8" fill="#8ea0b8">{m} m</text>
          </g>
        ))}
        {/* 셀(땅): HAND 높이까지 */}
        <rect x={groundX} y={y(handM)} width={W - 8 - groundX} height={BASE - y(handM)} fill="#3b4a63" style={{ transition: "y .8s ease, height .8s ease" }} />
        <text x={groundX + 8} y={y(handM) - 5} fontSize="9" fill="#e5ecf5" fontWeight="700">셀 표면 · HAND {handM.toFixed(2)} m</text>
        {/* 물: 배수 기준면에서 관측 상승분까지 */}
        <rect className="dk-xs-water" x="34" y={y(rise)} width={W - 42} height={BASE - y(rise)} fill="url(#dk-water)" style={{ transition: "y .8s ease, height .8s ease" }} />
        <path
          className="dk-xs-wave"
          d={`M 34 ${y(rise)} q 8 -3 16 0 t 16 0 t 16 0 t 16 0 t 16 0 t 16 0 t 16 0 t 16 0 t 16 0 t 16 0 t 16 0 t 16 0 t 16 0 t 16 0 t 16 0 t 16 0 t 16 0 t 16 0 t 16 0 t 16 0 t 16 0 t 16 0`}
          fill="none" stroke="#7dd3fc" strokeWidth="1.4" style={{ transition: "d .8s ease" }}
        />
        {/* 임계선 */}
        {row && (
          <g style={{ transition: "transform .8s ease" }}>
            <line x1="34" x2={W - 8} y1={y(threshold)} y2={y(threshold)} stroke={tone} strokeWidth="1.2" strokeDasharray="4 3" />
            <text x={W - 10} y={y(threshold) - 4} textAnchor="end" fontSize="8.5" fill={tone} fontWeight="700">선택 임계 {threshold.toFixed(2)} m</text>
          </g>
        )}
        {/* 배수 기준면 */}
        <line x1="34" x2={W - 8} y1={BASE} y2={BASE} stroke="#7dd3fc" strokeWidth="1" />
        <text x="36" y={BASE + 11} fontSize="8" fill="#8ea0b8">배수 기준면(하천) 0 m{cell?.local_drainage_elevation_m != null ? ` · 표고 ${cell.local_drainage_elevation_m.toFixed(1)} m` : ""}</text>
        <text x={W - 10} y={BASE + 11} textAnchor="end" fontSize="8" fill="#8ea0b8">{cell ? `셀 ${cell.grid_id}${cell.mean_elevation_m != null ? ` · 평균 표고 ${cell.mean_elevation_m.toFixed(1)} m` : ""}` : "셀 정보 없음"}</text>
      </svg>
      <div className="dk-xs-legend" aria-label="단면도 값 구분">
        <span><i className="measured" /> 파란 영역 · 관측 수위 기준 대비 상승분</span>
        <span><i className="derived" /> 점선 · HAND 선택 임계(파생)</span>
      </div>
      <dl className="dk-xs-values">
        <div><dt>실측 관측 수위</dt><dd>{row?.observed_wl != null ? `${row.observed_wl.toFixed(2)} m` : "—"}<small>{row?.wl_ts ?? "단계 0 · 상승 전"} · 홍수통제소</small></dd></div>
        <div><dt>실측값 차분</dt><dd style={{ color: "#7dd3fc" }}>{rise.toFixed(2)} m<small>기준 관측 대비 상승분</small></dd></div>
        <div><dt>선택 임계(파생)</dt><dd style={{ color: tone }}>{row ? `${threshold.toFixed(2)} m` : "—"}<small>상승분 + 재구성 가중분</small></dd></div>
        <div><dt>임계 추가분(파생)</dt><dd style={{ color: tone }}>{row ? `${derivedMargin.toFixed(2)} m` : "—"}<small>실측 수위가 아님</small></dd></div>
        <div><dt>시간당 강우</dt><dd>{row?.rain != null ? `${row.rain.toFixed(1)} mm` : "—"}<small>KMA AWS</small></dd></div>
      </dl>
      <p className={`dk-xs-status ${selected ? "on" : ""}`}>
        {cell
          ? selected
            ? `이 단계에서 지하차도 셀이 envelope에 포함됩니다 (임계 ${threshold.toFixed(2)} m ≥ HAND ${handM.toFixed(2)} m)`
            : row
              ? `아직 미포함 (임계 ${threshold.toFixed(2)} m < HAND ${handM.toFixed(2)} m)`
              : "단계 0 · 수위 상승 전"
          : "지하차도 위치의 HAND 셀을 찾지 못했습니다"}
      </p>
      <small className="dk-note">
        실측값은 홍수통제소의 관측 수위(절대 관측값)와 그 기준 대비 차분입니다.
        파란 영역은 그 차분을 배수 기준면 위 높이로 표현한 것이며, 점선 임계와 추가분은 HAND 재구성용 파생값입니다.
        수위는 DEM 절대 표고로 변환되지 않았고(DQ-007), 지하차도 내부 수심은 이 모델이 계산하지 않습니다.
      </small>
    </div>
  );
}
