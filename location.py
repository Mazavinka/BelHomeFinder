from logger import logger
import json
from shapely.geometry import shape, Point
from shapely.geometry.base import BaseGeometry
import osmium
from math import radians, sin, cos, sqrt, asin
from typing import Dict, Set

OSM_FILE = "./geo/belarus-251117.osm.pbf"

CITY_OBJECTS = {
    "subway":  {"key": "railway", "value": "subway_entrance"},
    "pharmacy": {"key": "amenity", "value": "pharmacy"},
    "kindergarten": {"key": "amenity", "value": "kindergarten"},
    "school": {"key": "amenity", "value": "school"},
    "bank": {"key": "amenity", "value": "bank"},
    "supermarket": {"key": "shop", "value": "supermarket"},
    "convenience": {"key": "shop", "value": "convenience"},
    "mall": {"key": "shop", "value": "mall"},
}

POI_DATA = {k: [] for k in CITY_OBJECTS.keys()}


class POIHandler(osmium.SimpleHandler):
    def node(self, n):
        if not n.tags:
            return

        for key, rule in CITY_OBJECTS.items():
            if n.tags.get(rule["key"]) == rule["value"]:
                POI_DATA[key].append({
                    "name": n.tags.get("name:ru") or n.tags.get("name") or "",
                    "lat": n.location.lat,
                    "lon": n.location.lon
                })

    def way(self, w):
        for key, rule in CITY_OBJECTS.items():
            if w.tags.get(rule["key"]) == rule["value"]:
                if w.nodes:
                    lat = sum(n.lat for n in w.nodes) / len(w.nodes)
                    lon = sum(n.lon for n in w.nodes) / len(w.nodes)

                    POI_DATA[key].append({
                        "name": w.tags.get("name:ru") or w.tags.get("name") or "",
                        "lat": lat,
                        "lon": lon
                    })



handler = POIHandler()
handler.apply_file(OSM_FILE, locations=True)

for k, v in POI_DATA.items():
    print(f"  {k}:{len(v)} шт.")


def distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2

    return 2 * R * asin(sqrt(a))


def find_nearby(lat: float, lon: float, radius: int = 500) -> Dict[str, Set[str]]:
    result = {k: set() for k in CITY_OBJECTS.keys()}
    for key, poi_list in POI_DATA.items():
        for poi in poi_list:
            if distance(lat, lon, poi["lat"], poi["lon"]) <= radius:
                result[key].add(poi["name"])
    return result


def load_district_geojson(city: str) -> list[tuple[str | None, BaseGeometry]]:
    path = f"./geo/{city}.geojson"
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    districts = []

    for feature in data['features']:
        props = feature['properties']

        name = props.get("name:ru")

        polygon = shape(feature['geometry'])
        districts.append((name, polygon))

    return districts


def get_unique_nearby_objects(nearby_objects: list, limit: int) -> list:
    if not nearby_objects or limit is None or limit < 1:
        return []
    return [obj for obj in set(nearby_objects) if obj != ''][:limit]


def get_district_by_point(lat: float, lon: float, districts: list[tuple[str | None, BaseGeometry]]):
    if lat != 0.0 and lon != 0.0:
        point = Point(lon, lat)

        for name, polygon in districts:
            if polygon.contains(point):
                return name

    return None


if __name__ == "__main__":
    nearby = find_nearby(53.917755, 27.594841, 500)
    print(nearby["subway"])

