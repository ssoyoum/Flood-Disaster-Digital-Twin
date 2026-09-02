# WORKLOG

## 프론트 실행 및 CORS 수정

- 시작 시각: 2026-08-30 12:12:01 +09:00
- 종료 시각: 2026-08-30 12:14:59 +09:00
- 총 소요시간: 3분

주요 작업:
- Vite dev server가 기본 포트 대신 다른 로컬 포트로 실행될 수 있는 상황을 확인했다.
- FastAPI CORS 설정을 로컬 개발 포트 전체에 대응하도록 조정했다.
- 현재 개발 실행 조합을 `frontend 5180` + `backend 8010`으로 확인했다.

검증 결과:
- Backend tests: `6 passed`
- Frontend build: 통과
- Frontend dev URL 및 Osong API 응답 확인 완료

문제/해결:
- 문제: Vite가 `5175` 등으로 이동하면 기존 CORS 허용 목록에 없어 API 호출이 막힘. 해결: local dev origin regex 추가.

## 온라인 Basemap 및 지도 정보 표시

- 시작 시각: 2026-08-30 12:35:11 +09:00
- 종료 시각: 2026-08-30 12:39:31 +09:00
- 총 소요시간: 4분

주요 작업:
- API key가 필요 없는 OpenStreetMap raster basemap을 MapLibre에 연결했다.
- AOI 원본은 유지하고 기본 화면만 궁평2지하차도 주변으로 확대되도록 조정했다.
- 건물을 유형별 색상으로 구분하고, 건물/시설/지하차도 popup 정보를 추가했다.
- 화면에 OpenStreetMap attribution과 외부 tile 사용 사실을 표시했다.

검증 결과:
- Backend tests: `6 passed`
- Frontend build: 통과
- Frontend dev URL HTTP `200`

문제/해결:
- 문제: MapLibre 타입상 `attributionControl: true`가 허용되지 않음. 해결: `attributionControl: { compact: true }`로 수정.

## Provenance Data Vintage 표시 개선

- 시작 시각: 2026-08-30 12:47:20 +09:00
- 종료 시각: 2026-08-30 12:51:08 +09:00
- 총 소요시간: 4분

주요 작업:
- Provenance 영역을 Source, Vintage, Status, Role 카드 구조로 개선했다.
- Event Year와 각 레이어 Data Vintage를 분리해서 표시했다.
- 지도 레이어 패널과 객체 popup에 source/vintage/status 정보를 추가했다.
- 온라인 basemap은 분석 데이터와 분리해 `CURRENT / LIVE REFERENCE`로 표시했다.

검증 결과:
- Frontend build: 통과
- Status API 기준 vintage 값 확인 완료

문제/해결:
- 문제: basemap을 `TEMPORARY` 상태로 보이면 분석 데이터처럼 오해될 수 있음. 해결: 프론트 표시용 `REFERENCE` 배지로 분리.

## Basemap/Analysis Vintage 선택 분리

- 시작 시각: 2026-08-30 12:54:59 +09:00
- 종료 시각: 2026-08-30 12:58:12 +09:00
- 총 소요시간: 4분

주요 작업:
- 온라인 basemap은 2023 선택이 불가능하므로 `CURRENT / LIVE REFERENCE`로 고정 표시했다.
- OSM processed analysis layer에 2023/2026 vintage 선택 UI를 추가했다.
- 사용자 화면에서 개발용 status 값 표시를 제거하고 source/vintage/role 중심으로 정리했다.
- 건물/시설 popup도 source와 data vintage만 표시하도록 정리했다.

검증 결과:
- Frontend build: 통과
- Backend tests: `7 passed`
- `layer_year=2023/2026` API 응답 확인 완료

문제/해결:
- 문제: 온라인 basemap을 사건연도 자료처럼 보이게 할 수 없음. 해결: basemap은 current context로 분리하고, 연도 선택은 processed analysis layer에만 적용.

## TODO Manual Action 위치 정리

- 시작 시각: 2026-08-30 12:58:43 +09:00
- 종료 시각: 2026-08-30 13:00:03 +09:00
- 총 소요시간: 2분

주요 작업:
- `Manual Action Required` 섹션을 `Known Issues` 바로 위로 이동했다.
- 사용자 직접 다운로드/승인 필요 데이터 항목을 KMA, 공식 행정경계, DSSP API로 정리했다.
- 상단 중복 섹션을 제거했다.

