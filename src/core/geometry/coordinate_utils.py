import math
import json
import logging
from pathlib import Path
import pyproj
import ezdxf
from shapely.geometry import Point, LineString

logger = logging.getLogger(__name__)

def remove_z_from_coords(coords):
    try:
        # coord is list/tuple of numbers
        if isinstance(coords, (list, tuple)) and len(coords) > 0 and isinstance(coords[0], (int, float)):
            return [coords[0], coords[1]]
        # nested
        return [remove_z_from_coords(c) for c in coords]
    except Exception:
        return coords

def strip_z_from_geojson(geojson_obj: dict) -> dict:
    try:
        if geojson_obj.get("type") == "FeatureCollection":
            for f in geojson_obj.get("features", []):
                g = f.get("geometry")
                if g and isinstance(g, dict) and "coordinates" in g:
                    g["coordinates"] = remove_z_from_coords(g["coordinates"])
        elif geojson_obj.get("type") in ("Feature",):
            g = geojson_obj.get("geometry")
            if g and isinstance(g, dict) and "coordinates" in g:
                g["coordinates"] = remove_z_from_coords(g["coordinates"])
        elif geojson_obj.get("type") in ("Point","LineString","Polygon","MultiPoint","MultiLineString","MultiPolygon","GeometryCollection"):
            if "coordinates" in geojson_obj:
                geojson_obj["coordinates"] = remove_z_from_coords(geojson_obj["coordinates"])
        return geojson_obj
    except Exception:
        return geojson_obj

def _collect_lonlat(coords, acc):
    if coords is None:
        return
    if isinstance(coords, (list, tuple)):
        if len(coords) >= 2 and isinstance(coords[0], (int, float)) and isinstance(coords[1], (int, float)):
            # lon, lat
            acc.append((coords[0], coords[1]))
        else:
            for c in coords:
                _collect_lonlat(c, acc)

def compute_bounds_from_geojson(geojson_obj: dict):
    try:
        points = []
        if geojson_obj.get("type") == "FeatureCollection":
            for f in geojson_obj.get("features", []):
                g = f.get("geometry")
                if g and isinstance(g, dict):
                    _collect_lonlat(g.get("coordinates"), points)
        else:
            g = geojson_obj.get("geometry") if geojson_obj.get("type") == "Feature" else geojson_obj
            if g and isinstance(g, dict):
                _collect_lonlat(g.get("coordinates"), points)
        if not points:
            return None
        lons = [p[0] for p in points]
        lats = [p[1] for p in points]
        min_lon, max_lon = min(lons), max(lons)
        min_lat, max_lat = min(lats), max(lats)
        return [[min_lat, min_lon], [max_lat, max_lon]]
    except Exception:
        return None

def is_valid_lonlat(lon, lat) -> bool:
    try:
        return isinstance(lon, (int, float)) and isinstance(lat, (int, float)) and -180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0
    except Exception:
        return False

def filter_geojson_valid(geojson_obj: dict) -> dict:
    try:
        feats = geojson_obj.get("features", []) if geojson_obj.get("type") == "FeatureCollection" else []
        filtered = []
        for f in feats:
            g = f.get("geometry", {})
            t = g.get("type")
            coords = g.get("coordinates")
            acc = []
            _collect_lonlat(coords, acc)
            # Aceptar si hay al menos una coord dentro de rango
            if any(is_valid_lonlat(lon, lat) for lon, lat in acc):
                filtered.append(f)
        logger.info(f"Filtrado: {len(filtered)}/{len(feats)} features válidas por rango")
        return {"type": "FeatureCollection", "features": filtered}
    except Exception:
        return geojson_obj

def build_transformer(input_epsg: int, output_epsg: int) -> pyproj.Transformer:
    return pyproj.Transformer.from_crs(f"EPSG:{input_epsg}", f"EPSG:{output_epsg}", always_xy=True)

def utm_to_latlon_coords(transformer: pyproj.Transformer, x: float, y: float):
    lon, lat = transformer.transform(x, y)
    return lon, lat

def calculate_text_angle(text_point, polyline_vertices):
    point_shapely = Point(text_point)
    polyline_shapely = LineString(polyline_vertices)
    min_dist = float('inf')
    angle = 0.0
    for i in range(len(polyline_vertices) - 1):
        segment = LineString([polyline_vertices[i], polyline_vertices[i + 1]])
        dist = point_shapely.distance(segment)
        if dist < min_dist:
            min_dist = dist
            dx = polyline_vertices[i + 1][0] - polyline_vertices[i][0]
            dy = polyline_vertices[i + 1][1] - polyline_vertices[i][1]
            angle = math.degrees(math.atan2(dy, dx)) % 360
    return angle, min_dist

def transform_coords(coords, transformer):
    if isinstance(coords, (list, tuple)):
        if len(coords) >= 2 and isinstance(coords[0], (int, float)) and isinstance(coords[1], (int, float)):
            x, y = transformer.transform(coords[0], coords[1])
            return [x, y]
        return [transform_coords(c, transformer) for c in coords]
    return coords

def transform_geojson(geojson_obj: dict, transformer) -> dict:
    try:
        obj = json.loads(json.dumps(geojson_obj))
        if obj.get("type") == "FeatureCollection":
            for f in obj.get("features", []):
                g = f.get("geometry")
                if g and isinstance(g, dict) and "coordinates" in g:
                    g["coordinates"] = transform_coords(g["coordinates"], transformer)
        elif obj.get("type") == "Feature":
            g = obj.get("geometry")
            if g and isinstance(g, dict) and "coordinates" in g:
                g["coordinates"] = transform_coords(g["coordinates"], transformer)
        elif obj.get("type") in ("Point","LineString","Polygon","MultiPoint","MultiLineString","MultiPolygon","GeometryCollection"):
            if "coordinates" in obj:
                obj["coordinates"] = transform_coords(obj["coordinates"], transformer)
        return obj
    except Exception:
        return geojson_obj
