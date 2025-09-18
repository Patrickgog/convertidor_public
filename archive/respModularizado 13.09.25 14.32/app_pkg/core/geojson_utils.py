import json
from typing import Any, Dict, List, Tuple, Union, Optional

import pyproj

Coordinates = Union[List[Any], Tuple[Any, ...]]


def remove_z_from_coords(coords: Coordinates) -> Coordinates:
    """Remove Z values recursively from coordinates structures.

    Accepts nested lists/tuples of coordinates and returns the same structure
    without the Z component where applicable.
    """
    try:
        if isinstance(coords, (list, tuple)) and len(coords) > 0 and isinstance(coords[0], (int, float)):
            return [coords[0], coords[1]]
        return [remove_z_from_coords(c) for c in coords]  # type: ignore[return-value]
    except Exception:
        return coords


def strip_z_from_geojson(geojson_obj: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of a GeoJSON object with Z values stripped from coordinates."""
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
        elif geojson_obj.get("type") in (
            "Point",
            "LineString",
            "Polygon",
            "MultiPoint",
            "MultiLineString",
            "MultiPolygon",
            "GeometryCollection",
        ):
            if "coordinates" in geojson_obj:
                geojson_obj["coordinates"] = remove_z_from_coords(geojson_obj["coordinates"])  # type: ignore[index]
        return geojson_obj
    except Exception:
        return geojson_obj


def compute_bounds_from_geojson(geojson_data: Dict[str, Any]) -> Optional[List[List[float]]]:
    """Compute bounds [[minLat, minLon], [maxLat, maxLon]] from a GeoJSON object.

    Returns None if bounds cannot be computed.
    """
    bounds: List[List[float]] = []
    if not geojson_data or "features" not in geojson_data:
        return None

    for feature in geojson_data["features"]:
        geom = feature.get("geometry")
        if not geom or "coordinates" not in geom:
            continue

        coords = geom["coordinates"]
        if geom["type"] == "Point":
            coords = [coords]
        elif geom["type"] in ("LineString", "MultiPoint"):
            pass
        elif geom["type"] in ("Polygon", "MultiLineString"):
            coords = [c for sublist in coords for c in sublist]
        elif geom["type"] == "MultiPolygon":
            coords = [c for sublist in coords for subsublist in sublist for c in subsublist]
        else:
            continue

        if not bounds:
            if not coords:
                continue
            bounds = [list(coords[0]), list(coords[0])]  # type: ignore[index]
        for lon, lat in coords:
            if lon < bounds[0][0]:
                bounds[0][0] = lon
            if lat < bounds[0][1]:
                bounds[0][1] = lat
            if lon > bounds[1][0]:
                bounds[1][0] = lon
            if lat > bounds[1][1]:
                bounds[1][1] = lat
    if not bounds:
        return None
    return [[bounds[0][1], bounds[0][0]], [bounds[1][1], bounds[1][0]]]


def filter_geojson_valid(geojson_data: Dict[str, Any]) -> Dict[str, Any]:
    """Filter out features with invalid coordinates layout for their geometry type."""
    if not geojson_data or "features" not in geojson_data:
        return geojson_data

    valid_features: List[Dict[str, Any]] = []
    for feature in geojson_data["features"]:
        geom = feature.get("geometry")
        if not geom or "coordinates" not in geom:
            continue

        coords = geom.get("coordinates")
        if not coords:
            continue

        gtype = geom.get("type")
        if gtype == "Point":
            if len(coords) < 2:
                continue
        elif gtype in ("LineString", "MultiPoint"):
            if not all(isinstance(c, list) and len(c) >= 2 for c in coords):
                continue
        elif gtype in ("Polygon", "MultiLineString"):
            if not all(
                isinstance(sublist, list)
                and all(isinstance(c, list) and len(c) >= 2 for c in sublist)
                for sublist in coords
            ):
                continue
        elif gtype == "MultiPolygon":
            if not all(
                isinstance(sublist, list)
                and all(
                    isinstance(subsublist, list)
                    and all(isinstance(c, list) and len(c) >= 2 for c in subsublist)
                    for subsublist in sublist
                )
                for sublist in coords
            ):
                continue

        valid_features.append(feature)

    geojson_data["features"] = valid_features
    return geojson_data


def transform_coords(coords: Coordinates, transformer: pyproj.Transformer) -> Coordinates:
    """Apply a pyproj transformer to nested coordinates structures."""
    if isinstance(coords, (list, tuple)):
        if (
            len(coords) >= 2
            and isinstance(coords[0], (int, float))
            and isinstance(coords[1], (int, float))
        ):
            x, y = transformer.transform(coords[0], coords[1])
            return [x, y]
        return [transform_coords(c, transformer) for c in coords]  # type: ignore[return-value]
    return coords


def transform_geojson(geojson_obj: Dict[str, Any], transformer: pyproj.Transformer) -> Dict[str, Any]:
    """Return a transformed copy of a GeoJSON object using the provided transformer."""
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
        elif obj.get("type") in (
            "Point",
            "LineString",
            "Polygon",
            "MultiPoint",
            "MultiLineString",
            "MultiPolygon",
            "GeometryCollection",
        ):
            if "coordinates" in obj:
                obj["coordinates"] = transform_coords(obj["coordinates"], transformer)  # type: ignore[index]
        return obj
    except Exception:
        return geojson_obj


def utm_to_latlon_coords(transformer: pyproj.Transformer, x: float, y: float) -> Tuple[float, float]:
    """Transform a single UTM pair (x, y) to lon/lat using the given transformer."""
    lon, lat = transformer.transform(x, y)
    return lon, lat


__all__ = [
    "remove_z_from_coords",
    "strip_z_from_geojson",
    "compute_bounds_from_geojson",
    "filter_geojson_valid",
    "transform_coords",
    "transform_geojson",
    "utm_to_latlon_coords",
]