검증 결과:
- `Manual Action Required`는 162행, `Known Issues`는 186행에 위치함.
- `TODO.md` 첫 바이트가 `#`으로 확인되어 BOM 없음.

문제/해결:
- 문제: 문서 저장 중 BOM이 붙음. 해결: 첫 줄을 다시 패치해 BOM 제거.

## MOLIT GIS건물통합정보 2023-07 확보 시도

- 시작 시각: 2026-08-30 13:08:36 +09:00
- 종료 시각: 2026-08-30 13:13:54 +09:00
- 총 소요시간: 6분
주요 작업:
- VWorld 공식 `GIS건물통합정보`에서 2023-07 기준 파일을 조회했다.
- 충청북도 전체데이터 기준일 `2023-07-12`, `dsFileSq=1724`, 표기 용량 `84MB` 항목을 확인했다.
- 검색 결과 HTML과 로그인 필요 다운로드 응답을 `data/raw/building_integrated/`에 보존했다.
- TODO와 source availability manifest에 `MANUAL_DOWNLOAD_REQUIRED` 사유와 수동 다운로드 위치를 기록했다.

검증 결과:
- 공식 검색 결과는 확인됨.
- SHP ZIP 원본은 비로그인 직접 다운로드가 0바이트 또는 HTML 응답으로 반환되어 미확보.

문제/해결:
- 문제: VWorld 다운로드 로직이 로그인 상태를 요구함. 해결: 우회 구현 없이 수동 다운로드 대상으로 전환.

## MOLIT GIS건물통합정보 원본 반입 검증

- 시작 시각: 2026-08-30 13:16:51 +09:00
- 종료 시각: 2026-08-30 13:21:17 +09:00
- 총 소요시간: 5분
주요 작업:
- 사용자가 저장한 `AL_43_D010_20230712.zip` 원본을 확인했다.
- 이전 비로그인 다운로드 실패 응답 파일을 삭제했다.
- manifest, TODO, Data Guide를 원본 확보 완료 상태로 갱신했다.

검증 결과:
- ZIP 내부 SHP/SHX/DBF/PRJ/CPG 확인.
- DBF 기준 811,450 records, geometry `Polygon`, CRS `Korean_1985_Modified_Korea_Central_Belt`.

문제/해결:
- 문제: TODO 첫 화면의 갱신 시각이 오래되어 변경이 안 된 것처럼 보임. 해결: `Last Updated`를 현재 작업 시각으로 갱신.

## 오송 건물 기준 레이어 정책 반영

- 시작 시각: 2026-08-30 17:10:00 +09:00
- 종료 시각: 2026-08-30 17:16:45 +09:00
- 총 소요시간: 7분
주요 작업:
- 공식 2023 `GIS건물통합정보`를 기준 건물 레이어로 정리했다.
- OSM 2023은 QA 보조 레이어, OSM 2026은 2023 분석 제외/추후 비교 후보로 분리했다.
- 프론트의 2026 분석 레이어 선택을 제거하고 API도 2023으로 fallback되게 조정했다.
- `MATCHED`, `OFFICIAL_ONLY`, `OSM_ONLY` QA 플래그와 일치율 지표 아이디어를 TODO/결정 기록에 남겼다.

검증 결과:
- Backend tests: `7 passed`
- Frontend build: 통과

문제/해결:
- 문제: OSM 2026 선택 UI가 2023 사건 분석 데이터처럼 보일 수 있음. 해결: 선택 UI 제거 및 2023 분석 고정.

## 충남 건물통합정보와 KMA 강우 원본 확인

- 시작 시각: 2026-08-30 17:18:00 +09:00
- 종료 시각: 2026-08-30 17:25:11 +09:00
- 총 소요시간: 8분
주요 작업:
- 충남 `AL_44_D010_20230712.zip` 원본과 KMA AWS CSV 원본을 확인했다.
- KMA CSV를 오송 raw 폴더로 이동하고, 이전 VWorld 실패 응답 파일을 삭제했다.
- manifest, TODO, Data Guide를 충남 건물통합정보와 KMA 강우 확보 완료 상태로 갱신했다.

검증 결과:
- 충남 ZIP: SHP 2개 part, 총 1,283,619 records, geometry `Polygon`, CRS `Korean_1985_Modified_Korea_Central_Belt`.
- KMA CSV: 청주금천 327 및 오창가곡 977, 총 144 rows, 기간 2023-07-14 01:00 through 2023-07-17 00:00 KST.

