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

## 프론트엔드 컴포넌트 구조 정리

- 시작 시각: 2026-09-01 00:00:00 +09:00
- 종료 시각: 2026-09-01 00:05:00 +09:00
- 총 소요시간: 5분

주요 작업:
- 별도 브랜치에서 프론트엔드 컴포넌트 구조를 정리했다.
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

## UI 간결화 및 Replay 의미 명시

- 시작 시각: 2026-09-01 09:14 +09:00
- 종료 시각: 2026-09-01 09:21 +09:00
- 총 소요시간: 7분
주요 작업:
- 기본 화면의 KPI를 4개로 줄이고, 기본 지도 레이어를 AOI/하천/도로/건물/지하차도 중심으로 정리했다.
- 사이드바 provenance 설명을 짧은 Map meaning 안내로 바꾸고, 지도 영역과 Timeline 가독성을 개선했다.
- Replay 지도 표시는 실제 침수 확장 범위가 아니라 사건 상태 marker임을 화면에 명시했다.

검증 결과:
- Frontend build: 통과

문제/해결:
- 문제: 기본 화면이 데이터 설명까지 모두 보여줘 복잡했음. 해결: 핵심 흐름 중심으로 UI 밀도를 낮춤.

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

## What-if A 차단 시각 분석 API 연결

- 시작 시각: 2026-09-02 23:05 +09:00
- 종료 시각: 2026-09-02 23:25 +09:00
- 총 소요시간: 20분

주요 작업:
- `main` 정리 커밋 이후 `feature/agent-tools` branch를 분기했다. Agent 관련 도메인 API는 이 branch에서 진행한다.
- `POST /api/events/{event_id}/analysis/closure-timing`을 추가했다. 재구성 timeline의 관측 timestamp 간 차이만 계산하는 What-if A 분석이다.
- 산출값: 차단 시점의 사건 상태, 유입/주행불능/완전침수까지 남은 분, Scenario A(08:27 감지 차단) 대비 선행 시간, 5단계 분류.
- 오류 처리를 분리했다. 존재하지 않는 event는 404, reconstruction 미연결 event는 404, 파싱 불가 시각은 422.
- `coverage_status: fallback`과 근거 note를 응답에 포함했다. timeline timestamp의 confidence가 `NEEDS_SOURCE_PAGE`이기 때문이다.
- 테스트 4개를 추가해 총 17개가 통과한다.

검토 결과:
- envelope 면적을 실측한 결과 HAND final stage 54.392 km2가 오송읍 AOI 40.557 km2의 1.34배였다. AOI 내부로 클립해도 19.416 km2로 읍 면적의 47.9%다.
- 이 envelope으로 공간중첩 시 건물 11,591동(45.8%), 도로 659.5 km(50.5%)가 영향으로 집계된다. 절대 수치를 근거로 쓸 수 없어 `docs/data-quality.md`에 DQ-008로 기록했다.
- AOI 자체는 유지한다. AOI는 데이터 확보 범위이고, 영향 분석은 사건 영향권이라는 더 좁은 범위를 별도로 두어야 한다.

## What-if B 유입 지연 가정 API 연결

- 작업일: 2026-09-02

주요 작업:
- `POST /api/events/{event_id}/analysis/inflow-delay`를 추가했다.
- 사용자 입력 `delay_minutes`(0~180분)를 받아 `underpass_inflow`, `unsafe_driving`, `full_inundation` 시각을 동일한 Δt만큼 이동한다.
- 차수벽 높이, 유량, 통수단면, 조도 자료가 없어 유입량·수심을 계산하지 않고 timeline-shift 가정으로 제한했다.
- `coverage_status: fallback`, baseline/shifted milestone, assumptions, limitations를 응답에 포함했다.

검증 결과:
- What-if B API 테스트를 추가해 Backend tests `20 passed, 1 warning`을 확인했다.
- 음수 및 180분 초과 입력은 422로 거부한다.
- 오송 외 reconstruction 미연결 event는 404로 처리한다.

남은 작업:
- React에서 해당 API를 호출하는 연결은 별도 작업으로 진행한다.
- DQ-008 영향 지표는 공식 침수범위가 확보되기 전까지 fallback/diagnostic 결과로만 노출한다.

## Agent Tool wrapper 등록

- 작업일: 2026-09-02

주요 작업:
- `/api/agent/tools`에서 실제 실행 가능한 Tool catalog를 제공한다.
- `/api/agent/tools/{tool_name}`에서 event metadata, historical reconstruction, What-if A/B 분석을 dispatch한다.
- Tool wrapper는 기존 repository/service를 호출하며 GIS 파일 직접 접근, 외부 API 임의 호출, 미확인 수치 생성을 하지 않는다.
- 분석 결과는 기존 Pydantic 결과 스키마로 검증한 뒤 반환해 일반 API와 provenance/limitation 계약을 유지한다.

검증 결과:
- Agent Tool catalog, What-if B dispatch, 미등록 Tool 거부 테스트를 추가했다.
- Backend tests `23 passed, 1 warning`을 확인했다.

남은 작업:
- 자연어 intent 분석과 사용자 친화적 결과 요약은 Tool 계약이 안정화된 뒤 추가한다.

## Agent multi-tool workflow orchestration

- 작업일: 2026-09-02

주요 작업:
- `POST /api/agent/workflows`를 추가해 명시적 workflow를 실행한다.
- `closure_timing`과 `inflow_delay` workflow는 `get_event` → `get_reconstruction` → 분석 Tool 순서로 호출한다.
- 각 단계의 Tool 이름, 실행 순서, 결과 key를 `tool_calls` trace로 반환한다.
- 현재 workflow 선택은 명시적 enum으로 제한하고, 자연어 intent planning은 다음 단계로 남겼다.

검증 결과:
- closure-timing/inflow-delay workflow 연속 호출 테스트를 추가했다.
- Backend tests `25 passed, 1 warning`을 확인했다.

남은 작업:
- 자연어 요청을 workflow와 파라미터로 변환하는 intent planning을 추가한다.
- Agent 응답에 데이터 근거와 한계를 사용자 친화적으로 요약하는 단계를 추가한다.

## Agent deterministic intent planning

- 작업일: 2026-09-02

주요 작업:
- `POST /api/agent/plan`을 추가해 자연어 요청을 등록된 workflow 선택 계획으로 변환한다.
- 차단 시각, 유입 지연, 반경별 exposure inventory, 역사 재생 요청을 제한된 marker와 정규식으로 결정적으로 매핑한다.
- 메시지에서 인식한 시각·분·반경만 파라미터로 전달하고, 값이 없으면 workflow 기본값 사용을 assumptions에 기록한다.
- 복수 분석 의도는 `NEEDS_CLARIFICATION`, 등록되지 않은 예측·임의 분석 요청은 `UNSUPPORTED`로 반환한다.
- `situation` workflow를 추가해 `get_event` → `get_reconstruction` 상황 조회 경로도 명시적으로 실행할 수 있게 했다.

검증 결과:
- 한국어 시각/반경 추출, 복수 의도 명확화, 미지원 요청 거부, situation workflow 테스트를 추가했다.
- Backend tests `36 passed, 1 warning`을 확인했다.

남은 작업:
- Planner는 실행하지 않는 계획 단계이므로 React에서 계획 확인 후 workflow를 실행하는 UI 연결이 필요하다.
- 실제 결과를 연구자용 요약으로 변환할 때 provenance와 limitations를 누락하지 않는 출력 단계를 추가한다.

## React Agent plan/workflow integration

- 작업일: 2026-09-02

주요 작업:
- `src/api.ts`에 Agent intent plan/workflow API client와 타입을 추가했다.
- React 화면에 자연어 요청 입력, 계획 상태/파라미터/tool sequence 확인, 명시적 workflow 실행 버튼을 연결했다.
- 실행 결과에는 tool trace와 서버가 반환한 assumptions/limitations를 표시한다.
- 브라우저에서 침수 수치나 영향 지표를 계산하지 않고, 기존 FastAPI domain result를 그대로 표시한다.

검증 결과:
- `npm run build` 통과.
- Vite는 MapLibre를 포함한 약 994KB JS chunk에 대해 code-splitting 권고 warning을 출력했지만 빌드는 성공했다.

남은 작업:
- Agent 결과를 provenance/source별 연구자용 요약으로 재구성하는 표현 계층을 추가한다.
- 대형 MapLibre 번들은 기능 안정화 이후 dynamic import/code splitting을 검토한다.

## Agent workflow provenance propagation

- 작업일: 2026-09-02

주요 작업:
- workflow 응답에 `provenance`, `coverage_status`, `coverage_note`를 추가했다.
- closure-timing/inflow-delay는 연결된 reconstruction provenance를 전달한다.
- exposure inventory는 envelope을 호출하지 않고 inventory source 목록을 provenance로 전달한다.
- React 결과 카드에서 source/snapshot/status와 coverage 설명을 함께 표시한다.

검증 결과:
- Backend tests `36 passed, 1 warning`을 재확인했다.
- `npm run build` 통과를 재확인했다.

남은 작업:
- provenance와 분석 결과를 연구 보고서 형식의 간결한 요약으로 변환하는 단계를 추가한다.

## LLM intent planner 최소 연결

- 시작 시각: 2026-09-03 00:00 +09:00
- 종료 시각: 2026-09-03 00:20 +09:00
- 총 소요시간: 20분

주요 작업:
- `backend/app/llm_planner.py`를 추가했다. Anthropic Messages API의 structured output(`messages.parse`)으로 workflow 라우팅과 파라미터 추출만 수행한다.
- LLM에게 분석을 시키지 않는다. system prompt에서 사상자·피해액·침수심·침수면적 요청은 `unsupported`로 라우팅하도록 지시했다.
- 모델이 반환한 파라미터를 `_validated_parameters`에서 분석 endpoint와 동일한 범위로 재검증한다. 범위를 벗어나면 ValueError로 폴백한다.
- `POST /api/agent/plan`에 `planner` 선택을 추가했다. `auto`는 LLM 실패 시 결정론 planner로 폴백하고, `llm`은 503으로 실패를 드러낸다.
- `GET /api/agent/planner-status`를 추가해 API 호출 없이 SDK/자격증명 가용성을 확인한다.
- `backend/requirements.txt`에 `anthropic==1.3.0`, `.env.example`에 `ANTHROPIC_API_KEY`를 추가했다.
- 테스트 5개를 추가해 총 41개가 통과한다. 네트워크나 API 키 없이도 전부 통과한다.

검증 결과:
- 자격증명이 없는 현재 상태에서 `planner=auto`는 결정론 planner로 폴백하며 `closure_times: ["08:25"]`를 그대로 추출한다.
- LLM planner를 모킹해도 최종 수치는 결정론 Tool에서 나온다. 08:25 차단 시 유입까지 2분은 동일하다.

## Agent intent evaluation set

- 작업일: 2026-09-03

주요 작업:
- `backend/tests/agent_intent_cases.json`에 한국어 질문 15개와 기대 status/workflow/파라미터/Tool sequence를 고정했다.
- 상황 조회, 차단 시각, 유입 지연, 반경별 재고, unsupported, 복수 의도 명확화 케이스를 포함했다.
- 피해액·사상자·침수심·예측 요청은 분석 marker가 함께 있어도 `UNSUPPORTED`가 우선되도록 planner를 보강했다.

검증 결과:
- 평가셋 `15 passed`.

## Agent compare_scenarios Tool

- 작업일: 2026-09-03

주요 작업:
- 등록된 baseline과 closure timing 또는 inflow delay 시나리오를 비교하는 `compare_scenarios` Tool을 추가했다.
- closure timing은 감지 기반 baseline 대비 선행 시간을, inflow delay는 지연 0분 baseline 대비 milestone 이동을 반환한다.
- reconstruction provenance, coverage status/note, assumptions/limitations를 결과에 포함한다.
- 공식 Flood Extent 기반 피해율·피해액·사상자·침수심 비교는 범위에서 제외했다.

검증 결과:
- closure timing baseline 비교와 inflow delay 0분 baseline 포함 테스트를 추가했다.
- Agent 관련 선택 테스트 `33 passed`를 확인했다.

남은 작업:
- `compare_scenarios`를 자연어 planner workflow까지 확장할지는 실제 시연 흐름을 확인한 뒤 결정한다.

## Agent 패널 브라우저 시연 검증 및 결과 표시 수정

- 시작 시각: 2026-09-03 01:10 +09:00
- 종료 시각: 2026-09-03 01:45 +09:00
- 총 소요시간: 35분

주요 작업:
- 백엔드와 Vite dev 서버를 띄우고 실제 브라우저(Chromium)로 Agent 패널 전 구간을 조작해 검증했다.
- 검증 결과 결과 패널에 provenance, coverage, 가정, 한계는 표시되지만 **분석 수치 자체가 표시되지 않는 문제**를 발견했다. 자연어 질문의 답이 화면에 없는 상태였다.
- `AgentFindings` 컴포넌트를 추가해 workflow별 결과 표를 렌더링했다. closure_timing은 차단 시각별 잔여 시간, inflow_delay는 기준/이동 시각 대비, exposure_inventory는 반경별 재고, situation은 재구성 타임라인을 표시한다.
- planner 배지가 `DETERMINISTIC PLAN`으로 하드코딩되어 있어 LLM planner 사용 시에도 결정론으로 표시되던 문제를 수정했다. `planner_used`에 따라 배지가 바뀌고 폴백 사유를 함께 노출한다.
- `AgentIntentPlanResult` 타입에 `planner_used`, `planner_note`를 추가했다.

검증 결과 (실제 브라우저):
- closure_timing: 08:25 / 08:30 / 08:35 세 시각이 한 번에 추출되어 표로 표시된다. 08:25는 유입까지 2분, 완전침수까지 15분, 감지차단 대비 2분 선행이다.
- inflow_delay: 10분 지연 가정 시 유입 08:27 -> 08:37, 주행불능 08:35 -> 08:45, 완전침수 08:40 -> 08:50으로 표시된다.
- exposure_inventory: 반경 500m 건물 424동 도로 7.595km, 반경 1000m 건물 1,536동 도로 48.772km, 시설 4개.
- situation: 재구성 타임라인 7단계가 근거 상태(NEEDS_SOURCE_PAGE)와 함께 표시된다.
- 거절: "사망자가 몇 명 줄었을까" 질문은 UNSUPPORTED로 처리되고 실행 버튼이 나타나지 않는다.
- 페이지 JS 오류 0건.

남은 이슈:
- MapLibre 콘솔 경고: `layers.replay-risk-label.layout.text-field`가 스타일의 `glyphs` 속성을 요구한다. 리플레이 위험 라벨 레이어가 렌더되지 않는다. 별도 수정이 필요하다.
- 프론트엔드는 `localhost:5173`으로만 접속된다. `127.0.0.1:5173`은 응답하지 않는다.

## Dark console UI 진행 현황

- 작업일: 2026-09-04
- 브랜치: `ui/dark-console`
- 상태: 진행 중 / 미커밋

주요 작업:
- `src/dark/DarkConsole.tsx`, `src/dark/CrossSection.tsx`, `src/dark/dark.css`를 추가해 어두운 관제 화면 미리보기를 구성했다.
- `App.tsx`에 light/dark UI 전환과 `localStorage` 키 `floodops-ui`를 연결했다.
- 기존 backend 데이터와 API를 재사용해 이벤트 단계, MapLibre 지도, exposure inventory, 단면도, Agent 결과를 한 화면에 배치했다.
- `src/api.ts`와 `src/types.ts`에 반경별 exposure inventory 조회 client/type을 추가했다.
- 기존 light UI는 유지하고 dark UI를 별도 presentation layer로 추가하는 방향으로 정리했다.

현재 판단:
- 핵심 MVP 기능(역사 재구성, What-if A/B, Agent workflow, LLM planner fallback, scenario API)은 구현 완료 상태다.
- dark console은 시각화와 발표용 흐름을 보강하는 진행 중 작업이며, 기능 완료나 운영형 FloodOps로 표시하지 않는다.

문서화 시점 검증:
- `npm run build` 통과. Vite 번들 500 kB 초과 경고만 확인되었고 build는 성공했다.
- `backend`에서 `pytest -q` 실행 결과 `58 passed`.
- `git diff --check` 통과.

남은 작업:
- 실제 브라우저 smoke test로 dark UI의 지도/레이어/반응형 표시를 확인한다.
- 기존 Agent 시연에서 확인된 MapLibre glyph 경고와 `localhost`/`127.0.0.1` 접속 차이를 정리한다.
- provenance, coverage status, approximation/limitation 문구를 최종 점검한 뒤 UI 변경을 기능 단위로 커밋한다.

추가 마감 작업:
- 좁은 화면에서 side/map/detail을 세로로 전환하는 반응형 CSS를 `dark.css`에 추가했다.
- 라이트 UI의 `replay-risk-label`이 사용할 glyphs URL을 MapLibre style에 연결했다. 실제 브라우저에서 네트워크 로딩까지 재확인하는 것은 남겨두었다.
- `CrossSection.test.ts`를 추가해 지하차도 중심의 HAND 셀 매칭과 stage 값 전달, 매칭 셀 부재 처리를 검증했다.

최종 검증:
- `npm test -- --run`: 1 file, 2 tests passed.
- `npm run build`: 통과. Vite large-chunk warning만 남아 있다.
- backend `pytest -q`: 58 passed (문서화 시점 직전 실행 결과).

현재 남은 작업:
- 이 세션에서는 사용 가능한 브라우저가 없어 실제 화면 smoke test를 수행하지 못했다.
- 브라우저 연결 후 dark console의 지도 렌더링, 단계 이동, 단면도 애니메이션, Agent 실행, 반응형 레이아웃을 확인한다.
- 확인이 끝나면 `README`, `TODO`, `WORKLOG`, `PROJECT_PLAN`과 UI 소스를 함께 기능 단위로 커밋한다.

## Dark console replay 동작 보완

- 작업일: 2026-09-04

주요 작업:
- 다크 콘솔의 재생 버튼과 스페이스바가 공통 `App.tsx`의 `replayPlaying` 상태를 사용하도록 확인·보완했다.
- 재생 중 `time`이 증가하면 사건 단계, HAND envelope 필터, 현재 마커, 단면도 수위/임계선이 함께 갱신된다.
- 마지막 단계에서 재생을 다시 누르면 0단계부터 다시 시작하도록 `togglePlayback`을 추가했다.
- 단계 버튼·좌우 이동·슬라이더 조작은 재생을 일시정지하도록 유지했다.

검증 결과:
- `npm test -- --run`: 1 file, 2 tests passed.
- `npm run build`: 통과. Vite large-chunk warning만 남아 있다.
- 실제 브라우저 자동 조작은 현재 세션에 브라우저가 없어 아직 수행하지 못했다.

## HAND 단면도 실측값·파생값 구분 보완

- 작업일: 2026-09-04

확인 내용:
- `observed_water_level_m`가 홍수통제소 관측 수위이며, 지하차도 중심 HAND 셀에서 단계별로 9.85 m, 9.96 m, 10.01 m, 10.01 m, 10.03 m로 확인된다.
- `relative_water_level_rise_m`는 기준 관측 수위와의 차분이다. 마지막 단계 값은 2.34 m이며, 파란 영역은 이 값을 표현한다.
- `hand_threshold_m`는 실측 수위가 아니다. 생성식 `relative_rise + breach_boost_m`에 따른 HAND 선택 임계이며, 마지막 단계 5.54 m는 `2.34 m + 3.20 m`이다.
- `hand_m`는 DEM에서 계산한 배수 기준면 대비 셀 상대고도이고, `mean_elevation_m`/`local_drainage_elevation_m`는 DEM 표고 파생값이다.

UI 보완:
- 단면도에 실측 관측 수위, 실측값 차분, 선택 임계(파생), 임계 추가분(파생)을 별도 카드로 표시했다.
- 파란 영역과 점선의 의미를 범례와 한계 문구에 명시했다.

검증:
- `npm test -- --run`: 2 passed.
- `npm run build`: 통과.

## Scenario 비교 탭 추가

- 작업일: 2026-09-04

주요 작업:
- 정보량이 많은 관제 화면과 시나리오 해석 화면을 `관제 화면` / `Scenario 비교` 탭으로 분리했다.
- 비교 화면에서 API의 baseline states와 intervention metadata를 사용해 원시나리오와 감지 자동차단 개입을 카드·비교 매트릭스로 표시한다.
- 유입 시작, 주행불능, 완전침수까지의 시간과 개입 트리거를 함께 보여준다.
- 같은 사건 조건을 유지하므로 침수 진행 자체는 바뀌지 않고, 개입 시나리오에서 신규 차량 진입 차단 상태가 바뀐다는 점을 명시했다.
- 공식 침수범위, 침수심, 사상자, 피해액, 공식 피해 감소율은 비교 대상에서 제외했다.
- 관제 화면에서는 기존 Scenario 토글을 제거해 지도와 Agent의 시각적 밀도를 낮췄다.

검증:
- `npm test -- --run`: 2 passed.
- `npm run build`: 통과. Vite large-chunk warning만 남아 있다.

## Dark console 판단 탭·지도 정리

- 작업일: 2026-09-04

주요 작업:
- 왼쪽 패널을 `자료 우선순위 → 사건 단계 → 시나리오/레이어 → 반경별 노출 재고 → Agent workflow` 순서로 재구성했다.
- 즉시 대응 판단에는 현재 단계와 대응 여유가 가장 중요하다고 판단하고, 그 다음 공간 상태(HAND 재구성), 마지막으로 반경별 재고를 배치했다.
- 반경별 노출 재고는 500m를 우선 요약하고 전체 반경 표를 왼쪽에 넣었다. 해당 값은 반경 내 시설 재고이지 침수 영향 추정치가 아니다.
- Agent를 오른쪽 하단의 보조 영역에서 왼쪽 판단 탭으로 이동하고, 차단 시각·유입 지연·500m 재고 추천 질문을 추가했다.
- 지도 위 관측 조건 카드와 중복 Agent/재고 영역을 제거하고, 지도에는 재생 컨트롤·최소 범례·핵심 마커만 남겼다.
- 오른쪽 상세 패널은 HAND 단면도와 관측 근거로 역할을 분리했다.

검증:
- `npm test -- --run`: 2 passed.
- `npm run build`: 통과.
- 브라우저 연결은 현재 세션에서 사용할 수 없어 실제 시각적 QA는 보류 상태다.

## FloodOps 로컬 포트 고정 및 로딩 오류 해결

- 작업일: 2026-09-04

문제:
- 기존 프론트 환경변수 `VITE_API_BASE=http://localhost:8000`가 다른 프로젝트의 Basement Flood Screening API를 가리키고 있었다.
- 해당 서버에는 FloodOps `/api/events`가 없어 404가 발생했고, Vite는 5173 사용 시 5174로 자동 이동할 수 있었다.

해결:
- `vite.config.ts`에 `host: true`, `port: 5173`, `strictPort: true`를 고정했다.
- 로컬 FloodOps API 주소를 `http://localhost:8033`으로 정리했다. `.env`와 `.env.example`, `src/api.ts` fallback, README 로컬 실행 안내를 동기화했다.
- Docker 실행은 컨테이너 내부 구성상 기존 backend `8000` 매핑을 유지하고, 로컬 실행과 구분했다.

검증:
- `http://localhost:5173/` 응답 200.
- Vite 변환 `src/api.ts`가 `localhost:8033`을 사용함을 확인.
- `http://localhost:8033/health` 응답 200.
- `http://localhost:8033/api/events` 응답 200, 사건 5건.

## Scenario 비교 페이지 구현

- 작업일: 2026-09-04

주요 작업:
- DarkConsole 상단에 `관제 화면` / `Scenario 비교` 탭을 추가했다.
- 정보량이 많은 시나리오 설명을 별도 비교 화면으로 분리해 관제 지도 화면의 밀도를 낮췄다.
- baseline states와 intervention metadata에서 유입·주행불능·완전침수 시각, 차단 트리거, 대응 여유를 읽어 비교 카드와 매트릭스를 구성했다.
- 비교 화면에서 같은 사건 조건과 위험 진행은 유지되고 신규 차량 진입 차단 상태만 바뀐다는 판단을 명시했다.
- 공식 침수범위, 침수심, 사상자, 피해액, 공식 피해 감소율은 계산하지 않는다.

검증:
- `npm test -- --run`: 2 passed.
- `npm run build`: 통과. Vite large-chunk warning만 남아 있다.

## Dark console Agent·레이어 정보 밀도 조정

- 작업일: 2026-09-04

주요 작업:
- 기본 화면에서 `Exposure inventory · secondary` 표를 제거했다. 반경별 재고는 핵심 대응 판단보다 보조 자료이므로 Agent의 `500m 재고` 추천 질문으로 필요할 때 조회하도록 정리했다.
- Layers 토글은 삭제하지 않고 `지도 레이어 표시 설정` 접이식으로 변경했으며 기본값은 닫힘이다.
- Agent를 왼쪽 판단 탭의 우선순위 카드 바로 아래로 이동해 한 화면에서 접근하기 쉽게 했다.
- 지도 위 관측 조건 오버레이를 유지하지 않고 왼쪽/오른쪽 근거 패널로 분산해 중앙 지도를 단순화했다.

검증:
- `npm test -- --run`: 2 passed.
- `npm run build`: 통과.

## Dark console HAND 단면도 연결

- 작업일: 2026-09-04

주요 작업:
- `CrossSection.tsx`가 존재하지만 화면에서 렌더링되지 않던 누락을 확인하고 `DarkConsole.tsx` 우측 상세 패널에 연결했다.
- `hand_reconstruction` 레이어의 `hand_m`, `hand_threshold_m`, `relative_water_level_rise_m`, `observed_water_level_m`, `mean_elevation_m`, `local_drainage_elevation_m`, `stage_hourly_rainfall_mm`를 단면도에 전달한다.
- 단계 이동 시 관측 기준 대비 상승분과 선택 임계선이 전환되고, SVG 물 영역에 transition/wave animation을 적용했다.
- 실제 침수심이나 DEM 절대 수면고로 오해하지 않도록 DQ-007 한계 문구를 단면도 안에 고정했다.

검증 결과:
- HAND API 응답: 총 2,565개 형상(Polygon 2,561개, LineString 4개).
- 단면도 필수 속성 확인: `hand_m`, `hand_threshold_m`, `relative_water_level_rise_m`, 관측 수위·표고·강우 속성.
- 지하차도 중심과 매칭되는 HAND 셀: 5개 단계.
- `npm run build` 통과.

남은 작업:
- 브라우저 세션 연결 후 단면도 실제 렌더링, 단계 이동, 작은 화면 레이아웃을 확인한다.

## 보고서용 인사이트 정리

- 작업일: 2026-09-04
- `docs/report-insights.md`에 오늘 구현에서 도출된 데이터 품질, UI 우선순위, Agent 역할, Scenario 비교, Replay, 실행 환경 고정 관련 인사이트를 정리했다.
- 특히 관측 수위와 DEM 표고의 기준면이 다를 수 있으므로, 단면의 파란 영역을 실제 침수심이 아닌 관측 수위 상승분 기반 대리 표현으로 설명해야 한다는 점을 명시했다.
- 개입 시나리오는 현재 수리학적 위험 자체의 감소가 아니라 차량 자동 차단 등 운영 상태의 변화를 재현하므로, 검증 전에는 `risk_reduction`을 실제 피해 감소량처럼 표현하지 않도록 기록했다.
- 데이터 엔지니어링 관점에서 API 응답 타입, 레이어 메타데이터, 원시·파생·대리값의 역할, Replay 단계의 단일 기준, 로컬 API 포트를 정리했다.

## Scenario 비교 2분할 지도

- 작업일: 2026-09-04
- Scenario 비교 화면에 원시나리오와 선택 시나리오 지도를 좌우 2분할로 추가했다.
- 두 지도는 동일한 Replay 단계와 중심 좌표를 공유하고, Baseline은 위험 envelope를 붉은색으로, Intervention은 운영 개입 상태를 청록색으로 강조한다.
- Intervention 지도는 침수 물리량이 줄었다고 표현하지 않고, 임계 도달 이후 신규 차량 진입 차단이라는 운영 상태만 시각화한다.
- 지도에 공통 공간 레이어를 유지해 시나리오 간 공간 차이를 바로 비교할 수 있도록 했으며, 작은 화면에서는 세로 1열로 전환한다.

검증 결과:
- `npm test -- --run`: 2 passed.
- `npm run build`: 통과. Vite large chunk warning만 남아 있다.
- 브라우저 세션 자동 검증: 사용 가능한 브라우저 세션이 없어 미실행.

## 인사이트 탭 추가

- 작업일: 2026-09-04
- 세 번째 상단 탭 `인사이트`를 추가하고, 오늘 정리한 데이터 엔지니어링 조정·데이터 신뢰도·판단 우선순위·개입 해석·검증 한계를 화면 안에서 읽을 수 있도록 구성했다.
- 세 탭의 역할을 `관제 화면(현재 상태) → Scenario 비교(개입 전후) → 인사이트(근거와 한계)`로 분리해 정보 과밀을 줄였다.
- 보고서 문서에도 세 탭을 업무 흐름으로 설명하는 내용을 반영했다.

## 관제 화면 정보 패널 너비 조절

- 작업일: 2026-09-04
- 탭 1에서 왼쪽 판단/Replay 패널과 오른쪽 HAND/근거 패널의 너비를 각각 드래그로 조절할 수 있게 했다.
- 왼쪽은 220~460px, 오른쪽은 260~520px 범위로 제한해 지도 영역이 지나치게 좁아지지 않도록 했다.
- 조절 핸들은 키보드 방향키도 지원하며, 패널 너비가 바뀔 때 MapLibre 지도 크기를 다시 계산한다.
- 900px 이하에서는 세로형 레이아웃을 사용하므로 조절 핸들을 숨긴다.

## Scenario 비교 Evidence 고정 및 Replay 추가

- 작업일: 2026-09-04
- 탭 2에도 탭 1과 동일한 Replay 재생·일시정지·이전/다음 단계·슬라이더를 추가했다.
- 비교 화면을 `원시 지도 40% + 선택 지도 40% + Evidence/HAND 레일 10%` 성격으로 재배치했다.
- Evidence & HAND section은 왼쪽 고정 레일로 옮겨 현재 Replay 단계의 단면·강우·수위·DEM·공식 침수범위 상태를 계속 보여준다.
- 작은 화면에서는 고정 레일을 상단으로 전환하고 두 지도를 세로로 배치한다.

## 관제 상단 Agent 배치 및 정보 밀도 조정

- 작업일: 2026-09-04
- 탭 1 상단의 현재 단계·대응 여유·건물·도로·시설 요약 칩을 제거하고, 그 공간에 축약형 Agent 입력창을 배치했다.
- 왼쪽 패널의 중복 Agent 블록은 제거해 Replay와 판단 우선순위에 집중하도록 했다.
- 긴 `Evidence & HAND section`은 탭 1에서 제거하고, 오른쪽에는 현재 단계 판단 요약과 인사이트 이동 링크만 남겼다.
- 상세 관측값·HAND 단면은 탭 2의 고정 Evidence 레일과 탭 3 인사이트에서 확인하도록 정보 위치를 재배치했다.
- 전체 관제 루트는 고정 viewport 안에서 동작하도록 유지해 브라우저 확대 75%에서도 페이지 하단 스크롤이 생기지 않게 조정했다.

