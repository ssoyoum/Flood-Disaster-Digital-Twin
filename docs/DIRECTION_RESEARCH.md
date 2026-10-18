# 방향 조사 — 지하차도 다음, 어디까지 넓힐 수 있나

조사일 2026-10-16. 세 갈래로 조사했다.

1. 하천 영향형 지하차도가 몇 곳인지 데이터로 확인
2. 논문 조사
3. 원래 기획안 범위(사건 재구성·반사실, 다사례)로 넓혔을 때 같은 틀이 통하는지

확정된 전제는 [direction-underpass-control-twin] 결정(2026-10-16)을 따른다. 관제 화면과 통제 판단 보드를 하나로 묶고, 고객은 B2G 실증 → B2B 확장으로 잡고, 소프트웨어만 한다.

---

## 1. 결론

| 질문 | 답 |
| --- | --- |
| 지하차도만으로 충분한가 | **아니다.** 하천 수위가 선행 지표가 되는 지하차도는 근거를 갖고 목표로 삼을 수 있는 수가 **약 10~25곳**(관측소 5~12곳 묶음)이다. 77~82%는 내수형이거나 판단할 수 없다. |
| 어디로 넓히나 | **강물이 위험을 만드는 시설**로 넓힌다: 하천 영향형 지하차도, **하천변 출입구**(산책로·둔치주차장·하상도로), **저지대 마을 대피 단위** |
| 무엇을 빼나 | 반지하·지하철 출입구·도심 지하주차장 같은 내수형. 기후에너지환경부 도시침수예보(2026-06~, 서울 6개 구, 우리 도림천 사례 지역 포함)가 이미 맡고 있다. |
| 논문이 지지하는 것 | 백테스트로 경보 기준을 고르는 방식, 수치는 계산기가 내고 LLM은 설명만 하는 구조, 사건 재구성·반사실 분석 |
| 논문 때문에 고칠 것 | "디지털 트윈" 용어. 양방향 제어가 없으면 엄밀히는 디지털 섀도다. "남은 분"은 예측이 아니라 기준선(현재 추세 연장)이라고 써야 한다. 사후확신 편향에도 대비해야 한다. |
| 비어 있는 곳 (주장할 수 있는 지점) | 하천 수위로 시설 통제를 정하는 규칙의 정량 연구, 시설 단위 통제 기준의 다년 백테스트, 미래 자료를 막은 "개입 시점" 반사실 도구 |

**범위 문장(제안)**

> 하천 수위·댐 방류를 선행 지표로, **하천과 맞닿은 시설**(지하차도·하천변 출입구·저지대 마을)의 통제·대피 시점을 판단하고 그 기준을 과거 사건으로 검증하는 소프트웨어

---

## 2. 하천 영향형 지하차도는 몇 곳인가

방법: `facility_gauge_links.csv`, 홍수통제소 1시간 수위 2019~2026, 품질 마스크를 썼다. 같은 하천 여부는 OSM 하천 이름으로 판정했다. 고도 힌트는 관측소 영점표고+계획홍수위와 SRTM 지면고의 차이다(궁평2 기준 +2.0 m). 스크립트와 결과 CSV는 [research/underpass_river_influence/](research/underpass_river_influence/)에 있다.

| 항목 | 시설 | 고유 관측소 |
| --- | ---: | ---: |
| 5 km 안 수위 관측소 있음 | 229 | 107 |
| 그중 홍수예보 지점(시계열 있음) | 93 | 37 |
| 93곳 중 주의보 / 경보 / 계획홍수위 초과 사상 1건 이상 | 87 / 39 / 7 | 27 / 13 / 3 |
| **A등급**: 경보 초과 연도 1개 이상 + 같은 하천 1.5 km 안 + 고도 힌트 −3 m 이상 | **9** | 5 |
| **B등급**: 주의보 이상 + 같은 하천 1.5 km 안 + 고도 힌트 −3 m 이상 | **25** | 12 |
| 계획홍수위 표고가 지면보다 10 m 넘게 낮음(범람이 직접 닿기 어려움) | 84 | — |

