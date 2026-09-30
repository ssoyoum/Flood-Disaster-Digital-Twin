# Osong processed data: sources and terms

| File | Source | Terms |
| --- | --- | --- |
| `osong_official_buildings_2023.geojson` | 국토교통부 GIS건물통합정보 (VWorld, 충청북도 2023-07-12) | CC BY — 출처: 국토교통부 GIS건물통합정보 |
| `osong_osm_roads_2023.geojson`, `osong_osm_roads_2026.geojson` | OpenStreetMap via Overpass API | ODbL 1.0 — © OpenStreetMap contributors. Derived databases must stay under ODbL. |
| `osong_wamis_rivers.geojson` | WAMIS 국가수자원관리종합정보시스템 하천망 | 공공누리 유형 표시 없음 (미확인) |
| `osong_hand_*` | Derived from Copernicus DEM, WAMIS rivers, HRFCO water level, KMA AWS rainfall | DERIVED_APPROXIMATION — not an official flood extent |

The Safemap flood-marks WMS image (`data/raw/.../safemap_if_0092_wms`) is 공공누리 제4유형
(출처표시·상업적 이용 금지·변경 금지). It stays out of the repository and the deploy image.

Full provenance, checksums, and acquisition dates are in `data/manifests/source-availability.yml`.