문제/해결:
- 문제: 기존 후보 관측소 ID가 실제 CSV와 달랐음. 해결: 오창가곡을 `977`로 정정.

## 공식 건물통합정보와 KMA 강우 processed 변환

- 시작 시각: 2026-08-30 17:31:00 +09:00
- 종료 시각: 2026-08-30 17:40:09 +09:00
- 총 소요시간: 10분
주요 작업:
- 충북/충남 공식 `GIS건물통합정보` SHP를 오송 AOI 기준으로 subset하고 `EPSG:4326` GeoJSON으로 변환했다.
- 공식 건물과 OSM 2023 건물 footprint를 교차 매칭해 `MATCHED`, `OFFICIAL_ONLY`, `OSM_ONLY` QA 플래그를 생성했다.
- KMA AWS 원본 CSV를 UTF-8 표준 CSV로 정규화하고 backend rainfall provenance를 KMA 관측자료로 연결했다.
- TODO, Data Guide, manifest, validation report를 산출물 기준으로 갱신했다.

검증 결과:
- 공식 건물 subset: 25,283 Polygon, QA: `MATCHED` 1,251 / `OFFICIAL_ONLY` 24,032 / `OSM_ONLY` 1,817.
- KMA rainfall processed: 144 rows, 청주금천 327 및 오창가곡 977.
- Backend tests: `7 passed`; frontend build: 통과.

문제/해결:
- 문제: API가 여전히 OSM 건물을 기준 레이어로 반환함. 해결: `buildings` 레이어를 공식 processed 건물로 연결.

## WAMIS 공식 하천망 원본 확보 및 오송 subset 생성

- 시작 시각: 2026-08-30 17:45:00 +09:00
- 종료 시각: 2026-08-30 17:59:13 +09:00
- 총 소요시간: 15분

주요 작업:
- WAMIS 자료실에서 국가하천 `ntn_rvr.zip`과 지방하천 `lcl_rvr.zip` 원본을 확보했다.
- 오송 AOI bbox 기준으로 국가/지방 하천 polygon subset과 combined GeoJSON을 생성했다.
- 다음 사건에서도 재사용할 수 있도록 WAMIS 하천망 확보·subset 스크립트와 Data Guide 지침을 추가했다.
- VWorld 국가기본도 하천 후보는 로그인 수동 다운로드 필요 상태로 manifest에 분리 기록했다.

검증 결과:
- 원본 SHP: 국가하천 73개, 지방하천 3,783개, `EPSG:5179`, Polygon/MultiPolygon.
- 오송 processed: 8개 Polygon/MultiPolygon, `EPSG:4326`; 하천명 `미호천`, `조천` 등 UTF-8 정상 확인.

문제/해결:
- 문제: PowerShell 기본 콘솔 출력에서 하천명이 깨져 보임. 해결: GeoJSON UTF-8 값과 replacement 문자 부재를 직접 검증하고 지침에 기록.

## TODO 오송 확보 현황 요약 갱신

- 시작 시각: 2026-08-30 18:02:00 +09:00
- 종료 시각: 2026-08-30 18:02:35 +09:00
- 총 소요시간: 1분

주요 작업:
- `TODO.md` 상단 In Progress의 현재 확보 자료 목록에 WAMIS 공식 국가하천/지방하천 SHP를 추가했다.
- DEM과 WAMIS 하천망은 원본/processed 확보 완료, 분석/API 연결은 남은 작업으로 구분했다.

검증 결과:
- `TODO.md` 상단 요약이 High Priority의 하천망 상태와 일치함.

## WAMIS 하천망 API/지도 연결

- 시작 시각: 2026-08-30 18:14:19 +09:00
- 종료 시각: 2026-08-30 18:16:06 +09:00
- 총 소요시간: 2분

주요 작업:
- Backend `waterways` 레이어를 OSM 2023 하천선에서 WAMIS 공식 하천 polygon processed 파일로 교체했다.
- MapLibre에서 하천 polygon fill/outline을 표시하고, 클릭 시 하천명·등급·출처·기준시점 popup을 보여주도록 했다.
- Provenance와 KPI 문구를 WAMIS 공식 하천망 기준으로 정리했다.

