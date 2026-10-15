# 시설 레지스트리 — 운영 시설과 후보 시설

트윈의 단위는 시설(지하차도)이다. 이 문서는 시설을 **어떤 형식으로 등록하고, 어떤 조건을 채워야 운영 시설이 되는지**를 정한다. 코드에 박혀 있던 `FACILITIES` 딕셔너리를 데이터 파일로 옮겨, "같은 등록 형식 · 운영 시설 1곳 · 후보 N곳(채우지 못한 관문 명시)"을 그대로 보여줄 수 있게 했다.

## 두 파일

| 파일 | 관리 방식 | 들어가는 것 |
|---|---|---|
| `data/facilities/registry.json` | 손으로 관리 | 관문 정의 4개, **OPERATIONAL** 시설 (지금은 궁평2지하차도 1곳) |
| `data/facilities/candidates.json` | `data/scripts/build_facility_candidates.py`가 생성 | **CANDIDATE** 시설 (지금은 5곳), 입력 행 수·입력 파일 SHA-256·선정 규칙·제외 목록(`excluded`) |

로더는 `backend/app/facility_registry.py`다. 두 파일을 읽어 검증하고, `twin.py`의 `FACILITIES`는 `facility_registry.operational()`이 돌려주는 딕셔너리를 그대로 쓴다. 후보 파일이 없으면 후보 0곳으로 뜬다. 레지스트리 파일이 없거나 검증에 실패하면 **서버가 뜨지 않는다** (시설 id와 필드를 이름으로 지목하는 `ValueError`).

## 등록 형식 (필드)

| 필드 | OPERATIONAL | CANDIDATE | 뜻 |
|---|---|---|---|
| `id` | 필수 | 필수 | ASCII 슬러그. 후보는 `cb-<국토부 순번>-<이름>` |
| `name` `kind` `driver` | 필수 | 필수 | `driver`는 `river_stage`(하천 영향형) 또는 `unverified` |
| `status` | `OPERATIONAL` | `CANDIDATE` | 아래 생애주기 참고 |
| `region` | 필수 | 필수 | 시도 + 시군구 |
| `location` | `[lon, lat]` 필수 | `[lon, lat]` 또는 `null` | 후보 좌표는 OSM 이름 매칭 결과라 확인이 필요하다 |
| `road` `managing_agency` | 값 | 자료 없으면 `null` | 공공데이터 목록에는 관리기관이 비어 있다 |
| `event_id` | 필수 | 없음 | 검증 사건 (`osong-2023`) |
| `source` | 필수 | 필수 | `dataset_id`, `source_record_id`/`molit_no`, `source_url`, `source_date` |
| `gauge` | 필수. `station_id`, `datum_el_m`, `levels_m`{`attention` `advisory` `warning` `severe` `planned_flood`}, `source` | **`null` 강제** | 그 시설 관측소의 공식 수위만 쓴다 |
| `rain_station` `history_series` | 있으면 사용 | 없음 | |
| `control_rule` | 필수 (`id` `stage_floor` `rate_window_min` `lead_threshold_min` `basis` …) | **`null` 강제** | |
| `reference_event` | 필수 (시각 4개 + `source`) | **`null` 강제** | |
| `nearby_gauges` | 없음 | 최대 3개, 가까운 순 | 관측소 코드·이름·거리·홍수예보 지점 여부·공식 수위. **후보일 뿐 대표성 확인이 아니다** |
| `gates` | 4개 모두, `UNKNOWN` 불가 | 4개 모두 | 아래 관문 참고 |
| `review_notes` | 없음 | 생성기가 자료에서 찾은 확인 사항 | 예: 좌표가 운영 시설과 겹침 |

## 등록 관문 4개

| id | 이름 | 묻는 것 |
|---|---|---|
| `inflow_path` | 유입 경로 | 강물이 넘쳐 들어오는지(하천 영향형), 빗물이 고여 차는지(내수 배수형) 실제 경로를 확인했는가 |
| `representative_gauge` | 대표 관측소 | 연결한 관측소가 같은 유역이고 그 시설의 유입을 설명하는가 |
| `site_instrumentation` | 현장 계측 | 침수심·집수정 수위·펌프 상태를 시각과 함께 확보했는가 |
| `validation_event` | 검증 사건 | 시각이 확인된 침수·통제 기록으로 백테스트할 수 있는가 |

관문 상태:

| 상태 | 뜻 | 화면 |
|---|---|---|
| `CONFIRMED` | 자료로 확인함 | ✓ |
| `PENDING` | 후보 자료는 있으나 확인 전 (예: 5 km 안 홍수예보 관측소) | 확인 중 |
| `MISSING` | 조사했고 자료가 없음을 확인함. 한계로 화면에 표시한다 | 없음 |
| `UNKNOWN` | 조사하지 않음 | 미확인 |

