from logger import logger
import json
from shapely.geometry import shape, Point


def load_district_geojson(city):
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


def get_district_by_point(lat, lon, districts):
    if lat != 0.0 and lon != 0.0:
        point = Point(lon, lat)

        for name, polygon in districts:
            if polygon.contains(point):
                return name

    return None


if __name__ == "__main__":
    pass