검증 결과:
- Backend tests: `7 passed`
- Frontend build: 통과
- API spot check: `waterways` source type `OFFICIAL_RIVER_NETWORK`, feature count 8, 하천명 `미호천` 확인.

## 침수범위 전 오송 MVP 연결 마무리

- 시작 시각: 2026-08-30 18:30:23 +09:00
- 종료 시각: 2026-08-30 23:23:14 +09:00
- 총 소요시간: 293분

주요 작업:
- Copernicus DEM에서 오송 AOI 고도 격자와 저지대 지형 컨텍스트를 생성하고 API/지도/Provenance에 연결했다.
- KMA AWS processed 강우 144 rows를 `/flood/timeline` 실제 관측 응답으로 연결했다.
- 침수흔적도 미확보 상태에서는 노출 KPI를 계속 `PENDING_FLOOD_EXTENT`로 유지했다.
- TODO, Data Guide, manifest, validation report를 산출물 기준으로 갱신했다.

검증 결과:
- Backend tests: `8 passed`
- Frontend build: 통과
- manifest YAML 및 validation JSON 파싱 통과

문제/해결:
- 문제: `rasterio`가 없어 DEM 처리를 못 할 수 있었음. 해결: 기존 설치된 `tifffile`로 GeoTIFF 태그와 픽셀 값을 읽어 처리.

## HRFCO 수위와 SGIS 2023 행정경계 확보

- 시작 시각: 2026-08-31 11:58:00 +09:00
- 종료 시각: 2026-08-31 12:13:34 +09:00
- 총 소요시간: 16분

주요 작업:
- HRFCO OpenAPI로 오송 인근 수위관측소 제원과 2023-07-14 through 2023-07-17 10분 수위 XML을 확보했다.
- 청주시(미호강교) `3011665`를 primary 수위 지점으로 두고, 팔결교 `3011635`와 세종시(미호교) `3011685`를 보조 지점으로 보존했다.
- SGIS OpenAPI로 2023 충북 시군구/청주시 흥덕구 읍면동 경계를 확보하고 오송읍 `33043110`을 `EPSG:4326` processed AOI로 변환했다.
- Backend AOI를 SGIS 2023 오송읍 경계로 연결하고 수위 data status를 추가했다.

검증 결과:
- 수위 processed: 1,299 rows, 최대 수위 10.09m, 3개 관측소 좌표 확인.
- 행정경계 processed: 오송읍 1개 Polygon, 좌표 범위 `127.27565~127.35781`, `36.58285~36.66842`.

문제/해결:
- 문제: SGIS GeoJSON 원본 좌표가 경위도가 아니라 EPSG:5179 평면좌표였음. 해결: processed 생성 시 EPSG:4326으로 명시 변환.

## DSSP-IF-00117 침수흔적도 API 원본 검증

- 시작 시각: 2026-08-31 12:30:00 +09:00
- 종료 시각: 2026-08-31 12:45:00 +09:00
- 총 소요시간: 15분

주요 작업:
- 재난안전데이터공유플랫폼 키 3개 조합을 확인해 `DSSP-IF-00117`에 정상 접근되는 키를 식별했다.
- `DSSP-IF-00117` API 원본 39페이지, 38,003 records를 `data/raw/flood_extent/osong/dssp_if_00117_pages/`에 저장했다.
- 전체 record에서 2023년, 충북, 청주시 `43113` 조건을 검증하고 오송 2023 후보 GeoJSON을 생성했다.

검증 결과:
- `DSSP-IF-00117`: `resultCode=00`, 38,003 records, WKT geometry, raw CRS 추정 `EPSG:3857`.
- 2023년 record 0건, 청주시 `43113`의 2023 후보 0건. 실제 오송 Flood Extent로 연결하지 않음.

문제/해결:
- 문제: 승인 API는 열렸지만 데이터셋에 2023 오송 record가 없음. 해결: 원본 확보와 부재 검증만 기록하고 Flood Extent는 `TEMPORARY`로 유지.

## DSSP-IF-10175/10184 IP 재등록 후 원본 검증

- 시작 시각: 2026-08-31 12:55:00 +09:00
- 종료 시각: 2026-08-31 13:05:00 +09:00
- 총 소요시간: 10분