- 후보는 **대전 갑천·유등천·대전천 권역**에 몰려 있다: 도마·오량·갑천·만년·문예·현암·대전역·진터·둔산 등. 그 밖에 고양 원당, 양산 양주, 서울 개봉·가락이 있다.
- **두 번째 검증 사건 후보**
  1. 대전 **만년지하차도 2020-07-30**: YTN 08:53 보도가 "만년 지하차도 등 통제", 원촌교 경보 초과를 전했다. 같은 하천(갑천) 만년교 관측소가 0.22 km 거리이고, 수위는 05시 3.35 → 08시 4.37 → 09시 4.45 m였다.
  2. 고양 2025-08-13: 원당교 12:30 홍수경보, 관내 지하차도 7곳 통제. 시설 이름은 확인하지 못했다.
  - 두 사건 모두 침수 원인이 하천인지 내수인지는 아직 확인하지 않았다.
- 한계
  - OSM 좌표는 지하차도 최저점이 아니다. SRTM 오차는 수 m다.
  - 과거 사건에 현재 임계값을 적용했다(2020년 원촌교 경보는 보도상 4.5 m, 현재 값은 4.8 m).
  - 1시간 자료라 순간 정점을 놓칠 수 있다.
  - 임계값이 있는 관측소 121곳은 시계열이 없다. 이번에 홍수통제소 키를 읽지 못해 새로 받지 않았다.

→ **지하차도 하나만으로는 시장이 좁다.** 다만 대전 권역에 묶음이 있어 첫 B2G 실증 지역 후보로는 좋다.

---

## 3. 원래 기획안 범위로 넓히면

점수는 1~5점이다(데이터 / 코드 재사용 / 시장·고객 / 물산업 연계 / 차별성). 근거는 조사 시점의 공개 자료와 보도다.

| 유형 | 데이터 | 코드 | 시장 | 물산업 | 차별성 | 합 | 근거 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| (기준) 하천 영향형 지하차도 | 4 | 5 | 4 | 4 | 3 | 20 | 구현됨. 내비게이션 홍수 알림(2024~)과 일부 겹침 |
| **A. 하천변 출입구** (산책로·둔치주차장·하상도로) | 4 | 5 | 4 | 5 | 4 | **22** | 같은 수위 규칙에 댐 방류 규칙만 추가하면 된다. 차단기는 깔렸는데 "언제 닫을지" 기준이 없다 |
| **B. 저지대 마을 대피 단위** | 3 | 4 | 4 | 4 | 3 | **18** | 안동·가평 수위가 있고 대피 반사실 코드도 있다. 특보와 차별화가 필요하다 |
| C. 지하주차장 | 2 | 3 | 2 | 2 | 3 | 12 | 목록이 없고 고객이 민간이다. 포항 냉천 수위는 2023-04부터라 2022 사건을 백테스트할 수 없다 |
| D. 반지하 | 3 | 3 | 3 | 2 | 1 | 12 | 도시침수예보가 같은 지역을 직접 다룬다 |
| E. 지하철·지하상가 | 2 | 2 | 2 | 1 | 1 | 8 | 운영기관이 자체 대응하고 도시침수예보에도 포함된다 |
| F. 계곡 캠핑장 | 3 | 2 | 2 | 3 | 3 | 13 | 관측소가 없고 사고 원인이 산사태와 섞인다 |
| G. 해안 저지대 | 3 | 2 | 2 | 1 | 2 | 10 | 관측 체계가 다르고 해수부 영역이다 |

### A. 하천변 출입구 — 지하차도 다음 1순위

- **설치는 됐는데 판단 기준이 없다**
  - 행안부는 하상도로 270곳 자동차단에 국비 약 202억 원을 지원했다(2023~24). 경기도는 하천 출입구 1,174곳에 127억 원을 들인다.
  - 2026-07-08 대전 유등천 하상도로에서 차단기가 열린 채 차량이 진입했다. 보도는 "강우량이나 하천 수위 등 구체적인 차단 기준은 마련돼 있지 않았다"고 썼다.