`MISSING`과 `UNKNOWN`은 다르다. 궁평2는 현장 계측이 `MISSING`이다 — 침수 센서·집수정 자료가 없다는 것을 알고, 하천 수위만으로 선행 지표를 내며 화면에 "침수심을 측정하지 않는다"고 적는다. 운영 시설은 관문을 `UNKNOWN`으로 둘 수 없다.

### 지금의 궁평2지하차도

| 관문 | 상태 | 근거 |
|---|---|---|
| 유입 경로 | CONFIRMED | 미호강 범람 → 임시제방 붕괴 → 유입 (2023-07-15) |
| 대표 관측소 | CONFIRMED | 미호강교 3011665 · 1.17 km · 홍수예보 지점 · 국무조정실 감찰이 본 관측소 |
| 현장 계측 | MISSING | 현장 침수 센서·집수정 수위 자료 없음 → 하천 수위만 사용 |
| 검증 사건 | CONFIRMED | osong-2023 · 유입 08:27 · 첫 권고 05:50 |

## 생애주기 CANDIDATE → OPERATIONAL

1. 후보는 생성기가 공공 목록에서 뽑는다. 사람이 손으로 `candidates.json`을 고치지 않는다 (다시 생성하면 사라진다).
2. 담당자(관리기관 또는 프로젝트 담당)가 관문을 하나씩 확인한다. 확인한 근거는 `registry.json`의 `gates.*.note`에 출처와 함께 적는다.
3. 관문 4개가 모두 `CONFIRMED` 또는 `MISSING`이고, 그 시설 관측소의 공식 수위(`gauge.levels_m`)·규칙(`control_rule`)·검증 사건(`reference_event`)을 채울 수 있을 때 `registry.json`의 `facilities`에 **새 항목을 손으로 추가**한다. 후보 항목을 복사해 `status`만 바꾸는 것이 아니다.
4. 생성기를 다시 돌리면 운영 시설과 id가 겹치는 후보가 있을 경우 로더가 거부한다. 그 시설의 후보 슬러그(`SLUGS`)를 지우거나 선정 규칙에서 빼서 다시 생성한다.
5. 운영 시설이 되면 `/api/twin/facilities`에 나오고 상태·백테스트·기준 검토·예측 준비도 엔드포인트가 열린다.

결정 주체: 관문 확인과 등록은 담당자의 판단이다. 트윈은 후보를 자동으로 운영 시설로 올리지 않는다. 후보 순서는 국토부 순번이며 위험 순위가 아니다.

## 임계값을 복사하지 않는다

- 궁평2의 `levels_m`(관심 5.0 · 주의보 7.0 · 경보 8.0 · 계획홍수위 9.38 m)은 **미호강교 관측소의 공식 수위**다. 다른 시설에 그대로 쓰면 틀린 값이다.
- 로더는 후보에 `gauge`·`control_rule`·`reference_event`가 조금이라도 들어 있으면 서버를 띄우지 않는다. 테스트 `test_validator_rejects_a_candidate_that_sneaks_in_a_control_rule`이 이를 고정한다.
- 후보의 `nearby_gauges`에 있는 공식 수위는 그 관측소의 값을 **참고로** 옮긴 것이고, 대표 관측소로 확인되기 전까지 규칙에 쓰지 않는다.
- `river_stage_v1`의 60분·30분 같은 수치도 오송에서 정한 가정이다. 새 시설은 그 시설의 배수능력·과거 체수와 대조해 따로 정한다 ([UNDERPASS_EXPANSION.md](UNDERPASS_EXPANSION.md)).

## API

```
GET /api/twin/registry
{
  "gates": [{"id": "inflow_path", "label": "유입 경로", "question": "..."}, ...4개],
  "operational": [{"id": "gungpyeong2-underpass", "status": "OPERATIONAL", "gates": {...}, "unmet_gates": ["site_instrumentation"],
                   "gauge": {"station_id": "3011665", "name": "청주시(미호강교)"}, "event_id": "osong-2023", ...}],
  "candidates": [{"id": "cb-519-osong-biopolis", "status": "CANDIDATE", "location": null, "nearby_gauges": [], "gauge": null,
                  "control_rule": null, "gates": {...모두 UNKNOWN...}, "unmet_gates": [...4개], ...}, ...],
  "counts": {"operational": 1, "candidate": 5}
}

GET /api/twin/facilities            # 운영 시설만. 각 항목에 status·gates가 추가됐다 (기존 필드 유지)
GET /api/twin/facilities/cb-519-osong-biopolis/status
→ 409 {"detail": {"code": "FACILITY_NOT_OPERATIONAL", "facility_id": "cb-519-osong-biopolis",
                  "status": "CANDIDATE", "unmet_gates": ["inflow_path", "representative_gauge", "site_instrumentation", "validation_event"]}}
GET /api/twin/facilities/nope/status → 404
```