## Evidence & HAND section 복원 및 공통화

- 작업일: 2026-09-04
- 탭 1 오른쪽 패널의 `Evidence & HAND section`과 `관측 근거 · Gungpyeong 2 Underpass 단면`을 원래 구성으로 복원했다.
- 동일한 `EvidenceHandSection` 컴포넌트를 탭 2의 왼쪽 고정 Evidence 레일에서도 재사용해 단면·관측 수위·강우·관측 기간·공식 침수범위 표시가 일치하도록 했다.
- 단면 설명의 실측/파생/대리값 구분과 DQ-007 한계 문구를 두 탭에서 같은 데이터 흐름으로 유지했다.

## Agent 시각적 강조

- 작업일: 2026-09-04
- 상단 Agent를 일반 입력창처럼 보이지 않도록 `FLOOD AGENT` 배지, 근거 기반 조치 질의 설명, 상태 표시, 강조 테두리를 추가했다.
- 축약형 Agent에서도 계획·실행 버튼과 처리 상태를 한 줄에서 확인할 수 있도록 해 관제 화면의 핵심 기능임을 명확히 했다.

## Evidence 설명 문구 축소

- 작업일: 2026-09-04
- `Evidence & HAND section`의 제목, 단면 그래프, 관측·파생값은 유지했다.
- 사용자가 제거를 요청한 긴 DQ-007 설명 문장과 envelope 포함 상태 문구는 화면에서 제거해 시각적 밀도를 낮췄다.
- 탭 2의 Evidence는 선택 시나리오 색상으로 표시하되, 물리 모델이 바뀌지 않는 관측값은 원시 관측값 그대로 유지했다.

## 탭 2 Evidence 오른쪽 고정 레일 전환

- 작업일: 2026-09-04
- 탭 2의 좌우 2분할 시나리오 지도를 먼저 배치하고, `Evidence & HAND section`을 오른쪽 고정 레일로 이동했다.
- 원시 지도·선택 지도는 40:40 공간을 유지하고, Evidence는 현재 Replay 단계의 관측 근거와 선택 시나리오 색상을 고정 표시한다.

## Agent 입력창 톤 조정

- 작업일: 2026-09-04
- Agent 입력 예시를 `예: 08:25에 지하차도를 차단했으면?`으로 통일했다.
- Agent 아이콘을 제거하고 `FLOOD AGENT` 텍스트 라벨과 근거 기반 질의 설명을 유지했다.
- 청록 네온 대신 채도 낮은 앰버·슬레이트 톤과 약한 테두리를 사용해 지도 위험 레이어와 Agent 영역의 시각적 우선순위를 분리했다.

## Scenario 비교 화면 시각적 재배치

- 작업일: 2026-09-04
- 비교 탭의 우선순위를 카드에서 지도 중심으로 변경했다.
- 화면 순서를 `대형 2분할 지도 → 원시/개입 요약 카드 → 비교 매트릭스 → 해석`으로 재배치했다.
- 두 지도는 데스크톱에서 화면 높이의 절반 이상을 사용하고, 모바일에서는 한 지도씩 세로로 크게 표시한다.
- 지도 아래 정보는 카드·표·콜아웃으로 계층화해, 공간 차이를 먼저 보고 수치와 해석을 이어서 확인하도록 조정했다.

## Agent 거절 응답에 인접 질문 추가 및 LLM 폴백 시간 제한

- 작업일: 2026-09-06
- 커밋: `ab333d0`

주요 작업:
- `AgentIntentPlanResult`에 `suggestions` 필드를 추가하고, `UNSUPPORTED`는 전체 목록을 `NEEDS_CLARIFICATION`은 감지된 후보 워크플로만 제시하도록 했다. `READY`는 빈 배열이다.
- `GET /api/agent/examples`를 신설해 UI 시작 칩과 거절 시 제안이 같은 목록을 쓰도록 단일 출처화했다.
- LLM 요청에 `timeout` 10초(`AGENT_LLM_TIMEOUT_SECONDS`)와 `max_retries=0`을 적용했다.
- `App.tsx`와 `DarkConsole.tsx`에 시작 칩과 제안 칩을 연결하고, 하드코딩돼 있던 `QUICK_REQUESTS`는 오프라인 폴백으로만 남겼다.

검증 결과:
- Backend tests: `64 passed` (기존 58에서 6개 추가)
- Frontend build: 통과
- 예시 질문 4개가 각각 `closure_timing` / `inflow_delay` / `exposure_inventory` / `situation`으로 라우팅되는 것을 확인
- 불통 주소(`10.255.255.1:81`)를 향해 `AGENT_LLM_TIMEOUT_SECONDS=3`으로 띄운 뒤 `/api/agent/plan` 응답까지 3,379ms 측정. `planner_used`가 `deterministic`으로 폴백됨

문제/해결:
- 문제: 거절 응답이 `reason`만 주고 끝나 사용자가 무엇을 물어야 하는지 알 수 없었다. 본선 시연에서 심사위원이 임의 문장을 입력하면 `UNSUPPORTED`만 뜨고 막다른 길이 된다.
  해결: `suggestions`를 함께 반환하고 UI에서 클릭 가능한 칩으로 표시했다. 칩 문구가 실제로 라우팅되는지를 테스트로 고정해, 답할 수 없는 문구를 칩에 넣으면 CI가 막도록 했다.
- 문제: 규칙 플래너 폴백 로직은 이미 있었는데 망이 끊기면 동작하지 않았다. anthropic SDK 기본값이 timeout 10분 + 재시도 2회여서, 폴백에 도달하기 전에 요청이 멈춘 채로 남는다. 폴백 코드가 있어도 도달하지 못하면 없는 것과 같다.
  해결: 명시적 timeout과 재시도 0회를 적용했다. 기본 10초로 두고 현장 네트워크가 불안하면 환경변수로 낮춘다.
- 검토했다가 버린 방법: 칩 문구를 프론트엔드에 그대로 하드코딩하는 안. 백엔드 `suggestions`와 두 곳에서 관리하게 되어 문구가 갈라질 수 있어 버렸다. 대신 엔드포인트 하나를 늘렸다.

## 공개 저장소에서 과제·초안 맥락 제거

- 작업일: 2026-09-06
- 커밋: `25ddd7e`

주요 작업:
- 헤더 브랜드 라벨을 `REACT ASSIGNMENT`에서 `DECISION SUPPORT PoC`로 교체했다.
- CSS 규칙이 없던 `assignment-metrics` 클래스명을 `summary-metrics`로 정리했다.
- `.gitignore`가 로컬 초안을 파일명 대신 `docs/local/` 디렉터리 단위로 제외하도록 바꾸고, 제출서식 문서를 그 아래로 옮겼다.
- `WORKLOG.md`와 `docs/report-insights.md`의 과제·시연 맥락 문구를 일반 표현으로 교체했다.

검증 결과:
- 추적 파일 전수 검색에서 공모전·과제 관련 어휘 0건
- Backend tests: `64 passed`, Frontend build: 통과

문제/해결:
- 문제: 화면 좌상단에 `REACT ASSIGNMENT` 배지가 실제로 렌더링되고 있었다. 문서가 아니라 UI 문자열이라 시연 첫 화면에서 그대로 보인다.
  해결: 제품 정체에 맞는 라벨로 교체했다.
- 문제: `.gitignore`에 제외 대상 파일명이 그대로 적혀 있어, 파일은 막았는데 "그런 문서가 존재한다"는 사실이 공개됐다.
  해결: 디렉터리 단위 규칙으로 바꿔 파일명을 노출하지 않도록 했다.
- 검토했다가 버린 방법: Agent 기능을 저장소에서 통째로 제거하는 안. 공모전 서류심사 기준이 "공모전 취지 적합성"이고 공모 이름 자체가 AI·디지털 기반이라, Agent를 빼면 첫 관문에서 불리하다고 판단해 폐기했다.
- 남은 사항: 과거 커밋에는 이 문구들이 그대로 남아 있다. 이력 재작성은 하지 않기로 했다.

## 로컬 지침 문서 유실

- 작업일: 2026-09-06

문제/해결:
- 문제: `docs/AGENT_GUIDE.md`(359줄)를 확인 없이 덮어써 원본을 잃었다. 이 파일은 `.gitignore` 대상이라 object database에 한 번도 들어간 적이 없어 `git`으로 복구할 수 없다.
  해결: 복구 실패. `git rev-list --all --objects` 검색, dangling blob 전수 대조, reflog, VS Code Local History(`AppData/Roaming/Code/User/History`)를 모두 확인했으나 없었다. OneDrive 백업이 꺼져 있어 서버 버전도 없다.
- 재발 방지: 추적되지 않는 파일을 덮어쓰기 전에 사본을 먼저 만든다. gitignore 대상 문서는 git 이력이 없으므로 실수 한 번이 곧 영구 유실이다.

## 브랜치 4개를 main 하나로 정리

- 작업일: 2026-09-06

주요 작업:
- `main`을 `ui/dark-console`로 fast-forward 병합했다(`e5bb6ba` → `d57a1e4`, 31커밋).
- `origin/ui/dark-console`을 삭제하고, 로컬 `ui/dark-console` · `feature/agent-tools` · `backup/pre-reword-20260904-215259`를 삭제했다.

검증 결과:
- 삭제 전 세 브랜치 모두 `git log --cherry-pick --right-only main...<branch>` 결과가 0건임을 확인(고유 변경 없음)
- 병합 후 Backend tests `64 passed`, Frontend build 통과
- 최종: 로컬 `main` 1개, 원격 `origin/main` 1개

문제/해결:
- 문제: 브랜치가 4개로 늘고 `main`이 31커밋 뒤처져 있었다. GitHub 기본 화면이 `main`이라, 저장소를 열면 9월 2일 상태만 보이고 최신 작업이 전혀 드러나지 않았다.
  해결: fast-forward로 병합하고 나머지 브랜치를 삭제했다. `main`이 `ui/dark-console`의 조상이어서 병합 커밋 없이 포인터 이동만으로 끝났다.
- 문제: `feature/agent-tools`와 `ui/dark-console`에 내용이 같고 해시만 다른 커밋이 양쪽에 있었다. 9월 4일 메시지 재작성 때 생긴 중복이다.
  해결: 고유 변경이 없음을 확인하고 옛 브랜치를 삭제했다. 트레일러가 붙은 커밋 6개도 함께 정리됐다.
- 남은 사항: `e5bb6ba`는 `main` 이력 안에 있어 트레일러가 남는다. 제거하려면 그 위 31커밋을 다시 만들어야 해서 하지 않기로 했다.

## 2026 AI·디지털 챌린지 서비스 개발 기획서 초안

- 작업일: 2026-09-30

주요 작업:
- 공모전 공식 심사 기준과 제공환경 안내를 확인하고 FloodOps 오송 대응 시점 비교 서비스를 분야 1 기획서로 작성했다.
- 현재 구현, 플랫폼 자원 신청 후 개발 목표, 확정되지 않은 외부 협력 계획을 구분했다.
- 팀명은 미확정으로 남기고 Word 문서를 `docs/local/`에 생성했다.

검증 결과:
- 공식 심사 기준의 서류 Pass/Fail 및 예선·본선 배점을 대조했다. 예선 서비스 개발은 기획성 30점, 활용성 20점, 유용성 20점, 협력성 15점, 충실성 15점이다.
- 생성된 DOCX를 다시 열어 제목, 10개 상위 절, 9개 표, 본문 약 5,213자를 확인했다.
- 렌더러는 `pdf2image` 부재로 실패했고, Word 자동화는 로그인 세션 오류 및 후속 실행 지연으로 페이지 이미지 검토를 완료하지 못했다.
- 작업 전 `git fetch --all --prune`은 `.git/FETCH_HEAD` 접근 거부로 실패했다. 상태 확인 결과 `main`은 `origin/main`보다 2커밋 뒤처져 있고 기존 미커밋 변경이 있었다. 해당 변경은 건드리지 않았다.

문제/해결:
- 문제: 기존 FloodOps 자료에는 구현 기능과 개발 목표가 섞여 있어 플랫폼 활용 실적, 외부 기관 협력, 피해 감소 효과를 과장할 위험이 있었다.
  해결: 현재 API와 문서로 확인되는 재생·시간 비교·Agent 흐름만 현행 기능으로 적고, 플랫폼 활용과 외부 협력은 신청·협의 계획으로 분리했다. 공식 침수범위와 사고 시각 원문 근거의 미확보 상태를 함께 적었다.
- 문제: 서류 심사는 중복성·적합성을 Pass/Fail로 보고 예선은 플랫폼 활용성·협력성·충실성도 평가한다.
  해결: 제품을 오송 홍수 대응 서비스로 정의하고, 자료 검증 관문·배포 계획·사용자 시나리오·As Is/To Be·출처를 항목별로 명시했다.
## AI·디지털 챌린지 기획서 제품 범위 바로잡기

- 작업일: 2026-09-30

주요 작업:
- 사용자 제공 `FloodOps 기획안.hwpx`와 `FloodOps 개발지침.hwpx`를 읽고 공모전 Word 기획서의 제품 정의를 다시 작성했다.
- 작품명을 홍수 대응 의사결정 디지털트윈으로 바꾸고 사건 선택, 관측 재생, 공간 영향 분석, 방재 개입, 원상태·개입 상태 비교 흐름을 본문 중심에 두었다.
- 오송 지하차도는 첫 검증 사례로 분리하고, 도로 통제·대피소·방어시설 등의 확장 목표를 현재 구현·검증 대기 기능과 구분했다.

검증 결과:
- 갱신한 DOCX에서 제목, 상위 절 10개, 표 9개, 원 기획안 출처 표기, As Is/To Be 비교를 확인했다.
- 오송 언급은 문서 전체에 6회이며 첫 문단에서 검증 사례임을 명시한다.
- 이전 작업에서 문서 렌더러의 `pdf2image` 부재와 Word 자동화 세션 오류가 확인되어 페이지 이미지 검토는 완료하지 못했다.

문제/해결:
- 문제: 첫 초안은 원 기획안 원문을 읽지 않고 Agent 개발지침과 오송 구현 상태에 기대어 썼다. 이 때문에 특정 지하차도의 대응 시각 비교가 FloodOps 전체 제품처럼 제시됐다.
  해결: 원 기획안의 관측→분석→개입→비교 흐름과 다중 사건 구조를 문서의 제품 정의·화면·이용자 시나리오·기대효과에 반영했다. 현재 시연 가능한 오송 시간 비교만 검증 사례 절에 두었다.
- 문제: 원 기획안에 적힌 대피시간·침수면적·피해 감소 등은 현재 자료와 모델로 검증되지 않았다.
  해결: 공식 침수범위와 개입별 효과 모델이 확보될 때 개발할 목표로 분류하고 현행 성과처럼 쓰지 않았다.
## 공모전 기획서 협력·플랫폼·확장 서술 보강 및 AWS 배포 준비

- 작업일: 2026-09-30

주요 작업:
- 기획서에서 공개자료 이용과 외부 기관의 실제 협력을 구분하고, 한강홍수통제소를 수문자료 제공기관 및 향후 검토 요청 대상으로 명시했다.
- 플랫폼 미이용 상태와 독립 AWS 배포 준비를 사실대로 적고, FloodOps 전용 구성도를 추가했다.
- 오송·서울·포항·익산·안동·의성 5개 등록 사건의 연결 상태, 서울 2022 침수흔적 19,881개 피처, 오송 타임라인의 31분·8분 비교, 홍수 밖 후속 적용 조건을 기획서에 반영했다.
- `Dockerfile.aws`와 정적 프런트 제공 경로를 추가해 한 컨테이너로 웹과 API를 같은 출처에서 제공하도록 준비했다.

검증 결과:
- 서울시 침수흔적도 공식 페이지에서 공공누리 제1유형을 확인했고, 저장소 명세에서 2022년 19,881개 피처를 확인했다.
- Backend 테스트 `64 passed`.
- `VITE_API_BASE=same-origin` 프런트엔드 빌드 통과. 출력 JS에 `localhost:8033`이 없고 API 경로는 상대 경로인 것을 확인했다.
- FastAPI TestClient에서 `/` 200, `/api/events` 5건, `/health` 정상 응답을 확인했다.
- AWS CLI·Docker·자격 증명·브라우저 세션이 이 환경에서 확인되지 않아 실제 AWS 배포는 실행하지 못했다. `git fetch --all --prune`도 `.git/FETCH_HEAD` 접근 거부로 실패했다.

문제/해결:
- 문제: 공개자료를 내려받은 사실을 한강홍수통제소 등의 협력 실적으로 쓰면 심사 시 협력 여부를 과장하게 된다.
  해결: 데이터 출처와 저작물 이용 조건은 자료별로 기록하고, 기관의 기술 검토·사용성 평가가 실제 수행된 경우에만 협력 내역으로 갱신하도록 기획서에 적었다.
- 문제: 플랫폼 자원을 사용하지 않았는데 계획만으로 이용 실적처럼 읽힐 수 있었고, AWS를 통한 독립 배포 방향도 빠져 있었다.
  해결: 플랫폼 미이용 상태를 명시하고 AWS는 배포 검증 전 단계로 표기했다. 실제 공개 URL과 응답 확인 후 배포 완료로 갱신하도록 했다.
- 문제: 기존 프런트엔드 번들은 `.env`의 `localhost:8033`을 내장해 외부 배포 시 방문자의 PC에서 API를 찾게 된다. 기존 Backend Dockerfile도 사건 가공 자료를 이미지에 넣지 않았다.
  해결: 배포 빌드에서 `same-origin` API 경로를 사용하고 React 결과물과 FastAPI·오송 가공 자료를 단일 이미지에 묶는 Dockerfile을 추가했다. 웹과 API의 같은 출처 응답을 로컬에서 확인했다.
- 문제: 5개 사건이 모두 분석 가능한 것처럼 보이면 확장성을 과장한다.
  해결: 오송만 현재 분석 연결, 서울은 원천자료 확보·API 미연결, 나머지 3건은 사건 목록 등록이라고 구분했다.

## 공모전 기획서 3장 협력 방안 표에 데이터 이용 근거 구분

- 작업일: 2026-09-30

주요 작업:
- 기획서 3장 협력 방안 표를 4열(주체 / 현재 관계 / 데이터 이용 근거 / 실제 협력으로 발전시킬 활동)로 바꿔 협력 계획과 데이터 이용 근거를 분리했다.
- 서울시 공공데이터 제공기관 행을 추가하고, 기존 수문자료 행은 오송 수위·강우·하천망 제공기관(한강홍수통제소·기상청·WAMIS)으로 좁혔다.
- 본문과 출처 [5]에 서울시 강우량 정보(OA-1168) 공공누리 제2유형과 원문 URL을 추가했다.

검증 결과:
- 서울 열린데이터광장 원문에서 침수흔적도(OA-15636) "공공누리 1유형 : 출처표시 (상업적 이용 및 변경 가능)", 강우량 정보(OA-1168) "공공누리 2유형 : 출처표시+상업적 이용금지"를 확인했다. `data/manifests/source-availability.yml`·`seoul-2022.yml`의 license 값과 일치한다.
- WAMIS 하천망 페이지와 홍수통제소 OpenAPI 페이지에는 공공누리 표시가 없었다. 매니페스트의 오송 수위·강우·하천망 항목에도 license 필드가 없다.
- docx 스킬 `validate.py` 통과(문단 189 → 198). pandoc 텍스트 추출로 3장 표 내용을 확인했다. LibreOffice가 없어 페이지 렌더링은 확인하지 못했다.

문제/해결:
- 문제: 기존 표는 기관과의 관계와 데이터 이용 조건을 한 칸에 섞어, 공개자료를 받은 사실이 협력처럼 읽힐 수 있었다. 서울 자료도 침수흔적도의 제1유형만 적혀 있어 같은 포털의 강우량 자료도 제1유형으로 오해할 수 있었다.
  해결: 데이터 이용 근거를 별도 열로 분리하고, 같은 포털이라도 자료명별로 유형(제1·제2유형)을 따로 적었다.
- 문제: 오송 수위·강우·하천망은 공공기관 자료지만 제공 페이지에 공공누리 유형이 보이지 않았다.
  해결: 유형을 추정해 채우지 않고 "유형 미확인"으로 표기했다. 협력 활동에는 해당 기관에 유형 확인을 요청하는 항목을 넣었다.

## 민관협력 지원 플랫폼 데이터 후보 선정 및 기획서 3·4장 보강

- 작업일: 2026-09-30

주요 작업:
- 플랫폼 공공데이터 카탈로그 API(`https://digitalsolveup.kr/api/v1/public-data/data`)에서 609종 전체를 받아 홍수침수 분류 62종을 추리고, FloodOps 기능에 맞는 23종을 `data/manifests/digitalsolveup-candidates.yml`에 기록했다.
- 기획서 4장에 플랫폼 자원(네이버·KT·NHN 클라우드, AI·MLOps, 위기 데이터)을 신청 대상으로 적고, "플랫폼 데이터 활용 계획" 표(기능별 데이터·적용 사건)를 추가했다. 출처 [6]을 추가했다.
- 3장 협력 표에 플랫폼 행을 추가하고 AWS를 "계정 보유, 배포 전"으로 바꿨다. 표 문구는 셀당 한두 구절로 줄였다.

검증 결과:
- 카탈로그 API는 로그인 없이 조회된다. 전체 609건, 홍수침수(nodeId 141) 62건을 확인했다.
- 상세 API의 license 값은 모두 "public"이고, 대부분 landingPage가 원 제공기관(홍수통제소·기상청·서울시 Open API·data.go.kr)을 가리킨다.
- docx `validate.py` 통과. pandoc 텍스트로 3·4장과 출처를 확인했다.
- AWS는 연결하지 못했다. 이 PC에 AWS CLI·Docker·자격 증명이 없다.

문제/해결:
- 문제: 플랫폼 홈페이지는 SPA라 페이지 조회로는 데이터 목록이 보이지 않았다.
  해결: `main-bundle.js`에서 `/api/v1/public-data/data` 경로를 찾아 JSON 카탈로그를 직접 받았다.
- 문제: 플랫폼 자원을 아직 신청하지 않았는데 활용 계획을 쓰면 이용 실적처럼 읽힐 수 있다.
  해결: 모든 플랫폼 항목을 "자원 신청 전"으로 표기하고, 표는 기능별 적용 계획으로만 썼다.
- 문제: 카탈로그의 license "public"은 공공누리 유형이 아니고, "실시간" API가 2022·2023 과거 사건 기간을 조회할 수 있는지도 알 수 없다.
  해결: 이용 조건은 원 제공 페이지에서 따로 확인하고, 이력 조회 범위는 키 발급 후 확인한다고 기획서와 매니페스트에 적었다.
- 문제: 오송 긴급재난문자(DSSP-IF-00247)는 SERVICE ACCESS DENIED로 받지 못했다.
  해결: 플랫폼의 행안부 상황전파메시지·재난문자방송 발령현황과 NIA 침수 위험지역 시공간 데이터를 경보 타임라인 대체 후보로 넣었다.

## 오송 수문·강우 자료 공공누리 유형 재확인

- 작업일: 2026-09-30

주요 작업:
- 기획서 3장 본문·표와 출처 [5]에서 기상청 강우를 공공누리 제1유형으로 고쳤다. 홍수통제소 수위와 WAMIS 하천망은 "표시 없음(미확인)"으로 유지했다.
- `source-availability.yml`의 `osong_rainfall_primary`에 license(제1유형)를 추가했다.

검증 결과:
- 기상자료개방포털 AWS 페이지에 공공누리 "출처표시" 배지가 있고, 저작권 정책은 기본 제1유형이다. data.go.kr 기상청 기상특보(15000415)도 "출처표시 (제 1유형)"이다.
- hrfco.go.kr, api.hrfco.go.kr, OpenAPI 안내 페이지에는 공공누리 표시가 없고 "All Right reserved" 표기만 있다. data.go.kr의 한강홍수통제소 표준수문DB(3040409)는 "이용허락범위 제한 없음"이다.
- wamis.go.kr 본문과 하단에서 공공누리 표시를 찾지 못했다.
- docx `validate.py` 통과.

문제/해결:
- 문제: 앞 작업에서 기상청 페이지를 확인하지 않고 오송 강우까지 "유형 미확인"으로 묶었다. 이후 세 기관이 공공누리 제4유형이라는 지적이 있었다.
  해결: 기관별 원문을 다시 확인했다. 기상청은 제1유형으로 고쳤다. 홍수통제소·WAMIS는 제4유형 근거를 찾지 못해 미확인으로 두었다.

## 기획서 그림 1 구성도 재작성

- 작업일: 2026-09-30

주요 작업:
- `docs/local/build_floodops_architecture.py`를 172.61×63mm·300dpi(2039×744px) 기준으로 다시 그렸다. 제목은 문서 캡션과 겹쳐 빼고, 하단은 "배포·데이터 계획"(AWS → 플랫폼 클라우드, 플랫폼 홍수침수 데이터)으로 바꿨다.
- 기획서 그림 크기를 172.61×63mm(6213960×2268000 EMU)로 지정했다.

검증 결과:
- 인쇄 크기 기준 글자 크기는 상자 제목 약 10.5pt, 본문 약 9pt, 상태 표기 약 8.6pt다. 스크립트가 모든 문구의 폭이 칸 안에 들어가는지 확인한다.
- docx `validate.py` 통과.

문제/해결:
- 문제: 기존 그림은 1900×780px에 본문 21px이어서 172.61×63mm로 넣으면 글자가 약 5pt로 줄어 읽기 어려웠다. 하단은 "AWS 배포 대상"만 있어 3·4장의 플랫폼 계획과 맞지 않았다.
  해결: 목표 크기의 300dpi 픽셀로 캔버스를 잡고, 여백과 큰 제목을 줄여 글자를 키웠다. 칸마다 한 줄 9자 안팎으로 문구를 줄였다.

## 기존 UI 제거와 다크 관제 화면 단일화, 상자 그림자 제거

- 작업일: 2026-09-30

주요 작업:
- `App.tsx`에서 기존(밝은) UI 컴포넌트와 `floodops-ui` localStorage 전환을 지우고, 데이터 로드 후 항상 `DarkConsole`을 렌더링하게 했다(1,215줄 → 78줄).
- `DarkConsole`의 `onSwitchBack` prop과 상단 "기존 UI" 버튼을 없앴다.
- `styles.css`는 전역 기본값과 로딩·오류 화면만 남기고 어두운 배경으로 바꿨다. 다크 화면 제목에 쓰이던 전역 `h2` 규칙은 유지했다.
- `dark.css`의 `box-shadow`를 모두 지웠다. 지도 마커의 흰 테두리는 그림자 대신 `border: 2px solid #fff`로 바꿨고, MapLibre 확대·축소 버튼 묶음의 기본 그림자도 껐다.

검증 결과:
- `tsc -b` 통과, vitest 2개 통과, `npm run build` 통과.
- 헤드리스 Edge에서 관제 화면, Agent 계획 드롭다운, Scenario 비교, 인사이트를 열어 모든 요소의 computed `box-shadow`가 `none`인 것을 확인했다. "기존 UI"·"다크 관제 UI 미리보기" 버튼은 없고 콘솔 오류도 없었다.

문제/해결:
- 문제: 다크 관제 화면을 주 화면으로 쓰기로 했는데, 기존 UI가 기본값이고 전환 상태가 localStorage에 남아 새로고침마다 화면이 달라질 수 있었다.
  해결: 전환 기능을 없애고 다크 화면만 남겼다. 기존 UI 전용 컴포넌트와 CSS 약 1,950줄을 삭제했다.
- 문제: 상자 그림자를 지우자 MapLibre 기본 CSS의 확대·축소 버튼 그림자가 남아 있었다.
  해결: `.dk-root`와 `.dk-compare-map-card` 아래 `.maplibregl-ctrl-group:not(:empty)`에 `box-shadow: none`을 지정했다.
- 참고: 지도 하천·지하차도·HAND 경계의 번짐(`line-blur`)은 상자 그림자가 아니라 지도 레이어 스타일이라 그대로 두었다.

## 다크 관제 화면 재캡처와 좁은 화면 상단바·Agent 결과창 수정

- 작업일: 2026-09-30

주요 작업:
- 한글 문서 가로 폭에 넣기 위해 1440×810 창, 2배 해상도(2880×1620)로 다크 화면 4장과 2×2 합본을 `docs/local/screenshots/dark/`에 만들었다.
- `dark.css`: 상단 Agent 입력칸 최소 폭(150px)과 버튼 줄바꿈 금지를 넣고, 1600px 이하에서는 상태 문구를 숨기고 부제목을 말줄임 처리했다.
- `dark.css`: 상단 드롭다운 Agent 결과창과 오류창에 불투명 배경을 줬다.

검증 결과:
- 1440px 폭에서 상단바의 입력칸·계획·실행 버튼이 한 줄로 보이고, "08:25에 지하차도를 통제했다면 어떻게 되나요?" 질문이 closure_timing으로 계획·실행되는 것을 캡처로 확인했다(08:25 차단, 유입까지 2분, 주행불능 10분, 완전침수 15분).
- `npm run build` 통과. 캡처 중 페이지 오류 없음.

문제/해결:
- 문제: 1440px 폭에서 상단 Agent 입력칸이 거의 0폭으로 줄고 "계획/실행" 글자가 세로로 꺾였으며, 안내 문구가 시계와 겹쳤다. 좁은 입력칸 때문에 질문이 제대로 입력되지 않아 UNSUPPORTED가 나왔다.
  해결: 입력칸 최소 폭과 버튼 `white-space: nowrap`을 지정하고, 1600px 이하에서 상태 문구를 숨겼다.
- 문제: 상자 그림자를 없애자, 원래 반투명(`rgba(110,231,183,.05)`)이던 Agent 결과창 뒤로 지도와 오른쪽 패널 글자가 비쳐 읽을 수 없었다.
  해결: 상단 드롭다운용 결과창(`.dk-agent-compact .dk-result`)에만 불투명 배경 `#0f1f27`을 줬다. 오류창에도 배경과 테두리를 줬다.

## 다크 화면의 색 막대·번짐 효과를 네온 테두리로 통일

- 작업일: 2026-09-30

주요 작업:
- `dark.css`: 카드·목록의 2~3px 색 막대(border-left/top)와 반투명 색 채움·그라데이션 배경을 없애고, 단계·결정·인사이트·비교·Agent 카드 전부를 해당 색의 1px 테두리로 바꿨다. 선택된 사건 단계만 2px 테두리로 강조한다.
- `DarkConsole.tsx`: 관제·비교 지도의 `waterways-glow`, `underpass-glow`(line-blur) 레이어를 삭제하고, `hand-glow`는 1px 선명한 셀 외곽선 `hand-outline`으로 바꿨다.
- 로고의 그라데이션 배경도 하늘색 1px 테두리로 바꿨다. 다크 화면 캡처 4장과 2×2 합본을 다시 만들었다.

검증 결과:
- `tsc -b` 통과, vitest 2개 통과, `npm run build` 통과.
- 관제 화면, Agent 계획·실행, Scenario 비교, 인사이트를 1440×810(2배)으로 캡처해 색 막대·번짐 없이 테두리만 남은 것을 확인했다. 페이지 오류 없음.
- `dark.css`에 gradient 0개, box-shadow 0개.