- **현장 기준이 제각각이다**: 부산은 호우 예비특보 때 일괄 차단하고, 춘천은 의암댐 방류가 초당 2,000톤을 넘으면 차단한다.
- **목록**: 행안부 둔치주차장 API가 있다(data.go.kr 15153330, 15153334). 전국 개수와 좌표 필드는 아직 확인하지 않았다.
- **검증 사건**: 가평 대보교 2025-07-20(홍수경보 02:40, 수위 02시 4.30 → 04시 9.03 m, 심각 수위 6.4 m)과 대전 유등천 2026-07-08.
- **B2B와 맞는다**: 차단기 업체(용인·김포·수원·포항 등 운영, AI 수위센서 업체 다수)에 "언제 닫을지" 판단 엔진을 공급한다.

### B. 저지대 마을 대피 단위 — 2순위

- 인명피해우려지역은 2026년 **9,412곳**이다. 범정부 대책은 통제·대피 기준을 "강수량을 반영한 정량 기준"으로 바꾼다고 했다.
- 차별점은 마을마다 대피 소요시간 대비 남은 분을 계산하고, 그 마을의 과거 사건으로 백테스트하는 것이다.
- 안동 2026-07-19: 미천 운산리 최고 3.92 m로 관심 수위(3.8)는 넘었지만 주의보(4.3)에는 못 미쳤는데 대피했다. 기준 검토 탭의 "일찍 알림 ↔ 불필요 권고" 맞바꿈을 설명하기 좋은 사례다(10분 자료로 재확인 필요).

### 원래 사례들의 자리

| 사례 | 새 범위에서의 역할 |
| --- | --- |
| 오송 2023 | 하천 영향형 지하차도의 기준 사례(운영 등록) |
| 안동·의성 2026 | 저지대 마을 대피 단위의 첫 사례 |
| 서울 2022 | 내수형의 경계를 보여주는 검증 사례. 신대방1교 수위는 2023-04부터라 수위 백테스트가 불가능하다 |
| 포항 2022 | 하천 영향형 지하주차장 사례 카드. 수위 백테스트는 불가능하다 |
| (신규) 가평 2025 | 하천변·마을 대피 검증 사건 후보 |
| (신규) 대전 만년 2020 | 두 번째 지하차도 검증 사건 후보 |

---

## 4. 논문이 말하는 것

조사 범위는 Crossref·KoreaScience·J-STAGE·출판사 페이지에서 서지를 직접 확인한 41편이다. DBpia·RISS 본문은 끝까지 확인하지 못했으므로, 아래에서 "없음"은 "찾지 못함"이라는 뜻이다.

### 근거가 있는 주장

- 지하공간 침수는 수 분 안에 생명을 위협한다. 계단 탈출 한계 수심은 0.3~0.4 m이고, 시설 안 수심 기준만으로는 판단 시간이 부족하다 [5][6][8][9].
- 홍수 사망 중 차량 관련 비중이 크다(텍사스 58%). 진입 통제가 핵심 개입이다 [12].
- 경보 임계값은 선행 시간과 오경보의 맞바꿈이고, 과거 자료로 검증해 고른다 [17][18][19].
- 사건 재구성·반사실 분석은 훈련·사후 검토 방법으로 확립돼 있다 [28][30][32].
- 수치는 결정론적 계산에 맡기고 LLM은 문제 분해·설명만 하는 설계가 타당하다 [39][41].

### 고칠 것 (심사·발표에서 공격받을 지점)

