# FloodOps TODO

Last Updated: 2026-08-30 10:00 KST

## Manual Action Required

현재 사용자의 직접 조치가 필요한 항목입니다. 아래 상태는 새 데이터셋을 추가로 수집하라는 뜻이 아니라, 기존 공식 출처의 인증·승인 또는 수동 다운로드가 완료될 때까지 대기하는 상태입니다.

- [ ] KMA AWS/ASOS 오송 2023 강우 원본 다운로드
  - 상태: `MANUAL_DOWNLOAD_REQUIRED`
  - 관측소 후보: 오창가곡 `683`, 청주금천 `327`
  - 기간: `2023-07-15` ~ `2023-07-16` KST
  - 요소: 강수량 `SFC02010001`
  - 공식 페이지: https://data.kma.go.kr/data/grnd/selectAwsRltmList.do?pgmNo56=
  - 다운로드 후 저장 위치: `data/raw/rainfall/osong/`
  - 상세 기준: `data/manifests/source-availability.yml`의 `osong_rainfall_primary`
- [ ] 2023년 인접 한국 공식 행정경계 확보
  - 상태: `MANUAL_DOWNLOAD_REQUIRED`
  - SGIS: `accessToken` 필요
  - 행안부 도로명주소 전자지도: 신청·본인확인·기관 승인 필요
  - 상세 사유: `data/manifests/source-availability.yml`의 행정경계 항목

## In Progress

- [ ] 2023 오송 사건을 대표 분석 사건으로 완성
  - 기본 사건: `2023 오송 하천·교통시설 침수 · 미호강 · 궁평2지하차도`
  - 분석 흐름: `미호강·제방 → 범람 → 지하차도 → 차량·통행자`
  - 우선 분석 대상: 지하차도·교통시설
  - 현재 확보: 2023-07-15 OSM 공간 스냅샷, 2023년 인구 래스터, Copernicus DEM, geoBoundaries, NASA POWER 보조자료, 공식 사건 보고서
  - 미확보: 2023 오송 침수흔적도, 2023-07-15 수위·강우 관측소 원본
- [ ] 오송 확보 원본 레이어와 과거자료 기반 분석값 연결
  - 실행 중 API를 호출하지 않고 승인 후 확보한 원본 응답을 스냅샷으로 사용
  - 인구는 공식 통계 우선순위와 `event_year`/자료 기준연도를 분리해 관리
  - DEM은 현재 원본 확보 단계이며 저지대·고도 파생 레이어 연결 필요

## To Do

### High Priority

#### Data acquisition status

- [x] KOSIS official 2023 eup-myeon-dong population raw data
  - Source: `DT_1B04005N`, 2023-01 through 2023-12
  - Raw: `data/raw/population/kosis_101_DT_1B04005N_M_2023.zip`
  - Osong-eup code: `4311325000`, 264 age/month records
  - 2023-07 official Osong-eup population: 27,125
  - WorldPop remains fallback spatial-distribution data only
- [ ] KMA AWS/ASOS official rainfall observation
  - `MANUAL_DOWNLOAD_REQUIRED`
  - Candidates: 오창가곡 `683`, 청주금천 `327`
  - Period: 2023-07-15 through 2023-07-16 KST
  - Element: 강수량, `SFC02010001`
  - Official page: `https://data.kma.go.kr/data/grnd/selectAwsRltmList.do?pgmNo56=`
  - Direct request returned a header-only CSV; no observation rows were stored
  - `MANUAL_DOWNLOAD_REQUIRED` means the official site requires a user download; it is not a request to collect another dataset
  - After manual download, place the file under `data/raw/rainfall/osong/` for validation and normalization
- [ ] Korean official administrative boundary near 2023
  - `MANUAL_DOWNLOAD_REQUIRED`
  - SGIS boundary API requires `accessToken`; unauthenticated request returned HTTP 500
  - MOIS road-name address electronic map includes administrative boundaries but requires application, identity verification, and approval
  - `MANUAL_DOWNLOAD_REQUIRED` means the existing source is awaiting user authentication/approval, not that a new source should be added
