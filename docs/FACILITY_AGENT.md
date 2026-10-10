# 시설 통제 판단 Agent

2026-10-10 기준. 현재 등록 시설은 궁평2지하차도(`gungpyeong2-underpass`, 검증 사건 `osong-2023`) 한 곳이다. 상태 보드 전체 개편에 앞서 기존 화면에서 시설 관측·규칙·백테스트를 질의할 수 있게 연결했다.

## 화면에서 사용

1. 오송 화면을 연다.
2. 상단 Agent의 **분석 범위 → 시설 통제 판단**을 고른다.
3. **과거 재생 시각**에 `2023-07-15T08:00`을 입력한다. 비워두면 트윈의 연결 모드(live 또는 replay)를 따른다.
4. 시설 상태·통제 기준·과거 백테스트 추천 질문을 선택하거나 직접 질문한다.
5. 답변 아래 **호출 결과 보기**에서 시설·시각, 관측 수위·여유·단계, 규칙과 한계를 확인한다.

시설 또는 재생 시각을 바꾸면 이전 대화와 진행 중 요청을 버린다. "과거 사건 분석"에서는 기존 통제 시각·유입 지연·HAND 분석을 사용할 수 있다. 시설 범위의 모델은 그 도구들을 호출할 수 없다.

## 세 도구의 역할

| 도구 | 반환 근거 | 계산하지 않는 것 |
|---|---|---|
| `get_facility_status` | 관측 모드·시각·수위·계획홍수위 여유·상승 속도·단계·검토 권고·신선도 | 침수심, 확정 유입 시각, 안전 보장, 통제 실행 |
| `get_control_rule` | `river_stage_v1` 조건, 관측소 메타데이터, 근거와 가정 | 미연결 공식 지침 확정, 자동 차단 승인 |
| `get_facility_backtest` | 저장된 2023년 수위에 같은 규칙을 적용한 첫 검토 시각·사건 시각까지 시간차 | 실제 통제 이력, 피해 감소, 대피 성공률 |

시설·시각은 요청 최상위 입력이며 서버가 고정한다. 모델이 다른 값을 넣으면 실행 전에 거절한다. 명시한 시각은 과거 재생에만 사용하며 live API를 조회하지 않는다. 시간대가 있는 ISO 입력은 KST로 변환한다.

```json
{
  "event_id": "osong-2023",
  "facility_id": "gungpyeong2-underpass",
  "observation_at": "2023-07-15T08:00:00",
  "message": "시설 상태와 통제 검토 기준을 함께 설명해줘",
  "history": []
}
```

`POST /api/agent/ask`에 전달한다. 카탈로그·추천 질문은 `GET /api/agent/tools`·`GET /api/agent/examples`에 같은 `event_id`·`facility_id` 쿼리를 준다. 직접 실행은 `POST /api/agent/tools/{tool_name}`이며 범위 입력을 동일하게 준다.

## 관측과 판단의 경계

- replay의 `fresh`는 **선택한 재생 시각에 대한 자료 나이**다. 지금 신선한 실측이라는 뜻이 아니다. replay의 `decision_usable`은 항상 false다.
- live 관측의 내부 신선도 한도는 10분 자료 20분, 1시간 자료 90분이다. 법정 통제 기준이 아니다. 누락·한도 초과이면 `NEEDS_DATA`이며 현재 통제 판단에 사용할 수 없다고 설명한다.
- live 소스 실패 시 과거 관측으로 대체하지 않는다. 키를 포함할 수 있는 원본 오류 URL도 반환하지 않는다.
- `decision_usable`은 live 관측의 기본 신선도 통과 표시다. 기관 운영 승인·통제 허가를 뜻하지 않는다.
- 계획홍수위 도달 또는 경보 수위 이상에서 상승 속도 외삽의 도달 시간이 60분 이하이면 **통제 검토**를 제안한다. 최근 30분 상승 속도의 외삽은 예보나 지하차도 유입 예측이 아니다.
- 기준값은 2026년 조회 관측소 메타데이터다. 2023년 기준과의 일치, 최신 공식 통제 지침 원문, 사건 출처 쪽수는 추가 확인이 필요하다.
- DQ-009: 국무조정실 발표의 요건 충족 시각은 06:40, 보관된 10분 관측이 9.38m에 닿는 시각은 06:50이다. 답변에 이 차이를 유지한다.
- 모델 실패·근거 없는 안전 또는 통제 완료 주장 시 도구 값으로 설명문을 구성한다. `diagnostics.completion_source`의 `model`과 `registered_tools`를 구분한다. 실제 통제는 현장 계측·관리기관 기준·담당자 판단이 우선한다.

## 로컬 대조

```powershell
python -m pytest backend/tests/test_agent_facility.py -q
python backend/evaluation/evaluate_agent.py --suite facility --output docs/local/facility-agent-offline.json
python backend/evaluation/evaluate_agent.py --suite facility --mode live --output docs/local/facility-agent-live.json
```

시설 suite는 평가 프로세스의 관측 모드를 replay로 고정한다. **`--mode live`는 실제 Gemini 호출**이며 실시간 HRFCO 관측 검증이라는 뜻이 아니다. 로컬 JSON은 답변·시설·시각·도구 입력·직접 API 대조·완료 경로를 남긴다. 실제 모델 요청량을 사용한다.

2026-10-10 소수 질문에서 offline 3/3(등록 도구 설명), 실제 Gemini 3/3(모델 설명, HTTP 6회)을 확인했다. 공개 배포·장시간 사용·동시 부하·기관 실증은 이 결과에 포함되지 않는다.