`/status` `/backtest` `/criteria-review` `/forecast-readiness` `/rise-forecast` 모두 같은 규칙이다. 운영 시설 요약에는 `levels_m`이 들어가지 않는다 (임계는 시설별 엔드포인트에서만).

## 후보 다시 만들기

```powershell
python data/scripts/build_facility_candidates.py
```

네트워크 없이 `data/processed/facilities/`의 CSV 3개와 `registry.json`만 읽는다. 선정 규칙:

- (a) `underpass_coordinates.csv`의 충청북도 행 중 좌표가 있고, `facility_gauge_links.csv`에 5 km 안 홍수예보 수위관측소(`flood_forecast_station=Y`)가 있는 행
- (b) [UNDERPASS_EXPANSION.md](UNDERPASS_EXPANSION.md)의 청주 1차 확인 후보 3곳 (국토부 순번 519·521·523), 좌표가 없어도 포함. 국토부 순번이 같고 이름이 같은 좌표 행이 있으면 좌표·관측소를 붙인다.

관문은 모두 `UNKNOWN`으로 두되, 5 km 안 홍수예보 관측소가 있으면 `representative_gauge`만 `PENDING`(관측소·거리 기록). 그 밖의 값은 만들지 않는다.

OSM 좌표가 목록상 시군과 어긋나는 행은 스크립트의 `EXCLUDED_ORDINALS`에 이유와 함께 적어 후보에서 빼고, 생성 파일의 `excluded`에 그대로 남긴다. 생성 파일에는 생성 시각 대신 입력 파일 4개의 SHA-256이 들어가므로 입력이 같으면 다시 만들어도 바이트 단위로 같다.

### 지금의 후보 5곳 (2026-10-14 생성)

입력: `underpass_coordinates.csv` 938행(충북 32행, 좌표 6행) · `facility_gauge_links.csv` 1,698행 · `chungbuk_underpass_candidates.csv` 32행.

| id | 시설 | 지역 | 좌표 | 대표 관측소 관문 | 확인 사항 |
|---|---|---|---|---|---|
| `cb-519-osong-biopolis` | 오송바이오폴리스지하차도 | 청주시 | 없음 | UNKNOWN (좌표 없음) | |
| `cb-521-yongam` | 용암지하차도 | 청주시 | 있음 | UNKNOWN — 5 km 안 수위관측소 3곳(운암1교 1.01 km 등) 모두 홍수예보 지점 아님 | |
| `cb-523-hakpyeong` | 학평지하차도 | 청주시 | 없음 | UNKNOWN (좌표 없음) | |
| `cb-921-simgok` | 심곡지하차도(복) | 영동군 | 있음 | PENDING — 영동군(초강교) 3004685 · 4.22 km | |
| `cb-933-gungpyeong` | 궁평지하차도 | 청주시 | 있음 | PENDING — 청주시(미호강교) 3011665 · 1.16 km | 좌표가 운영 시설 궁평2지하차도와 0.1 km 안에 겹침 → OSM 매칭이 이웃 시설을 가리켰을 수 있음 |

충북 좌표 행 중 빠진 3곳: 고명지하차도(제천, 가장 가까운 홍수예보 지점 구곡교 10.93 km), 터미널 지하차도(청주, 흥덕교 5.12 km — 5 km 기준 밖), 계룡지하차도(복)(목록상 영동군인데 OSM 좌표가 대전 유성구 만년교 0.39 km에 있어 다른 시설을 가리킨 매칭으로 보고 `EXCLUDED_ORDINALS`로 제외, 좌표 확인 뒤 재검토). 기준을 바꾸려면 스크립트의 `MAX_GAUGE_KM`을 고치고 다시 생성한다.

## 관련 문서

- [PLAN_UNDERPASS_TWIN.md](PLAN_UNDERPASS_TWIN.md) 8절 — 같은 등록 형식으로 넓히는 방법
- [UNDERPASS_EXPANSION.md](UNDERPASS_EXPANSION.md) — 공공 목록 4종·충북 32행·시설 하나를 추가할 때 필요한 자료
- [FACILITY_AGENT.md](FACILITY_AGENT.md) — 시설 Agent 도구 (운영 시설만 대상)