#### DSSP API status (status tracking only; priority is defined below)

- `BLOCKED_BY_API_APPROVAL`: `DSSP-IF-00117`, `DSSP-IF-10175`, `DSSP-IF-10184`, `DSSP-IF-00247`
- Applications submitted; no raw response is stored until approval and credentials are issued
- This status summary is not an additional High Priority work item

- [ ] 행정안전부 침수흔적도 `DSSP-IF-00117` 원본 확보
  - 오송 2023 실제 Flood Extent 확보
  - 승인 후 1회 다운로드한 원본 응답을 저장하고 사건 연도·공간 범위·geometry·CRS·feature count 검증
- [ ] 기상청 AWS/ASOS 또는 지자체 관측망 강우 원본 확보
  - 오송 2023-07-15 사건 시간창과 관측소 위치를 일치시킨 실제 측정값 확보
  - `VERIFIED + OBSERVATION`으로 저장하고 NASA POWER로 대체하지 않음
- [ ] 사건 설명용 공식자료와 공간분석용 기반자료의 역할 검증
  - 공식자료: 침수흔적도, KMA AWS/ASOS, 피해·대피·긴급재난문자
  - 오픈 기반자료: OSM, WorldPop, Copernicus DEM
  - NASA POWER는 주 강우자료가 아닌 보조·비교자료로만 사용
- [ ] 오송 침수흔적도와 건물·도로·궁평2지하차도 중첩 분석
  - 침수 건물 수, 침수 도로 길이, 지하차도 포함 여부를 실제 geometry로 계산
- [ ] 공간중첩 분석에서 processed 건물 폴리곤 사용
  - processed 원본에 보존된 OSM 건물 폴리곤을 침수흔적도와 중첩 분석에 사용
- [ ] 2023 오송 공식 읍면동·세부 공간인구 확보
  - 우선순위 1: 통계청/SGIS 등 한국 공식 세부 공간인구
  - 우선순위 2: 공식 읍면동 전체 인구 + WorldPop 공간분포 보정
  - 오송읍 전체 인구와 지역별 비교값은 공식 통계만 사용
  - `event_year: 2023`과 인구자료 기준연도를 manifest에 별도 기록
- [ ] WorldPop 2023 인구를 오송 사건 격자 집계에 연결
  - 공식 세부격자 인구가 없을 때만 공식 읍면동 인구의 공간분포 보정에 사용
  - WorldPop 단독 사용은 공식 인구자료 확보가 불가능할 때의 fallback으로 제한
  - Flood Extent 내부 공간분포 추정 결과만 `DERIVED`로 표시
- [ ] 미호강 하천망과 행정경계 확보
  - 초기 공간자료: OSM 하천망, geoBoundaries ADM1/ADM2 확보 완료
  - 사건연도와 가장 가까운 한국 공식 행정경계 원본을 우선 확인
  - `event_year`와 `boundary_snapshot`을 별도 필드로 기록
  - 범람 원인과 읍·면·동별 집계에 사용

### Medium Priority

- [ ] 피해침수 `DSSP-IF-10175` 원본 확보
  - 실제 피해 기록과 침수흔적도·공간분석 결과를 대조해 검증
  - 피해 유형·발생 시각·위치·공간 객체의 원본 필드 보존
- [ ] 재해구호상황보고 `DSSP-IF-10184` 원본 확보
  - 대피 인원·이재민 등 사건 피해 해석 자료 확보
  - 보고 기준일과 집계 단위를 기록하고 공간자료와 구분해 저장
- [ ] 네 가지 API 자료의 과거 스냅샷 검증·정규화
  - API 승인 후 원본 응답, 요청 시각, 데이터 연도, 응답 스키마, SHA-256을 manifest에 기록
  - 애플리케이션 실행 중 API를 매번 호출하거나 실시간 반영하지 않음