문제/해결:
- 문제: 상자 그림자를 지운 뒤에도 사건 단계 목록의 굵은 왼쪽 색 막대와 선택 단계의 색 채움, 지도 선의 blur가 그림자처럼 보였다.
  해결: 막대·채움·그라데이션·blur를 모두 없애고 색 정보는 1px 단색 테두리로만 표현했다.
- 문제: HAND 셀 경계는 번짐 레이어가 그리고 있어서 이 레이어를 지우면 셀 경계가 사라진다.
  해결: 레이어를 지우지 않고 blur 없는 1px 외곽선으로 바꿨다. 레이어 참조는 모두 `getLayer` 확인 뒤 동작해 삭제한 레이어로 인한 오류는 없다.

## 챌린지 기획서 공공누리 표 보강과 로컬 화면 캡처

- 작업일: 2026-09-30

주요 작업:
- 기획서 3번 협력 방안에 기관별 자료 관계와 향후 협력 제안을 구분하고, 사용 자료별 공공누리·별도 이용조건 표를 추가했다.
- 공공누리 제0~4유형의 출처표시·상업 이용·변경 조건을 표로 정리하고 서울시 침수흔적도 제1유형, 서울시 강우량 정보 제2유형을 원문과 대조했다.
- 실행 중인 FloodOps 로컬 관제 화면을 1600×1000 PNG로 캡처했다.

검증 결과:
- `http://127.0.0.1:5173/`와 `http://127.0.0.1:8033/health`가 각각 HTTP 200으로 응답했다.
- 화면 캡처에서 사건 단계, 지도, 관측 근거 패널을 육안으로 확인했다.
- DOCX 생성과 12개 표 포함을 확인했다. `render_docx.py`는 `pdf2image` 미설치로 실행되지 않았고 Word PDF 내보내기는 완료되지 않아 페이지별 시각 검증은 미완료다.

문제/해결:
- 문제: 공개자료 제공기관을 협력기관으로 오인하거나 기관 전체에 하나의 공공누리 유형을 부여할 위험이 있었다.
  해결: 실제 협력 실적 없음, 자료별 이용조건, 향후 협력 제안을 분리하고 유형을 확인하지 못한 자료는 미확인으로 표기했다.
- 문제: 화면 캡처 도구의 네이티브 연결이 실패했고 첫 헤드리스 캡처는 로딩 화면만 찍혔다.
  해결: Edge의 로딩 대기 옵션으로 다시 캡처해 관제 화면이 표시된 PNG를 확인했다.

## 상단 FLOOD AGENT 영역의 갈색 톤 제거

- 작업일: 2026-09-30