주요 작업:
- IP 등록 변경 후 재난안전데이터공유플랫폼 키 3개 조합을 다시 확인했다.
- `DSSP-IF-10175` 피해침수 원본 49페이지, 48,050 records를 저장했다.
- `DSSP-IF-10184` 재해구호상황보고 원본 40페이지, 39,188 records를 저장했다.
- 두 데이터셋에서 2023 청주시/오송 후보 record를 검증하고 candidate JSON을 생성했다.

검증 결과:
- `DSSP-IF-10175`: `resultCode=00`, 2023 청주/오송 후보 0건.
- `DSSP-IF-10184`: `resultCode=00`, 2023 청주/오송 후보 0건.
- `DSSP-IF-00247`: available key set 기준 `SERVICE_ACCESS_DENIED`.

문제/해결:
- 문제: API 접근은 열렸지만 두 원본 모두 2023 오송 직접 record가 없음. 해결: 원본 확보와 부재 검증만 기록하고 분석 입력으로 연결하지 않음.

## DSSP 원본 재검증 및 10184 구호상황 후보 복구

- 시작 시각: 2026-08-31 13:05:00 +09:00
- 종료 시각: 2026-08-31 13:18:00 +09:00
- 총 소요시간: 13분

주요 작업:
- 이미 확보한 DSSP raw 원본을 재다운로드 없이 다시 스캔해 발생연도와 자료연도 `+1` 가능성을 확인했다.
- `DSSP-IF-10184`의 행정코드가 `43113`이 아니라 청주 단위 `4311`로 들어오는 것을 반영해 2023년 7월 후보를 재산출했다.
- TODO, source availability manifest, validation report의 10184 상태를 후보 0건에서 후보 확인 상태로 정정했다.

검증 결과:
- `DSSP-IF-00117`: `FLDN_YR=2023` 0건, `FLDN_YR=2024` 0건, 오송 AOI geometry 교차 후보는 과거연도 records만 확인.
- `DSSP-IF-10184`: 2023년 7월 청주 `4311*` 후보 22건, 오송 관련 텍스트 hit 9건.

문제/해결:
- 문제: 10184 첫 검증 필터가 `43113`으로 너무 좁아 청주 단위 구호상황 record를 놓침. 해결: `4311*` + `202307*` 기준으로 재검증하고 Flood Extent가 아닌 구호상황 자료로 분리 기록.

## Safemap 침수흔적도 WMS 스냅샷 연결

- 시작 시각: 2026-08-31 17:30:00 +09:00
- 종료 시각: 2026-08-31 17:48:00 +09:00
- 총 소요시간: 18분

주요 작업:
- 생활안전지도 `IF_0092_WMS` 인증키 재확인 후 오송 bbox 침수흔적도 PNG 스냅샷을 확보했다.
- 로컬 WMS PNG를 FastAPI endpoint로 제공하고 MapLibre image overlay로 표시하도록 연결했다.
- Safemap WMS는 시각 검증용 raster hazard layer로 기록하고, 벡터 Flood Extent 및 노출 KPI 계산은 계속 보류했다.

검증 결과:
- WMS PNG: 1024x1024, 296,634 bytes, 비투명 픽셀 146,863.
- Backend tests: `9 passed`
- Frontend build: 통과

문제/해결:
- 문제: 초기 Safemap 키 호출은 등록 오류였음. 해결: 키 반영 후 재시도해 WMS PNG 응답을 확보하고 실패 HTML 응답은 삭제.

## 오송 관측 컨텍스트 분석 패널 연결

- 시작 시각: 2026-08-31 19:08:46 +09:00
- 종료 시각: 2026-08-31 19:14:30 +09:00
- 총 소요시간: 6분

주요 작업:
- KMA 강우 processed CSV에서 피크 강우량, 피크 시각, 관측소 정보를 API summary에 추가했다.
- HRFCO 10분 수위 processed CSV에서 최고수위와 미호강교 primary 지점 최고수위 정보를 API summary에 추가했다.
- Frontend에 `Observed Hydromet` 패널을 추가해 강우, 미호강 수위, Safemap WMS 침수흔적 연결 흐름을 표시했다.

검증 결과:
- Backend tests: `9 passed`
- Frontend build: 통과

문제/해결:
- 의미 있는 오류 없음.

## 데이터 품질 이슈 관리 문서 추가

- 시작 시각: 2026-08-31 22:53:00 +09:00
- 종료 시각: 2026-08-31 22:56:00 +09:00
- 총 소요시간: 3분