- [ ] 오송 사건 강우·수위·DEM·인구·침수흔적도 provenance 화면 추가
- [ ] 사건별 데이터 연도와 취득일을 레이어 상세 화면에 표시
- [ ] 궁평2지하차도와 도로 통제 분석을 별도 시설 타입으로 모델링
- [ ] 전국 사건의 AOI별 원본 데이터 검색·다운로드 파이프라인 구축
- [ ] 실제 공간 분석 결과를 Baseline/What-if API에 연결
- [ ] API 키 미입력, 응답 없음, 사건 데이터 없음 상태의 테스트 추가
- [ ] Playwright E2E로 오송 기본 진입·사건 전환·API 설정 흐름 검증

### Low Priority

- [ ] 긴급재난문자 `DSSP-IF-00247` 원본 확보
  - 사건 당시 경보·대피 안내의 발송 시각과 대상 지역 확보
  - 문자 발송 이력은 Historical Replay와 타임라인 검증용 스냅샷으로만 사용

- [ ] 2022 서울·2022 포항·2024 익산·2026 안동·의성 비교 분석
- [ ] DEM 기반 흐름 방향·저지대 파생 레이어
- [ ] 매년 프로젝트 갱신 시 네 가지 API를 재신청·재다운로드하고 과거 스냅샷을 추가
- [ ] Vector Tile/PMTiles/COG 및 AOI Bounding Box 조회 최적화
- [ ] Historical Replay와 WebSocket 이벤트 재생
- [ ] PostGIS 스키마·Alembic migration 및 배치 적재
- [ ] HEC-RAS 또는 LISFLOOD-FP 결과 연동

### Future Ideas

- [ ] 궁평2지하차도 사후 설치 안전시설 What-if 시나리오 확장
  - 대상 시설: 수위센서 + 자동 진입차단시설, 차수시설
  - `BASELINE` (2023 당시 상태): 범람 → 지하차도 진입 가능
  - `INTERVENTION`: 수위센서·자동 진입차단시설 또는 차수시설을 메타데이터로 적용
  - `Scenario A`: 수위 감지 → 자동 진입차단
  - `Scenario B`: 차수시설 → 유입량 감소
  - 충북도 자료의 최저점 침수심 15cm 자동작동 기준은 공식자료로 재검증한 뒤 시나리오 파라미터로 사용
  - 이번 MVP에서는 시설 효과 계산, 차량 노출 추정, 교통량 모델링을 구현하지 않음

## Completed

### 2026-08-30

- [x] 기본 대표 사건을 `osong-2023`으로 변경하고 5개 사건 카탈로그를 유지
- [x] 사건 선택 시 사건별 Flood Extent, 타임라인, 공간 레이어, Baseline을 다시 조회
- [x] 오송 Copernicus DEM GLO-30 원본 확보
  - 타일: `N36_00_E127_00`
  - 제품 고도 자료 취득 기간: 2011-2015
  - 파일 객체 수정일: 2022-05-09
- [x] WorldPop Korea 2023 100m 인구 원본 확보
- [x] 오송 OSM 원본 확보
  - 조회 범위: `[36.58, 127.27, 36.68, 127.40]`
  - 대상: 건물, 도로, 하천, 시설, 지하차도
- [x] 오송 OSM geometry 보존 processed 데이터 생성 및 검증
  - `data/processed/osong/`에 건물 폴리곤, 도로, 하천, 시설, 터널 GeoJSON 생성
  - geometry type, validity, feature count, CRS `EPSG:4326` 검증
- [x] 오송 사건일 기준 OSM historical snapshot 확보 및 processed 데이터 생성
  - 요청 시점: `2023-07-15T23:59:59Z`
  - 건물 2,859개, 도로 6,727개, 하천 147개, 시설 386개, 터널 95개
  - 응답 DB timestamp는 별도로 기록하고 사건 스냅샷 날짜와 혼동하지 않음
