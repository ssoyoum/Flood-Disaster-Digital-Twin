import json
import osm2geojson

input_file = r"data\raw\여기에_OSM_JSON_경로\osong_osm.json"
output_file = r"data\processed\osong\osong_osm.geojson"

with open(input_file, "r", encoding="utf-8") as f:
    osm_data = json.load(f)

geojson_data = osm2geojson.json2geojson(osm_data)

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(geojson_data, f, ensure_ascii=False, indent=2)

print("완료:", output_file)