| 지적 | 대응 |
| --- | --- |
| 양방향 제어가 없으면 디지털 트윈이 아니라 디지털 섀도다 [21][22][23] | "의사결정 지원 트윈"으로 쓰고 정의를 먼저 밝힌다. 국가 물관리 디지털트윈 플랫폼[27]과 경쟁하지 않는 "시설 단위 판단 계층"으로 둔다 |
| "남은 분"은 선형 외삽, 즉 기준선이다 [13]. 제방 붕괴 같은 불연속은 못 잡는다 | "현재 속도 기준 기준선"으로 표기한다. 예측 모델은 연구 카드로만 둔다(현행 유지) |
| "06:40에 통제했다면"은 사후확신 편향이다 [33] | 각 시각에 그 시각까지의 자료만 쓰는 설계(`_review_flags`)를 앞에 내세운다 |
| 오송은 정보 부족이 아니라 조직 실패였다 [4]. 경보를 받아도 위험을 과소평가한다 [20] | 화면만 주지 말고 기존 차단기·상황실 업무 흐름에 붙는다(B2B). 판단 기록을 남겨 사후 감사에 쓰게 한다 |
| 시설 단위 사건 수가 적어 오경보율 추정이 불안정하다 | 시설 하나가 아니라 같은 관측소 묶음과 다년 자료로 센다. 두 번째 검증 사건을 확보한다 |

### 연구 공백 = 우리가 주장할 수 있는 지점

1. 하천 수위로 시설(지하차도·하천변) 통제를 정하는 규칙의 정량 연구가 없다. 국내 문헌은 위험도 분류 [1], 내수 재현 [2][3], 거버넌스 [4]에 머문다.
2. 시설 통제 권고 임계값을 다년 자료로 백테스트한 연구가 없다. 돌발홍수 예보 쪽에만 있다 [17][18][19].
3. 오송의 시각별 재구성과 개입 시점 반사실 연구가 없다.
4. 미래 자료를 막은 "개입 시점" 반사실 훈련 도구가 없다. 하방 반사실 연구는 위험 자체를 바꾼다 [28][29].
5. 실시간 관측과 대피 시점을 연결한 연구가 없다 [34][35][36][37].
6. 결정론적 계산기를 쓰는 감사 가능한 LLM 에이전트의 국내 재난 적용 사례가 드물다.

### 참고문헌