- [x] 오송 행정경계 원본 및 AOI subset 확보
  - `event_year: 2023`, `boundary_snapshot.ADM1: 2023`, `boundary_snapshot.ADM2: 2020`을 분리 기록
  - 사건연도 또는 가장 가까운 연도의 경계를 우선하는 정책을 manifest에 기록
  - 원본 2종과 AOI subset 2종을 매니페스트에 기록
- [x] 오송 NASA POWER 시간별 강수 원본 및 processed CSV 확보
  - NASA POWER 원본: 2023-07-15~16, 48개 시점, `PRECTOTCORR`, `source_type: REANALYSIS`, `raw_status: VERIFIED`
  - 프로젝트용 processed CSV 변환본만 `processed_status: DERIVED`
- [x] 오송 공식 사건 보고서 원본 PDF 및 텍스트 추출본 확보
  - CODIL 보고서 93쪽, `미호강`·`궁평` 텍스트 추출 검증
- [x] 오송 MVP 핵심 교통시설 `궁평2지하차도` 시설 레이어 생성
  - 공식 검증: 시설명 `궁평2지하차도`, 노선 `지방도 508호선`, 관리기관 `충청북도도로관리사업소`
  - 2023-07-15 OSM historical snapshot의 way 2개를 `MultiLineString` 1개 피처로 결합
  - 결과: `data/processed/osong/gungpyeong2_underpass.geojson`, `EPSG:4326`, SHA-256 manifest 기록
  - 추가 교통량 모델링·차량 노출 추정은 MVP 범위에서 제외
- [x] 재난안전데이터공유플랫폼 서비스 키 입력·연결 테스트 UI 구현
- [x] 서울 2022 공식 침수흔적도 19,881개 피처의 API 연결

## Known Issues

- [ ] 오송 Flood Extent는 현재 사건 위치 기반 임시 폴리곤이며 관측 침수흔적도가 아님
- [ ] 신청한 재난안전데이터공유플랫폼 API는 승인 전이라 실제 응답을 저장하지 못함
- [ ] 공식 세부 공간인구는 아직 확보 전이며, 공식 읍면동 인구는 확보됨. WorldPop은 fallback 공간분포 자료로만 사용
- [ ] DEM은 확보했으나 고도·흐름 파생 분석에 연결하지 않음
- [ ] 앱은 현재 지도 성능을 위해 OSM 건물 중심점을 사용하며, 공간중첩 분석은 processed 폴리곤으로 분리해야 함
- [ ] OSM API 레이어는 중심점 변환을 사용하지만 processed 원본에는 건물 폴리곤이 보존됨
- [ ] OSM 2026-08-30 스냅샷은 현재 참고용이며 2023 오송 시뮬레이션에 사용하지 않음
- [ ] 기존 애플리케이션의 공간 레이어 연결은 이번 데이터 확보 작업에서 수정하지 않아 2023 historical OSM snapshot과 아직 연결되지 않음
- [ ] NASA POWER 강수는 재분석 자료이며 실제 관측소 강우량을 대체하지 않음
- [ ] 기상청 AWS/ASOS 실제 측정 강우 원본은 아직 확보 전임
- [ ] 오송 timeline은 2023-07-15 형식의 데모값이며 실제 관측 시계열이 아님
- [ ] geoBoundaries ADM2는 `boundary_snapshot: 2020`이며 `event_year: 2023`과 별도임; 2023년에 더 가까운 한국 공식 ADM2 원본을 추가 확인해야 함
- [ ] 오송 AOI OSM 행정경계 쿼리는 서버 timeout으로 확보하지 못해 geoBoundaries로 대체함
- [ ] 전국 침수흔적도는 후보 데이터셋만 확인했으며 오송 record 다운로드는 미완료

## Future Ideas

- [ ] LLM Translation Reviewer
- [ ] 개인별 학습 추천
- [ ] DB 기반 Lesson/Draft 관리
- [ ] 관리자 권한 인증
