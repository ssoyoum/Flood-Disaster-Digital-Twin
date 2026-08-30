from functools import lru_cache

from shapely.geometry import Point, shape
from shapely.ops import unary_union

from .data import EVENT_ID, get_event, get_layers
from .schemas import ExposureMetrics, Intervention


@lru_cache(maxsize=1)
def _flood_shape():
    geometries = []
    for feature in get_event()["flood_extent"]["features"]:
        geometry = shape(feature["geometry"])
        if geometry.geom_type == "GeometryCollection":
            polygon_parts = [part for part in geometry.geoms if part.geom_type in {"Polygon", "MultiPolygon"}]
            if not polygon_parts:
                continue
            geometry = unary_union(polygon_parts)
        geometries.append(geometry)
    return unary_union(geometries)


def calculate_baseline(event_id: str = EVENT_ID) -> ExposureMetrics:
    flood = _flood_shape() if event_id == EVENT_ID else shape(get_event(event_id)["flood_extent"]["features"][0]["geometry"])
    layers = get_layers(event_id)
    exposed_buildings = [feature for feature in layers["buildings"]["features"] if flood.contains(Point(feature["geometry"]["coordinates"]))]
    exposed_infrastructure = [feature for feature in layers["infrastructure"]["features"] if flood.contains(Point(feature["geometry"]["coordinates"]))]
    exposed_shelters = [feature for feature in layers["shelters"]["features"] if flood.contains(Point(feature["geometry"]["coordinates"]))]
    return ExposureMetrics(
        flooded_area_km2=round(flood.area * 111 * 111, 2),
        exposed_population=sum(feature["properties"]["population"] for feature in exposed_buildings),
        exposed_buildings=len(exposed_buildings),
        affected_road_length_km=round(len([road for road in layers["roads"]["features"] if shape(road["geometry"]).intersects(flood)]) * 3.4, 1),
        critical_infrastructure=len(exposed_infrastructure),
        affected_shelters=len(exposed_shelters),
    )


def apply_intervention(intervention: Intervention, event_id: str = EVENT_ID) -> tuple[ExposureMetrics, list[str]]:
    baseline = calculate_baseline(event_id)
    reductions = {
        "EVACUATION": (0.22, 0.0, "대피 대상 인구를 우선 대피시키는 단순화된 추정"),
        "ROAD_CLOSURE": (0.08, 0.27, "침수 예상 도로를 통제해 2차 노출을 줄이는 단순화된 추정"),
        "SHELTER_OPEN": (0.18, 0.0, "추가 대피소 개방으로 대피 가능 인구를 늘리는 단순화된 추정"),
        "TEMPORARY_BARRIER": (0.3, 0.0, "임시 방어시설이 침수 범위를 일부 줄인다는 단순화된 추정"),
        "LEVEE_IMPROVEMENT": (0.35, 0.0, "제방 개선 효과를 사전 정의된 비율로 반영한 추정"),
        "INFRASTRUCTURE_PROTECTION": (0.0, 0.0, "핵심 시설 보호 조치의 시설 위험 감소만 반영한 추정"),
    }
    population_reduction, road_reduction, assumption = reductions[intervention.type]
    result = baseline.model_copy(
        update={
            "exposed_population": round(baseline.exposed_population * (1 - population_reduction)),
            "affected_road_length_km": round(baseline.affected_road_length_km * (1 - road_reduction), 1),
            "critical_infrastructure": 0 if intervention.type == "INFRASTRUCTURE_PROTECTION" else baseline.critical_infrastructure,
            "affected_shelters": 0 if intervention.type == "SHELTER_OPEN" else baseline.affected_shelters,
        }
    )
    return result, [assumption, "실제 수리모형 결과가 아닌 시나리오 추정값", "입력 데이터와 모델 버전은 데모 고정값"]
