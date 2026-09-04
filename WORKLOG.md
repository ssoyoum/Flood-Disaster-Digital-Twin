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
- `compare_scenarios`를 자연어 planner workflow까지 확장할지는 해커톤에서 실제 시연 흐름을 확인한 뒤 결정한다.

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