주요 작업:
- 프로젝트 데이터 품질 이슈를 관리할 `docs/data-quality.md` 기준 문서를 추가했다.
- 기관별 snapshot 차이, WMS raster/vector 구분, DSSP 후보 사용 가능성, 강우·수위 시간축 정합성을 초기 이슈로 기록했다.

검증 결과:
- 문서 상단 요약, 이슈별 Status/Impact/원인/영향/해결/검증/근거/Residual risk 항목 포함 확인.

문제/해결:
- 의미 있는 오류 없음.

## TODO 운영 구조 재정리

- 시작 시각: 2026-08-31 22:56:00 +09:00
- 종료 시각: 2026-08-31 23:00:00 +09:00
- 총 소요시간: 4분

주요 작업:
- `TODO.md`를 NOW, BLOCKED, NEXT, LATER, DONE SUMMARY 중심으로 재구성했다.
- Known Issues 반복 항목은 TODO 액션으로 정리하고, 데이터 품질 문제는 `docs/data-quality.md`를 기준 문서로 분리했다.
- 완료 상세는 `WORKLOG.md`와 manifest/report를 기준으로 확인하도록 TODO 상단 안내를 정리했다.

검증 결과:
- NOW 항목을 오송 MVP 완료에 직접 필요한 5개 작업으로 제한.

문제/해결:
- 의미 있는 오류 없음.

## 오송 사고 재현 방식 재정의

- 시작 시각: 2026-08-31 23:03:00 +09:00
- 종료 시각: 2026-08-31 23:08:00 +09:00
- 총 소요시간: 5분

주요 작업:
- 오송 케이스를 Flood Extent 선행 확보형이 아니라 강우·수위·제방붕괴·지하차도 침수 시간축 기반 재현 케이스로 재정의했다.
- TODO의 NOW/BLOCKED/NEXT를 재현 입력값, 사건기록 검증, 후행 Flood Extent 검증 흐름에 맞춰 정리했다.
- 데이터 품질 문서에 사건 시간축 원문 근거 미연결 이슈를 추가하고, 결정 기록에 D-010을 남겼다.

검증 결과:
- 문서 변경만 수행했으며 코드 테스트는 실행하지 않음.

문제/해결:
- 문제: 기존 TODO가 공식 Flood Extent 미확보를 시뮬레이션 차단 요소처럼 표현함. 해결: Flood Extent를 후행 검증자료로 재분류.

## FloodOps 1.0 문서 정의 동기화

- 시작 시각: 2026-08-31 23:23:00 +09:00
- 종료 시각: 2026-08-31 23:26:00 +09:00
- 총 소요시간: 3분

주요 작업:
- README, TODO, PROJECT_PLAN을 `Historical Disaster Reconstruction Digital Twin MVP` 정의에 맞춰 동기화했다.
- FloodOps 1.0/2.0/3.0/Operational Twin 발전 단계를 문서화했다.
- 오송 reference case를 관측자료·사건기록·공간맥락·대응개입 What-if 흐름으로 정리했다.

검증 결과:
- README 첫 화면, TODO NOW, PROJECT_PLAN 정의/Phase 구분에서 같은 MVP 정의 사용 확인.

문제/해결:
- 문제: 기획안 일부에 Flood Extent 선행·일반 시뮬레이션 중심 표현이 남아 있었음. 해결: 사고 재현 중심 표현으로 정리.

## Historical Replay 및 자동 진입차단 Intervention MVP

- 시작 시각: 2026-08-31 23:27:00 +09:00
- 종료 시각: 2026-08-31 23:40:00 +09:00
- 총 소요시간: 13분

주요 작업:
- `/api/events/osong-2023/reconstruction` endpoint를 추가해 7개 사건 replay event, baseline, intervention, provenance, limitations를 반환하도록 구현했다.
- Frontend에 Historical Replay 재생/정지/슬라이더 UI와 Baseline/Intervention 1개 비교 패널을 추가했다.
- Intervention은 수위센서 + 자동 진입차단시설 rule-based scenario로 구현하고, 노출 KPI는 계속 `PENDING_FLOOD_EXTENT`로 유지했다.

검증 결과:
- Backend tests: `11 passed`
- Frontend build: 통과
- API 확인: reconstruction `200`, replay event 7개, response window 8분, scenario `PENDING_FLOOD_EXTENT`
- Dev server 확인: backend health `200`, frontend `200`