| 번호 | 저자 | 연도 | 제목 | 게재처 | DOI/URL |
|---|---|---|---|---|---|
| 1 | 김길호·곽재원·박문형 | 2024 | 전국 지하차도 침수위험 분류 연구 | 기후연구 19(4) | 10.14383/cri.2024.19.4.199 |
| 2 | Eum, Song, Jung | 2026 | CCTV-based Quantitative Validation of a Coupled 1D–2D Model for the 2020 Choryang No.1 Underpass Flooding Event | 한국안전학회지 41(1) | 10.14346/JKOSOS.2026.41.1.97 |
| 3 | 유동현·송창근 | 2020 | 동수역학 모형을 이용한 침수사고 분석 및 특성요인도를 활용한 재해 원인 고찰 | 융합정보논문지 10(10) | 10.22156/CS4SMB.2020.10.10.128 |
| 4 | Choi N.-h. | 2025 | Analysis of the Circular Causal Structures of the Gungpyeong 2 Underpass Flood Disaster | 한국시스템다이내믹스연구 26(4) | 10.32588/ksds.26.4.5 |
| 5 | Baba et al. | 2011 | Experimental studies on difficulty of evacuation from underground spaces under inundated situations using real scale models | JSCE Ser. F2 67 | 10.2208/jscejusr.67.12 |
| 6 | Ishigaki et al. | 2016 | Vulnerability to Underground Inundation and Evacuation in Densely Urbanized Area | J. Disaster Research 11(2) | 10.20965/jdr.2016.p0298 |
| 7 | 김예림 외 | 2021 | 실증실험기반 지하공간 침수 대피 한계수심 변화에 관한 연구 | 한국수자원학회 학술발표회 | koreascience.kr/article/CFKO202133451036811.page |
| 8 | 국토교통부 | 2024–2025 | 도로터널 방재·환기시설 설치 및 관리지침 일부개정 | 국토부 예규 | molit.go.kr/USR/I0204/m_45/dtl.jsp?idx=18479 |
| 9 | 서울신문 | 2024 | 지하차도 물 15㎝ 차면 통제 (보도) | 서울신문 2024-03-18 | m.go.seoul.co.kr/news/2024/03/18/20240318009005 |
| 10 | Pregnolato et al. | 2017 | The impact of flooding on road transport: A depth-disruption function | Transp. Res. D 55 | 10.1016/j.trd.2017.06.020 |
| 11 | Martínez-Gomariz et al. | 2018 | Stability criteria for flooded vehicles: a state-of-the-art review | J. Flood Risk Manag. 11 | 10.1111/jfr3.12262 |
| 12 | Han, Sharif | 2020 | Vehicle-Related Flood Fatalities in Texas, 1959–2019 | Water 12 | 10.3390/w12102884 |
| 13 | Pappenberger et al. | 2015 | How do I know if my forecasts are better? Using benchmarks in hydrological ensemble prediction | J. Hydrology 522 | 10.1016/j.jhydrol.2015.01.024 |
| 14 | WMO | 2011 | Manual on Flood Forecasting and Warning (WMO-No.1072) | WMO | community.wmo.int/en/bookstore/manual-flood-forecasting-and-warning |
| 15 | Barnes et al. | 2007 | False Alarms and Close Calls: A Conceptual Model of Warning Accuracy | Weather & Forecasting 22 | 10.1175/waf1031.1 |
| 16 | LeClerc, Joslyn | 2015 | The Cry Wolf Effect and Weather-Related Decision Making | Risk Analysis 35(3) | 10.1111/risa.12336 |
| 17 | Sawada et al. | 2022 | Impact of cry wolf effects on social preparedness and the efficiency of flood early warning systems | HESS 26 | 10.5194/hess-26-4265-2022 |
| 18 | Zhang et al. | 2024 | Determining the threshold of issuing flash flood warnings based on people's response process simulation | HESS 28 | 10.5194/hess-28-5229-2024 |
| 19 | Verkade, Werner | 2011 | Estimating the benefits of single value and probability forecasting for flood warning | HESS 15 | 10.5194/hess-15-3751-2011 |
| 20 | Thieken et al. | 2023 | Performance of the flood warning system in Germany in July 2021 | NHESS 23 | 10.5194/nhess-23-973-2023 |
| 21 | National Academies | 2024 | Foundational Research Gaps and Future Directions for Digital Twins | National Academies Press | 10.17226/26894 |
| 22 | Kritzinger et al. | 2018 | Digital Twin in manufacturing: A categorical literature review and classification | IFAC-PapersOnLine 51(11) | 10.1016/j.ifacol.2018.08.474 |
| 23 | Wright, Davidson | 2020 | How to tell the difference between a model and a digital twin | Adv. Model. Simul. Eng. Sci. 7 | 10.1186/s40323-020-00147-4 |
| 24 | Malleson et al. | 2024 | Digital twins on trial | Environ. Plan. B | 10.1177/23998083241262893 |
| 25 | Hlal et al. | 2025 | Digital Twin Technology for Urban Flood Risk Management: A Systematic Review | Remote Sensing 17 | 10.3390/rs17173104 |
| 26 | Macatulad, Biljecki | 2024 | Continuing from the Sendai Framework midterm: Opportunities for urban digital twins in disaster risk management | IJDRR | 10.1016/j.ijdrr.2024.104310 |
| 27 | 원유승 외 | 2022 | 디지털트윈 기반으로의 물관리 전환 | 물과 미래 55(11) | koreascience.kr/article/JAKO202206881890298.page |
| 28 | Woo | 2019 | Downward Counterfactual Search for Extreme Events | Front. Earth Sci. 7 | 10.3389/feart.2019.00340 |
| 29 | Lin et al. | 2020 | Modeling Downward Counterfactual Events | Front. Earth Sci. 8 | 10.3389/feart.2020.575048 |
| 30 | Shepherd et al. | 2018 | Storylines: an alternative approach to representing uncertainty in physical aspects of climate change | Climatic Change 151 | 10.1007/s10584-018-2317-9 |
| 31 | Merz et al. | 2024 | Spatial counterfactuals to explore disastrous flooding | Environ. Res. Lett. 19 | 10.1088/1748-9326/ad22b9 |
| 32 | Keating et al. | 2016 | From event analysis to global lessons: disaster forensics for building resilience | NHESS 16 | 10.5194/nhess-16-1603-2016 |
| 33 | Fischhoff | 1975 | Hindsight ≠ foresight | J. Exp. Psychol.: HPP 1(3) | 10.1037/0096-1523.1.3.288 |
| 34 | 음정인·김형규 | 2024 | 서울특별시 반지하 가구를 고려한 홍수 취약성 평가 | 한국기후변화학회지 15(1) | 10.15531/ksccr.2024.15.1.035 |
| 35 | 최유라 | 2025 | 반지하 주택 침수 영향요인의 공간적 분포 특성 분석 | 토지주택연구 16(4) | 10.5804/LHR.2025.16.4.1 |
| 36 | 박상식·지용근 | 2026 | 재난 사각지대의 반지하주택 침수대응 재난관리 정책 개선 방안 연구 | 한국안전학회지 41(1) | 10.14346/JKOSOS.2026.41.1.59 |
| 37 | 장혜리 외 | 2025 | HEC-RAS 2D를 이용한 냉천 유역 해안도시 복합 침수 모델링 | 한국수자원학회논문집 58(S4) | 10.3741/JKWRA.2025.58.S-4.1617 |
| 38 | Lei et al. | 2025 | Harnessing Large Language Models for Disaster Management: A Survey | Findings of ACL 2025 | arxiv.org/abs/2501.06932 |
| 39 | Karimanzira et al. | 2025 | Improved Flood Management and Risk Communication Through Large Language Models | Algorithms 18(11) | 10.3390/a18110713 |
| 40 | Ji et al. | 2023 | Survey of Hallucination in Natural Language Generation | ACM Computing Surveys 55(12) | 10.1145/3571730 |
| 41 | Gao et al. | 2023 | PAL: Program-aided Language Models | ICML 2023 | proceedings.mlr.press/v202/gao23f.html |

