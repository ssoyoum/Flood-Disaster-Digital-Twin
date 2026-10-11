import { useEffect, useMemo, useRef, useState } from "react";
import * as api from "../api";
import type { LayersResponse, ReconstructionResponse } from "../types";
import { ScenarioMap, type MapSync } from "./DarkConsole";
import { localizeReconstruction } from "./ko";

/*
 * 지금 상태 보드의 공간 상태 카드.
 * 과거 재생 시각이면 그 시각까지 진행된 사건 단계의 HAND 근사 범위를 보여준다.
 * 실시간 모드에는 침수 범위 관측이 없으므로 범위를 그리지 않고 시설 위치만 둔다.
 */
export default function TwinSpatial({ eventId, at, replay }: { eventId: string; at: string | null; replay: boolean }) {
  const [layers, setLayers] = useState<LayersResponse | null>(null);
  const [reconstruction, setReconstruction] = useState<ReconstructionResponse | null>(null);
  const [failed, setFailed] = useState(false);
  const sync = useRef<MapSync>({ maps: [], syncing: false });

  useEffect(() => {
    let active = true;
    setFailed(false);
    Promise.all([api.getLayers(eventId), api.getReconstruction(eventId)])
      .then(([nextLayers, nextReconstruction]) => { if (active) { setLayers(nextLayers); setReconstruction(localizeReconstruction(nextReconstruction)); } })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [eventId]);

  // 재구성 단계 시각은 +09:00이 붙은 KST, 보드의 시각은 시간대 없는 KST라 앞 16자리로 비교한다.
  const stage = useMemo(() => {
    if (!reconstruction || !replay || !at) return -1;
    let index = -1;
    reconstruction.replay.forEach((item, i) => { if (item.time.slice(0, 16) <= at.slice(0, 16)) index = i; });
    return index;
  }, [reconstruction, replay, at]);

  return (
    <article className="tw-card tw-spatial" aria-label="공간 상태">
      <p className="tw-eyebrow">공간 상태 · {replay ? "2023년 사건 재구성(HAND 근사)" : "실시간 침수 범위 없음"}</p>
      {failed ? <p className="dk-error">지도 자료를 불러오지 못했습니다.</p>
        : layers && reconstruction ? (
          <ScenarioMap layers={layers} reconstruction={reconstruction} time={stage} mode="baseline" title={replay ? "선택 시각의 사건 단계" : "시설 위치"} sync={sync.current} />
        ) : <small className="ub-note">지도를 불러오는 중…</small>}
      <small className="ub-note">
        {!replay
          ? "실시간 모드에서는 침수 범위를 추정하지 않습니다. 과거 재생 시각을 고르면 2023년 사건 단계의 근사 범위를 겹쳐 봅니다."
          : stage < 0
            ? "선택한 시각은 첫 사건 단계(04:10 홍수경보) 전이라 표시할 범위가 없습니다."
            : "관측 단계별로 낮은 땅을 이어 그린 근사 범위이며 공식 침수범위·침수심·수리모형 결과가 아닙니다."}
      </small>
    </article>
  );
}