문제/해결:
- 문제: 초기 구현은 replay 목록만 표시해 Historical Replay로 보기 부족했음. 해결: 재생/정지 버튼과 timeline slider를 추가.
- 문제: 기존 backend dev server가 이전 코드로 떠 있어 `/reconstruction`이 404를 반환함. 해결: 8000번 backend를 재시작해 새 endpoint 응답 확인.

## React 과제 제출 브랜치 구조 정리

- 시작 시각: 2026-09-01 00:00:00 +09:00
- 종료 시각: 2026-09-01 00:05:00 +09:00
- 총 소요시간: 5분

주요 작업:
- `react-assignment` 브랜치를 생성하고 React 과제용 컴포넌트 구조를 정리했다.
- `App`은 `time`, `scenario`, `layers`, `eventData` 상태를 관리하고 `EventHeader`, `MapPanel`, `Timeline`, `HydrometPanel`, `ScenarioToggle`, `ProvenancePanel`을 조립하도록 정리했다.
- 기존 오송 Historical Replay와 Baseline/Intervention 기능은 유지했다.

검증 결과:
- Frontend build: 통과
- Backend tests: `11 passed`

문제/해결:
- 의미 있는 오류 없음.

## Historical Replay 지도 상태 오버레이 연결

- 시작 시각: 2026-09-01 09:03 +09:00
- 종료 시각: 2026-09-01 09:08 +09:00
- 총 소요시간: 5분
주요 작업:
- Timeline의 `time`과 `scenario` 상태를 `MapPanel`에 전달하도록 연결했다.
- 궁평2지하차도 위치에 replay 위험 상태 GeoJSON 오버레이, 라벨, 선 색상 변화를 추가했다.
- Intervention 모드에서는 08:27 이후 자동 진입차단 상태가 지도에서 별도 색상으로 표시되도록 했다.

검증 결과:
- Frontend build: 통과
- Backend tests: `11 passed`

문제/해결:
- 문제: Play 시 카드만 강조되고 지도는 정적으로 유지됨. 해결: MapLibre `replay-risk` source를 시간 상태에 따라 갱신하도록 연결.

## React 과제 UI 간결화 및 Replay 의미 명시

- 시작 시각: 2026-09-01 09:14 +09:00
- 종료 시각: 2026-09-01 09:21 +09:00
- 총 소요시간: 7분
주요 작업:
- 과제 화면의 기본 KPI를 4개로 줄이고, 기본 지도 레이어를 AOI/하천/도로/건물/지하차도 중심으로 정리했다.
- 사이드바 provenance 설명을 짧은 Map meaning 안내로 바꾸고, 지도 영역과 Timeline 가독성을 개선했다.
- Replay 지도 표시는 실제 침수 확장 범위가 아니라 사건 상태 marker임을 화면에 명시했다.

검증 결과:
- Frontend build: 통과

문제/해결:
- 문제: 과제용 화면이 본 프로젝트 데이터 설명까지 모두 보여줘 복잡했음. 해결: 제출용 핵심 흐름 중심으로 UI 밀도를 낮춤.

## 오송 approximate flood envelope 생성 및 연결

- 시작 시각: 2026-09-01 10:02 +09:00
- 종료 시각: 2026-09-01 10:19 +09:00
- 총 소요시간: 17분
주요 작업:
- KMA 강우, Flood Control Office 수위, Copernicus DEM 저지대 셀, WAMIS 하천, 궁평2지하차도, 사건 시간축으로 temporary approximate flood envelope를 생성했다.
- `approx_flood_envelope` 레이어를 Backend Repository/API/React/MapLibre에 연결하고 Timeline 단계별로 현재 envelope만 표시하도록 했다.
- manifest와 data-quality 문서에 `TEMPORARY`, `DERIVED_APPROXIMATION`, official Flood Extent/2D hydraulics 아님을 기록했다.

검증 결과:
- 생성 파일: `data/processed/osong/osong_approx_flood_envelope_timeline.geojson`
- Feature count: 1127 total, stage counts 36/96/182/241/270/298
- Backend tests: `11 passed`
- Frontend build: 통과

문제/해결:
- 문제: 물리 침수범위 없이 지도 변화가 약했음. 해결: 공식 자료 기반 사건 시간축과 DEM 저지대 조건을 결합한 임시 근사 envelope를 별도 레이어로 추가.
## FloodOps 개발 지침 및 기획 문서 재정렬