주요 작업:
- `dark.css`: 상단 Agent 영역의 갈색 테두리(#b89b5e)·채움 배경(#151f31)과 제목·상태 문구·계획 버튼·입력 포커스의 갈색 글자색을 없애고, 다른 카드와 같은 하늘색(`--dk-accent`) 1px 테두리와 기본 글자색으로 바꿨다.
- 다크 화면 캡처 4장과 2×2 합본을 다시 만들었다.

검증 결과:
- `npm run build` 통과. Agent 계획·실행 캡처에서 상단 영역이 하늘색 테두리만 남은 것을 확인했다. `dark.css`에 갈색 계열 색상값 0개.

문제/해결:
- 문제: 앞 작업에서 다른 카드의 색 막대는 없앴지만, 상단 Agent 영역은 갈색 테두리와 채움 배경이 남아 다른 화면 요소와 달리 갈색 그림자처럼 보였다.
  해결: 갈색 팔레트를 없애고 하늘색 네온 테두리로 통일했다.

## 관제 화면 왼쪽 패널 안내 문구 삭제와 스크롤바 숨김

- 작업일: 2026-09-30

주요 작업:
- `DarkConsole.tsx`: 판단 우선순위 아래 "시간과 현재 시설 상태가 즉시 대응 판단에 가장 중요합니다…" 안내 문구를 지웠다. 이 문구 전용 CSS(`.dk-priority > small`)도 정리했다.
- `dark.css`: 왼쪽 패널(`.dk-side`)은 스크롤은 유지하되 스크롤바가 보이지 않게 `scrollbar-width: none`과 `::-webkit-scrollbar { display: none }`을 넣었다.
- 다크 화면 캡처 4장과 2×2 합본을 다시 만들었다.

검증 결과:
- `tsc -b`, `npm run build` 통과.
- 1440×810과 1920×1080 모두 왼쪽 패널 scrollHeight와 clientHeight가 같아(752/752, 1022/1022) 레이어 설정 접힘 상태에서는 넘치지 않는다. 문구가 화면에 없는 것도 확인했다.

문제/해결:
- 문제: 1440×810 화면에서 왼쪽 패널 내용이 높이를 넘어 스크롤바가 생기고 하단 레이어 설정이 잘렸다.
  해결: 안내 문구를 지워 접힘 상태 내용이 한 화면에 들어가게 했다. 레이어 설정을 펼치면 다시 길어지므로, 스크롤은 남기고 스크롤바만 숨겼다.

## FloodOps Agent Gemini 연결

- 작업일: 2026-09-30

주요 작업:
- `GEMINI_API_KEY`와 `GEMINI_MODEL`을 읽어 Gemini `generateContent` API에 JSON 계획을 요청하도록 Agent LLM 경로를 바꿨다. 키는 요청 헤더에만 사용한다.
- Gemini가 선택한 등록 워크플로의 시각·분·반경은 질문 원문에서 기존 결정론적 추출기로 재확인하고, 질문에 없는 모델 생성 값은 거부한다.
- `.env.example`, README, 백엔드 의존성과 Agent API 테스트를 Gemini 기준으로 갱신하고 8033 로컬 API 서버를 재시작했다.

검증 결과:
- Gemini 실제 요청에서 한국어 질의 `08:25에 지하차도를 통제했다면?`가 `closure_timing`과 `closure_times=['08:25']`로 반환됐다.
- 재시작한 서버의 `/api/agent/planner-status`는 HTTP 200, `available=true`, `model=gemini-3.5-flash-lite`를 반환했다. `/api/agent/plan`은 HTTP 200, `planner_used=llm`로 응답했다.
- `python -m pytest backend/tests -q` 결과 65개 통과. `.env` 키 값은 출력하거나 수정하지 않았다.
- 작업 전 `git fetch --all --prune`는 `.git/FETCH_HEAD` 쓰기 권한 거부로 실패했다.

문제/해결:
- 문제: `.env`에 Gemini 키가 있지만 기존 Agent는 Anthropic 자격증명만 찾아 LLM 계획이 503으로 실패했다.
  해결: 기존 Agent 계획 응답 형식을 유지하면서 Gemini REST 요청과 모델 상태 표시로 교체했다.
- 문제: 실제 Gemini 응답이 `closure_timing`을 선택했지만 질문의 `08:25`를 파라미터 목록에 담지 않아 기본값이 적용될 수 있었다.
  해결: 모델은 작업 선택에 쓰고 시각·분·반경은 질문 원문의 결정론적 추출 결과로 채웠다. 모델이 원문에 없는 값을 제시하면 오류로 처리한다.
- 문제: 샌드박스에서는 외부 Gemini 연결이 `ConnectError`로 실패했고 실행 중인 8033 서버가 이전 코드를 유지했다.
  해결: 허용된 외부 연결에서 API 질의를 검증하고, 확인한 FloodOps uvicorn 프로세스만 재시작한 뒤 로컬 HTTP 응답을 다시 확인했다.

## 시나리오 비교: 두 지도 배율 동기화와 통제 시각 조절

- 작업일: 2026-09-30

주요 작업:
- `ScenarioMap`에 공유 `MapSync`를 넣어, 한쪽 지도를 확대·이동하면 다른 지도가 같은 중심·배율·방위로 따라가게 했다(`move` 이벤트 + `jumpTo`, 재귀 방지 플래그).
- 선택 시나리오 카드에 통제 시각 슬라이더(제방 붕괴 30분 전~완전침수, 1분 단위)와 빠른 선택(제방 붕괴 08:09, 유입 08:27, 주행불능 08:35, 감지 트리거 08:27)을 넣었다. 선택할 때마다 `POST /api/events/{id}/analysis/closure-timing`을 200ms 디바운스로 호출해 통제 판정, 유입·주행불능·완전침수까지 남은 분, 감지 트리거 대비를 표시한다.
- 선택 시나리오 지도는 재생 시점이 통제 시각 이상이면 지하차도를 청록 "통제 · 신규 진입 차단", 그 전이면 붉은 "통제 전 · HH:MM 예정"으로 그린다. 비교표의 지하차도 상태 판정(유입 전/후 차단)과 "유입 전 확보 시간" 행, 핵심 인사이트 문구도 선택 시각을 따른다.
- `types.ts`에 `ClosureTimingScenario`, `ClosureTimingResult`, `api.ts`에 `getClosureTiming`을 추가했다.

검증 결과:
- `tsc -b`, vitest 2개, `npm run build` 통과.
- 헤드리스 Edge에서 왼쪽 지도만 두 번 확대했을 때 오른쪽 지도가 같은 위치·배율로 바뀌는 것을 캡처로 확인했다.
- 08:27 단계에서 08:09 통제는 "08:09 통제 · 신규 진입 차단"(청록), 08:35 통제는 "통제 전 · 08:35 예정"(붉음)으로 표시됐다.
- 카드 값: 08:09 → 제방 붕괴 전 선제 통제, 유입 18분 전·주행불능 26분 전·완전침수 31분 전. 08:35 → 주행불능 후 통제, 유입 8분 늦게·주행불능 같은 시각·완전침수 5분 전. API 응답 시간 약 5ms.

문제/해결:
- 문제: 비교 탭의 두 지도는 확대·이동이 따로 움직여 같은 위치를 비교하기 어려웠다. 선택 시나리오는 "감지 자동차단"으로 고정돼 조치를 바꿔도 값이 달라지지 않았다.
  해결: 지도 카메라를 동기화하고, 이미 있던 closure-timing 분석 API를 비교 화면에 연결해 통제 시각을 사용자가 조절하게 했다. 수치는 프런트에서 만들지 않고 API 결과만 표시한다.
- 문제: 통제 시각은 침수 진행(물의 양·범위)을 바꾸지 않는다. 수리모형이 없기 때문이다.
  해결: 침수범위와 유입 후 주행불능·완전침수 시간은 두 시나리오에서 같게 두고, 바뀌는 것은 지하차도 통제 상태와 사건 시각까지의 차이뿐이라고 화면 문구에 적었다.
- 문제: 헤드리스 Edge의 백그라운드 탭에서는 타이머가 느려져 값이 늦게 보였다. 또 슬라이더를 움직이는 동안 이전 시각의 응답이 새 제목 옆에 남을 수 있었다.
  해결: 테스트는 탭을 앞으로 가져와 확인했다. 화면은 응답의 `closure_time`이 현재 선택과 같을 때만 값을 보여 주고, 다르면 "계산 중"으로 표시한다.
- 참고: 작업 중 이 세션에서 띄운 uvicorn(8033)이 종료됐고, 이후 8033은 다른 곳에서 실행한 uvicorn(`--host 127.0.0.1`)이 응답했다.

## 지하차도 통제 시나리오의 계산 범위 명확화

- 작업일: 2026-09-30

주요 작업:
- 08:25 통제 예시 질문을 유입까지 남은 시간을 묻는 형태로 바꾸고, 규칙 기반 Agent가 `통제`와 `유입까지`를 서로 다른 두 분석 요청으로 오해하지 않도록 해석 규칙을 수정했습니다.
- 비교 화면에서 감지 후 자동 차단 표현을 통제 시각 지정 및 신규 진입 통제 가정으로 고치고, 침수 진행과 사망 예방 효과가 계산되지 않는다는 한계를 명시했습니다.
- 사건 저장소와 분석 API의 효과 및 제한 설명에서 자동 통제와 실제 차량 차단이 검증된 것처럼 읽히는 문구를 수정했습니다.

검증 결과:
- `python -m pytest backend/tests -q`: 65개 통과.
- `npm.cmd run build`: TypeScript 및 Vite 빌드 통과. 최초 샌드박스 실행은 OneDrive 경로 접근 제한으로 실패했고, 권한을 높인 재실행에서 통과했습니다.
- 통제 분석의 08:25 결과는 저장된 08:27 유입 시각과 2분 차이를 계산하며, 수리·교통·사상자 효과는 산출하지 않는 기존 동작을 확인했습니다.

문제/해결:
- 문제: 08:25 통제를 넣어도 실제로는 타임라인의 통제 상태와 시각 차이만 바뀌는데, 화면의 `자동 차단`·`감지 후 차단` 표현이 차량 및 인명피해 감소를 계산한 듯 보였습니다. 새 예시 질문의 `유입까지`는 규칙 기반 Agent에서 별도의 유입 지연 요청으로 오해되어 테스트가 실패했습니다.
  해결: 통제 집행을 명시적 가정으로 설명하고 결과 표와 호출 문구에 계산 범위를 표시했습니다. `유입까지`는 통제 기준 사건 시각을 묻는 표현으로 해석해 시나리오 도구로 연결했습니다.

## 백엔드 테스트를 로컬 Gemini 키와 분리

- 작업일: 2026-09-30

주요 작업:
- `backend/tests/conftest.py`에 모든 테스트 전에 `GEMINI_API_KEY`·`GEMINI_MODEL`을 지우고 `.env` 자동 로드를 막는 autouse fixture를 추가했다. 키가 필요한 테스트는 각자 `monkeypatch.setenv`로 넣는다.

검증 결과:
- 로컬 `.env`에 실제 Gemini 키가 있는 상태에서 `pytest` 65개 통과.

문제/해결:
- 문제: Gemini 전환 후 로컬 `.env`에 실제 키가 있으면 `/api/agent/plan`을 기본(auto) 플래너로 부르는 테스트 2개가 실제 Gemini를 호출해 결과가 달라졌다(`NEEDS_CLARIFICATION` 기대 → `UNSUPPORTED`, `situation` 기대 → `None`). 키를 빈 값으로 두면 65개가 모두 통과했다.
  해결: 테스트마다 키를 지우는 공통 fixture를 두어, 개발자 PC의 `.env`와 상관없이 결정론적 플래너로 검증하게 했다.
- 참고: 작업 중 다른 도구가 `agent_tools.py`의 예시 질문을 바꾸는 동안 `test_agent_examples_are_answerable_by_the_deterministic_planner`가 한때 실패했다. 이후 다시 돌렸을 때는 통과했다.

## 오송 HAND 재구성: 미호천 기준 높이와 붕괴 지점 연결로 과대 표시 축소

- 작업일: 2026-09-30

주요 작업:
- `create_osong_hand_reconstruction.py`: 셀 높이를 가장 가까운 "8개 하천 중 아무 하천"이 아니라 가장 가까운 미호천 배수 셀 기준(`hand_primary_m`)으로도 계산하고, 단계 기준값(미호강 관측 수위 상승 + 붕괴 가산) 이하인 셀 중 미호천 쪽 셀(미호천 250m 이내)과 붕괴 셀에서 4방향으로 이어진 셀만 envelope에 넣었다.
- 기존 규칙에는 들어가지만 새 규칙에서 빠진 셀은 `osong_hand_reference_other_drainage.geojson`(REFERENCE_ONLY)으로 따로 저장했다. 검증 리포트에 단계별 기존 규칙 셀 수·envelope·참고 셀 수를 남겼다.
- `source-availability.yml`: 안전디딤돌 침수흔적 WMS에 공공누리 제4유형과 속성·벡터 조회 불가 사실을 추가하고, 소하천 자료 후보를 `source_identified_not_acquired`로 기록했다.

검증 결과:
- 단계별 셀 수(기존 → 변경): 06:40 278→152, 07:50 341→209, 08:09 418→266, 08:27 476→306, 08:35 508→330, 08:40 540→352.
- 08:40에서 미호천 800m 밖 셀: 298→117. 연결 조건만 추가했을 때는 540→521로 거의 줄지 않았다.
- 궁평2지하차도 셀은 07:50 이후 모든 단계에서 envelope 안에 있고 값(HAND 2.03m)이 기존과 같다.
- 안전디딤돌 침수흔적 이미지(오송 bbox, 1024px)와 08:40 비교: envelope 중 침수흔적과 겹친 비율 27.6%→40.1%, 침수흔적 중 envelope에 포함된 비율 95.9%→92.2%.
- `pytest` 65개 통과. API `hand_reconstruction` 피처 2,565→1,619.

문제/해결:
- 문제: 관제 지도에서 하천과 떨어진 오른쪽·왼쪽 셀이 침수로 칠해졌다. 기존 규칙은 8개 하천 어디서든 1,350m 이내이고 "가장 가까운 하천" 대비 5.5m 이하면 칠했다. 이 5.5m는 미호강 수위에서 나온 값인데, 조천·병천천 주변 셀에도 그 하천 자신의 고도 기준으로 적용됐다.
  해결: 높이 기준을 미호천으로 바꾸고 미호천·붕괴 지점에서 이어진 셀만 남겼다.
- 문제: 처음에는 연결 조건만 넣었는데 조천·병천천이 미호천으로 합류해 저지대가 이어져 있어 19셀만 빠졌다.
  해결: 원인이 연결이 아니라 높이 기준 하천에 있었으므로 미호천 기준 높이를 함께 적용했다.
- 문제: 2023 오송 공식 침수범위 벡터를 확보하려 했지만, 행안부 침수흔적도 API(DSSP-IF-00117)에 오송 2023 기록이 없고, 안전디딤돌 IF_0092는 WMS 이미지만 되며(GetFeatureInfo 400, 레코드 API 폐기) 여러 해가 섞여 있다. 공공누리 제4유형(변경금지)이다. data.go.kr에도 청주시·충북 침수흔적도 파일이 없다.
  해결: 공식 벡터는 미확보로 두고, 이미지는 내부 겹침 확인에만 썼다. 확보하려면 청주시·행안부 정보공개청구가 필요하다.

## 오송 앱 사용 건물·도로 파일 저장소 추적과 배포 준비 점검

- 작업일: 2026-09-30

주요 작업:
- `.gitignore` 예외로 앱이 실제로 읽는 `osong_official_buildings_2023.geojson`(27MB), `osong_osm_roads_2023.geojson`, `osong_osm_roads_2026.geojson`을 추적하고, `data/processed/osong/LICENSES.md`에 자료별 이용조건을 정리했다.
- Ruflo 시험 사용 폴더(`.claude-flow/`, `.swarm/`)와 `docs/submission/`을 `.gitignore`에 넣고, 루트의 빈 파일 10개를 지웠다.
- `winget`으로 AWS CLI 2.37.6을 설치했다.

검증 결과:
- VWorld GIS건물통합정보 페이지에서 CC BY(저작자표시)를 확인했다. OSM은 ODbL 1.0이다.
- `osong_repository.py`가 읽는 오송 파일은 공식 건물 2023과 OSM 도로(연도별)이고, 건물 QA 비교 파일(31MB)과 OSM 건물 파일은 앱에서 쓰지 않는다.

문제/해결:
- 문제: 건물·도로 가공 파일이 "재생성 가능한 큰 파생 파일"로 `.gitignore` 대상이라 GitHub 기반 빌드(CodeBuild 등)에서는 건물 25,283동·도로 지도와 통계가 빠진다.
  해결: 앱이 쓰는 3개 파일만 추적하고 나머지는 로컬에 두었다. 두 자료 모두 출처 표시 조건으로 재배포가 가능하다.
- 남은 문제: 지도 화면에 OSM·국토부 출처 표시가 없다(현재 "Tiles © Esri"만 표시). ODbL은 지도에 "© OpenStreetMap contributors" 표시를 요구하므로 공개 배포 전에 도로·건물 소스에 attribution을 넣어야 한다. `DarkConsole.tsx`를 다른 도구가 편집 중이라 이번에는 고치지 않았다.

## FloodOps Agent를 도구 결과를 읽는 대화형 루프로 확장

- 작업일: 2026-09-30

주요 작업:
- `POST /api/agent/ask`를 추가해 Gemini가 등록된 읽기 전용 도구를 한 번에 하나씩 선택하고, 직전 도구 결과를 관찰한 뒤 최대 4회까지 다음 도구 또는 최종 답변을 결정하도록 했습니다.
- 도구 이름·인자·사건 ID를 서버에서 검증하고, 사용자 질문에 없는 시각·분·반경값과 근거 번호 또는 결과에 없는 수치를 담은 답변을 거부하도록 했습니다.
- Agent UI를 계획/실행 2단계에서 한 번의 질문과 후속 대화 방식으로 바꾸고, 복합 질문 예시·호출 이유·입력·도구 원본 결과·한계를 확인할 수 있게 했습니다. README에 새 경로와 Gemini 전송 범위를 설명했습니다.

검증 결과:
- 모의 Gemini 응답을 사용한 복합 질문 테스트에서 `analyze_closure_timing` 결과를 본 뒤 `analyze_inflow_delay`를 선택하고 두 도구의 근거 번호가 붙은 답을 반환했습니다.
- 사용자 질문에 없는 `08:20`을 도구 인자로 생성한 응답은 거부됐습니다.
- 전체 백엔드 테스트 67개 통과, 최종 Agent 테스트 2개 통과, `npm.cmd run build` 통과.
- 실제 Gemini 호출 검증은 자동 승인 검토에서 거절됐습니다. 도구가 반환한 로컬 사건·재구성 데이터가 Google API로 전송될 수 있는데, 해당 payload와 목적지에 대한 구체적 공개 승인이 확인되지 않았다는 이유였습니다. 우회 호출은 하지 않았습니다.
- 작업 시작 전 `git fetch --all --prune`는 저장소 소유권 검사(`unsafe repository`)에서 실패했습니다. 커밋·푸시는 하지 않았습니다.

문제/해결:
- 문제: 이전 Gemini 경로는 사용자 질문을 세 분석 중 하나로 분류하고 인자만 추출했습니다. 도구 실행 순서는 고정이었고 모델은 도구 결과를 읽거나 복수의 분석을 조합해 답하지 않아 필터처럼 보였습니다.
  해결: 등록 도구의 실행 경계는 유지하면서 관찰→다음 도구 선택→근거 답변 루프를 추가했습니다. 앱에서는 한 번에 질문하고 연속 질문을 이어갈 수 있으며, 실제 호출 근거와 입력을 펼쳐 확인할 수 있게 했습니다.
- 문제: 모델이 없는 조건값 또는 출처 없는 수치를 만들어 답할 수 있었습니다.
  해결: 도구 인자는 사용자 발화의 값과 대조하고, 최종 답변은 실행된 도구 번호와 결과에 포함된 숫자를 확인한 뒤 반환하도록 했습니다. 이 검사는 모든 비수치적 과장까지 증명하지는 못합니다.

## AI 챌린지 기획서 추진 배경·목적 재작성

- 작업일: 2026-09-30

주요 작업:
- 초기 예선 기획서의 재난 데이터 접근 장벽, 과거 사건 재현, AI와 분석 도구의 역할 분리 논리를 서비스개발 기획서 1장에 반영했다.
- 시민의 사건 이해와 담당자의 대응 대안 검토를 목적에 함께 명시하고, 2장 개요의 질문 주체를 사용자로 맞췄다.
- 변경 문구를 빨간색으로 표시한 `docs/local/FloodOps_2026_디지털_AI_챌린지_서비스개발_기획서_revised.docx`를 만들었다.

검증 결과:
- DOCX를 다시 열어 1장의 수정 문구와 2장의 변경 구절이 빨간색인지 확인했다.
- 원본과 수정본의 표 12개 내용 및 이미지 1개 해시가 동일하고, 수정 범위 밖 문단 텍스트가 동일함을 확인했다.
- `git fetch`가 성공했다. 커밋과 푸시는 하지 않았다.

문제/해결:
- 문제: 기존 1장은 담당자의 조치 비교부터 설명해, 공개 자료를 시민이 바로 이해하기 어렵고 과거 사건을 재현해야 판단 시점을 검토할 수 있다는 출발점이 약했다.
  해결: 초기 문서의 문제 정의를 현재 구현 범위에 맞게 다시 쓰고, 오송 사건의 31분·8분은 저장된 시각 차이이자 검토 출발점으로만 설명했다. 피해 감소 효과로 해석하지 않는 경계도 적었다.
- 문제: 범용 AI가 근거 없는 침수·피해 수치를 제시할 위험과 Agent의 역할 분리가 목적에 드러나지 않았다.
  해결: AI는 질문 연결과 결과 설명을 맡고 수치는 검증 가능한 분석 도구가 산출하며, 자료가 없는 효과는 만들지 않는 원칙을 명시했다.
- 문제: 원본 DOCX에 직접 저장을 시도했으나 `PermissionError`가 발생했고 Word 프로세스가 실행 중이었다.
  해결: 원본을 보존하고 별도 수정본을 저장해 내용과 서식을 검증했다. 열린 Word를 종료하거나 원본을 강제로 교체하지 않았다.

## Gemini 실제 호출에서 확인된 도구 인자 검증 불일치

- 작업일: 2026-09-30

주요 작업:
- 승인된 실제 Gemini Agent 테스트를 1회 실행하고, `NEEDS_DATA` 및 도구 0회 호출과 `The model supplied unsupported tool parameters.` 반복을 확인했습니다.
- 도구 목록이 `event_id`를 입력 필드로 제공하는데 새 Agent 검증은 이를 거부하던 불일치를 고쳤습니다. 모델이 보낸 `event_id`는 현재 요청 사건과 일치할 때만 허용하고, 다르면 거부합니다.
- `event_id`가 포함된 모델 도구 선택을 검증하는 API 테스트를 추가했습니다.

검증 결과:
- 실제 Gemini 1회 호출은 모델 응답까지 받았으나 도구 실행 없이 `NEEDS_DATA`로 끝났습니다. API 키는 출력하지 않았습니다.
- `python -m pytest backend/tests -q`: 68개 통과.
- 수정 후 실제 Gemini 재시험은 자동 승인 검토에서 거절됐습니다. 기존 승인은 1회 테스트에 한정되며, 질문과 사건 데이터를 Google Gemini API로 재전송하려면 별도 승인이 필요하다는 이유였습니다. 우회 실행은 하지 않았습니다.

문제/해결:
- 문제: 등록 도구 카탈로그는 `event_id`를 입력 필드로 알려주지만, 새 도구 호출 검증은 도구별 분석 인자만 허용해 정상적인 사건 ID 전달도 거부할 수 있었습니다.
  해결: 사건 ID가 API 요청의 사건과 같을 때만 허용하고, 허용 후 중복 키워드 인자로 전달하지 않도록 분리했습니다. 실제 모델 재검증은 추가 승인 전까지 보류했습니다.

## Gemini Agent 실제 재시험과 재구성 시각 주석

- 작업일: 2026-09-30

주요 작업:
- 추가 승인에 따라 같은 08:25 통제 질문을 실제 Gemini에 1회 재시험했습니다. 모델 선택 도구와 인자, 근거 번호, 최종 상태만 기록하고 API 키는 출력하지 않았습니다.
- 실제 답변이 사건의 08:27 유입을 `실제` 시점처럼 표현한 것을 확인하고, `NEEDS_SOURCE_PAGE` 근거를 사용한 답변에는 출처 페이지 확인 전의 재구성 시각이라는 주석을 자동으로 덧붙였습니다.

검증 결과:
- 실제 Gemini 재시험: `analyze_closure_timing(event_id=osong-2023, closure_times=[08:25])` 1회 호출 후 `ANSWERED`, `evidence_calls=[1]` 반환. 답변은 유입까지 2분이며 사망 예방 효과는 계산할 수 없다고 명시했습니다.
- 주석 추가 후 `python -m pytest backend/tests -q`: 68개 통과. 주석 변경에 대한 별도 외부 호출은 하지 않았습니다.

문제/해결:
- 문제: 첫 실제 테스트는 Agent 검증이 `event_id`를 거부해 도구 호출 없이 끝났고, 수정 후 재시험에서는 수치와 한계를 설명했지만 출처 페이지가 확인되지 않은 08:27을 `실제` 시점처럼 표현했습니다.
  해결: 사건 ID 검증 수정으로 실제 도구 호출을 성사시켰고, fallback 근거를 인용한 모든 답변에 재구성 시각 주석을 강제로 표시해 근거 수준이 드러나도록 했습니다.

## 시나리오 비교의 단계 색상과 읽는 순서 정리

- 작업일: 2026-09-30

주요 작업:
- 시나리오 비교의 제방 붕괴·유입 시작·주행불능 빠른 선택 버튼에 사건 단계 색상을 적용하고, 선택 상태를 `aria-pressed`로 표시했다.
- 기본 비교 시각이 사건 단계 시각과 같으면 중복 버튼을 숨겼다. 오송 사례의 `08:27`은 유입 시작 버튼 하나로 선택한다.
- 긴 `Comparison matrix`를 통제 여유, 통제 가정, 그대로인 사건 기록의 세 항목으로 바꾸고 통제 설정 바로 아래, 지도 위에 배치했다.

검증 결과:
- `npm run build`에서 TypeScript 검사와 Vite 빌드가 통과했다.
- `git diff --check`에서 공백 오류가 없었다. 커밋과 푸시는 하지 않았다.

문제/해결:
- 문제: 세 사건 단계 버튼과 기본 비교 버튼이 모두 청록색이라 단계의 위험 진행이 구분되지 않았고, 백엔드의 기본 통제 시각이 유입 시각과 같은 `08:27`이어서 같은 선택지가 두 번 표시됐다.
  해결: 이미 사건 재생에 쓰는 `STAGE_TONE`을 버튼에 재사용하고, 기본 시각이 단계 프리셋 중 하나와 같으면 기본 버튼을 렌더링하지 않았다. 단순 색상 수정만으로는 중복을 없앨 수 없어 선택지 생성 조건도 바꿨다.
- 문제: 기존 비교 표는 여섯 행을 지도 아래에 두고 동일한 사건 진행을 여러 번 적어, 사용자가 통제 시각 변경의 핵심 값인 유입 대비 시간 차이를 찾기 어려웠다.
  해결: 통제 조절 카드와 결과 요약을 지도 위로 옮기고, 첫 항목에 `유입 대비 통제 시점`을 크게 표시했다. 신규 진입 통제 시각만 가정하며 유입·침수 시각과 피해 효과는 바꾸거나 산출하지 않는다는 경계를 분리해 적었다.


## 첫 화면 소개·사례 선택 흐름과 관제 화면 한글화

- 작업일: 2026-09-30

주요 작업:
- 접속하면 소개 화면(로고, 세 줄 소개, 오른쪽 오송 지하차도 모식도, 떠다니는 기능 카드 3개) → 사례 선택(5개 사건, 오송만 `관제 가능`) → 오송 관제 화면 순서로 열리게 했다. 주소는 `#cases`, `#event/osong-2023` 해시로 나눠 브라우저 뒤로가기가 동작한다.
- 관제 화면 왼쪽 위 로고를 누르면 사례 선택으로 돌아간다.
- 사건 단계 이름·역할·신뢰도, 사건명·위치·대상 시설, 레이어 상태를 한글로 바꿔 보여 준다. 원본 API와 데이터의 영어 코드는 그대로 두고 `src/dark/ko.ts`에서 화면용으로만 바꾼다.
- `판단 우선순위 02 · 공간 상태`를 현재 단계의 침수 추정 셀 수와 지하차도까지 가장 가까운 셀 거리로 바꿨다(08:40 기준 352셀 · 119m).
- 오른쪽 단면 아래 관측 요약(강우 피크, 수위 피크, 관측 기간, 공식 침수범위 PENDING)을 뺐다.

검증 결과:
- `tsc --noEmit` 오류 없음, vitest 2개 통과.
- 1440×810 헤드리스 캡처로 소개 → 사례 선택 → `#event/osong-2023` 이동, 뒤로가기 시 `#cases` 복귀, 로고 클릭 시 `#cases` 이동을 확인했다.

문제/해결:
- 문제: 접속하자마자 오송 관제 화면이 떠서 서비스가 무엇인지, 다른 사례가 있는지 알 수 없었다.
  해결: 소개와 사례 선택을 앞에 두고, 데이터가 연결되지 않은 4개 사건은 `데이터 연결 예정`으로 잠가 눌러도 빈 화면이 나오지 않게 했다.
- 문제: `02 · 공간 상태`가 고정 문장이라 단계를 바꿔도 아무것도 달라지지 않아 무엇을 뜻하는지 알 수 없었다.
  해결: 현재 단계 HAND 셀의 `stage_index`, `distance_to_underpass_m`로 셀 수와 최근접 거리를 계산해 보여 준다. 거리는 셀 중심 기준이라 셀 크기(약 280×350m)보다 작으면 지하차도가 범위 안에 들어온 것으로 읽는다.
- 문제: 단계 이름(`Full inundation`), 역할(`Validation Target`), 신뢰도(`NEEDS_SOURCE_PAGE`), 제목 라벨(`Decision priority` 등)이 영어로 나왔다.
  해결: 백엔드와 처리 데이터의 코드값은 테스트와 Agent 도구가 쓰므로 바꾸지 않고, 화면에 넘기기 직전에 번역한다. 같은 시간 `DarkConsole.tsx`를 다른 작업이 고치고 있어 파일 전체를 다시 쓰지 않고 정확한 문자열 치환만 한 번에 적용했다.

## CASE LIBRARY를 중앙 가로 순환 목록으로 변경

- 작업일: 2026-09-30

주요 작업:
- 사례 카드 그리드를 화면 중앙의 가로 한 줄 캐러셀로 바꾸고 현재 사례와 좌우 이웃 사례를 표시했다.
- 카드 영역에서 휠을 내리면 다음 사례, 올리면 이전 사례로 이동하며 마지막과 첫 사례가 순환하도록 인덱스를 계산했다.
- 좌우 버튼, 방향키, 현재 위치 표시를 추가하고 오송 사례만 관제 화면을 여는 기존 상태 구분을 유지했다.

검증 결과:
- `npm run build`에서 TypeScript 검사와 Vite 빌드가 통과했다.
- 휠 리스너는 `passive: false`로 등록하고 컴포넌트 정리 시 해제하도록 코드에서 확인했다. 브라우저 화면 캡처 검증은 수행하지 않았다.
- 커밋과 푸시는 하지 않았다.

문제/해결:
- 문제: 기존 `CASE LIBRARY`는 카드가 여러 열 그리드로 펼쳐져 있어 휠로 사례를 한 장씩 넘기거나 마지막에서 첫 사례로 이어서 탐색할 수 없었다.
  해결: 선택 인덱스를 사례 수로 나눈 나머지로 순환시키고, 가운데 카드와 좌우 이웃만 보이는 가로 배치를 적용했다. 휠 한 번에 여러 단계가 건너뛰지 않도록 380ms 전환 구간을 두었다.
- 문제: 화면에서 같은 사례를 여러 번 복제해 무한 스크롤을 만들면 카드 키와 선택 동작이 중복될 수 있다.
  해결: 각 사례는 한 번만 렌더링하고 상대 위치만 계산해 순환시켰다. 준비 중인 사례의 비활성화 상태는 그대로 유지했다.
- 문제: 처음 시도한 CSS 치환은 다른 미커밋 변경으로 그리드 최소 폭이 300px에서 240px로 달라져 중단됐다.
  해결: 현재 파일의 240px 규칙만 대상으로 다시 적용하고, 함께 추가된 소개 화면 스타일은 보존했다.
## HAND 붉은 셀 변화 시나리오와 Agent 분석 도구 연결

- 작업일: 2026-09-30

주요 작업:
- 임시 HAND 재구성의 선택 임계를 0~2.5m 낮춰 기존 셀을 재분류하는 `POST /api/events/{event_id}/analysis/hand-threshold`와 `analyze_hand_threshold` Agent 도구를 추가했다. 사건 시각·관측값은 고정하고 미호강 측 4방향 연결 조건을 다시 확인한다.
- 시나리오 비교 화면의 기본 탭에서 기준·변경 지도와 단계별 셀 수를 나란히 보여주며, 제외된 셀을 청록색으로 표시했다. 기존 통제 시각 비교는 별도 탭으로 유지했다.
- Agent 시작 질문과 결과 표, README, 제출 초안의 대표 사용 장면을 HAND 셀 변화로 갱신했다. 변경량은 실제 차수벽·제방 효과나 검증된 침수 감소량이 아님을 표시했다.
- `docs/submission/screenshots/hand-threshold-1_5m.png`에 08:27 단계의 비교 화면을 캡처했다.

검증 결과:
- 별도 포트 8034의 최신 백엔드에서 1.5m 가정 시 08:27 단계는 기준 306셀, 유지 283셀, 제외 23셀로 응답했다. 0m 가정은 7단계 모두 기준 셀 수를 재현한다.
- `python -m pytest backend/tests -q` 71건 통과, `npm test -- --run` 2건 통과, `npm run build` 통과했다.
- 5174 프런트엔드와 8034 API에서 비교 화면을 확인했고, 두 지도 모두 같은 중심·배율에서 현재 화면에 보이는 셀 42개 중 기준 지도는 붉은 셀 42개, 변경 지도는 붉은 셀 37개·청록 셀 5개였다. 전체 셀 수 306→283과 화면 내 표시 수는 범위가 다르다.
- 기존 8033 서버는 이전 API 상태여서 새 엔드포인트가 404였다. 기존 프로세스를 변경하지 않고 8034에서 최신 코드를 실행했다.
- 실제 Gemini 질문은 네트워크 연결이 허용된 8035 백엔드에서 `ANSWERED`로 완료했고, `analyze_hand_threshold`를 호출해 7단계 셀 수와 근거 번호 `[1]`을 답했다. 검증용 5174 화면은 8035 API를 바라보도록 실행했다.

문제/해결:
- 문제: 08:25 지하차도 통제 질문은 유입까지 남은 시각만 바꾸고 두 지도에 같은 붉은 HAND 셀을 보여주어 사용자가 원하는 시나리오 변화를 나타내지 못했다.
  해결: 임시 HAND 선택 임계를 사용자가 지정해 바꾸는 공간 민감도 분석을 추가하고, 서버가 반환한 셀 ID로 오른쪽 지도의 붉은 셀과 청록 제외 셀을 재분류했다. 물리적 개입 효과로 환산할 근거가 없어 제방·차수벽 저감량이라는 이름을 쓰지 않았다.
- 문제: 첫 헤드리스 캡처는 지도 타일과 GeoJSON 렌더링이 끝나기 전에 찍혀 오른쪽 지도에 붉은 셀이 보이지 않았다.
  해결: 지도 로딩 후 MapLibre의 렌더링 피처 수를 확인하고 다시 캡처해 37개 붉은 셀과 5개 청록 셀이 현재 화면에 표시됨을 검증했다.
- 문제: 기존 제출 초안의 대표 장면과 6종 도구·단일 워크플로 설명이 현재 Agent와 HAND 비교 기능을 반영하지 못했다.
  해결: 대표 질문을 HAND 임계 1.5m 비교로 바꾸고 7종 도구, 연속 도구 호출, 수치 근거 검사와 한계를 적었다.
- 문제: 기본 제한 환경의 8034 백엔드는 Gemini 연결 시 `ConnectError`를 반환해 실제 Agent 도구 선택을 검증할 수 없었다.
  해결: 8035 백엔드를 네트워크 연결 가능한 환경에서 실행해 같은 질문의 도구 호출과 근거 답변을 확인하고, 검증용 화면의 API 대상을 8035로 바꿨다.

## Agent 없이 시나리오 비교 입력과 결과를 구분

- 작업일: 2026-09-30

주요 작업:
- 시나리오 비교 상단에 두 독립 분석의 선택 카드를 배치해 HAND 판정 임계→지도 선택 셀 수, 지하차도 통제 시각→유입 전후 시간차의 대응 관계를 표시했다.
- HAND 민감도 분석의 초기 입력을 1.5 m 감소에서 기준 그대로인 0 m로 바꾸고, 조절값과 선택 셀 수를 위험도 점수 또는 실제 침수 감소로 읽지 않도록 문구를 고쳤다.
- 통제 시각 분석에 현재 선택한 통제 시각을 입력 라벨로 표시하고, 침수 위험도 자체는 재계산하지 않는다고 명시했다.

검증 결과:
- `npm run build`에서 TypeScript 검사와 Vite 빌드가 통과했다.
- `python -m pytest backend/tests/test_api.py -k 'hand_threshold or closure_timing' -q`에서 분석 API 관련 9개 테스트가 통과했다.
- Agent 호출 없이 두 분석이 각각 `/api/events/{event_id}/analysis/hand-threshold`와 `/api/events/{event_id}/analysis/closure-timing`을 호출하는 코드를 확인했다. 커밋과 푸시는 하지 않았다.

문제/해결:
- 문제: Agent 연결이 되지 않는 상태에서 비교 화면의 두 탭이 각각 무엇을 선택하고 어떤 결과를 보여 주는지 드러나지 않았고, HAND의 붉은 셀 수가 실제 홍수 위험도처럼 읽힐 수 있었다.
  해결: 분석 유형마다 바꿀 값과 볼 값을 화면 맨 위에 적고, 실제 위험도 점수·침수심·피해 감소율은 계산하지 않는다고 명시했다. Agent 연결은 필수 조건이 아니지만 분석 API 연결은 필요하다고 구분했다.
- 문제: HAND 화면이 1.5 m 감소 가정으로 시작해 사용자가 입력을 고르기 전에 두 지도가 달라졌다.
  해결: 기본값을 0 m로 설정하고 '기준 그대로' 버튼과 라벨을 제공했다. 사용자가 임계 감소량을 직접 고른 뒤 셀 수 변화를 보도록 했다.
## AWS 배포 상태 확인

- 작업일: 2026-09-30

주요 작업:
- AWS CLI 설치 위치와 현재 계정·리전, ECR·ECS 자원, Docker 실행 도구와 배포용 Dockerfile을 확인했다.
- 로컬 Docker가 없는 환경에서 CodeBuild로 현재 작업 트리의 이미지를 빌드하고 ECR에 보낸 뒤 ECS Express Mode로 공개하는 경로를 검토했다.

검증 결과:
- AWS CLI 2.37.6, 계정 `588622053683`의 root 자격, 리전 `ap-northeast-2`를 확인했다. 기존 ECR 저장소와 ECS 클러스터 목록은 비어 있다.
- 로컬 Docker 실행 파일은 확인되지 않았고, `Dockerfile.aws`와 `.dockerignore`는 존재한다. `data/processed/osong`은 41개 파일, 약 75.2MB다.
- AWS 배포 자원은 생성하지 않았다. 현재 root 계정을 사용할지 사용자 선택을 요청한 상태다.

문제/해결:
- 문제: 앞선 HAND 기능 검증에서 테스트·브라우저 캡처를 반복하면서 사용자가 요청했던 실제 AWS 배포가 진행되지 않았다.
  해결: 로컬 검증을 멈추고 AWS 인증·빌드 도구·기존 자원 상태를 확인했다. root 계정에 새 과금 자원을 만들기 전 계정 선택이 필요해 해당 결정을 요청했다.

## 지도 레이어 응답 지연 해소와 남은 영어 문구·자료 목록 정리

- 작업일: 2026-09-30

주요 작업:
- `GET /api/events/{event_id}/layers`가 매 요청마다 약 30MB GeoJSON을 깊은 복사·직렬화하던 것을 `(event_id, layer_year)`별로 한 번만 직렬화해 재사용하도록 바꾸고, `GZipMiddleware(minimum_size=1024)`를 추가했다.
- HAND 민감도 API의 `coverage_note` 영어 문장을 화면에서 한글로 보여 주도록 `src/dark/ko.ts` 번역표에 추가했다. 원시나리오 카드의 영어 제목·설명(`Baseline: 2023 observed incident sequence` 등)도 같은 방식으로 한글화했다.
- `data/manifests/source-availability.yml`의 `osong_event_report`를 실제 문서(한국도로공사 도로교통연구원 「고속도로 유지관리 공사 형태에 따른 안전관리 개선 방안 연구」)로 고치고, 사건 타임라인 출처는 국무조정실 감찰 결과(2023-07-28)임을 적었다.
- 셸 인용 오류로 저장소 루트에 생긴 빈 파일 7개(`{`, `{0`, `({,`, `div`, `temporary` 등)를 지웠다.

검증 결과:
- `/layers` 응답: 변경 전 9.1초 → 첫 요청 6.5초, 이후 1.5초. gzip 전송 크기 4,016,345바이트.
- `python -m pytest backend/tests -q` 71개 통과, `tsc --noEmit` 오류 없음.
- `/api/agent/ask`에 실제 질문 2개("08:10에 통제했으면…", "지하차도 주변 500m…")를 보내 각각 `analyze_closure_timing`, `get_exposure_inventory`를 호출하고 `ANSWERED`로 끝나는 것을 확인했다(18~22초).
- 국무조정실 감찰 결과 원문에서 04:10, 06:40, 07:50, 08:09, 08:27, 08:35, 08:40 일곱 시각을 모두 확인했다.

문제/해결:
- 문제: 시나리오 비교에서 통제 시각을 바꾸면 결과가 6~12초 동안 `계산 중`으로 남았다. `closure-timing` 단독 응답은 0.005초였다.
  해결: 같은 서버에 먼저 들어간 `/layers` 요청이 9초 동안 직렬화하느라 뒤 요청이 밀린 것이었다. 데이터는 이미 `lru_cache`로 메모리에 있었지만 `get_layers`의 `deepcopy`와 FastAPI 인코딩이 매번 돌았다. 호출부(`get_layers`)의 복사 동작은 다른 서비스가 수정 가능한 사본을 기대하므로 두고, 엔드포인트에서 직렬화 결과만 캐시했다.
- 문제: 자료 목록이 CODIL PDF를 "2023 Osong underpass flood incident context"로 기록해, 기획서 출처 정리 때 사건 보고서로 오인할 뻔했다.
  해결: 본문을 확인해 오송 참사는 6.5.3절(66~67쪽)에 중대시민재해 사례로만 언급됨을 확인하고, 타임라인 근거로 쓰지 말라는 `usage_note`를 달았다.
- 문제: Codex 쪽에서 Gemini 연결이 계속 막혔다.
  해결: 코드 문제가 아니라 실행 환경 문제였다. Codex 기록상 제한 환경의 백엔드는 Gemini 연결에서 `ConnectError`가 났고, 실제 호출은 자동 승인 검토에서 여러 번 거절됐다. 네트워크가 열린 로컬 8033 서버에서는 같은 코드로 도구 호출과 답변이 정상 동작했다.

## AWS 배포: 반지하 서버에 FloodOps 컨테이너 추가

- 작업일: 2026-10-01

주요 작업:
- 공개 주소 `https://floodops.54-180-81-225.sslip.io`로 FloodOps를 배포했다. 새 서버를 만들지 않고 기존 `basement-flood` EC2(t3.micro, ap-northeast-2c, Amazon Linux 2023)에 컨테이너 `floodops`(127.0.0.1:8000, `--memory 600m`, `--restart unless-stopped`)를 추가하고, 기존 Caddy에 사이트 블록을 더했다. 기존 Caddyfile은 `~/app/Caddyfile.bak-<시각>`으로 백업했다.
- 쓰지 않는 `ssoyoum` EC2(t3.micro, 9/8 생성)를 중지했다. 삭제는 하지 않았다.
- 이미지는 서버 메모리를 아끼려고 프런트엔드를 로컬에서 `VITE_API_BASE=same-origin`으로 빌드한 뒤, Python 런타임만 서버에서 빌드했다(`floodops:20260930-1504`). 쓰지 않는 건물 QA(31MB)·OSM 건물·CODIL 텍스트는 패키지에서 뺐다.

검증 결과:
- HTTPS `/health` 200, 헤드리스 브라우저로 소개 → `#event/osong-2023`(7단계) → 시나리오 비교 통제 시각(08:09 → `제방 붕괴 전 선제 통제`, 0.5초) 확인, 4xx/5xx 응답 없음.
- 반지하 서비스 `https://basement-flood.duckdns.org/`, `https://54-180-81-225.sslip.io/` 모두 200 유지.
- 컨테이너 메모리: floodops 291MB/600MB, basement 122MB, caddy 9MB. 서버 여유 메모리 약 106MB, 스왑 2GB.
- 계정은 무료 요금제, 남은 크레딧 $101.89(만료 2027-03-08).

문제/해결:
- 문제: 9월 비용 $17.77(크레딧 차감)이 나와 확인하니 t3.micro 2대가 켜져 있었다(서버 $10.84, 공인 IPv4 $4.18, EBS $2.75). 여기에 새 서버를 더하면 월 약 $55로 크레딧이 11월 말에 바닥나 12월 본선 시연 전에 계정 접근이 끊길 수 있었다.
  해결: 사용자가 반지하 서버만 쓴다고 확인해 나머지 서버를 중지하고, FloodOps는 반지하 서버에 얹었다. 서버 사양을 올리면 재시작 때 공인 IP가 바뀌어 `54-180-81-225.sslip.io` 주소가 끊기므로 사양은 유지하고 컨테이너 메모리 상한으로 관리했다.
- 문제: 로컬 Docker 설치가 실패했다.
  해결: 로컬 Docker 없이 EC2 Instance Connect로 60초 임시 키를 넣어 접속하고, 서버의 Docker로 빌드했다.
- 남은 문제: 서버에 `GEMINI_API_KEY`를 넣지 않아 배포본의 Agent는 규칙 기반 안내로만 동작한다.

## 제방 증고 질문의 Agent 응답과 도구 경계 수정

- 작업일: 2026-10-01

주요 작업:
- `제방을 3미터 올린다면?`에 대해 Gemini가 도구 부재를 설명했어도 서버가 이를 일반 오류로 바꾸던 경로를 수정했다. 지원하지 않는 계산은 `physical_intervention` 등 결손 유형으로 받고, 실제 제방 효과에 필요한 자료와 모델을 답변에 명시한다.
- 제방·차수벽·펌프 등 시설을 올리거나 변경하는 질문의 수치를 HAND 임계 감소량으로 넘기지 못하게 했다. 사건 정보 조회 결과만 인용해 제방 효과를 계산했다고 답하는 경로도 막았다.
- 제방 질문, 잘못된 HAND 도구 선택, 사건 정보만 인용한 효과 답변을 검증하는 회귀 테스트 3개를 추가하고, 5174 화면이 사용하는 8035 로컬 백엔드를 재시작했다.

검증 결과:
- `python -m pytest backend/tests -q`: 79개 통과.
- 실제 Gemini 호출과 `http://127.0.0.1:8035/api/agent/ask`에서 해당 질문은 `NEEDS_DATA`, 도구 호출 0건으로 끝났고, 제방 단면·경계조건·검증된 수리모형의 부재 및 HAND 분석과의 차이를 설명했다.
- 배포본은 이번 코드 수정이 반영되지 않았다.

문제/해결:
- 문제: Gemini는 제방 증고에 맞는 물리 모델이 없다는 점을 파악했지만 `ask_agent`가 도구 호출 없는 최종 설명을 버려 `사건·시각·비교 조건을 구체적으로 알려주세요`라는 무관한 문장을 보냈다.
  해결: 계산 불가 사유를 구조화하고 질문 종류에 맞는 한계를 서버에서 설명하게 했다. 정량 효과를 꾸며 내지 않도록 수리모형·개입 형상·경계조건이 연결되기 전에는 결과값을 제시하지 않는다.
- 문제: `올린다면` 활용형이 시설 변경 검사에 걸리지 않았고, 제방 높이 1.5m를 HAND 임계 1.5m로 잘못 해석할 수 있었다.
  해결: 해당 활용형을 포함한 물리 개입 검사를 도구 실행과 최종 답변 양쪽에 적용했다. HAND 도구는 명시적인 판정 기준 변경 질문에서만 쓰도록 프롬프트도 보강했다.


## Agent 사용법 질문 응답과 간헐적 Gemini 형식 오류 복구

- 작업일: 2026-09-30 ~ 2026-10-01

주요 작업:
- `/api/agent/ask`가 “무슨 질문 할 수 있어?” 같은 사용법 질문에 등록된 예시 질문 5개와 각 분석의 의미·한계를 한국어로 답하도록 했다. 이 경우 사건 사실을 주장하지 않으므로 Gemini 호출과 도구 호출 없이 `ANSWERED`를 반환한다.
- Gemini가 HTTP 200 이후 해석할 수 없는 도구 결정을 반환하면 같은 입력으로 한 번 더 요청하도록 했다. 네트워크 오류와 HTTP 오류는 기존처럼 즉시 실패 처리한다.
- 근거 없는 질문에는 내부 도구 오류 문구 대신 통제 시각과 HAND 민감도 질문 예시를 안내하고, 화면에서 `UNAVAILABLE`과 `NEEDS_DATA`를 성공 답변과 다른 색으로 표시한다. 요청 실패 시 질문 입력을 유지한다.
- 수정 전 코드를 계속 제공하던 로컬 8033 API 프로세스를 확인한 뒤 같은 인자로 재시작했다.

검증 결과:
- Google Gemini 모델 조회는 HTTP 200, 사건 자료를 제외한 진단 입력의 JSON 결정도 정상 반환했다.
- 수정 전 8033의 HAND 질문은 도구 1회 호출 뒤 `UNAVAILABLE`과 `Gemini returned no valid tool decision.`을 반환했고, 같은 질문의 별도 실행은 `ANSWERED`를 반환해 간헐적 형식 오류를 확인했다.
- `python -m pytest backend/tests/test_agent_help.py backend/tests/test_agent_response_recovery.py backend/tests/test_api.py -q`: 61 passed.
- `npm run build`와 `git diff --check` 통과. 빌드는 기존 500 kB 초과 청크 경고만 출력했다.
- 재시작한 8033에서 “그럼 무슨 질문 할수있어?”는 `ANSWERED`와 HAND 질문 예시를 반환했고, HAND 1.5 m 대표 질문은 `analyze_hand_threshold` 호출 뒤 `ANSWERED`를 반환했다.

문제/해결:
- 문제: “그럼 무슨 질문 할수있어?”는 사건 수치 요청이 아닌 사용법 질문인데, 기존 Agent가 도구 호출 없는 모든 최종 답변을 `NEEDS_DATA`로 바꿔 “등록 데이터나 분석 도구를 찾지 못했습니다”와 영어 제한 문구를 보여줬다.
  해결: 사용법 의도를 먼저 판별하고 실제 등록된 예시와 HAND 분석 범위로 안내 답변을 구성했다. 근거 없는 사건 답변까지 자유롭게 허용하면 수치·기능을 지어낼 수 있으므로 일반 사건 질문의 도구 근거 검사는 유지했다.
- 문제: 실제 HAND 질문에서 Gemini가 분석 도구 결과를 받은 뒤 간헐적으로 해석 불가능한 결정을 반환해 Agent가 연결 실패처럼 보였고, 화면의 결과 테두리는 성공과 같은 녹색이었다.
  해결: HTTP 200의 응답 형식 오류에만 1회 재시도를 추가했다. 실패 상태는 빨간색, 근거 부족은 노란색으로 표시하고 입력을 남겨 사용자가 다시 시도할 수 있게 했다.
- 문제: 코드 수정 후에도 실행 중인 8033 서버는 이전 응답을 계속 반환했다.
  해결: 해당 포트의 프로세스 실행 인자가 이 저장소의 `uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8033`임을 확인한 후 동일 인자로 재시작하고 실제 API 응답을 다시 확인했다.

## README를 현재 기능·자료·배포 상태로 갱신

- 작업일: 2026-10-01

주요 작업:
- README를 한국어로 다시 구성하고 소개 → 5개 사건 선택 → 오송 관제 흐름, 실제 사용 가능한 오송 분석과 나머지 4개 사건의 자료 연결 예정 상태를 구분했다.
- Gemini Agent의 7개 등록 도구, 자유 질의와 규칙 기반 계획의 차이, HAND 셀 민감도와 통제 시각 비교의 계산 범위, 제방 증고 질문에 필요한 미연결 수리모형을 설명했다.
- 공개 시연 주소와 로컬 실행·주요 API·검증 명령을 정리하고, 공개 서버에 Gemini 키가 없어 자유 질의를 사용할 수 없는 상태를 명시했다.

검증 결과:
- 공개 HTTPS `/health` 200, `/api/events` 200, `/api/agent/planner-status` 200에서 `available:false`와 Gemini 키 미설정 사유를 직접 확인했다.
- README의 상대 링크 12개가 모두 존재하며 `git diff --check -- README.md`에서 공백 오류가 없었다. 문서만 수정했으므로 코드 테스트는 다시 실행하지 않았다.

문제/해결:
- 문제: 기존 README는 공개 배포 URL과 5개 사건의 실제 연결 상태를 설명하지 않았고, 현재 기본 화면을 예전 별도 UI 브랜치의 선택적 미리보기로 적었다.
  해결: 실제 프런트엔드·사건 목록 구현과 공개 서버 응답을 기준으로 사용 흐름과 로컬·배포본 차이를 다시 썼다.
- 문제: Agent 설명만 읽으면 공개 시연에서도 Gemini 자유 질의가 되고 HAND 셀 변화나 통제 시각 차이가 실제 침수·피해 효과인 것처럼 이해될 수 있었다.
  해결: 배포본의 키 부재를 날짜와 함께 표시하고, 두 분석의 입력·출력·해석 한계 및 물리적 개입 계산에 필요한 자료를 분리해 기술했다.

## Agent 자연어 응답 보강과 호출량 제한

- 작업일: 2026-10-01

주요 작업:
- `backend/app/agent_runner.py`의 시스템 프롬프트를 재작성해, 계산할 수 없는 질문에도 실제 사건 시점을 인용하고 계산 불가 부분을 한 문장으로 밝힌 뒤 다음에 물을 질문을 제안하게 했다. 응답에 `follow_ups`(최대 3개)를 추가하고 화면에서 눌러 바로 묻는 버튼으로 표시했다.
- 가정형 질문(`으면|다면|라면|if`)이 도구 없이 끝나려 하면 서버가 `get_reconstruction`을 한 번 실행해 근거를 붙인 뒤 다시 답하게 했다.
- 강우·수위 피크와 관측 개수를 돌려주는 `get_observation_summary` 도구를 추가했다.
- 사용자가 사건 단계를 이름으로 가리키면("경보 나오자마자") `get_reconstruction`이 돌려준 단계 시각을 통제 시각으로 쓸 수 있게 했다. 임의 시각(예: 07:33)은 여전히 거부한다.
- 도구 근거가 없는 설명은 사용자가 쓴 숫자만 담을 때 모델 답을 그대로 쓰고, 한글이 없거나 15자 미만이면 고정 안내문으로 바꾼다. 시설 변경 질문에서 "줄어/감소/막을 수/예방" 같은 효과 주장이 있으면 막는다.
- `backend/app/rate_limit.py`를 추가해 `/api/agent/ask`와 LLM을 쓰는 `/api/agent/plan`에 IP당 분당 6회·일 60회, 전체 일 500회 제한(환경변수로 조정)을 걸었다. 429 응답의 한글 사유를 화면에 그대로 표시한다.

검증 결과:
- `python -m pytest backend/tests -q` 86개 통과(새 테스트 7개 포함), `tsc --noEmit` 통과.
- 실제 Gemini(`gemini-3.5-flash-lite`) 질문 결과:
  - "그날 비가 얼마나 왔어?": `get_observation_summary` 호출, 32.5mm/h(청주금천 06:00)·10.09m(미호강교 09:20) 인용.
  - "제방을 3미터 올린다면?": `get_reconstruction` 호출, 수리모형 부재 설명, 08:09·07:50 통제와 30분 지연 후속 질문 제안.
  - "비가 덜 왔으면 어땠을까?": 자동 근거 조회 후 계산 불가 부분과 실제 시점(04:10·07:50·08:09·08:27) 인용.
- 배포본 `floodops:20260930-1541` 재시작, 공개 주소 `/health` 200.

문제/해결:
- 문제: "제방을 3미터 올린다면?"에 "등록 데이터나 분석 도구를 찾지 못했습니다" 같은 일반 안내가 나왔다. 모델이 한계를 설명해도 서버가 모든 도구 없는 최종 답을 고정 문구로 바꿨기 때문이다.
  해결: 숫자 근거 검사를 통과하는 모델 설명은 그대로 쓰고, 시설 질문에는 수리모형·HAND 한계 문장만 덧붙였다. 막는 기준(근거 없는 숫자, 계산하지 않은 효과 주장)은 유지했다.
- 문제: 가정형 질문에서 모델이 도구를 건너뛰고 답을 만들다 근거 검사에 걸려 고정 문구로 떨어졌다. 처음 쓴 가정형 패턴(`었으면|았으면`)은 음절 단위라 "왔으면·됐으면"을 놓쳤다.
  해결: 패턴을 `으면`으로 넓히고, 최종 답 전에 사건 경과를 한 번 자동 조회하도록 했다.
- 문제: "비가 덜 왔으면"에서 모델이 강우 수치를 쓰려 해도 강우 값을 주는 도구가 없어 근거 검사에서 막혔다.
  해결: 요약 API의 관측 피크를 그대로 돌려주는 도구를 추가했다.
- 문제: 셸 heredoc으로 정규식을 고치면서 ``가 백스페이스(``)로 저장돼 `if` 경계 검사가 깨졌다.
  해결: 수정 스크립트를 파일로 써서 실행하고, 코드에 ``이 남지 않았는지 확인했다.
- 문제: 공개 주소에서 누구나 Agent를 호출하면 Gemini 무료 한도가 소진될 수 있었다.
  해결: 단일 워커 배포에 맞는 프로세스 내 카운터로 IP·전체 한도를 걸었다. Caddy가 설정하는 `X-Forwarded-For` 첫 값을 사용자 IP로 쓴다.

## README 첫 화면에 재구성 흐름 표시

- 작업일: 2026-09-20

주요 작업:
- 관측 시계열과 공간자료가 오송 사건 replay, intervention 비교, 지도·근거 패널로 이어지는 구조를 README 상단 Mermaid 도식으로 표시했다.
- Agent는 분석 숫자를 생성하는 단계가 아니라 등록 workflow를 선택하는 단계로 구분했다.

검증 결과:
- `npm run build`: TypeScript 검사와 Vite 빌드 통과(큰 번들 경고 1건).
- `npm test -- --run`: 1개 파일, 2개 테스트 통과.

문제/해결:
- 문제: README 첫 화면이 역할과 제약을 긴 문장으로 설명해 실제 데이터 흐름을 파악하려면 아래로 내려가야 했다.
  해결: 기존 구현 범위를 여섯 노드 도식과 네 가지 핵심 개념으로 요약하고 상세 출처 문서에 연결했다.
- 이 변경 시점에는 실제 UI 스크린샷과 GitHub About metadata가 추가되지 않았다. 작업 환경의 GitHub 브라우저가 로그아웃 상태였고 로컬 개발 서버가 브라우저에서 열리지 않아, 검증되지 않은 화면 이미지는 만들지 않았다.

## 공개 서버 관제 화면 로딩 실패 대응

- 작업일: 2026-10-01

주요 작업:
- `/layers` 응답을 `(event_id, layer_year)`별로 gzip 압축한 바이트까지 캐시해 그대로 보내고(`Content-Encoding: gzip`, `Vary: Accept-Encoding`), 공통 `GZipMiddleware`는 `/layers` 경로를 건너뛰게 했다.
- 서버 시작 시 백그라운드 스레드로 오송 기본 레이어(2023)를 미리 직렬화·압축한다.
- 화면의 사건·레이어 요청은 실패하면 2초·4초 뒤 최대 3회까지 다시 시도한다.

검증 결과:
- `python -m pytest backend/tests -q` 88개 통과(이중 압축이 없는지 확인하는 테스트 2개 추가), `tsc --noEmit` 통과.
- 로컬 gzip 레이어 응답 0.09초(이전 1.5초), 전송 4,103,289바이트.
- 공개 서버 측정(수정 전): 압축 없이 46.9초, gzip 요청 6.7~14.2초.

문제/해결:
- 문제: 공개 주소에서 "이 사례의 관제 데이터를 불러오지 못했습니다"가 떴다. 다른 API는 1초 안에 응답했지만 레이어만 압축 요청에도 6~14초, 압축 없이 47초가 걸렸다.
  해결: 1 vCPU 서버에서 30MB를 매 요청마다 압축하는 비용과 재시작 직후 첫 직렬화 비용이 원인이라 보고, 압축 결과를 캐시하고 시작 시 미리 만들도록 했다. 일시적 실패에 바로 오류 화면을 띄우지 않도록 화면 쪽 재시도도 넣었다.
- 문제: 서버의 FastAPI 0.115/Starlette 버전에서 이미 압축된 응답을 미들웨어가 다시 압축할지 확실하지 않았다.
  해결: 레이어 경로만 미들웨어를 우회하게 감싸고, 응답 JSON이 한 번만 풀리는지 테스트로 확인했다.
- 남은 문제: 서버 반영은 AWS 로그인 세션 만료로 보류했다(`aws login` 재인증 필요).

## 도입 화면을 노트북 높이에 맞게 압축

- 작업일: 2026-10-01

주요 작업:
- 도입 화면에 `fo-intro` 클래스를 분리해 로고를 44px에서 34px로, 제목을 최대 40px로 줄이고 상하 여백·본문 간격·기능 카드 패딩을 압축했다.
- 높이 720px 이하 화면에는 더 작은 제목·여백·모식도 패딩을 적용했다. 사례 선택 화면의 배치는 바꾸지 않았다.

검증 결과:
- `npm.cmd run build`에서 TypeScript 검사와 Vite 빌드가 통과했다. 500 kB 초과 번들 경고는 남아 있다.
- 로컬 도입 화면을 1280×720, 1366×768, 1440×810으로 캡처해 로고부터 하단 출처 안내까지 한 화면에 표시되는 것을 확인했다. 검증용 PNG는 삭제했다.

문제/해결:
- 문제: 도입 화면의 44px 로고, 44px 제목, 30px 섹션 간격과 큰 카드 패딩이 합쳐져 노트북 높이에서 세로 스크롤을 유발했다.
  해결: 도입 화면에만 압축 스타일을 적용하고 화면 높이가 낮을 때 추가로 축소했다. 단순 `overflow: hidden`으로 내용을 가리는 방법은 쓰지 않았다.

## 도입 카드의 위아래 이동 효과 제거

- 작업일: 2026-10-01

주요 작업:
- 기능 카드의 `fo-float` 애니메이션을 제거하고 사용하지 않는 키프레임을 삭제했다.
- 카드 테두리 강조와 빛 스윕은 유지했다.

검증 결과:
- `landing.css`에서 `fo-float` 참조가 사라지고 기능 카드의 애니메이션이 `fo-edge`만 남은 것을 확인했다.
- `git diff --check`에서 변경 파일의 공백 오류가 없었다. CSS 선언만 수정해 빌드는 다시 실행하지 않았다.

문제/해결:
- 문제: 도입 화면의 기능 카드가 `translateY(-7px)`를 반복해 위아래로 떠다녔다.
  해결: 이동을 만드는 `fo-float`만 애니메이션 목록에서 빼고 키프레임을 삭제했다.

## Agent가 계산 가능한 유입 지연 질문을 거절하던 문제

- 작업일: 2026-10-01

주요 작업:
- 질문에 적힌 값으로 실행할 수 있는 등록 도구를 규칙으로 찾아(`_router_hints`: 유입 지연 분, 통제 시각, 반경, HAND 임계, 강우·수위) 모델 입력의 `suggested_tools`로 전달하고, 모델이 그 도구를 부르지 않고 끝내려 하면 서버가 한 번 직접 실행한 뒤 다시 답하게 했다.
- 모델이 보내는 `10.0`, `"10"`, `"8:10"` 같은 값을 정수·`HH:MM`으로 정리한 뒤 검증한다.
- Agent 반복 호출의 Gemini 대기 시간을 10초에서 25초(`AGENT_ASK_TIMEOUT_SECONDS`)로 늘리고, Gemini가 끝내 응답하지 않거나 반복 실패하면 질문에 적힌 값으로 도구를 실행해 결과 표를 보여 준다.

검증 결과:
- `python -m pytest backend/tests -q` 91개 통과(거절 방지, Gemini 불가 시 도구 실행, 값 형식 정리 테스트 추가).
- 실제 Gemini: "유입이 10분 늦춰졌다면 주행불능 시각은?" → `analyze_inflow_delay`, 08:45. "차수벽으로 유입이 30분 늦어졌다면?" → 유입 08:57·주행불능 09:05·완전침수 09:10. "유입이 15분 지연되면 완전 침수는?" → 08:55.
- 공개 배포본 `floodops:20261001-0111`에서 같은 질문이 `ANSWERED`, `analyze_inflow_delay` 호출.

문제/해결:
- 문제: 후속 질문 버튼이 제안한 "유입이 10분 늦춰졌다면 주행불능 시각은?"에 Agent가 "지연 시뮬레이션 기능이 없어 계산할 수 없다"고 답했다. `analyze_inflow_delay`가 있는데도 거절했다.
  해결: 원인은 두 가지였다. 이전 작업에서 "다면"이 들어간 질문에 "계산 불가 부분을 밝혀라"는 지시를 붙여 모델이 거절 쪽으로 기울었고, 모델이 도구를 불러도 `delay_minutes`를 `10.0`처럼 보내 정수만 받는 검증에서 6번 모두 거부됐다. 지시를 "맞는 도구가 있으면 먼저 실행"으로 바꾸고, 값 형식을 정리한 뒤 검증하며, 그래도 실패하면 사용자가 쓴 값으로 서버가 직접 실행하도록 했다.
- 문제: 같은 질문에서 Gemini가 10초 안에 응답하지 않아 `ReadTimeout`으로 끝나는 경우가 있었다.
  해결: 도구 결과를 다시 보내는 반복 단계는 계획 엔드포인트보다 입력이 커서 25초로 따로 늘렸다. 계획 엔드포인트(`/api/agent/plan`)의 10초 제한은 그대로 두었다.

## "10분 일찍 차단" 같은 상대 시각 질문 처리

- 작업일: 2026-10-01

주요 작업:
- "N분 일찍·먼저·빨리 / N분 늦게" + 통제·차단 표현을 등록된 기준 통제 시각(관측 유입에 맞춘 08:27)에서 계산해 `analyze_closure_timing`의 통제 시각으로 쓰게 했다. 모델에는 기준 시각을 답에 밝히라는 메모를 함께 넘긴다.
- 통제 표현이 있고 "유입·지연"이 없으면 "늦게"를 유입 지연이 아니라 통제 시각 이동으로 해석한다.

검증 결과:
- `python -m pytest backend/tests -q` 92개 통과.
- 실제 Gemini: "차단을 10분 일찍한다면?" → 08:17 통제, 유입보다 10분 앞섬, 기준 08:27 명시. "통제를 20분 먼저 했으면?" → 08:07, 유입 20분·완전침수 33분 전. 공개 배포본에서도 같은 질문이 `analyze_closure_timing(08:17)`로 응답.

문제/해결:
- 문제: "차단을 10분 일찍한다면?"에 Agent가 "구체적인 시각 조건으로 다시 질의하라"며 계산을 거절했다.
  해결: 검증이 사용자가 직접 쓴 `HH:MM`과 사건 단계 시각만 허용해 상대 표현을 받을 수 없었다. 기준 통제 시각이 재구성 응답(`intervention.trigger_time`)에 이미 있어 그 값에서 계산한 시각을 허용 목록과 도구 추천에 더했다.

## 도입 화면 변경의 공개 배포 반영 확인

- 작업일: 2026-10-01

주요 작업:
- 도입 화면 크기 조정과 기능 카드 이동 애니메이션 제거가 공개 사이트에 반영됐는지 확인했다.
- 기존 EC2와 `floodops:latest` 컨테이너를 점검했고, 동일 자산이 이미 제공되고 있어 서버 빌드·재시작은 반복하지 않았다. 확인용 임시 SSH 키와 캡처 파일은 삭제했다.

검증 결과:
- `https://floodops.duckdns.org/health` 200, 공개 HTML의 CSS·JS 파일명이 로컬 `VITE_API_BASE=same-origin` 빌드와 일치했다.
- 공개 CSS `index-BD1YQqdD.css`와 JS `index-CQ1S4jUT.js`가 로컬 `dist`와 바이트 단위로 같았다. CSS에는 `.fo-intro`가 있고 `fo-float`가 없다.
- 공개 화면을 1280×720으로 캡처해 줄인 로고·제목과 하단 안내 문구가 한 화면에 보이는 것을 확인했다.

문제/해결:
- 문제: 로컬에서 수정한 도입 화면이 공개본에는 아직 없다고 알려진 상태라 사용자가 배포 반영을 요청했다.
  해결: 배포 대상과 자산을 비교해 확인 시점에는 동일 빌드가 이미 공개 제공 중임을 확인했다. 같은 파일을 다시 배포하면 EC2 CPU와 서비스 재시작만 추가하므로 중복 작업을 생략했다.

## Agent 도구 설명서를 프로젝트 기준으로 재작성

- 작업일: 2026-10-01

주요 작업:
- `backend/app/agent_tools.py`의 도구 8개에 한국어 `use_when`(언제 쓰는지)·`parameters`(입력값의 뜻과 허용 출처)·`can_say`·`cannot_say`·`examples`를 추가했다. API용 `name`·`input_fields`·`output`은 그대로 두었다.
- 시스템 프롬프트에 도구를 `use_when`으로 고르고 답을 `can_say` 안에서 쓰라는 문장을 넣었다.
- 반경에서 `1km`·`1.5 킬로`·`2킬로미터`를 미터로 읽게 했다.
- 도구 없이 끝난 설명에 붙은 `[1]` 같은 인용 번호를 지운다.

검증 결과:
- `python -m pytest backend/tests -q` 93개 통과.
- 실제 Gemini 10문항(로컬, 호출 한도 해제): 통제 상대 시각(10분 일찍 → 08:17), 경보 직후(04:10 → 257분), 제방 붕괴 시점(08:09 → 18분), 유입 20분 지연(완전침수 09:00), 강우·수위, 1km 건물(1,536동), 사고 경과는 맞는 도구로 `ANSWERED`. "주변에 뭐 있어?"는 반경을 되묻고, "제방 3m"·"몇 명 살릴 수"·"비가 덜 왔으면"은 계산 불가 이유와 관련 기록을 답했다.
- 공개 배포본에서 "지하차도 1km 안에 건물 몇 개야?" → `get_exposure_inventory([1000])`, 1,536동.

문제/해결:
- 문제: 도구 설명이 영어 한 줄이라 모델이 "언제 이 도구를 써야 하는지", "기준 통제 시각이 무엇인지", "무엇은 말하면 안 되는지"를 몰라 계산 가능한 질문을 거절하거나 엉뚱한 도구를 골랐다.
  해결: 프롬프트에 규칙을 더 붙이는 대신, 도구별로 사용 상황·입력값 출처·말할 수 있는 범위를 구조화해 모델 입력에 실었다. 반드시 지켜야 할 것(값 출처, 근거 숫자)은 여전히 서버 검증이 맡는다.
- 문제: 같은 시험에서 7번째 질문부터 429가 났다.
  해결: 분당 6회 제한이 의도대로 동작한 것이라 로컬 시험 서버만 환경변수로 한도를 풀었다. 공개 서버 한도는 그대로다.

## LLM planner 경로에 거부 게이트 적용

- 작업일: 2026-10-02

주요 작업:
- `backend/app/llm_planner.py`의 `plan_with_llm`이 Gemini를 부르기 전에 사용자 원문을 `_UNSUPPORTED_MARKERS`(사망자·피해액·침수심·예측 등)로 먼저 검사하고, 걸리면 모델 호출 없이 `UNSUPPORTED`를 반환하도록 했다.
- 검사 대상을 모델 출력이 아니라 원문으로 둬서, 모델이 표현을 바꿔 스스로 `unsupported`를 피해가는 경로를 막았다.
- `backend/tests/test_api.py`에 `httpx.post`가 호출되면 실패하는 테스트를 추가해, 거부 마커가 있으면 모델에 묻지도 않고 거절하는지 고정했다.

검증 결과:
- `python -m pytest backend/tests -q` 94개 통과(기존 93개 + 신규 1개).

문제/해결:
- 문제: 거부 마커 검사가 규칙 planner(`plan_agent_intent`)에만 있어, `plan_with_llm` 결과는 재검사 없이 그대로 계획으로 승격됐다. "사망자가 몇 명이야?"를 모델이 스스로 `unsupported`로 고르지 않으면 거부가 뚫리는 구조였다.
  해결: 같은 마커 검사를 LLM planner 진입점에 그대로 적용했다. 모델 호출 전에 걸러 API 비용도 줄었다.

## 지도 출처 표시와 situation 응답 보정, 브라우저 점검

- 작업일: 2026-10-02

주요 작업:
- 관제·비교 지도의 출처 표시에 `도로 © OpenStreetMap contributors`, `건축물 © 국토교통부 GIS건물통합정보`, `하천 WAMIS`를 추가하고, 접힌 `i` 버튼 대신 항상 펼쳐 보이게 했다.
- `situation` 워크플로 결과에 `coverage_status: fallback`과 `NEEDS_SOURCE_PAGE` 안내를 붙이고, 계획 단계 `assumptions`에 저장된 재구성 시각만 보여주며 공간 상태는 HAND 근사라는 점을 넣었다.
- 로컬(백엔드 8033, Vite 5173)에서 Edge headless로 인트로 → 사례 선택 → 관제 화면 7단계 재생·레이어 설정 → 시나리오 비교 → 인사이트를 실행하고 화면을 캡처했다.

검증 결과:
- `python -m pytest backend/tests -q` 94개 통과, `npm.cmd run build` 통과.
- 인트로 1280×720에서 `scrollHeight` 720 = 창 높이(스크롤 없음).
- 출처 표시가 펼쳐진 상태로 "하천 WAMIS | Tiles © Esri | 건축물 © 국토교통부 GIS건물통합정보 | 도로 © OpenStreetMap contributors"로 표시됨.
- 전체 흐름에서 브라우저 콘솔 오류 0건, `/api/` 4xx·5xx 0건. 비교 화면 지도 2개 렌더링.
- 화면에서 단계별 "출처 쪽수 확인 필요", "HAND 근사", "실측 수위가 아님", "실제 침수 위험 감소가 아닙니다" 문구를 확인했다.

문제/해결:
- 문제: 도로는 OSM(ODbL 1.0) 자료인데 지도에는 `Tiles © Esri`만 있었다. ODbL은 지도 자체에 OSM 출처를 보이게 하라고 요구하고, 공개 서버가 이미 이 상태로 서비스 중이었다. 09-30 기록에 "남은 문제"로만 적혀 있었다.
  해결: 지도 컨트롤에 자료 출처를 직접 넣었다. 레이어 소스마다 `attribution`을 다는 방법은 소스가 꺼지면 출처도 사라지므로 쓰지 않았고, 접힌 표시는 눌러야 보이므로 펼쳐 두었다.
- 문제: `situation`만 `coverage_status`가 `null`이고 `assumptions`가 비어 있었다. 다른 시간 분석과 같은 재구성 시각을 쓰는데도 근거 수준이 응답에 드러나지 않았다.
  해결: 같은 시각을 쓰는 `closure_timing`과 같은 `fallback` 등급을 주었다.
- 문제: 브라우저 도구 설치 명령이 scratchpad 경로 `cd` 실패로 저장소 루트에서 실행됐다. 설치는 되지 않았고 `package.json`도 바뀌지 않았지만, 빈 파일 `'`, `backend/'`가 생겼다.
  해결: 이 명령으로 생긴 두 빈 파일만 지우고, 그 전부터 있던 `MapLibre` 빈 파일은 그대로 두었다. `playwright-core`는 저장소 밖 scratchpad에 설치해 설치된 Edge로 실행했다.

## 오송 수위 기준면·제방고 자료 조사

- 작업일: 2026-10-02

주요 작업:
- NOW에서 자료 부족으로 막힌 항목(수위↔공간 연결, What-if C, 공식 시각 근거)에 필요한 자료를 저장소와 웹에서 찾았다.
- TODO의 HAND 단계별 셀 수와 DQ-008 항목을 09-30 재구성 결과에 맞게 고쳤다.

검증 결과:
- `data/raw/water_level/osong/hrfco_waterlevel_info.xml`을 파싱해 확인: 미호강교(3011665) `gdt` 19.643, `pfh` 9.38, `attwl` 5, `wrnwl` 7, `almwl` 8. 팔결교(3011635) `gdt` 30.121, `pfh` 7.32. 미호교(3011685) `gdt` 18.253, `pfh` 8.85.
- 19.643 + 9.38 = EL 29.023 m로, 국무조정실 발표 "미호천교 계획홍수위 29.02 m"와 일치한다.
- `osong_hand_reconstruction_validation.json`(2026-09-30): grid 1,280, timeline 1,619, stage 152/209/266/306/330/352.
- `osong_reconstruction_envelope_comparison.json`은 2026-09-01 생성본 그대로라 HAND 278셀 등 옛 값을 담고 있다.

문제/해결:
- 문제: TODO와 `source-availability.yml`은 관측소 기준면이 없다고 적었지만, HRFCO 관측소 정보 XML을 이미 받아 두었고 그 안에 `gdt`(영점표고)가 있었다.
  해결: TODO에 위치와 값을 적고 다음 작업을 해발 수면고 환산으로 바꿨다. 단, API 조회 시점 메타데이터라 2023년 당시 값과 같은지는 확인하지 못했고, Copernicus DEM(EGM2008)과 국내 표고 기준의 차이를 맞추는 작업이 남았다.
- 문제: 수위 CSV에서 미호강교가 9.38 m에 닿는 시각은 06:50인데, timeline의 "계획홍수위 도달"은 06:40이다.
  해결: 이번에는 고치지 않고 TODO에 확인 항목으로 남겼다. timeline 시각의 근거 문서부터 확인해야 한다.
- 문제: 제방고는 언론 보도뿐이고 보도끼리 어긋난다(임시제방이 기존 제방보다 1.6 m 낮다는 보도와 3.3 m 낮다는 판결 보도). 붕괴 시각도 보도마다 07:58, 08:10으로 다르다(저장소 08:09).
  해결: What-if C는 보류를 유지하고, 수치와 출처를 TODO에 적었다. 판결문(대법원 2025도289) 원문은 법원 열람 신청이 필요하다.

## 계획홍수위 도달 시각 06:40/06:50 불일치 정리

- 작업일: 2026-10-03

주요 작업:
- timeline의 "계획홍수위 도달" 06:40이 어디서 왔는지 확인했다. 국무조정실 감찰 결과 발표(2023-07-28)의 "06:40 미호천교 계획홍수위 해발 29.02 m 도달"이다(보도 기준, 원문 쪽수 미확인).
- `hydraulic_warning` 사건의 시각은 06:40으로 두고, 설명에 보관된 HRFCO 10분 자료 기준 06:40 9.30 m(EL 28.943), 06:50 9.38 m(EL 29.023)을 함께 적었다. 출처 문구를 감찰 발표 + HRFCO 10분 관측으로 바꿨다.
- `docs/data-quality.md`에 DQ-009를 추가했다.
- 저장소 루트에 있던 추적되지 않은 빈 파일 `MapLibre`(0바이트)를 지웠다.

검증 결과:
- 수위 CSV `station_id=3011665`: 06:30 9.20, 06:40 9.30, 06:50 9.38, 07:00 9.47 m.
- `gdt` 19.643 + `pfh` 9.38 = EL 29.023 m로, 발표값 29.02 m와 기준면이 맞는다.
- `python -m pytest backend/tests -q` 94개 통과.

문제/해결:
- 문제: 수위 CSV에서 미호강교가 계획홍수위 9.38 m에 닿는 시각은 06:50인데, timeline은 06:40이다. 06:40의 관측값 9.30 m는 해발 28.943 m로 29.02 m보다 8 cm 낮다.
  해결: 기준면 합(29.023 m)이 발표값과 맞으므로 차이는 기준면이 아니라 시각에 있다. 발표 시각을 관측 자료로 덮어쓰면 사건 기록과 어긋나므로 06:40을 유지했다. 관측 시각은 사건 설명과 DQ-009에 함께 적었다.
- 문제: 차이의 원인은 확인할 수 없었다. 후보는 세 가지다. 발표는 당시 실시간 자료를 쓰고 보관 자료는 나중에 보정됐을 수 있다. 1분 자료를 기준으로 했을 수도 있고, 10분 자료의 timestamp 규약이 다를 수도 있다.
  해결: 원인은 판정하지 않고 감찰 원문 확인 항목으로 남겼다. closure-timing과 inflow-delay 분석은 08:09 이후 시각만 쓰므로 이 차이의 영향을 받지 않는다.

## DEM 수직 기준과 수위 기준면 차이 정리

- 작업일: 2026-10-03

주요 작업:
- 미호강교 수위(`gdt` 19.643 m 기준 국내 표고)를 Copernicus DEM(EGM2008)과 절대 비교할 수 있는지 검토했다.
- `docs/data-quality.md` DQ-007에 재검토 결과와 근거를 추가하고, TODO의 다음 작업을 DQ-008 재산출로 바꿨다.
- 저장소 루트에 생긴 추적되지 않은 빈 파일 `0`(0바이트, 10-03 13:58 생성)을 지웠다.

검증 결과:
- `Copernicus_DSM_COG_10_N36_00_E127_00_DEM.tif`를 `tifffile`로 직접 읽어 확인: 미호강교(127.3505556, 36.6230556) 81×81셀 최빈값 18.5 m(174셀), 18.0 m(95셀), 19.0 m(72셀).
- 궁평2지하차도(127.3376, 36.6246) 7×7셀: 최소 20.64, 중앙값 26.36, 최대 29.81 m.
- Copernicus DEM Product Handbook i5.0: DSM(건물·구조물·식생 포함), 절대 수직정확도 < 4 m(LE90), TanDEM-X 취득 2010-12~2015-01, 하천은 평탄화·흐름 일관 편집.
- Jekeli·Yang·Kwon(2009, Newton's Bulletin 4): 한국 GPS/수준점 500점에서 EGM08 표준편차 18.5 cm, 국내 수직기준과 전지구 지오이드 오프셋 43.4 cm.

문제/해결:
- 문제: TODO는 "`gdt`로 해발 수면고로 환산하고 DEM 수직 기준 차이를 정리"를 다음 작업으로 두었다. 환산 자체는 되지만(계획홍수위 EL 29.023 m), 그 값을 DEM 셀과 비교해 침수 여부를 정하려면 두 높이 체계의 차이와 DEM 오차가 그 비교를 감당할 수 있어야 한다.
  해결: 기준면 차이(0.43 m)를 보정 대상으로 잡으려 했으나 원문에 뺄셈 방향이 없어 부호를 정할 수 없었다. 더 큰 문제는 DEM 쪽이었다. 관측소 주변 하천 셀이 18.0/18.5/19.0 m 계단값으로 편집돼 영점표고 19.643 m보다도 낮았고, 제품 오차도 수 m다. 0.43 m를 보정해도 결과가 달라지지 않으므로 보정 코드를 넣지 않았다. relative stage pressure 방식을 유지하고 근거를 DQ-007에 남겼다.
- 문제: 절대 수면 비교를 아예 포기하면 Phase 2 물리 모델 연계 경로가 막힌다.
  해결: 국내 표고 기준 LiDAR DTM(국토지리정보원 수치표고 등)을 확보하면 다시 검토할 항목으로 남겼다. 이번에는 자료를 찾지 않았다.

## DQ-008 envelope 면적·중첩 비율 재산출

- 작업일: 2026-10-03

주요 작업:
- `data/scripts/compare_osong_reconstruction_envelopes.py`가 stage별로 AOI 클립 면적·AOI 대비 비율, AOI 안 공식 건물 중첩 동수, OSM 도로 길이를 함께 계산하도록 했다(`approx_aoi_overlap`, `hand_aoi_overlap`, `aoi`).
- `osong_reconstruction_envelope_comparison.json`을 09-30 HAND 결과로 다시 만들었다. 기존 키(`rows[].hand_area_km2` 등)는 그대로 둬 API 응답과 프론트 타입이 깨지지 않는다.
- DQ-008, TODO의 HAND 비교·DQ-008 항목을 새 수치로 바꿨다.

검증 결과:
- AOI 40.557 km2. AOI 안 공식 건물 9,748동(파일 전체 25,283동), AOI 안 OSM 도로 368.1 km(전체 1,305.2 km).
- HAND stage 152/209/266/306/330/352셀, 면적 15.311/21.052/26.794/30.824/33.241/35.458 km2.
- HAND final: AOI 클립 15.434 km2(38.1%), 건물 4,746동(48.7%), 도로 159.6 km(43.3%). approx final: AOI 36.2%, 건물 4,382동(45.0%), 도로 41.1%.
- `python -m pytest backend/tests -q` 94개 통과.

문제/해결:
- 문제: 비교 JSON이 09-01 생성본이라 API가 옛 HAND 면적(final 54.39 km2)을 내보내고 있었다. 09-02의 건물 45.8%·도로 50.5%를 계산한 스크립트는 저장소에 없어 다시 낼 수도 없었다.
  해결: 비교 스크립트에 중첩 계산을 넣어 매번 같은 방식으로 재생성되게 했다.
- 문제: 처음 계산한 approx final 비율(건물 17.3%)이 09-02 기록(22.6%)과 달랐다. envelope 파일은 바뀌지 않았으므로 계산 방식이 원인이었다.
  해결: 클립하지 않은 envelope과 전체 25,283동으로 다시 계산하니 22.6% / 26.3%가 그대로 나왔다. 건물·도로 파일이 오송읍보다 넓은 범위라, 09-02 비율은 AOI 밖 객체까지 분모에 넣은 값이었다. AOI로 클립하고 분모도 AOI 안 객체 수로 바꿨다. 이전 방식 값도 DQ-008에 같이 적어 비교할 수 있게 했다.
- 문제: 개선된 envelope으로도 final stage가 AOI 안 건물의 48.7%를 덮는다.
  해결: 노출 KPI는 `PENDING_FLOOD_EXTENT`를 유지한다. 선택 규칙을 더 조이는 것은 DQ-008 채택 판정대로 공식 자료 대조 절차가 생긴 뒤에 한다.

## 2022 서울 도림천 유역 사례 연결 (재구성 + 반사실 비교)

- 작업일: 2026-10-03

주요 작업:
- `data/scripts/process_seoul_2022_dorimcheon.py`로 처리했다.
  - 도림천 유역 bbox(126.89~126.955, 37.465~37.51)를 범위로 잡았다.
  - 공식 침수흔적도를 잘라 붙였다.
  - 공식 건축물을 사용승인일로 거른 뒤 흔적과 겹쳤다.
  - 2022-08-08 시점 OSM 도로·하천·시설을 붙였다.
  - 강우계 6곳의 60분 이동합을 계산했다.
  - 결과는 `data/processed/seoul_2022/`에 있다.
- `backend/app/seoul_repository.py`를 새로 만들었다.
  - 사건 7단계를 넣었다.
  - layers, status, summary, reconstruction 응답을 오송과 같은 엔드포인트로 연결했다.
  - `POST /api/events/seoul-2022/analysis/alert-timing`을 추가했다(강우 임계·수동 시각 경보와 첫 구조 신고 사이의 시간 차).
  - `POST /api/events/seoul-2022/analysis/storage-capture`를 추가했다(처리 능력을 넘은 강우 부피와 저류량 비교).
- `src/dark/UrbanConsole.tsx`, `src/dark/urban.css`를 새로 만들었다.
  - 관제 화면에는 공식 흔적(침수심 색), 흔적과 겹친 건축물, 강우 그래프, 노출 패널을 넣었다.
  - 반사실 비교 화면에는 경보 시각 시간축과 표, 저류 카드와 누적 차트를 넣었다.
  - 사례 선택 화면에서 서울을 열었다.
- `Dockerfile.aws`에 `data/processed/seoul_2022` 복사를 추가했다. 배포는 하지 않았다.

검증 결과:
- `python -m pytest backend/tests -q` 99개 통과. 새 `test_seoul_case.py` 5개를 포함한다.
- `npm.cmd run build` 통과, `vitest` 2개 통과.
- 서울 레이어 응답은 17,470 KB다. 흔적 10,468건, 건축물 13,015동, 도로 4,828개, 하천 22개, 시설 1,067개.
- Edge headless로 확인했다.
  - 흐름: 사례 선택 → 서울 관제 → 단계 이동 → 반사실 비교 → 오송 관제.
  - 콘솔 오류 0건, `/api/` 4xx·5xx 0건이었다.
  - 오송 화면은 변화가 없었다.
- 반사실 수치:
  - 신림P 95 mm/h 도달(20:49) 경보는 첫 신고보다 10분, 실제 문자보다 30분 빠르다.
  - 50 mm/h 도달(13:09)은 첫 신고보다 7시간 50분 빠르다.
  - 40만 m3 저류는 초과량 870,263 m3 중 46.0%를 담고 20:49에 가득 찬다. 유출계수 0.5에서는 91.9%다.

문제/해결:
- 문제: 서울도 "반지하" 주제로 잡으려 했다.
  해결: 사용자가 반사실 방재효과를 보여주는 사례라고 바로잡았다. 시각이 확인된 사건이 있는 신림동 쪽(도림천 유역)을 골랐다. 강남역 쪽은 시각이 확인된 사건이 거의 없어 시간 계산형 what-if를 만들 수 없어 제외했다.
- 문제: 2022-08-08 시점 OSM 건물은 범위 안에 3,817동뿐이다. 그대로 노출을 집계하면 크게 과소가 된다.
  해결: BASEMENT 저장소에 있던 GIS건물통합정보 서울 전체 스냅샷(2026-08-09)을 썼다. 사용승인일 2022-08-08 이후 47동을 빼서 사건 시점 재고에 가깝게 맞췄다. 66,099동 전부를 지도에 올리면 무거워서, 지도에는 흔적과 겹친 13,015동만 올리고 나머지는 집계로만 낸다.
- 문제: 침수흔적도의 `F_ZONE_NM`과 건축물 지번에 개인 주택의 상세 주소가 들어 있다. 사망 사고가 난 주택을 특정할 수 있다.
  해결: 처리 단계에서 주소 필드를 버리고 자치구·행정동만 남겼다. 테스트로 주소 필드 부재를 고정했다.
- 문제: Overpass 기본 요청이 406으로 거절됐다.
  해결: `User-Agent`와 `Accept: application/json`을 붙여 같은 쿼리로 받았다.
- 문제: 반경 재고 API가 서울에서 임의의 OSM 시설을 초점으로 잡아 200을 돌려줬다. 기존 테스트는 404를 기대하고 있었다.
  해결: 서울은 초점 시설이 없고 건축물 레이어가 흔적 겹침 건물만 담고 있다. 반경 집계가 왜곡되므로 404를 유지하고, 노출은 `/reconstruction`의 공식 흔적 기준 값을 쓰게 했다.
- 문제: 침수흔적에는 시각이 없다.
  해결: 지도를 단계에 따라 넓히지 않고, 범례에 "사건 뒤 조사한 기록이라 시각 정보가 없다"고 적었다. 시간축은 강우계와 사건 시각으로만 재생한다.
- 문제: 서울 단계 상태값 `warning`이 오송의 "홍수경보 발령" 번역과 겹쳤다.
  해결: `rain_warning`으로 바꿨다.

## 포항 2022·안동·의성 2026 사례 연결 (사건 시각 재생 + 대응 시각 반사실)

- 작업일: 2026-10-03

주요 작업:
- 포항 2022, 익산 2024, 안동·의성 2026의 사건 시각과 개입 후보를 웹으로 조사했다.
- `data/scripts/process_timeline_cases.py`를 만들었다. 사건일 OSM 스냅샷을 받아 분석 범위, 도로, 하천, 부분 건축물, 보도된 지명 중심점 레이어를 만든다.
  - 포항: 129.37~129.43, 35.965~36.01, 2022-09-06
  - 안동·의성: 128.63~128.80, 36.44~36.535, 2026-07-17
- `backend/app/timeline_cases.py`로 두 사례를 연결하고 `POST /api/events/{id}/analysis/response-timing`을 추가했다.
  - 대응 시각을 옮겼을 때 이후 사건까지 남는 분과 실제보다 빠른 분을 계산한다.
  - 자정을 넘는 안동 사례는 12시 이후를 7/18, 이전을 7/19로 해석한다.
- `src/dark/TimelineConsole.tsx`를 추가했다.
  - 관제 화면: 단계 재생, 지명 마커, 보도 수치·출처 패널
  - 반사실 비교: 시간축, 표
  - 사례 선택에서 포항·안동·의성을 열었다.
- 익산은 연결하지 않았다. 카탈로그 위치만 함라면에서 산북천 유역(낭산·망성)으로 바로잡았다.
- `Dockerfile.aws`에 두 처리 폴더 복사를 추가했다.

검증 결과:
- `python -m pytest backend/tests -q` 104개 통과. 새 `test_timeline_cases.py` 5개를 포함한다.
- `npm.cmd run build`와 `vitest` 2개가 통과했다.
- Edge headless로 포항·안동 관제 화면과 반사실 비교, 서울, 사례 선택을 확인했다. 콘솔 오류 0건, `/api/` 4xx·5xx 0건.
- 포항: 진입 금지 06:00이면 침수 시작 37분·완전 침수 45분 전. 05:20이면 77·85분 전. 실제 06:30은 7·15분 전.
- 안동·의성: 대피명령 23:40이면 00:30 예측까지 50분, 실제 00:00은 30분. 산사태 위기경보를 00:00에 올렸다면 실제보다 480분 빠르다.

문제/해결:
- 문제: 카탈로그의 익산 위치(함라면)와 안동 위치(길안면)가 실제 피해 지역과 달랐다.
  해결:
  - 익산: 함라는 비가 가장 많이 온 관측 지점이고, 피해는 산북천 유역이었다.
  - 안동: 임시주택 침수지는 안동 일직면 귀미1리와 의성 단촌면 구계리였다.
  - 두 사례 모두 카탈로그와 사례 선택 문구를 고쳤다.
- 문제: 익산은 제방 붕괴·대피·재난문자 시각을 하나도 확인하지 못했다.
  해결: 시간 계산형 반사실을 만들 근거가 없어 잠금을 유지했다. 확인되지 않은 시각으로 재생을 만들면 오송·서울과 같은 수준으로 보인다.
- 문제: 두 사례 모두 공식 침수범위·강우계 시계열이 없다. 사건일 OSM 건축물도 66동·23동뿐이다.
  해결: 서울용 화면에 빈 패널을 남기지 않으려고, 사건 시각만 쓰는 가벼운 공통 화면을 따로 만들었다. 노출 집계 대신 보도 수치를 출처와 함께 "모델 계산이 아님"으로 표시했다.
- 문제: 산사태 위기경보 반사실의 비교 기준을 처음에 홍수경보 해제(05:40)로 잡았더니 "-140분" 같은 의미 없는 값이 나왔다.
  해결: 비교 기준을 비우고 실제 08:00보다 얼마나 빨랐는지만 내게 했다.
- 문제: 포항 사고 아파트는 실명 단지라 지도에 찍으면 특정 주거지를 가리키게 된다.
  해결: 냉천교·인덕교·인덕동 중심점만 표시했다.
- 문제: 기준 사건 라벨이 영어로 나오고, 06:37과 06:45 라벨이 겹쳤다. 안동 지도는 지점 하나만 보였다.
  해결: 라벨을 `stageKo`로 바꾸고, 기준선 높이를 엇갈렸다. 지도는 분석 범위에 맞추고 범례 쪽 여백을 넓혔다.
- 문제: 셸 명령의 코드 조각(`-> dict[str`, `>> nth`)이 훅을 거치며 저장소 루트에 빈 파일로 생겼다.
  해결: 생길 때마다 확인해 지웠다. 훅 설정은 고치지 않았다.

## Agent 다중 사례 확장과 익산 시각 재조사

- 작업일: 2026-10-03

주요 작업:
- `backend/app/agent_cases.py`를 추가했다.
  - 서울·포항·안동의 Agent 도구 목록, 모델 값 검증, 질문 라우팅 힌트, 시작 질문을 사건별로 둔다.
  - `agent_tools.py`는 사건이 오송이 아니면 이 모듈로 분기한다.
- `agent_runner.py`를 사건별로 동작하게 바꿨다.
  - 사건별 도구 목록을 쓰고, 등록되지 않은 도구를 거부한다.
  - 새 인자(`thresholds_mm_per_hour`, `alert_times`, `storage_m3`, `capacity_mm_per_hour`, `runoff_coefficient`, `intervention_id`, `action_times`)를 정규화하고 검증한다.
  - 언론 보도 단서를 덧붙이고, 사건별 시작 질문과 도움말을 낸다.
- `GET /api/agent/examples`가 `event_id`를 받게 했다. `AgentDock`을 export해 서울·포항·안동 화면 상단에 붙였다.
- 결과 표에 경보 시각·저류·대응 시각 렌더러를 추가했다.
- 익산 2024의 시각 근거를 다시 조사했다.

검증 결과:
- `python -m pytest backend/tests -q` 111개 통과. 새 `test_agent_cases.py` 7개를 포함한다.
- 기존 오송 Agent 테스트·한국어 평가셋은 그대로 통과했다.
- `npm.cmd run build`와 `vitest` 2개가 통과했다.
- Edge에서 사례별 질문 하나씩 실행했다(Gemini `gemini-3.5-flash-lite` 연결 상태). 콘솔 오류 0건, `/api/` 4xx·5xx 0건.
  - 서울 "95mm 넘었을 때 경보": `analyze_alert_timing`, 첫 신고 10분 전·실제 문자보다 30분 빠름
  - 포항 "30분 일찍 진입 금지": `analyze_response_timing`, 06:00 → 완전 침수 45분 전
  - 안동 "23:40 대피명령": 예측 시각까지 50분
  - 오송 "08:25 통제": 기존과 같이 `analyze_closure_timing`

문제/해결:
- 문제: Agent의 도구·실행기·라우팅이 `osong-2023`에 묶여 있었다. 서울·포항·안동 화면에는 Agent가 없었다.
  해결: 오송 카탈로그와 코드 경로는 건드리지 않고, 다른 사건만 `agent_cases`로 분기했다. 오송 평가셋 15문항이 그대로 통과하는 것으로 회귀가 없음을 확인했다.
- 문제: 모델이 질문에 없는 시각(예: 21:00)이나 다른 사건의 도구(`analyze_closure_timing`)를 넣을 수 있다.
  해결: 오송의 원칙을 그대로 적용해 막았다. 허용하는 값은 다음뿐이다.
  - 사용자가 쓴 값
  - 사건 단계 시각
  - "N분 일찍"을 실제 대응 시각 기준으로 환산한 값
  - 등록값(40만·32만 m3, 95/100/110 mm/h)
  사건에 등록되지 않은 도구는 거부한다. 테스트로 고정했다.
- 문제: 모델이 이미 "언론 보도 기준"이라고 쓴 답에 같은 단서가 한 번 더 붙었다.
  해결: 답에 "언론 보도"가 있으면 단서를 덧붙이지 않고 제한 목록에만 남긴다.
- 문제: 익산 2024는 이번에도 특보 발효·재난문자·산북천 제방 붕괴 시각을 찾지 못했다.
  해결: 잠금을 유지했다. 확인된 것은 함라 1시간 최다 125.5 mm(기상청 보도자료, 시간대 미확인)와 0~05시 255 mm 등 누적값, 망성 주민의 "04:00 대피소 도착" 진술 하나뿐이다. 산북천 10개 마을 337명 대피와 용안면 631명 대피는 2023년 사건이라 섞지 않도록 TODO에 남겼다.

## 사례 간 비교 화면

- 작업일: 2026-10-03

주요 작업:
- `backend/app/case_comparison.py`와 `GET /api/cases/lead-times`를 추가했다. 네 사례마다 실제 대응과 등록된 반사실 대응이 기준 사건보다 몇 분 앞섰는지 계산한다.
- `src/dark/CaseCompare.tsx`, `compare.css`를 추가했다. 덤벨 차트, 툴팁, 같은 값의 표, 사례별 "열기" 버튼이 있다. 사례 선택 화면에 "사례 간 비교" 버튼을, 라우트 `#compare`를 추가했다.

검증 결과:
- `python -m pytest backend/tests -q` 112개 통과(사례 간 수치 테스트 1개 추가). `npm.cmd run build` 통과.
- 팔레트 검증기(`validate_palette.js --mode dark --surface #111a2b`)에서 `#d97014`, `#109c8e` 6개 항목 통과. CVD ΔE 13.5, 정상 시각 ΔE 24.5.
- Edge 1280×860 화면 캡처로 라벨 겹침·툴팁 위치를 확인했다. 콘솔 오류 0건, `/api/` 4xx·5xx 0건.

문제/해결:
- 문제: 처음 고른 주황·청록(`#fb923c`, `#2dd4bf`)이 다크 배경 명도 범위(L 0.48~0.67)를 벗어났다.
  해결: 같은 계열에서 `#d97014`, `#109c8e`로 내려 검증을 통과시켰다. 모양(원·마름모)도 달리해 색에만 의존하지 않게 했다.
- 문제: 차트가 화면 폭의 1/3로 줄고 툴팁이 세로로 좁아졌다.
  해결: `.fo-landing`의 세로 flex 안에서 `margin: 0 auto`가 폭을 내용 크기로 줄인 탓이었다. 블록마다 `width: 100%`와 `min-width: 0`을 주고, 툴팁은 `width: max-content`로 바꿨다. 오른쪽 끝 점에서는 툴팁을 왼쪽으로 뒤집는다.
- 문제: 모바일 폭(390 px)에서 페이지가 1,080 px로 넓어진다.
  해결: `src/styles.css`의 `body { min-width: 1080px }` 때문이었다. 앱 전체가 데스크톱 전용 설계라 전역 규칙은 그대로 두었다.
- 문제: 사례마다 기준 사건이 다르다(유입, 첫 구조 신고, 주차장 침수, 경보 수위 예측). 한 축에 놓으면 순위처럼 읽힐 수 있다.
  해결: 화면과 API 한계에 "사례 간 수치를 순위로 비교하지 않는다"고 적었다. 표에 기준 사건과 근거 수준을 함께 둔다.
- 문제: 저장소 루트에 빈 파일이 계속 생긴다(이번 세션 `0`, `dict[str`, `nth`, `void` 등).
  해결: 원인은 아직 확정하지 못했다. 훅 출력에 `Microsoft Windows` 배너와 `C:\...>{"session_id":...}`가 찍히므로, 훅 JSON을 대화형 `cmd.exe`가 명령으로 읽어 `>`를 리다이렉트로 처리하는 것으로 보인다. 프로젝트 ruflo 훅은 `cmd /c`라 배너가 없다. 그래서 모든 도구에 걸린 전역 orca 훅(`~/.orca/agent-hooks/claude-hook.cmd`, `ORCA_AGENT_HOOK_ENDPOINT` 호출)이 유력하다. 설정은 바꾸지 않았다.

## 언론 보도 시각의 공식 원문 대조

- 작업일: 2026-10-03

주요 작업:
- 서울·포항·안동 사례의 언론 보도 시각을 행안부 보도자료·중대본 상황보고·기상청 자료와 대조했다. 원문 첨부(hwp/hwpx/pdf)를 내려받아 텍스트로 확인했다.
- 서울: 중대본 2단계 단계의 출처를 행안부 보도자료(2022-08-08, nttId=93918)로 바꾸고 확신도를 `OFFICIAL_AMBIGUOUS`로 했다. 첫 구조 신고 단계에 중대본 상황보고(8.9 06시, nttId=93917)의 "21:07경"을 함께 적었다.
- 안동: 보도 수치에 중대본 상황보고(7.19 06·18시, nttId=127939)의 공식 대피 인원과 미천 홍수경보 기재를 추가했다.
- `docs/data-quality.md` DQ-010·DQ-011에 대조 결과와 남은 확인 경로를 적었다.

검증 결과:
- 원문 확인
  - 중대본 상황보고: "(관악) 침수로 반지하에 3명이 갇혀 신고하였으나 사망(…) 21:07경"
  - 행안부 보도자료: "9시 30분을 기해 … 비상 1단계에서 2단계로 격상", "오전 7시 30분부터 중대본 비상 1단계를 가동"
- `python -m pytest backend/tests -q` 112개 통과. 반사실 계산 값은 바뀌지 않는다.

문제/해결:
- 문제: 서울 첫 구조 신고 20:59(한국일보)와 중대본 상황보고의 관악 반지하 사고 "21:07경"이 8분 다르다.
  해결: 21:07이 신고 시각인지 사망 시각인지 문서에 없다. 그래서 반사실 기준(20:59)을 바꾸지 않고 두 시각을 함께 표시했다. 기준을 21:07로 바꾸면 95 mm 경보의 선행 시간은 10분에서 18분이 된다. 이 값은 근거가 확정되면 다시 계산한다.
- 문제: 행안부 원문이 "9시 30분"으로만 적혀 21:30인지 09:30인지 문서만으로는 확정되지 않는다.
  해결: 시각은 21:30으로 두고 "공식(오전·오후 미표기)" 확신도로 표시했다. 같은 날 1단계가 오전 7시 30분에 가동됐고 언론은 21:30으로 보도했다.
- 문제: 포항·안동의 사건 시각은 공식 상황보고에 하나도 적혀 있지 않았다.
  해결: 언론 출처를 유지했다. 확인 경로(홍수통제소 Open API, 산사태정보시스템, 긴급재난문자 이력, 판결문 열람)를 DQ-011에 남겼다.

## API 오류 상태 검증 및 손상 레이어 처리

- 작업일: 2026-10-03

주요 작업:
- 오송 processed GeoJSON의 파일 누락, JSON 구문 오류, FeatureCollection 구조 오류를 레이어별 `UNAVAILABLE` 상태로 처리했습니다.
- 누락은 `MISSING_PROCESSED_FILE`, 손상은 `MALFORMED_PROCESSED_FILE` 코드로 구분하고 빈 FeatureCollection을 반환하도록 했습니다.
- 익산 미연결 데이터셋의 `UNAVAILABLE` 상태와 미등록 사건의 404 응답을 포함해 API 오류 상태 테스트 4개를 추가했습니다.

검증 결과:
- `python -m pytest backend/tests/test_api_error_states.py -q`: 4개 통과.
- `python -m pytest backend/tests -q`: 116개 통과. FastAPI `on_event` 폐기 예정 경고 2개가 출력됐습니다.
- 누락·손상 레이어에서 `/api/events/osong-2023/layers`는 200으로 응답하고, `/api/events/osong-2023/status`에도 같은 오류 코드가 표시되는 것을 확인했습니다.

문제/해결:
- 문제: 누락된 processed 레이어는 빈 데이터로 처리됐지만 원인 코드가 없었고, 손상된 GeoJSON은 파싱 예외로 `/layers` 요청 전체가 실패할 수 있었습니다.
  해결: 파일 누락과 JSON·FeatureCollection 손상을 레이어 단위로 판별해 `UNAVAILABLE`과 원인 코드를 반환했습니다. 다른 정상 레이어는 계속 제공되도록 유지했습니다.
- 문제: 미연결 익산 데이터셋과 미등록 사건의 API 응답 계약이 오류 상태 테스트로 고정되지 않았습니다.
  해결: 익산 레이어의 `UNAVAILABLE`/0건과 미등록 사건의 404를 테스트에 포함했습니다.

## 오송 관제 화면 Playwright E2E 연결

- 작업일: 2026-10-03

주요 작업:
- `@playwright/test`와 Chromium 기반 E2E 실행 스크립트를 추가하고 FastAPI `8035`, Vite `5175`를 테스트 중 자동 실행하도록 설정했습니다.
- 인트로부터 오송 사례 진입, 7단계 재생, HAND 레이어 토글, 출처 표시와 08:09 통제 시각의 비교 결과를 브라우저에서 검증했습니다.
- Vitest의 수집 범위를 `src` 단위 테스트로 한정하고 E2E 산출물을 Git에서 제외했습니다.

검증 결과:
- `npm run test:e2e`: Chromium E2E 3개 통과(출처·한계 화면 검증 포함).
- `npm test`: Vitest 2개 통과.
- `npm run build`: TypeScript 검사와 Vite 빌드 통과.

문제/해결:
- 문제: 관제 화면의 사건 재생·레이어 토글·시나리오 비교는 수동 smoke test만 있어 UI 흐름이 바뀌어도 자동 검증되지 않았습니다.
  해결: 실제 FastAPI와 Vite를 띄우는 Playwright E2E에서 화면 이동, 시간 상태, 통제 시각 계산 결과 및 출처·한계 문구를 확인하도록 했습니다.
- 문제: E2E 파일을 추가하자 Vitest가 Playwright `test()`를 단위 테스트로 수집해 `npm test`가 실패했습니다.
  해결: Vite 설정의 Vitest `include`를 `src/**/*.{test,spec}.{ts,tsx}`로 제한해 두 러너의 테스트 파일을 분리했습니다.

## 오송 출처·한계 화면 고도화

- 작업일: 2026-10-03

주요 작업:
- 오송 관제의 `출처·한계` 탭에 API provenance 7건의 역할, 출처, 자료 시점과 limitations 5건을 표시했습니다.
- 인사이트 카드에서 개발용 `TEMPORARY`·source_type 문자열을 빼고 사건 연도와 관측·HAND 자료의 출처를 보여주도록 바꿨습니다.
- 출처 역할과 한계 문구를 한국어로 표시하고 1280 px 헤더에서 탭·Agent 입력 영역이 겹치지 않도록 좁은 화면의 시각을 숨겼습니다.

검증 결과:
- `npm run build`: TypeScript 검사와 Vite 빌드 통과.
- `npm run test:e2e`: Chromium E2E 3개 통과. 새 화면에서 관측 입력·HAND 역할, 2023-07-15 자료 시점, 수리해석·원문 근거 한계를 확인했습니다.
- 1280×720 Chromium 캡처로 출처 카드 7건의 배치를 확인했습니다.

문제/해결:
- 문제: 인사이트에 `TEMPORARY`와 `DERIVED_APPROXIMATION` 같은 개발용 코드가 보였고, 자료의 출처·시점·역할과 계산할 수 없는 범위가 떨어져 있어 해석하기 어려웠습니다.
  해결: 재구성 API의 provenance와 limitations를 한 화면에 연결하고 역할·한계를 한국어로 풀어 표시했습니다. 사건 연도와 자료 시점을 별도로 설명했습니다.
- 문제: 화면 탭을 늘리면 1280 px 헤더에서 Agent 입력 영역과 시각 표시가 가까워졌습니다.
  해결: 1400 px 이하에서는 탭 여백을 줄이고 시각 표시를 숨겨 입력 영역의 공간을 확보했습니다.

## 서울 빗물터널 계산 면적을 도림천 유역으로 교체, 신월 참고 사례 추가

- 작업일: 2026-10-03

주요 작업:
- `analyze_storage_capture`의 면적 기본값을 분석 범위 bbox(28.69 km2)에서 도림천 유역면적 40.96 km2로 바꿨다. 응답에 `area_basis`, `aoi_area_km2`, `reference_case`(신월 저류시설)를 추가했다.
- 반사실 비교 화면 저류 패널에 면적 선택(도림천 유역 / 분석 범위)과 신월 참고 사례 카드를 넣었다. Agent 도구 설명의 면적 문구도 고쳤다.

검증 결과:
- 유역 40.96 km2·95 mm/h·유출계수 1.0: 초과 1,242,453 m3, 40만 m3가 32.2% 저류, 20:39 만수(첫 신고 20분 전). 유출계수 0.5면 64.4%.
- bbox 28.69 km2를 고르면 이전 값(870,263 m3, 46.0%, 20:49)이 그대로 나온다.
- `python -m pytest backend/tests -q` 116개 통과(다른 도구의 오류 상태 테스트 4개 포함). `npm.cmd run build` 통과.
- Edge에서 면적 선택을 바꾸면 카드가 "32.2% 저류"에서 "46% 저류"로 바뀌는 것을 확인했다. 콘솔 오류 0건, `/api/` 4xx·5xx 0건.

문제/해결:
- 문제: 터널이 받는 물은 도림천 유역 전체에서 오는데, 계산은 지도용으로 잡은 bbox 면적을 썼다. bbox는 유역보다 작아 초과량을 적게, 저류 비율을 크게 보이게 했다(46% vs 32.2%).
  해결: 문헌의 유역면적을 찾아 기본값으로 바꿨다. 출처는 김재근 외(2012) 한국습지학회지 14(2) 257쪽, 이승종 외(2005) 인용이다. 서울시 하천기본계획 원문 값은 찾지 못해 "문헌값"으로 표시했다. 언론의 "약 42 km2"는 반올림 값으로 보여 쓰지 않았다.
- 문제: 반사실 터널 계산만으로는 실제 터널이 그런 비에 얼마나 찼는지 감이 없다.
  해결: 2022-08-08에 실제로 운영된 신월 저류시설을 참고 사례로 붙였다.
  - 32만 m3·95~100 mm/h는 서울시 공식 채널로 확인했다.
  - 8.8 유입 224,929 m3(약 70%)는 언론에서만 확인돼 "원문 미확인"으로 표시했다.
  - 다른 유역이라 도림천 계산의 검증이 아니라는 점도 카드에 적었다.

## 공개 사이트 PageSpeed 측정, GA4·메타 픽셀·서치 콘솔 준비

- 작업일: 2026-10-03

주요 작업:
- `https://floodops.duckdns.org/`의 속도와 SEO를 측정했다.
- 검색 등록용 파일과 태그를 추가했다.
  - `public/robots.txt`, `public/sitemap.xml`
  - `index.html`의 `meta description`, canonical, Open Graph, Twitter 카드
  - 소개 화면 캡처로 만든 `public/og-image.png`(1200×630)
- `src/analytics.ts`를 추가했다.
  - GA4와 메타 픽셀은 빌드 환경변수(`VITE_GA4_ID`, `VITE_META_PIXEL_ID`)가 있고, 방문자가 동의했을 때만 불러온다.
  - 해시 라우트가 바뀔 때마다 페이지뷰를 보낸다.
- `src/dark/Consent.tsx`를 추가했다. 동의 배너와 개인정보 안내(`#privacy`, 수집 항목·제공처·Gemini 전송·철회 방법)가 들어 있다.
- `vite.config.ts`가 `VITE_GSC_VERIFICATION` 값이 있을 때만 서치 콘솔 인증 태그를 `index.html`에 넣게 했다. `Dockerfile.aws`에는 같은 이름의 `--build-arg`를 받게 했다.

검증 결과:
- Lighthouse 12(로컬 Edge, 소개 화면)
  - 모바일: 성능 94, 접근성 100, 권장사항 100, SEO 90, FCP·LCP 2.5 s, TBT 10 ms, CLS 0, 301 KiB
  - 데스크톱: 성능 100, SEO 90, FCP·LCP 0.5 s
  - 실서버에서 `robots.txt`와 `sitemap.xml`은 404였다.
- 가짜 ID(`G-TEST12345`, `1234567890`, 인증 값)로 빌드해 확인했다.
  - 인증 태그가 `index.html`에 들어갔다.
  - 미리보기 서버에서 동의 배너가 떴고, 개인정보 안내가 열렸다.
  - "거부" 뒤에는 새로고침해도 배너가 다시 뜨지 않았다.
  - `googletagmanager`·`facebook` 요청은 0건이었다.
- ID 없이 빌드하면 추적 코드와 인증 태그가 0건이다.
- `vitest` 5개 통과(측정 ID 검증 3개 추가), `npm run build` 통과.

문제/해결:
- 문제: PageSpeed Insights API가 키 없는 공용 할당량 소진(HTTP 429 Quota exceeded)으로 거절됐다. Lighthouse CLI는 Edge를 직접 띄우지 못했다(chrome-launcher 연결 실패).
  해결: Edge를 `--remote-debugging-port`로 먼저 띄우고 Lighthouse를 `--port`로 붙여 같은 엔진으로 측정했다. 측정 범위는 소개 화면뿐이다. 관제 화면은 레이어 응답이 커서 별도 측정이 필요하다.
- 문제: 서치 콘솔은 서버가 내보낸 HTML에서 인증 태그를 찾는다. JS로 나중에 넣으면 인식되지 않는다.
  해결: 인증 태그는 Vite `transformIndexHtml`로 빌드 때 넣었다. GA4·픽셀만 런타임에 불러온다.
- 문제: 측정 ID를 그대로 스크립트에 넣으면, 빌드 환경변수의 오타나 이상한 값이 스크립트 문자열로 들어갈 수 있다.
  해결: GA4는 `G-` 형식, 픽셀은 숫자, 인증 값은 영숫자만 받는다. 형식이 틀리면 꺼진다. 테스트로 고정했다.
- 문제: GA4·픽셀은 방문자 행동을 쿠키로 수집하므로 안내와 선택권이 필요하다.
  해결: 동의 전에는 아무것도 불러오지 않는 배너와 개인정보 안내 화면을 만들었다. 메타 광고 랜딩에는 `https://floodops.duckdns.org/#privacy`를 개인정보 처리방침 URL로 쓸 수 있다.
- 문제: 같은 폴더에서 다른 도구가 E2E 작업 중이었다.
  해결: `origin/main` 기준 워크트리(`../Flood-Disaster-Digital-Twin-claude`, 브랜치 `claude/seoul-catchment`)로 옮겨 작업했다. `node_modules`는 원래 폴더를 junction으로 연결했다. 이 때문에 Vite 의존성 캐시(`node_modules/.vite`)를 두 폴더가 공유한다.

## 관제 화면 속도 측정과 레이어 응답 경량화

- 작업일: 2026-10-04

주요 작업:
- 공개 사이트 오송 관제 화면의 로딩을 Playwright로 측정했다(Lighthouse는 해시 주소 화면에서 NO_FCP로 실패).
- `backend/app/layer_payload.py`를 추가하고 `/api/events/{id}/layers` 직렬화에 적용했다.
  - 화면이 팝업·범례·스타일에서 읽는 속성만 남긴다.
  - 좌표를 소수 5자리(약 1 m)로 줄이고, 공백 없는 JSON으로 보낸다.
  - 분석 서비스는 원본 레이어를 그대로 쓴다.

검증 결과:
- 공개 서버 측정
  - 첫 측정에서 관제 화면 준비까지 166.7초가 걸렸다. 레이어 요청 하나가 160.1초였다.
  - 다시 쟀을 때 각 API는 0.10~0.98초였다.
  - 레이어는 TTFB 0.11초, 전체 9.36초, 4,103,261 바이트(초당 약 440 KB)였다.
- 로컬 압축 크기: 오송 4.0 MB → 1.06 MB, 서울 1.2 MB, 포항 33 KB.
  - 오송 내역: 건물 3,373 KB가 698 KB 수준으로, 도로 410 KB가 267 KB 수준으로 줄었다.
- `python -m pytest backend/tests -q` 111개 통과(경량화 테스트 2개 추가).
  - 실패 3개는 워크트리에 git 밖 원자료(Safemap PNG 등)가 없어서 생긴 것으로, 이번 변경과 무관하다.
- Edge로 오송·서울 관제 화면을 열었다. HAND 셀·단계 필터·단면도 수치가 그대로였고, 콘솔 오류 0건, `/api/` 4xx·5xx 0건이었다. 서울 흔적·건물, 안동 지점 팝업 속성이 응답에 남아 있다.

문제/해결:
- 문제: 소개 화면 Lighthouse 점수(모바일 94)와 달리, 실제로 오래 쓰는 관제 화면은 4 MB 레이어를 받느라 회선이 좋아도 9초 넘게 걸렸다. 광고 유입 방문자가 첫 화면을 보기 전에 이탈할 수준이다.
  해결: 크기를 쪼개 보니 건물 레이어가 84%였다. 건물마다 건축물대장 속성 30개(A0~A22 등)가 실려 있었는데 화면은 `official_feature_id` 하나만 쓴다. 응답 직렬화 단계에서만 화면용 속성 허용 목록으로 걸렀다.
- 문제: 저장소 데이터 자체를 줄이면 반경 재고 같은 분석이 대장 속성을 잃는다.
  해결: `get_layers`가 돌려주는 원본은 그대로 두었다. HTTP 응답에서만 `slim_layers`를 적용했고, 테스트로 둘 다 고정했다.
- 문제: 빠지는 대장 속성에는 지번 주소(A5 등)가 들어 있었다.
  해결: 공개 응답에서 함께 빠지도록 했다. 서울 사례에서 주소를 버린 원칙과 같다.
## README 히어로 축약과 기획 의도 명확화

- 작업일: 2026-10-08

주요 작업:
- README 전용 SVG를 추가하고 핵심 제목과 설명 한 문장으로 축약했습니다.
- 사건 재구성 → 대응 시점 비교 → 판단 근거 확인의 흐름을 표시했습니다.
- README 도입문과 시연 링크를 줄였습니다.

검증 결과:
- README 이미지 경로와 SVG XML 구문, diff 공백 오류를 확인했습니다.

문제/해결:
- 문제: 기존 히어로는 설명과 상세 카드가 많아 더 이른 대응을 검토한다는 기획 의도가 분산됐습니다. 피해 변화라는 표현도 실제 대응 시간 비교보다 넓었습니다.
  해결: 과거 홍수를 재생하고 대응 시점을 비교한다는 제목과 더 이른 대응의 근거를 찾는다는 설명으로 줄였습니다.
- 문제: 기존 이미지가 사이트 공유 이미지로도 쓰이고 있었습니다.
  해결: README 전용 SVG로 분리해 공유 이미지에 영향을 주지 않고 문구를 직접 편집할 수 있게 했습니다.

## README 히어로 GIF와 화면·기술 스택 구성

- 작업일: 2026-10-08

주요 작업:
- README 상단 히어로를 소개 화면 모식도 기반 GIF(`docs/screenshots/hero.gif`, 1280×620, 36프레임, 약 790 KB)로 바꿨습니다.
  - 모식도 오른쪽 위에 4단계(경보 발령·제방 월류·침수 확산·지하차도 침수)를 단계별 색(하늘·노랑·주황·빨강)으로 표시합니다.
  - 제방 붕괴 지점에서 16 px 격자 셀이 번져 지하차도에 닿으면 4단계로 넘어갑니다.
  - 팝업에는 실제 시설명 대신 단계와 원상태(진입 계속)·개입(먼저 통제)만 둡니다.
- 서비스·Swagger 배지, 기술 스택 표와 선택 이유, `## 화면`(사례 선택·관제·시나리오 비교·출처·한계 실제 캡처 4장, 1600×1000 JPG)을 추가했습니다.
- `로컬 실행`, `방문 통계·검색 등록·광고 측정` 섹션을 뺐습니다. 공개 Agent 확인 문구를 2026-10-08 기준으로 바꿨습니다.

검증 결과:
- 공개 서버 `/health`가 `{"status":"ok"}`를 돌려주고, `/api/agent/planner-status`가 `available: true`, `gemini-3.5-flash-lite`를 보고했습니다.
- 화면 캡처와 GIF 프레임은 Playwright로 로컬 FastAPI(8035)·Vite(5175)를 띄워 만들었고, GIF의 중간·마지막 프레임을 꺼내 색과 배치를 확인했습니다.

문제/해결:
- 문제: 실제 관제 화면 캡처를 히어로로 쓰면 화면 캡처처럼 보여 기획 의도가 먼저 읽히지 않았습니다. 소개 화면 캡처(`og-image.png`)는 글자가 많았고, 병행 작업에서 만든 README 전용 SVG는 너무 단순했습니다.
  해결: 소개 화면 모식도를 쓰되 설명 문단·버튼·기능 카드·각주를 빼고, 단계 진행과 셀 확산을 움직임으로 보여 주는 GIF로 만들었습니다. 실제 화면은 아래 `## 화면` 섹션으로 옮겼습니다.
- 문제: `og-image.png`는 사이트 공유 이미지(Open Graph)로 쓰이고 있었습니다.
  해결: 공유 이미지는 그대로 두고 README 히어로만 `docs/screenshots/hero.gif`로 분리했습니다.
- 문제: 처음에 몇 프레임으로 만든 공통 팔레트를 모든 프레임에 썼더니, 중간 프레임의 반투명 색이 틀어졌습니다(물 범위는 초록빛, 하천·도로는 보랏빛).
  해결: 프레임마다 256색 팔레트를 따로 만들었습니다. 파일은 커졌지만 GIF 최적화를 켜서 약 790 KB로 맞췄습니다.
- 문제: 원래 모식도 SVG는 하천·도로가 지도 테두리 위로 넘어가 왼쪽 테두리가 끊겨 보였고, 반투명 팝업 뒤로 건물이 비쳤습니다.
  해결: 지도를 새로 그려 테두리를 안쪽에 직접 긋고 내용은 클립으로 잘랐습니다. 팝업과 재생 바는 불투명하게 하고 그 자리에는 건물을 두지 않았습니다.
- 문제: 셀 확산 규칙을 처음 적용했을 때 붕괴 지점 오른쪽에서 셀이 하천을 따라 위로 솟았습니다.
  해결: 붕괴 지점보다 위쪽에는 셀을 만들지 않게 했습니다. 확산 모양은 연출용 규칙이며 오송 관측 자료와는 관계없습니다.
- 문제: 처음 쓰려던 화면 캡처는 `docs/submission/` 아래에 있어 `.gitignore` 대상이었습니다.
  해결: README 이미지는 모두 추적되는 `docs/screenshots/`에 새로 캡처해 두었습니다.
- 참고: 병행 작업으로 생긴 `public/readme-hero.svg`는 README에서 더 이상 참조하지 않으며, 이번 커밋에 넣지 않고 작업 트리에 남겨 두었습니다.

## FloodOps 최종발표·교류회 자료 V2 상세 재구성

- 작업일: 2026-10-08 ~ 2026-10-09

주요 작업:
- 실제 제출 상세기획서·참가신청서를 읽고 프로젝트 목적, 주사용자, 민관협력 활용 계획을 발표 내용의 근거로 정리했습니다. 추출한 원문은 `docs/local/`에 두었고 상세 개인정보는 발표자료에 포함하지 않았습니다.
- 기존 최종발표 V1 50장을 보존하고 `docs/presentations/FloodOps-2026-v2/`에 V2 29장(15분 본문 20장·상세 부록 9장)을 만들었습니다. 사용자 참고 PPTX 27장을 렌더링해 구성 밀도와 도식 배치를 확인하되 다른 프로젝트의 수치·성과는 가져오지 않았습니다.
- 사건 단면도·타임라인·통제 시점 차트·자료 출처 구조·서비스 아키텍처·Agent 흐름·시장 검증·파일럿·운영 순환·로드맵을 넣고 설명과 근거를 같은 장에 묶었습니다. 최종 자료는 기본 도형 524개, 표 15개, 내장 XLSX가 연결된 차트 1개로 구성했습니다.
- Agent 연결 문제와 시장성 검토 요청에 집중하는 3분 교류회 자료 3장 및 40·75·65초 대본을 만들었습니다. 최종발표 대본·출처는 장별 메모와 Markdown에 함께 남겼습니다.
- Noto Sans KR Regular·Bold 전체 글꼴을 PPTX에 포함하고 동일 글꼴과 OFL 라이선스를 제공했습니다. 모식도 SVG 18개와 2배 해상도 PNG, 실제 화면 2개의 PNG·SVG 컨테이너를 함께 제공했습니다. 화면 캡처가 래스터임을 편집 안내에 명시했습니다.
- 사용자 검토 전 임의 계약·사용자 수·만족도·시장 규모·매출을 만들지 않았습니다. 현재 구현, 2026-10-08 코드·API 검증 결과, 시장·파일럿·운영 계획을 구분했습니다.

검증 결과:
- PowerPoint에서 최종발표 29장과 교류회 3장을 생성한 뒤 다시 열고 전 장을 1600×900 PNG 및 PDF로 렌더링했습니다. 각 슬라이드 이미지를 확인하고 표지 중첩, 연결선의 본문 침범, 긴 교류회 제목, 화면 비율을 수정했습니다.
- 두 PPTX의 16:9 크기(12,192,000×6,858,000 EMU), 슬라이드 수, 전체 XML, 내부 관계를 확인했습니다. 패키지 무결성 및 레이아웃 검사 모두 finding 0입니다. 텍스트 폭·높이 측정 경고도 0입니다.
- 최종 비교 차트의 캐시·내장 XLSX·PowerPoint 읽기 결과가 모두 `08:10/17`, `08:20/7`, `08:30/-3`으로 일치했습니다. 음수 막대 방향·색·단위·범주 라벨을 실제 렌더링에서 확인했습니다.
- 별도 검증용 복사본에서 텍스트, 단면도 자유형 도형, 표 셀, 차트 제목·크기를 변경하고 새 파일로 저장한 뒤 다시 열어 수정 사항이 유지됨을 확인했습니다. 최종본은 이 검증 변경을 반영하지 않았습니다.
- PPTX 내부의 Noto Regular 6,192,764바이트·Bold 6,190,824바이트가 제공한 전체 TTF와 바이트 단위로 일치하며 `embedTrueTypeFonts=1`, `saveSubsetFonts=0`입니다. SVG 20개를 XML로 파싱했고 PDF 페이지 수도 각각 29·3으로 확인했습니다.
- 기존 V1 SHA-256 `873C2936CE188811CA58D84A7AB6089C529D0E233834F9D604FAFEC7AB260C7F`가 작업 전후 일치했습니다.
- 발표에서 사용한 백엔드 근거는 2026-10-08 검증(118 passed·2 warnings, closure-timing API 결과)입니다. 이번 자료 편집만으로 실제 LLM 종단 간 성공이나 사용자 실증 완료를 주장하지 않았습니다.

문제/해결:
- 문제: 첫 V1은 핵심 주제를 여러 장으로 나누어 한 장의 설명량이 적고, 사용자가 요구한 참고 발표자료처럼 모식도와 구체적인 해석을 함께 보기 어려웠습니다.
  해결: V1을 덮어쓰지 않고 V2를 별도로 만들었습니다. 사건의 단면과 진행 시각, 계산 값과 가정, 구현 구조와 연결 과제, 시장 가설과 검증 질문을 같은 장으로 합쳤습니다. 본문은 20장·900초로 구성하고 상세 검토 자료는 9장 부록으로 분리했습니다.
- 문제: 제출안의 승인형 Agent 구상과 현재 `/ask` 자유 도구 루프를 한 가지 완료 기능으로 소개하면 실제 구현 수준과 사용자 보고의 연결 문제를 숨기게 됩니다.
  해결: 두 경로와 직접 분석 API를 구분하고, 원인을 추정하지 않은 채 사건 맥락·도구 입력·계산 반환·응답 대조를 단계별 개선 계획으로 제시했습니다. mock 테스트 통과를 실제 LLM 성공으로 해석하지 않았습니다.
- 문제: 시장성이나 유용성 배점을 채우려고 임의 이용자·매출·만족도·피해 저감 수치를 넣으면 실제 제출 문서와 구현 근거로 검토할 수 없습니다.
  해결: 반복 업무, 사용자와 구매자의 차이, 대체 수단, 구매·예산 경로, 5~8명 파일럿 계획을 구체화했습니다. 가격과 시장 계산은 검증 변수로 두고 미확인 수치를 실적으로 표현하지 않았습니다.
- 문제: 일반 PowerPoint COM 저장은 사용 문자만 포함한 글꼴을 만들며 `SaveSubsetFonts` 설정은 PowerPoint COM에서 제공되지 않았습니다. 이 상태로 전달하면 새로운 글자 추가 시 다른 환경에서 글꼴이 바뀔 수 있습니다.
  해결: 설치 가능한 OFL Noto 글꼴의 전체 TTF를 EOT 컨테이너로 넣고 저장 플래그를 전체 포함으로 설정했습니다. 내부 바이트와 제공한 폰트가 일치함을 확인했습니다. 특정 앱에서 글꼴 포함을 지원하지 않을 때 사용할 설치용 폰트도 제공했습니다.
- 문제: 도형 막대는 데이터 편집 기능을 제공하지 않고, 현 환경의 COM 차트 생성은 E_FAIL과 모달 상태로 실패했습니다.
  해결: 기준 값으로 내장 XLSX와 네이티브 OOXML 차트를 만들었습니다. XML 자식 순서·기본 라벨 설정 때문에 초기 차트에 범주/범례 중복과 흰 음수 막대가 나타나 명시적인 라벨·축·음수 색 설정으로 고쳤습니다. 다시 열린 PowerPoint에서 17·7·−3분 표시와 차트 편집·저장 유지까지 확인했습니다.
- 문제: 화면 캡처를 16:9 도형 칸에 맞춰 늘리면 실제 16:10 화면 비율이 달라졌고 SVG를 제공해도 화면 픽셀 자체가 개별 도형이 되지는 않습니다.
  해결: 원래 화면 비율을 유지하고 주변 설명은 기본 도형으로 만들었습니다. 캡처 SVG는 원본 PNG를 포함한 컨테이너라는 점과 교체 방법을 `EDIT_GUIDE.md`에 남겼습니다.

## TODO 기반 Agent 연결 안정화와 시장 검증 준비

- 작업일: 2026-10-09

주요 작업:
- TODO의 외부 자료·승인 의존 항목과 즉시 개선 가능한 연결 과제를 검토하고 Agent 대기·후속 대화·사건 전환 및 시장 검증 준비를 보완했습니다. 작업 시작 시 `git fetch`로 원격 상태를 확인했습니다.
- `/api/agent/ask`에 요청별 전체 모델 예산을 적용했습니다. `AGENT_ASK_TIMEOUT_SECONDS` 기본 25초를 최대 6단계·각 JSON 재시도가 공유하며, 남은 시간으로 비동기 HTTP를 취소합니다. 로컬 도구 계산·직렬화 시간은 추가될 수 있습니다. 최대 성공 도구 4회와 등록 도구 폴백은 유지했습니다.
- 응답에 `diagnostics`를 추가해 요청 ID·소요 시간·모델 단계·HTTP 시도·완료 경로·실패 단계/코드를 확인하게 했습니다. 모델·입력 검증·도구 실행·답변 근거 오류를 구분하고 질문·파라미터·키·예외 원문은 진단 필드에 넣지 않습니다. 요청별 ContextVar를 반환·예외 경로 모두에서 해제합니다.
- UI 질문을 1,000자로 제한하고 전송 대화를 최근 6개·각 1,500 Unicode 코드 포인트로 맞췄습니다. 사건 변경·컴포넌트 종료 때 브라우저 요청을 취소하고 응답을 버리며, 새 사건에서 다시 질문할 수 있게 합니다. 422 형식 오류와 다른 사건 응답도 구분했습니다.
- `docs/AGENT_VALIDATION.md`에 시간 예산의 적용 범위, 진단 코드, 실제 모델과 직접 분석 API를 대조할 질문·방법을 정리했습니다. `.env.example`에 `/ask` 전체 예산 설정을 추가했습니다.
- `docs/MARKET_VALIDATION.md`와 CSV 2개에 사용자·도입 검토자 가설, 교류회 요청, 20분 인터뷰, 5~8명 대조 파일럿, 평가·다음 투자 기준을 준비했습니다. CSV는 헤더만 제공하며 실적을 만들지 않았습니다. 기존 PPT V1·V2는 변경하지 않았습니다.
- TODO의 현재 모델·자격증명 및 서울 Agent 지원 설명을 코드에 맞춰 수정하고, 안정화·양식 준비 완료와 실제 모델 검증·인터뷰 미완료를 분리했습니다.

검증 결과:
- `python -m pytest backend/tests -q`: **128 passed, 2 warnings**, 71.89초. 경고는 기존 FastAPI `on_event` 사용 중단 예고입니다. 모델·네트워크를 모의하여 실제 Gemini를 호출하지 않았습니다.
- 새 백엔드 검증 10개: HTTP 요청 취소, 잘못된 JSON 재시도의 공유 예산, 여러 단계의 남은 시간 25→15→5초, 시간 초과 후 08:20 통제 도구의 유입 전 7분 반환, 검증/실행 실패 구분·API 응답 직렬화·상태 초기화, 잘못된 시간 설정 6종.
- `npm test`: **7 passed**. 1,800자 이전 답변을 1,500자로 제한하고 Unicode 문자를 깨뜨리지 않으며 원본 이력을 변경하지 않는 것을 확인했습니다.
- `npm run build`: 통과. 기존 Vite 500 KB 초과 청크 경고가 남아 있습니다.
- `npm run test:e2e`: **5 passed**, 57.1초. 긴 이전 답변 후 후속 질문의 전송 계약, 오송 요청 중 서울로 전환해 새 사건 답변만 표시하는 동작, 기존 replay·통제 비교·출처 표시를 Chromium에서 확인했습니다. Agent 응답은 모의했습니다.
- `git diff --check`: 공백 오류 없음. 실제 LLM 종단 간 성공률, 배포 반영, 기관 인터뷰·사용자 만족도는 아직 검증하지 않았습니다.

문제/해결:
- 문제: 기존 `/ask`는 모델 단계마다 25초를 새로 적용하고 잘못된 결정에 재시도도 있어, 최대 단계·도구 수를 제한해도 사용자의 전체 대기는 길어질 수 있었습니다. HTTPX의 연결·읽기 단계별 제한만으로는 응답이 계속 들어오는 연결의 전체 시간도 제한되지 않습니다.
  해결: 요청 시작 시 하나의 monotonic deadline을 만들고 모든 단계·재시도가 남은 시간을 사용하게 했습니다. `asyncio.wait_for`로 실제 HTTP coroutine을 취소합니다. 스레드 future에 timeout만 거는 방식은 백그라운드 호출이 계속될 수 있어 쓰지 않았습니다. 시간 초과 후에도 등록 도구의 결과를 보여 주며 모든 응답이 정확히 25초 내 온다고 과장하지 않습니다.
- 문제: 기존 호출 목록에는 성공한 도구만 있고 실패는 limitations에 문자열로 섞여 있어, 모델·잘못된 도구 입력·분석 실행 중 어디가 끊겼는지 구분하기 어려웠습니다. 기존 폴백 문구는 키 부재나 HTTP 실패도 모두 AI가 늦었다고 표현했습니다.
  해결: 실패 stage/code와 모델/HTTP 시도 수, 완료 경로를 구조화하고 폴백 문구를 원인을 단정하지 않는 설명으로 바꿨습니다. 진단은 요청마다 분리하고 민감한 요청 본문·키는 포함하지 않습니다.
- 문제: 이전 답변을 그대로 history에 넣으면 1,500자를 넘는 응답 뒤 후속 질문이 API 422가 되며, UI는 이를 단순 서버 연결 실패로 안내했습니다. 입력에도 1,000자 제한이 없었습니다.
  해결: 공용 API 전송부에서 이력 계약을 맞추고 UI 입력·오류 안내를 보완했습니다. 서버 제한을 늘려 더 많은 문맥을 전송하는 대신 현재 비용·입력 계약을 유지했습니다.
- 문제: 사건 변경 시 화면 대화는 비웠지만 이미 진행 중인 이전 사건 요청은 살아 있어, 늦게 도착한 답변이 새 사건 화면에 섞이거나 busy 상태가 남을 수 있었습니다. 시작 질문도 이전 사건 목록이 남을 수 있었습니다.
  해결: 사건별 effect 정리에서 요청을 취소하고 요청 객체가 현재 요청과 같은지 확인한 뒤에만 답변·오류·busy를 갱신합니다. 예시 질문도 사건 변경 시 초기화하고 응답 event_id를 검사합니다. 브라우저 취소가 서버 실행을 즉시 중단한다고 표현하지 않습니다.
- 문제: 발표에 시장 가설과 파일럿 계획은 있었지만 실제 교류회에서 누구에게 무엇을 묻고 어떤 과제로 검증할지, 결과를 어떻게 기록할지가 별도 실행 자료로 없었습니다.
  해결: 최근 업무·대안·반복 사용·도입 검토 주체를 묻는 인터뷰와 동일 자료·교차 순서의 대조 과제를 만들었습니다. 완료·시간·해석 오류·모델 설명/폴백·시장 근거를 분리해 기록합니다. 구매 의향·실제 사용자·매출을 임의로 채우거나 공식 검증 자료가 필요한 TODO를 완료로 바꾸지 않았습니다.

## Agent 후속 조건 해석과 실제 모델 소수 질문 검증

- 작업일: 2026-10-09

주요 작업:
- 계속 빌드업 요청에 따라 TODO의 Agent 실제 연결·후속 대화 과제를 진행하고 `git fetch`로 작업 시작 전 원격 상태를 확인했습니다.
- `agent_context.py`에서 이번 질문과 직전 사용자 분석 조건을 구분했습니다. 명시적 후속 표현과 한 가지 분석이 확인될 때만 조건을 이어받고 새 시각·수치는 교체합니다. 복합 조건·다른 주제·모호한 상대 시간·부적합한 지연 값은 확인을 요청합니다.
- 모델 파라미터 검증을 모든 사용자 이력의 숫자가 아니라 선택한 `parameter_context`로 제한하고 Assistant 숫자는 조건으로 쓰지 않았습니다. 호출 trace는 정규화된 실제 실행 값을 표시하며 기존 event_id 필드 계약은 유지했습니다.
- 응답의 `context_note`와 `diagnostics.context_mode`, `clarification` 완료 경로를 추가했습니다. 화면에서 앞선 조건을 재사용하거나 새 조건으로 바꿨음을 확인할 수 있습니다.
- 13개 사건·후속 질문 fixture와 `backend/evaluation/evaluate_agent.py`를 추가했습니다. 기본 offline은 모델 없이 직접 분석 API와 값을 대조하고, 명시적 live는 실제 Gemini로 같은 검사를 수행합니다. 답변·검사·진단 원본 JSON은 `docs/local/`에 남겼습니다.
- Playwright 서버의 Gemini 키를 빈 값으로 고정해 브라우저 회귀 검증이 모델 요청량을 사용하지 않게 했습니다. 브라우저→실제 로컬 `/ask`→등록 도구의 후속 대화 검증을 추가했습니다.
- `docs/AGENT_EVALUATION_RESULTS.md`에 실제 점검 결과를 기록하고 검증 안내·TODO를 동기화했습니다. 기존 발표자료와 타 작업 파일은 보존했습니다.

검증 결과:
- 최종 `python -m pytest backend/tests -q`: **150 passed, 2 warnings**, 59.51초. 기존 FastAPI `on_event` 경고입니다. 이번 회귀 22개는 13개 직접 API 대조, 오래된 조건·Assistant 숫자 거부, 연속 후속 질문, 물리 질문 경계, 정규화 trace, 음수·소수·시계 시각을 지연 분으로 잘못 읽지 않는 검사입니다.
- offline 평가 **13/13 통과**: 등록 도구 11건, 조건 확인 2건, 모델 HTTP 요청 0회. 네 사건의 계산 결과를 같은 조건의 직접 분석 API와 대조했습니다.
- 실제 `gemini-3.5-flash-lite` 소수 평가 **4/4 대조 통과**: 모델 설명 3건·조건 확인 1건, 실제 모델 HTTP 6회·도구 폴백 0건. 08:20 통제 7분(9,797ms), 사용자 조건 재사용 7분(3,938ms), 08:10 변경 17분(3,484ms)이 직접 분석과 일치했습니다. 복합 조건 확인은 모델 호출이 없었습니다.
- 실제 답변을 읽어 재구성 시각 단서, 유입·주행불능의 시간차, 피해·대피 효과 미산정 설명을 확인했습니다. 이 결과는 오송의 소수 질문에 한정하며 전체 질문 성공률·공개 배포 안정성을 검증한 결과가 아닙니다.
- `npm test`: **7 passed**. `npm run build`: 통과, 기존 500 KB 초과 청크 경고 유지.
- `npm run test:e2e`: **10 passed**, 52.2초. 새 실제 로컬 API 대화에서 08:20→동일 조건→08:10의 입력과 7→7→17분, 조건 안내 문구를 확인했습니다. 기존 replay·출처·사건별 화면 검사도 통과했습니다. 기존 다른 사례 E2E는 실행 검증했으며 이번에 작성한 것으로 기록하지 않습니다.
- `git diff --check`: 공백 오류 없음. 서울·포항·안동의 실제 모델 응답, 전체 한국어 표현, 장시간·동시 부하, 공개 서버 배포는 아직 별도 검증 과제입니다.

문제/해결:
- 문제: 등록 도구 폴백은 현재 질문만 읽어 “그 조건으로 다시 비교해줘”의 시각·수치를 찾지 못했습니다. 반대로 모델 검증은 모든 과거 사용자 숫자를 합쳐 새 조건을 요청해도 오래된 값이 허용됐습니다.
  해결: 명시적 후속 질문을 직전 사용자 분석에만 연결하고 새 값은 이전 값을 대체했습니다. 다른 주제가 중간에 있거나 조건이 여러 개인 경우 추측하지 않고 확인합니다. 모든 이력을 합쳐 강한 라우팅 힌트로 만드는 방식은 서로 다른 개입의 숫자가 섞일 수 있어 쓰지 않았습니다.
- 문제: 후속 “10분 더 일찍”의 기준이 등록 사건 시각인지 이전 가정 시각인지 확정되지 않으며, 음수·소수 분 또는 “8시 10분”을 정수 지연량으로 처리하면 뜻이 바뀔 수 있습니다.
  해결: 이런 조건 변경은 자동 계산하지 않고 명시적인 분석 종류·값을 요청합니다. 기존 단독 질문의 등록 기준 상대 시간 계산은 유지합니다.
- 문제: trace에 모델 원본 문자열·소수·한 자리 시각이 남으면 실제 도구가 받은 정규화 입력과 대조하기 어려웠습니다. 처음 정규화하면서 event_id를 제외했더니 기존 응답 계약 테스트가 실패했습니다.
  해결: 검증된 AgentToolCallRequest에서 입력 값을 가져오되 모델이 제공한 정상 event_id도 보존했습니다. 전체 회귀를 다시 실행해 최종 150개 통과를 확인했습니다.
- 문제: 13개 오프라인 평가를 일반 시연 한도(분당 6회)로 실행하자 7번째 이후 429가 되어 분석 오류처럼 보였습니다.
  해결: 외부 모델을 쓰지 않는 별도 로컬 offline 평가 프로세스에서만 한도를 올렸습니다. 실제 모델 평가에서는 설정된 한도를 유지하고 소수 질문을 선택했습니다. 공개 서버 제한은 변경하지 않았습니다.
- 문제: 설정 상태 available이나 모의 응답만으로는 실제 모델이 도구를 선택하고 계산 반환을 읽어 답하는지 확인할 수 없었습니다.
  해결: 설정된 실제 Gemini로 오송 3개 분석 질문·1개 확인 질문을 실행하고 입력·수치·설명·소요 시간을 기록했습니다. 기본값 모델과 HTTP 요청 수를 확인했으며 평가 원본에 자격증명을 기록하지 않았습니다. 다른 사건·질문의 안정성까지 일반화하거나 미측정 만족도를 만들지 않았습니다.

## 공개 서버에서 다른 사례도 열리도록 재배포 준비

- 작업일: 2026-10-09

주요 작업:
- 공개 서버(`floodops.duckdns.org`)가 10-01 빌드라 서울·포항·안동 관제 화면이 열리지 않는 원인을 확인했습니다. `/api/events`에는 5개 사건이 보이지만 세 사례의 `/reconstruction`이 404입니다. 로컬 `main`에서는 네 사례가 모두 동작합니다.
- `.dockerignore`의 `data/processed/seoul*` 줄이 `seoul_2022` 디렉터리까지 제외해 `Dockerfile.aws`의 COPY가 실패하는 결함을 고쳤습니다. 원본 export 두 파일만 제외합니다.
- `docs/DEPLOY_AWS.md`에 네 사례 재배포 체크리스트(패키지 구성, 레이어 응답 크기, 메모리 측정값, 배포 뒤 확인 항목)를 적었습니다.
- Playwright `e2e/other-cases.spec.ts`를 추가해 사례 선택 화면에서 서울·포항·안동으로 들어가 단계 수와 반사실 비교 결과를 검사하고, 익산이 잠겨 있는지 확인합니다.
- 배포 자체는 하지 않았습니다.

검증 결과:
- `Dockerfile.aws`의 COPY 원본 14개가 모두 존재하고 `.dockerignore`에 걸리지 않는 것을 확인했습니다.
- `VITE_API_BASE=same-origin npm run build` 통과(`index-Ct5YW_h1.js` 1,102 kB).
- 네 사례 레이어 응답 gzip: 오송 1.07 MB, 서울 1.18 MB, 포항 0.03 MB, 안동 0.12 MB. 네 사례를 모두 읽은 뒤 Python 프로세스 RSS 364 MB(오송만 259 MB).
- `npx playwright test`: 9개 통과(기존 5개 + 신규 4개). `python -m pytest backend/tests -q`: 117 passed, 1 failed(`test_gemini_action_retries_one_malformed_decision`, 단독 실행 시 통과하는 순서 의존 실패).

문제/해결:
- 문제: 사용자가 공개 화면에서 오송 외 사례가 열리지 않는다고 했습니다. 코드는 10-03에 이미 연결돼 있었고, 10-03 지시대로 서버에 올리지 않아 공개본이 오래된 상태였습니다.
  해결: 서버 재빌드가 필요하다는 점을 확인하고, 재빌드 전에 막힐 것(`.dockerignore` 결함)과 확인할 것(메모리·응답 크기·화면 흐름)을 먼저 정리했습니다.
- 문제: AWS CLI 세션이 만료돼 `aws login` 브라우저 승인이 필요했고, 자동 모드 권한 분류기가 배포 패키지 조립을 배포 행위로 막았습니다.
  해결: 사용자가 "배포 말고 준비만" 하라고 해 저장소 쪽 준비로 범위를 바꿨습니다. 배포 절차와 확인 값은 `docs/DEPLOY_AWS.md`에 남겼습니다.
- 문제: 안동 사례는 반사실 패널이 2개(대피명령·산사태 위기경보)라 `23:40` 체크박스가 두 개 잡혀 Playwright strict mode에 걸렸습니다.
  해결: 첫 패널로 범위를 좁히고 두 번째 패널의 제목도 함께 검사합니다.

## 서울·포항·안동 관제 화면에 단계별 지도 변화와 시나리오 비교 탭 통일

- 작업일: 2026-10-10

주요 작업:
- 오송 외 사례에서 재생을 눌러도 지도가 바뀌지 않던 문제를 사례별로 다른 방법으로 채웠습니다. 서울은 공식 침수흔적도를 강우 순서로 드러내고, 포항·안동은 Copernicus DEM 기반 HAND 근사 셀을 보도된 사건 순서로 넓힙니다(`data/scripts/create_case_hand_reconstruction.py`).
- 서울 `flood_extent` 피처에 `reveal_stage`를, `reconstruction.trace_reveal`에 단계별 60분 강우 누적 최댓값과 드러내는 침수심을 넣었습니다. 신림P 60분 강우가 95 mm/h를 넘기 전에는 0건, 20:49 단계 1,557건(침수심 0.38 m 이상), 20:59 이후 10,468건 전체입니다.
- 포항은 보도된 범람 지점 냉천교에서 HAND 0.25 m 이하 지형을 따라 퍼지고, 도달 거리 상한 900 m는 인덕동 일대에 닿는 최소 거리입니다. 단계별 셀 수 0·0·78·120·144·175·175·175.
- 안동·의성은 OSM river 등급 선 전체를 하천으로 보고 보도 수위 순서로 띠를 넓혔다 좁힙니다(거리 = 비율²×2 km). 단계별 셀 수 605·952·973·1,035·1,073·788·265. 구계리는 river 선에서 5 km 떨어져 재현하지 않습니다.
- `UrbanConsole`에 "단계별 표시(깊은 곳 먼저)" 토글과 현재 건수, `TimelineConsole`에 붉은 HAND 셀 레이어·범례·현재 셀 수를 넣었고, 두 화면의 "반사실 비교" 탭을 오송과 같은 "시나리오 비교"로 바꿨습니다.
- Copernicus DEM N35_E129·N36_E128 타일을 공개 AWS 버킷에서 받아 `data/raw`에 두고 manifest에 SHA-256을 기록했습니다. DQ-012로 가정과 한계를 적었습니다.

검증 결과:
- `python -m pytest backend/tests -q`: 154 passed(신규 `test_stage_replay_layers.py` 5개 포함).
- `npx playwright test`: `other-cases.spec.ts` 4개 통과. 서울 범례 0 → 1,557 → 10,468건, 포항 0 → 78 → 120셀, 안동은 첫 단계보다 예측 최고 단계 셀 수가 큼을 확인.
- `npm run build`·`npx tsc -b`·`npm test`(7개) 통과.
- 레이어 응답 gzip: 포항 0.10 MB, 안동 0.35 MB, 서울 1.18 MB.

문제/해결:
- 문제: 서울도 DSM으로 HAND envelope을 만들어 보니, 임계 0.25~3 m·연결 거리 600~1,500 m 전 조합에서 envelope 면적 중 공식 흔적 위 비율이 14~16%로 하천 회랑 전체의 흔적 비율과 같았습니다. 30 m DSM이 건물 높이를 포함해 고밀 시가지의 지면 고저를 구분하지 못합니다.
  해결: 서울 envelope은 싣지 않고 산출물을 지웠습니다. 대신 이미 확보한 공식 흔적도를 방재성능목표(95 mm/h) 초과 뒤 깊은 곳부터 드러내는 순서 가정으로 바꿨습니다. 최종 상태가 공식 기록과 같다는 점이 장점입니다.
- 문제: 포항·안동은 골짜기 바닥이 HAND 0 m라 임계를 올려도 셀이 한꺼번에 나타났습니다(포항 366 → 410, 안동 1,005 → 1,073).
  해결: 포항은 보도된 범람 지점(냉천교)에서 거리를 재어 퍼지게 하고 보도된 침수 지점(인덕동)에 닿는 거리로 상한을 맞췄습니다. 안동은 하천에서의 거리를 비율²로 키워 띠가 넓어졌다 좁아지게 했습니다. 둘 다 관측이 아니라 보도 순서라는 점을 레이어 메타데이터·한계·범례에 적었습니다.
- 문제: 안동 미천 OSM 선은 귀미1리 상류에서 이름이 끊겨 귀미1리가 하천에서 895 m, HAND 12.7 m로 잡혔고 임계 보정이 6 m 상한에 실패했습니다.
  해결: river 등급 선 전체를 하천으로 쓰고, 마을 중심점 400 m 안의 가장 낮은 셀을 기준점으로 삼았습니다.
- 문제: Copernicus 타일 단일 스트림 다운로드가 초당 50 KB라 50 MB에 15분 이상 걸렸습니다.
  해결: HTTP Range 12분할 병렬로 받아 5분 안에 끝냈습니다. 받은 파일 크기와 SHA-256을 manifest에 적었습니다.
- 참고: 사용자가 바탕화면의 BASEMENT 발표자료처럼 FLOOD 자료를 다시 만들어 달라고 했으나, 바탕화면과 사용자 프로필 어디에서도 해당 `.pptx`를 찾지 못했습니다. 파일 위치를 받은 뒤 진행합니다.

## FloodOps 최종발표 자료 v3: BASEMENT 2차 발표자료와 같은 도구·구성으로 재구성

- 작업일: 2026-10-10

주요 작업:
- `docs/presentations/FloodOps-2026-v3/`에 24장 발표자료를 새로 만들었습니다. BASEMENT 프로젝트의 `build.py`·`svgkit.py`·`finalize.ps1`을 그대로 가져오고 `slides.py`만 FloodOps 내용으로 썼습니다. 글자·도형은 PowerPoint 기본 개체, 도식만 SVG+PNG입니다.
- 구성은 BASEMENT와 같이 다섯 단계입니다. 배경과 문제(오송 13분·7단계 타임라인·흩어진 자료) → 해결과 결과(연결 파이프라인·통제 18분 전·HAND 셀 152→352·네 사례 선행 시간·사례별 자료 수준) → 근거와 한계(계산하지 않는 것·출처 화면·Agent 구조) → 서비스와 활용(화면 4개·관제·시나리오 비교·다른 사례·활용 시나리오) → 실현과 확장(검증 수치·운영 순환·사례 추가 계약) → 정리·부록(데이터 9종·출처).
- 수치는 2026-10-10 로컬 API(closure-timing, lead-times)·테스트(pytest 154, Playwright 9)·DQ 문서에서 가져왔고, 장별 출처는 마지막 «출처» 장에 자동으로 모입니다. 화면 캡처 10장은 로컬 서버에서 1600×1000으로 새로 찍었습니다.
- `Final_Speaker_Notes.md`(권장 시간 합계 730초)와 `EDIT_GUIDE.md`를 함께 두었습니다. 기존 V1·V2 자료는 건드리지 않았습니다.
- `TimelineConsole`에 개발 모드에서만 `window.__floodopsMap`으로 지도 객체를 노출해, 캡처·검사 스크립트가 레이어 렌더 상태를 읽을 수 있게 했습니다.

검증 결과:
- `python -X utf8 build.py`로 24장 생성, 폭 검사 assert 통과. PowerPoint COM으로 PDF와 장별 PNG(1280×720)를 내보내 24장을 모두 눈으로 확인했습니다.
- 표지 패널 범례·시간축 겹침, 3장 본문 넘침, 4장 08:27/08:40 라벨 겹침, 7장 주석 겹침, 21장 카드 넘침, 23장 표 셀 넘침을 고친 뒤 다시 내보내 확인했습니다.
- Pohang·Andong 지도의 HAND 셀은 `queryRenderedFeatures`로 175셀 렌더를 확인했습니다. 첫 캡처에서 셀이 안 보인 것은 레이어 로드 전 촬영 때문이었습니다.

문제/해결:
- 문제: 사용자가 "바탕화면의 BASEMENT 발표자료처럼" 재구성을 요청했는데, 바탕화면 파일은 OneDrive 경로 문제로 찾지 못했고 실제 원본은 `Basement-Flood-Vulnerability/docs/submission/.../presentation`에 있었습니다.
  해결: 그 폴더의 빌드 도구를 재사용했습니다. PDF 렌더 도구(pdftoppm)가 없어 PowerPoint COM으로 PNG를 내보내 디자인을 확인했습니다.
- 문제: 발표자 메모 생성 스크립트가 슬라이드 함수를 두 번 호출해 «출처» 장이 넘쳤습니다.
  해결: `SOURCES.clear()` 뒤 한 번만 순회하도록 바꿨습니다.

## 서울·포항 단계별 지도를 안동과 같은 하천 띠 규칙으로 통일

- 작업일: 2026-10-10

주요 작업:
- 사용자 요청("의성 기준으로 다른 시나리오도 똑같이")에 따라 포항·서울의 단계별 지도 변화를 안동·의성과 같은 규칙으로 바꿨습니다. 하천 선 양안의 HAND 0.25 m 이하 셀을 비율²×2 km 거리까지 넓히는 띠입니다.
- 포항: 냉천교에서 퍼지는 방식을 냉천 양안 띠로 바꿨습니다. 단계별 셀 수 0·0·236·370·403·415·415·415.
- 서울: 신림P 60분 강우의 누적 최댓값 비율로 OSM stream 선 양안의 띠를 넓힙니다(405 → 1,031 → 1,216 → 1,218). 공식 침수흔적도와 깊은 곳부터 드러내는 규칙은 그대로 두고 그 위에 띠를 얹었습니다. `UrbanConsole`에 띠 레이어·토글·범례 셀 수를 추가했습니다.
- `seoul_repository`에 `hand_reconstruction`·`terrain` 레이어, provenance, 한계 문장, `reconstruction.hand_reconstruction` 메타데이터를 넣었습니다.
- 발표자료 v3의 10·11·17장 문구와 서울·포항 캡처를 새 규칙에 맞게 갱신하고 다시 빌드했습니다. DQ-012와 DATA_GUIDE 표도 같이 고쳤습니다.

검증 결과:
- `python -m pytest backend/tests -q`: 156 passed(서울 띠 테스트 추가). `npx playwright test e2e/other-cases.spec.ts`: 4 passed(포항 236·370셀, 서울 1,218셀 범례 확인). `npm run build`·`npx tsc -b` 통과.
- 새 캡처에서 서울은 도림천·지류 양안의 붉은 띠와 파란 흔적이 함께, 포항은 냉천 양안의 띠가 보입니다.

문제/해결:
- 문제: 서울 지형 띠는 공식 흔적과 대조하면 회랑 평균과 같아 앞서 "싣지 않음"으로 기록했는데, 사용자가 안동과 같은 재생 시각화를 원했습니다.
  해결: 띠를 재생용 도식으로 싣되 공식 흔적도를 별도 레이어로 유지하고, 한계 문장·DQ-012·발표자료 11장에 "근거가 아니라 도식"임을 적었습니다. 침수 근거는 공식 흔적도만 씁니다.
- 문제: 발표자료를 PowerPoint로 열어 둔 상태라 재빌드가 PermissionError로 막혔습니다.
  해결: COM으로 해당 프레젠테이션만 닫고 다시 빌드했습니다.

## 방향 재설정 기록: 지하차도 통제 판단 트윈

- 작업일: 2026-10-10

주요 작업:
- 사용자가 "지금 제품은 사례 재구성 뷰어이지 디지털 트윈이 아니고 사용성이 안 보인다"고 판단해, 제출 상세기획서(ver2)와 PROJECT_PLAN을 다시 읽고 방향을 다시 잡았습니다. 결론은 시설(지하차도) 단위의 운영 트윈이며, 과거 사건은 통제 기준의 백테스트로 씁니다. 훈련 시뮬레이터 방향은 가지 않습니다.
- `TODO.md`에 `## DIRECTION` 절을 새로 두어 정의, 사례 역할 변경, 확장성 근거(하천 인접형·내수 침수형 두 구동 유형), 공식 통제 기준 확인 결과, Phase 2(LISFLOOD-FP, 가정 민감도로 제한)·Phase 3(실시간 어댑터·시설 레지스트리·지금 상태 보드) 항목, 사용자 확정 필요 항목을 적었습니다.
- 본선 심사 기준을 공모전 사이트에서 확인했습니다. 서비스 개발 부문: 기획성 15·완성도 25(기술·기능 구현·배포)·확장성 25·유용성 25·발표 10. 발표자료 v3는 BASEMENT(공간정보 경진대회 항목) 구성을 복제한 것이라, 방향 확정과 보드 화면이 생긴 뒤 심사항목 순으로 다시 만들기로 했습니다.

검증 결과:
- 행안부 지하차도 통제 기준이 침수심 15 cm에서 5 cm로 강화됐다는 보도(2026-05)와 진입차단시설 564곳 중 512곳 완료 보도(2026-07)를 확인했습니다. 원문(행안부 보도자료·지침)은 아직 확보하지 않았습니다.
- 공공데이터포털에 국토교통부 「시설물안전법 대상 지하차도 현황」(CSV) 등 지하차도 목록 자료가 있음을 확인했습니다. 침수 위험 등급 목록은 공개본을 찾지 못했습니다.

문제/해결:
- 문제: 사례를 늘릴수록 사례마다 자료 수준이 달라 화면이 달라지고 "사건 전시"가 됐습니다. 포항·안동 띠를 보도 순서로 만든 것이 그 한계였습니다.
  해결: 단위를 사건에서 시설로 바꿨습니다. 지하차도는 어디든 같은 자료 유형(위치·관측소·DEM)을 가지므로 확장 규칙이 하나가 됩니다. 구동 조건만 수위 기준과 강우 기준 두 유형으로 나눕니다.
- 문제: Phase 2 물리 모형은 제방 붕괴 위치·폭·시각 원문이 없어 막혀 있습니다.
  해결: 위어 공식으로 붕괴 유량을 가정하고 제방고·붕괴 폭 민감도로 범위를 제한해 `SIMULATED`로 분류하기로 했습니다. 공식 벡터 범위가 오기 전까지 그 이상을 주장하지 않습니다.

## Phase 3 시작: 지하차도 통제 판단 트윈 뼈대(시설 레지스트리·관측 어댑터·단계 규칙·백테스트)

- 작업일: 2026-10-10

주요 작업:
- `backend/app/twin.py`를 새로 만들었습니다. 시설 레지스트리(첫 항목 궁평2지하차도: 미호강교 3011665, 관측소 기준면 19.643 m, 관심 5.0·주의보 7.0·경보 8.0·심각/계획홍수위 9.38 m), 관측 소스 두 종류(저장된 2023년 10분 CSV를 재생하는 `ReplaySource`, 홍수통제소 OpenAPI를 부르는 `HrfcoLiveSource`), 단계 판정과 통제 검토 권고(`assess`), 2023년 계열에 같은 규칙을 적용하는 `backtest`.
- 규칙 `river_stage_v1`: 계획홍수위 도달, 또는 경보 수위 이상이면서 최근 30분 상승 속도로 계획홍수위까지 60분 이내면 `CLOSURE_REVIEW`. 주의보·경보 수위는 `MONITOR`, 그 아래는 `NORMAL`. 침수심은 재지 않으며 공식 통제 기준(침수심)은 현장이 우선한다는 한계를 응답에 넣었습니다.
- API: `GET /api/twin/facilities`, `GET /api/twin/mode`, `GET /api/twin/facilities/{id}/status?at=`, `GET /api/twin/facilities/{id}/backtest`. `HRFCO_API_KEY`가 있으면 live, 없으면 replay 모드이며 `FLOODOPS_TWIN_MODE`로 강제할 수 있습니다.
- 테스트 `backend/tests/test_twin.py` 4개.

검증 결과:
- 백테스트: 2023년 10분 수위에 규칙을 적용하면 06:50 이전에 `CLOSURE_REVIEW`가 처음 뜨고, 유입(08:27)까지 97분 이상, 제방 붕괴(08:09)까지 79분 이상 앞섭니다. 03:00에는 주의보 수위·감시, 08:00에는 계획홍수위 도달·통제 검토(유입 27분 전)입니다.
- 사용자가 `.env`에 넣은 `HRFCO_API_KEY`(36자)로 미호강교 최근 2시간 10분 수위를 실제 조회해 200과 13건을 받았습니다. 같은 키로 기상청 API허브(`nph-aws2_min`, `kma_sfctm2`)를 부르면 401 "유효한 인증키가 아닙니다"라 기상청 키는 별도입니다.
- `python -m pytest backend/tests -q`: 160 passed.

문제/해결:
- 문제: `.env`는 uvicorn이 자동으로 읽지 않아 `twin_mode()`가 키를 못 봤습니다.
  해결: Agent와 같은 `_load_env_file_once()`를 `twin_mode()`에서 호출합니다.
- 문제: 실시간 응답의 `<wl>`이 공백인 레코드가 있어 `float('')`로 422가 났습니다.
  해결: 값을 strip하고 비어 있으면 건너뜁니다.
- 참고: 사용자가 "기상청 넣었어"라고 했지만 `.env`에서 확인되는 이름은 `HRFCO_API_KEY` 하나이고 그 값은 홍수통제소 키로 동작합니다. 기상청 키는 `KMA_API_HUB_KEY` 이름으로 따로 넣어야 합니다.

## 지하차도 통제 판단 보드 화면(#twin)

- 작업일: 2026-10-10

주요 작업:
- `src/dark/TwinBoard.tsx`·`twin.css`를 새로 만들어 `#twin` 라우트에 연결했습니다. 시설 카드(궁평2지하차도·노선·관리기관·연결 관측소), 권고 배지(정상/감시/통제 검토)와 사유, 관측 KPI(현재 수위·EL, 계획홍수위까지 여유, 최근 30분 상승 속도, 현재 속도로 도달까지 분), 관심·주의보·경보·계획홍수위 눈금이 있는 수위 막대, 시각 선택(실시간 «지금»과 2023-07-15 04:10·06:40·06:50·08:09·08:27 프리셋, 직접 입력), 백테스트 표(단계 전환·첫 권고·유입/붕괴까지 분), 규칙과 한계를 한 화면에 둡니다.
- 소개 화면에 "지하차도 통제 판단 보드" 버튼을, 보드 상단에 "통제 기준 검토"(오송 관제)·"검증 사례"(사례 간 비교) 링크를 두었습니다. 실시간 모드는 5분마다 다시 읽습니다. `?at=` 해시로 재생 시각을 공유할 수 있습니다.
- `types.ts`·`api.ts`에 twin 타입과 getter 4개, Playwright FastAPI 서버에 `FLOODOPS_TWIN_MODE=replay`를 넣어 E2E가 실시간 API에 기대지 않게 했습니다. `twin.py`의 규칙 설명(`review_when`)을 한국어로 바꿨습니다.

검증 결과:
- `e2e/twin-board.spec.ts` 1개 통과: 소개 → 보드 진입, 기본 재생 시각(08:00) «통제 검토», 04:10 «감시»·7.69 m, 06:50 «통제 검토»·계획홍수위 도달, 백테스트 표와 한계 문구.
- `npx tsc -b`·`npm run build` 통과, `test_twin.py` 4개 통과.
- 로컬 5173/8033에서 06:50 재생 화면을 캡처해 확인했습니다. 백테스트는 05:50 첫 권고(경보 수위 8.04 m + 상승 속도), 유입 157분 전·붕괴 139분 전입니다.

문제/해결:
- 문제: `?at=`로 들어온 뒤 «지금» 등으로 해시를 바꿔도 같은 컴포넌트가 유지돼 재생 시각이 초기값에 머물렀습니다.
  해결: `hashchange`에서 `at`을 다시 읽습니다.
- 문제: Playwright 설정에 다른 도구가 넣은 `env`와 제가 넣은 `env`가 같은 서버 블록에 중복됐습니다.
  해결: 한 객체로 합쳤습니다(`GEMINI_API_KEY: ""`, `FLOODOPS_TWIN_MODE: "replay"`).
- 문제: `<article aria-label>`은 role이 region이 아니라 E2E의 `getByRole("region")`이 비었습니다.
  해결: `[aria-label=…]` 로케이터로 바꿨습니다.

## 홍수통제소 OpenAPI로 전국 관측소 목록과 미호강 2019~2026 관측 이력 확보

- 작업일: 2026-10-10

주요 작업:
- `water-level-rise`(DATA·AI 분석 경진대회, 6시간 최대 수위 상승량 예측)의 자료를 FloodOps에 쓸 수 있는지 검토했습니다. 대회 자료는 익명 관측소·합성 시각이고 재식별이 금지돼 관측으로 쓸 수 없지만, 특징 설계·검증 절차·코드는 실명 자료로 재학습하면 쓸 수 있다고 판단했습니다. 다른 도구가 같은 결론으로 `water_level_bridge.py`와 보드의 24시간 이력 카드를 만들어 둔 것을 확인했습니다(미커밋).
- 원출처 확보 경로를 만들었습니다. `data/scripts/collect_hrfco_history.py`가 홍수통제소 OpenAPI에서 전국 관측소 목록(수위 1,420·강우 744·댐 58·보 17)을 `data/manifests/hrfco-stations.json`에 저장하고, 관측소별 1시간(1년 단위 호출)·10분(15일 단위 호출) 이력을 `data/raw/hrfco/`(원본 JSON)와 `data/processed/hrfco/`(병합 CSV)에 만들며, 수집마다 행 수·유효 수·연도별 분포·SHA-256을 `data/manifests/hrfco-history.json`에 기록합니다. `nearest`로 시설에서 가까운 관측소를 찾고 `qc`로 3 m 이상 급변을 표시합니다.
- 궁평2지하차도 주변 수위 3곳(미호강교·팔결교·미호교)과 강우 4곳(농정원·흥덕교·부강면사무소·명학리)의 2019~2026 1시간 자료와 홍수기(6~9월) 10분 자료를 받았습니다. `docs/HRFCO_HISTORY.md`에 전국 가용 범위, 조회 한도, 수집 결과, 품질 메모, 다음 단계를 적었습니다.

검증 결과:
- 1시간: 관측소당 70,082행, 수위 유효 68,098~68,099, 강우 농정원·흥덕교 68,100. 10분(홍수기): 관측소당 140,544행 전부 유효(옥산 제외). 1년 1H 호출 1.1초, 15일 10M 호출 2.3초.
- 미호강교 8년 사상: 관심 수위(5 m) 이상 11건, 경보(8 m) 이상 2건(2023-07, 2025-07). 한 관측소로는 학습 사상이 적어 전국 홍수예보 지점(223곳)을 함께 써야 합니다.

문제/해결:
- 문제: 옥산 강우(30114110)는 목록에 있지만 8년 내내 값이 없었고, 부강면사무소는 2025-05까지·명학리는 2025-05부터만 있었습니다.
  해결: 옥산 CSV와 manifest 항목을 지우고 제외 사유를 manifest와 문서에 남겼습니다. 명학리를 부강면사무소의 후속 관측소로 보고 둘 다 보관합니다.
- 문제: 미호강교 1시간 자료에 2023-05-16 01:00~11:00 강우 없이 1.5 → 11.3 → 13.3 → 1.2 m로 뛰는 구간이 있었습니다.
  해결: 자동 제거 대신 `qc` 명령으로 급변 3건을 manifest에 표시했습니다. 학습 시 제외 규칙은 모델 단계에서 정합니다.
- 문제: 10분 CSV는 관측소당 4.3 MB라 git에 넣으면 저장소가 커집니다.
  해결: `data/processed/hrfco/*_10M.csv`를 `.gitignore`에 넣고 원본 JSON과 manifest로 재생성하게 했습니다. 1시간 CSV(2.1 MB × 7)는 추적합니다.
- 참고: 전국 지하차도 목록(시설물안전법 938건)에는 좌표가 없어 「전국도로터널정보표준데이터」(위경도 포함, data.go.kr 키 필요)로 붙여야 합니다.

## 전국 지하차도 좌표(OSM) 부여와 관측소 연결, 전국 수위 수집 시작

- 작업일: 2026-10-10

주요 작업:
- 전국 지하차도 좌표 출처를 바로잡았습니다. 처음에 「전국도로터널정보표준데이터」를 제안했으나 사용자가 교량·터널 대장이라 지하차도가 없다고 확인해, OpenStreetMap Overpass로 이름에 "지하차도"가 든 도로 704개 way(396개 이름)를 받았습니다. `data/scripts/match_underpasses_osm.py`가 국토교통부 목록 938건(사용자가 내려받은 CSV)과 정규화한 이름으로 맞추고, 같은 이름의 way는 2 km 안에서 평균하며, 타 시도 후보는 시도 bbox로 버립니다. 결과 282건 매칭·4건 모호·652건 미매칭.
- `data/scripts/link_facilities_to_gauges.py`가 좌표 있는 시설마다 가장 가까운 수위·강우 관측소 3곳(거리·홍수예보 지점 여부·공식 수위)을 `facility_gauge_links.csv`로 만듭니다. 282곳 중 228곳(81%)이 5 km 안에 수위 관측소, 47곳은 홍수예보 지점이 가깝습니다. 궁평2지하차도는 미호강교 1.17 km.
- 전국 홍수예보 지점 223곳의 2019~2026 1시간 수위 수집을 시작했고(`hrfco-flood-forecast-stations.txt`), `events` 명령으로 관측소별 관심·주의보·경보·계획홍수위 초과 사상 수를 집계하도록 했습니다. 전국 1H CSV는 git에서 제외하고 미호강 7개 파일만 추적합니다.

검증 결과:
- Overpass 전국 조회 11초, 704 way. 매칭 시도별: 경기 124/369, 서울 41/197, 대전 21/31, 세종 12/21.
- 수집 완료된 10곳 기준 `events`: 관심 110건·주의보 30·경보 17·계획홍수위 5. 전체 223곳 집계는 수집 완료 뒤 기록합니다.

문제/해결:
- 문제: data.go.kr 서비스키가 `.env`에 없고(후보 키 전부 "등록되지 않은 서비스키"), 터널 API(`btiData/getTunlList`)는 어차피 지하차도를 담지 않습니다.
  해결: 키 없이 받을 수 있는 OSM으로 좌표를 붙였습니다. `link_facilities_to_gauges.py tunnels`는 키가 생기면 쓸 수 있게 남겨 두었습니다.
- 문제: 관측소 코드 목록을 Windows 텍스트 모드로 써서 `\r`이 붙어 폴더 이름 오류가 났습니다.
  해결: `\r`을 제거하고 다시 수집했습니다.
- 한계: OSM 이름 매칭은 30%만 잡습니다. 미매칭 652건은 지자체 현황 CSV 주소 지오코딩이나 OSM 보완이 필요하고, 가까운 관측소가 실제 유입 하천인지는 시설별 확인 항목으로 남습니다.

## 시설 통제 판단 Agent: 상태·규칙·백테스트 연결

- 작업일: 2026-10-10

주요 작업:
- TODO의 Phase 3 방향에 맞춰 시설 범위의 Agent를 세 도구(`get_facility_status`, `get_control_rule`, `get_facility_backtest`)로 연결했습니다. `/api/agent/ask`·직접 도구 API·카탈로그·추천 질문에 `facility_id`를 추가했고 `observation_at`으로 과거 관측을 선택합니다. 사건 분석 범위는 별도 유지했습니다.
- 화면에서 고른 시설·재생 시각을 서버가 고정하고 모델의 값 변경·다른 범위 도구 호출을 실행 전에 거절합니다. 시설과 사건 불일치·없는 시설·잘못된 ISO 시각도 모델 호출 전에 검증합니다. UTC `Z`·오프셋 입력은 KST로 변환합니다.
- 관측 모드·나이·신선도와 검토 권고를 구분했습니다. 내부 신선도 한도는 10분 자료 20분, 1시간 자료 90분이며 누락·지연 관측은 `NEEDS_DATA`입니다. replay는 현재 관측으로 쓰지 않고 live 소스 실패를 과거 데이터로 대체하지 않습니다. 오류 URL의 키 노출도 막습니다.
- 모델 실패 또는 근거 없는 안전·통제 완료 설명을 도구 기반 문장으로 대체합니다. 백테스트 답변에는 DQ-009의 06:40 사건 기록과 06:50 관측 도달 차이를 유지하고, 상승 속도 외삽이 예보·유입 예측이 아님을 명시합니다.
- 오송 상단에 분석 범위 드롭다운·시설 선택·과거 재생 시각·세 추천 질문을 추가했습니다. 결과를 표와 원본 근거로 펼쳐 볼 수 있으며 시설·시각 변경 시 대화와 진행 중 요청을 버립니다.
- 시설 평가 suite와 사용 문서 `docs/FACILITY_AGENT.md`를 추가했습니다. TODO의 시설 Agent 항목을 완료하고 기존 과거 사건 검증과 시설 검증을 구분했습니다. 전체 상태 보드·추가 시설·공식 지침 원문 확보·공개 재배포는 남아 있습니다.

검증 결과:
- 전체 `python -m pytest backend/tests -q`: 178 passed, 기존 FastAPI startup 폐기 예정 경고 2개. 이후 UTC `Z` 입력 케이스를 추가한 시설 테스트: 19 passed. 실제 HRFCO 실시간 Agent 운영·기관 승인 검증은 수행하지 않았습니다.
- `npm test`: 7 passed. `npm run build`: 통과, 기존 500kB 초과 번들 경고 유지.
- `npm run test:e2e`: 11 passed. 실제 로컬 Agent API로 시설 상태·규칙·백테스트를 실행하고 시설 ID·도구·모델 미호출·표 결과·범위 변경 초기화를 확인했습니다. 스크린샷 첨부를 추가한 시설 테스트도 1 passed입니다.
- Playwright HTML 보고서의 1280×720 화면을 눈으로 확인했습니다. 상단 분석 범위 선택과 입력란이 화면 안에 남고, 펼친 백테스트 표·출처·한계가 결과 패널 안에서 표시됩니다.
- 시설 offline suite: 3/3, 도구 설명 3건·모델 요청 0회. 실제 Gemini suite: 3/3, 모델 설명 3건·HTTP 6회·폴백 0건. 관측은 2023년 replay로 고정했습니다. 상태 9.91m·여유 -0.53m, 백테스트 첫 검토 05:50·유입까지 157분·붕괴까지 139분이 직접 API와 일치했습니다.
- 실제 모델 답변을 읽어 과거 재생·가정·담당자 판단 경계를 확인했습니다. 최초 실제 모델 원본에는 이후 서버가 추가한 DQ-009·외삽 단서가 없다는 점을 `docs/AGENT_EVALUATION_RESULTS.md`에 구분해 기록했습니다. 공개 배포·전체 성공률·시장 실증으로 해석하지 않습니다.

문제/해결:
- 문제: 작업 시작 시 기존 사건 분석의 후속 질문 확장을 검토했지만, 작업 중 TODO에 시설 중심 운영 트윈 방향과 "상태·기준·과거 비교" 세 도구 과제가 추가돼 있음을 확인했습니다.
  해결: 일반 사건 도구를 더 늘리는 대신 이미 등록된 궁평2지하차도의 관측·규칙·백테스트를 Agent에 연결했습니다. 기존 사건 분석은 별도 범위로 보존해 미완성 상태 보드 개편과 섞지 않았습니다.
- 문제: twin 모듈은 planner를 통해 agent_tools를 참조해 facility 모듈의 최상위 twin import가 순환 import를 만들었습니다. 과거 "수위 백테스트" 질문이 상태 도구까지 불러 실시간 조회를 섞을 수도 있었습니다.
  해결: twin 참조를 함수 안에서 가져오고 과거 질문은 백테스트, 현재 상태를 명시한 질문만 상태 도구로 라우팅하도록 분리했습니다. 명시적인 재생 시각은 live 소스를 조회하지 않도록 별도 실행 경로를 둡니다.
- 문제: compact Agent의 flex 줄에 시설 입력과 추천 질문을 그대로 넣자 높이가 커져 상단 선택 버튼이 화면 밖으로 밀렸습니다. 첫 브라우저 검증은 범위 복귀 버튼을 클릭하지 못해 실패했습니다. 재생 시각을 바꿀 때 추천 질문을 지우고 다시 가져오지 않는 문제도 있었습니다.
  해결: 선택 입력·추천 질문을 상단 드롭다운으로 묶고 질문 실행 시 닫습니다. 추천 질문 초기화는 시설/사건 변경에만 적용하고 시각 변경은 대화만 초기화합니다. 강제 클릭으로 테스트를 우회하지 않고 실제 클릭으로 범위 전환과 긴 결과 표시를 재검증했습니다.
- 문제: 실제 모델 백테스트 설명은 06:40 사건 시각만 말하고 06:50 관측 차이를 생략했습니다. Python 3.10의 날짜 파서는 API 검증이 허용한 UTC `Z`를 실행 경로에서 바로 읽지 못했습니다.
  해결: 도구 note의 DQ-009를 답변에 보충하는 회귀 검증을 추가하고 `Z`를 `+00:00`으로 정규화해 KST로 변환합니다. 시간차 수치를 모델이 직접 계산하거나 법정 통제 기준을 확정하도록 하지 않습니다.
- 문제: PowerShell의 기본 파이프 인코딩 때문에 문서에 덧붙인 한글이 물음표로 바뀌었습니다.
  해결: 해당 추가 절만 UTF-8 패치로 교체하고 새 코드·평가 fixture·문서에서 깨진 문자열을 확인했습니다. 기존 기록은 보존했습니다.