검증 메모

- 5 cm 기준, 오송 2~3분 침수, 경보 약 4시간 전 발령은 보도로만 확인했다.
- Ariyachandra & Wedawatta(2023)는 철회 논문이라 제외했다.
- 서울연구원 「서울시 지하차도의 침수 위험도 평가」(2024)는 PDF가 암호화돼 있어 제외했다.

---

## 5. 정할 것과 다음 단계

**정할 것**

1. 범위 문장을 "하천 접점 시설(지하차도·하천변 출입구·저지대 마을)"로 넓힐지
2. 지하차도 다음 첫 시설 유형: 하천변 출입구(1순위 권고)와 마을 대피 중 어느 것인지
3. STARTUP WATER(10/19 마감) 제안서를 넓힌 범위로 고쳐 낼지, 지하차도 범위 그대로 낼지

**다음 단계 (결정 후)**

- 대전 만년 2020-07-30을 두 번째 검증 사건으로 확인한다: 10분 수위 재수집, 통제 시각 원문, 침수 원인이 하천인지 내수인지.
- 가평 대보교 2025-07-20을 10분 자료로 재확인한다. 하천변·마을 대피 첫 사례가 된다.
- 둔치주차장 API의 필드와 개수를 확인한다. 인명피해우려지역 목록이 공개되는지도 확인한다.
- 시설 레지스트리에 시설 유형(`kind`)과 구동 유형(`driver: dam_release`)을 추가하도록 설계한다. 오송 임계값을 복사하지 않는 원칙은 유지한다.