- 시작 시각: 2026-09-01 10:45 +09:00
- 종료 시각: 2026-09-01 10:52 +09:00
- 총 소요시간: 7분
주요 작업:
- FloodOps를 `Historical Disaster Reconstruction + Counterfactual Intervention + Decision Support` 중심의 Digital Twin PoC로 재정의했다.
- `README.md`, `docs/PROJECT_PLAN.md`, `docs/DEVELOPMENT_GUIDE.md`, `docs/DECISIONS.md`, `TODO.md`를 같은 정의에 맞춰 정리했다.
- `approx_flood_envelope`를 `TEMPORARY + DERIVED + APPROXIMATION`으로 명시하고 공식 Flood Extent/수심/유속/정밀 예측으로 표현하지 않도록 지침화했다.

검증 결과:
- 문서 전용 변경이며 코드 테스트는 새로 실행하지 않았다.

문제/해결:
- 기존 일부 문서가 인코딩 깨짐 상태라 부분 수정 대신 기준 문서를 새 구조로 교체했다.

## HAND reconstruction 생성 및 지도 연결

- 시작 시각: 2026-09-01 14:32 +09:00
- 종료 시각: 2026-09-01 14:40 +09:00
- 총 소요시간: 8분

주요 작업:
- Copernicus DEM grid, WAMIS river, HRFCO 수위, KMA 강우, 사건 timeline을 이용해 HAND-like reconstruction grid/timeline을 생성했다.
- `hand_reconstruction` 레이어를 Backend Repository/API/React/MapLibre에 연결하고 기본 지도 레이어로 켰다.
- 수위값은 DEM 절대 수면고가 아니라 relative stage pressure로만 사용한다고 manifest와 data-quality 문서에 명시했다.

검증 결과:
- HAND grid 1,280 features, timeline 2,565 features, geometry `Polygon`/`LineString`.
- Backend tests: `11 passed, 1 warning`; frontend build: 통과, Vite chunk size warning만 있음.
- Repository 확인: `TEMPORARY DERIVED_APPROXIMATION 2565 ['LineString', 'Polygon']`.

문제/해결:
- 수위 관측 기준면과 DEM 기준면을 직접 맞출 수 없어 공식 Flood Extent/수심/유속이 아닌 HAND-like derived approximation으로 제한했다.

## Reconstruction envelope method comparison

- 시작 시각: 2026-09-01 14:41 +09:00
- 종료 시각: 2026-09-01 14:48 +09:00
- 총 소요시간: 7분

주요 작업:
- `approx_flood_envelope`와 `hand_reconstruction`의 stage별 feature count 및 EPSG:5179 기준 면적을 비교했다.
- 비교 산출물 `osong_reconstruction_envelope_comparison.json`을 만들고 `/reconstruction` API와 Replay UI에 연결했다.
- `DECISIONS.md`에 기존 단순 근사 방식과 HAND 기반 개선 방식의 차이, 수직 기준면 미가정 원칙을 상세 기록했다.

검증 결과:
- Final stage 면적 비교: approx 30.0194 km2, HAND 54.3915 km2.
- HAND는 모든 stage에서 approx보다 넓게 산출되며, 이는 공식 침수면적이 아니라 method diagnostic으로 기록했다.
- Backend tests: `11 passed, 1 warning`; frontend build: 통과, Vite chunk size warning만 있음.

문제/해결:
- 면적 차이가 실제 피해면적 차이로 오해될 수 있어 UI/manifest/decision 기록에 exposure KPI 근거가 아니라고 명시했다.

## TODO/WORKLOG HAND 상태 동기화

- 시작 시각: 2026-09-01 23:03 +09:00
- 종료 시각: 2026-09-01 23:05 +09:00
- 총 소요시간: 2분

주요 작업:
- HAND reconstruction과 approx envelope 비교는 산출물/API/UI/테스트가 완료된 상태이므로 TODO의 완료 여부를 WORKLOG와 맞췄다.
- 실제 수위 연결은 완료 처리하지 않고, 기준면·제방 붕괴·유량·배수시설·CCTV timestamp 검증 보강 항목으로 남겼다.

검증 결과:
- 문서 상태 동기화 작업이며 코드 테스트는 실행하지 않았다.
