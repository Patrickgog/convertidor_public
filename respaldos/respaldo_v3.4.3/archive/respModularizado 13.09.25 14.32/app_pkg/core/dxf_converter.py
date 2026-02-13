from typing import Any, Dict, List, Tuple
import json
import math
import tempfile
from pathlib import Path

import ezdxf
import pyproj
import shapefile  # pyshp
from simplekml import Kml

from app_pkg.utils.files import zip_directory


def export_geojson_to_dxf(geojson_data: Dict[str, Any], output_path: str) -> None:
    doc = ezdxf.new()
    msp = doc.modelspace()

    if not geojson_data or "features" not in geojson_data:
        doc.saveas(output_path)
        return

    for feature in geojson_data["features"]:
        geom = feature.get("geometry")
        if not geom or "coordinates" not in geom:
            continue

        geom_type = geom.get("type")
        coords = geom.get("coordinates")

        if geom_type == "Point":
            msp.add_point(coords)
        elif geom_type == "LineString":
            msp.add_lwpolyline(coords)
        elif geom_type == "Polygon":
            msp.add_lwpolyline(coords[0], close=True)
        elif geom_type == "MultiPoint":
            for point in coords:
                msp.add_point(point)
        elif geom_type == "MultiLineString":
            for line in coords:
                msp.add_lwpolyline(line)
        elif geom_type == "MultiPolygon":
            for polygon in coords:
                msp.add_lwpolyline(polygon[0], close=True)

    doc.saveas(output_path)


def _transform_xy(transformer: pyproj.Transformer, x: float, y: float) -> Tuple[float, float]:
    lon, lat = transformer.transform(x, y)
    return float(lon), float(lat)


def _entity_layer(ent) -> str:
    try:
        return str(getattr(ent.dxf, "layer", "default"))
    except Exception:
        return "default"


def convert_dxf(dxf_path: str, input_epsg: int, output_epsg: int, shapes_group_by: str) -> Dict[str, Any]:
    """Convierte un DXF a salidas estandarizadas: GeoJSON, JSON resumen, KMZ y Shapefiles.

    shapes_group_by: 'type' o 'layer' para agrupar Shapefiles.
    """
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    transformer = pyproj.Transformer.from_crs(f"EPSG:{input_epsg}", f"EPSG:{output_epsg}", always_xy=True)

    features: List[Dict[str, Any]] = []

    # Puntos
    for e in msp.query("POINT"):
        try:
            x, y = float(e.dxf.location.x), float(e.dxf.location.y)
            lon, lat = _transform_xy(transformer, x, y)
            features.append({
                "type": "Feature",
                "properties": {"type": "point", "layer": _entity_layer(e)},
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
            })
        except Exception:
            continue

    # Líneas simples
    for e in msp.query("LINE"):
        try:
            x1, y1 = float(e.dxf.start.x), float(e.dxf.start.y)
            x2, y2 = float(e.dxf.end.x), float(e.dxf.end.y)
            p1 = _transform_xy(transformer, x1, y1)
            p2 = _transform_xy(transformer, x2, y2)
            features.append({
                "type": "Feature",
                "properties": {"type": "polyline", "layer": _entity_layer(e)},
                "geometry": {"type": "LineString", "coordinates": [list(p1), list(p2)]},
            })
        except Exception:
            continue

    # LWPOLYLINE
    for e in msp.query("LWPOLYLINE"):
        try:
            pts = [(float(px), float(py)) for (px, py, *_rest) in e]
            coords = [list(_transform_xy(transformer, px, py)) for (px, py) in pts]
            features.append({
                "type": "Feature",
                "properties": {"type": "polyline", "layer": _entity_layer(e)},
                "geometry": {"type": "LineString", "coordinates": coords},
            })
        except Exception:
            continue

    # POLYLINE (2D)
    for e in msp.query("POLYLINE"):
        try:
            if e.is_3d_polyline or e.is_2d_polyline:
                pts = [(float(v.dxf.location.x), float(v.dxf.location.y)) for v in e.vertices()]
                coords = [list(_transform_xy(transformer, px, py)) for (px, py) in pts]
                if len(coords) >= 2:
                    features.append({
                        "type": "Feature",
                        "properties": {"type": "polyline", "layer": _entity_layer(e)},
                        "geometry": {"type": "LineString", "coordinates": coords},
                    })
        except Exception:
            continue

    # CIRCLE (aproximación a polilínea cerrada)
    for e in msp.query("CIRCLE"):
        try:
            cx, cy = float(e.dxf.center.x), float(e.dxf.center.y)
            r = float(e.dxf.radius)
            coords_ll: List[List[float]] = []
            steps = 64
            for i in range(steps + 1):
                ang = 2 * math.pi * i / steps
                x = cx + r * math.cos(ang)
                y = cy + r * math.sin(ang)
                lon, lat = _transform_xy(transformer, x, y)
                coords_ll.append([lon, lat])
            features.append({
                "type": "Feature",
                "properties": {"type": "circle", "layer": _entity_layer(e)},
                "geometry": {"type": "LineString", "coordinates": coords_ll},
            })
        except Exception:
            continue

    # ARC (aproximación a polilínea)
    for e in msp.query("ARC"):
        try:
            cx, cy = float(e.dxf.center.x), float(e.dxf.center.y)
            r = float(e.dxf.radius)
            start = math.radians(float(e.dxf.start_angle))
            end = math.radians(float(e.dxf.end_angle))
            # normalizar dirección
            if end < start:
                end += 2 * math.pi
            coords_ll: List[List[float]] = []
            steps = max(8, int((end - start) / (2 * math.pi) * 64))
            for i in range(steps + 1):
                ang = start + (end - start) * i / steps
                x = cx + r * math.cos(ang)
                y = cy + r * math.sin(ang)
                lon, lat = _transform_xy(transformer, x, y)
                coords_ll.append([lon, lat])
            features.append({
                "type": "Feature",
                "properties": {"type": "polyline", "layer": _entity_layer(e)},
                "geometry": {"type": "LineString", "coordinates": coords_ll},
            })
        except Exception:
            continue

    # SPLINE (aproximación mediante puntos de control discretizados)
    for e in msp.query("SPLINE"):
        try:
            # aproximación a ~100 segmentos a lo largo del parámetro
            try:
                pts_2d = [tuple(map(float, p)) for p in e.approximate(100)]
            except Exception:
                pts_2d = [(float(p[0]), float(p[1])) for p in e.control_points]
            coords = [list(_transform_xy(transformer, px, py)) for (px, py) in pts_2d]
            if len(coords) >= 2:
                features.append({
                    "type": "Feature",
                    "properties": {"type": "polyline", "layer": _entity_layer(e)},
                    "geometry": {"type": "LineString", "coordinates": coords},
                })
        except Exception:
            continue

    # ELLIPSE (aproximación polilínea)
    for e in msp.query("ELLIPSE"):
        try:
            # Parametrización de 0..2pi
            cx, cy = float(e.dxf.center.x), float(e.dxf.center.y)
            major = e.dxf.major_axis  # vector
            ratio = float(e.dxf.ratio)
            start = float(getattr(e.dxf, "start_param", 0.0))
            end = float(getattr(e.dxf, "end_param", 2 * math.pi))
            if end <= start:
                end += 2 * math.pi
            ux, uy = float(major.x), float(major.y)
            # Perpendicular minor axis
            vx, vy = -uy * ratio, ux * ratio
            steps = 128
            coords_ll: List[List[float]] = []
            for i in range(steps + 1):
                t = start + (end - start) * (i / steps)
                x = cx + ux * math.cos(t) + vx * math.sin(t)
                y = cy + uy * math.cos(t) + vy * math.sin(t)
                lon, lat = _transform_xy(transformer, x, y)
                coords_ll.append([lon, lat])
            features.append({
                "type": "Feature",
                "properties": {"type": "polyline", "layer": _entity_layer(e)},
                "geometry": {"type": "LineString", "coordinates": coords_ll},
            })
        except Exception:
            continue

    # HATCH (aproximación por bordes)
    for e in msp.query("HATCH"):
        try:
            for path in e.paths:
                coords_acc: List[List[float]] = []
                if path.is_edge_path:
                    for edge in path:
                        etype = edge.EDGE_TYPE
                        if etype == "LINE":
                            x1, y1 = float(edge.start[0]), float(edge.start[1])
                            x2, y2 = float(edge.end[0]), float(edge.end[1])
                            p1 = _transform_xy(transformer, x1, y1)
                            p2 = _transform_xy(transformer, x2, y2)
                            if not coords_acc:
                                coords_acc.append([p1[0], p1[1]])
                            coords_acc.append([p2[0], p2[1]])
                        elif etype == "ARC":
                            cx, cy = float(edge.center[0]), float(edge.center[1])
                            r = float(edge.radius)
                            start = math.radians(float(edge.start_angle))
                            end = math.radians(float(edge.end_angle))
                            if end < start:
                                end += 2 * math.pi
                            steps = max(8, int((end - start) / (2 * math.pi) * 64))
                            for i in range(steps + 1):
                                ang = start + (end - start) * i / steps
                                x = cx + r * math.cos(ang)
                                y = cy + r * math.sin(ang)
                                lon, lat = _transform_xy(transformer, x, y)
                                coords_acc.append([lon, lat])
                        elif etype == "SPLINE":
                            # aproximar con puntos discretos
                            pts = [(float(p[0]), float(p[1])) for p in edge.control_points]
                            for (px, py) in pts:
                                lon, lat = _transform_xy(transformer, px, py)
                                coords_acc.append([lon, lat])
                if len(coords_acc) >= 2:
                    closed = path.is_closed or (coords_acc[0] == coords_acc[-1])
                    if closed and len(coords_acc) >= 4:
                        features.append({
                            "type": "Feature",
                            "properties": {"type": "polygon", "layer": _entity_layer(e)},
                            "geometry": {"type": "Polygon", "coordinates": [coords_acc]},
                        })
                    else:
                        features.append({
                            "type": "Feature",
                            "properties": {"type": "polyline", "layer": _entity_layer(e)},
                            "geometry": {"type": "LineString", "coordinates": coords_acc},
                        })
        except Exception:
            continue

    # INSERT (blocks) como puntos y textos básicos
    for e in msp.query("INSERT"):
        try:
            x, y = float(e.dxf.insert.x), float(e.dxf.insert.y)
            lon, lat = _transform_xy(transformer, x, y)
            features.append({
                "type": "Feature",
                "properties": {"type": "block", "layer": _entity_layer(e), "name": str(e.dxf.name)},
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
            })
            # atributos como textos
            for a in getattr(e, "attribs", []):
                try:
                    ax, ay = float(a.dxf.insert.x), float(a.dxf.insert.y)
                    alon, alat = _transform_xy(transformer, ax, ay)
                    features.append({
                        "type": "Feature",
                        "properties": {"type": "text", "text": str(a.dxf.text), "layer": _entity_layer(e)},
                        "geometry": {"type": "Point", "coordinates": [alon, alat]},
                    })
                except Exception:
                    continue
        except Exception:
            continue

    # TEXT (como puntos con propiedad 'text')
    for e in msp.query("TEXT MTEXT"):
        try:
            x, y = float(e.dxf.insert.x), float(e.dxf.insert.y)
            lon, lat = _transform_xy(transformer, x, y)
            txt = str(getattr(e, "text", getattr(e.dxf, "text", "")).strip())
            features.append({
                "type": "Feature",
                "properties": {"type": "text", "text": txt, "layer": _entity_layer(e)},
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
            })
        except Exception:
            continue

    geojson = {"type": "FeatureCollection", "features": features}

    # JSON de resumen por layer/type
    summary: Dict[str, Any] = {"counts": {"layers": {}, "types": {}}}
    for f in features:
        lay = f.get("properties", {}).get("layer", "default")
        typ = f.get("properties", {}).get("type", "unknown")
        summary["counts"]["layers"][lay] = summary["counts"]["layers"].get(lay, 0) + 1
        summary["counts"]["types"][typ] = summary["counts"]["types"].get(typ, 0) + 1
    json_bytes = json.dumps(summary, indent=2).encode("utf-8")
    geojson_bytes = json.dumps(geojson, indent=2).encode("utf-8")

    # KMZ (vía simplekml)
    kml = Kml()
    folder_points = kml.newfolder(name="📍 Puntos")
    folder_lines = kml.newfolder(name="📏 Líneas")
    folder_texts = kml.newfolder(name="📝 Textos")
    for f in features:
        g = f.get("geometry", {})
        p = f.get("properties", {})
        if g.get("type") == "Point" and p.get("type") != "text":
            lon, lat = g["coordinates"]
            folder_points.newpoint(name=p.get("layer", ""), coords=[(lon, lat)])
        elif g.get("type") == "LineString":
            coords_line = g.get("coordinates", [])
            if len(coords_line) >= 2:
                folder_lines.newlinestring(name=p.get("layer", ""), coords=coords_line)
        elif p.get("type") == "text" and g.get("type") == "Point":
            lon, lat = g["coordinates"]
            folder_texts.newpoint(name=p.get("text", ""), coords=[(lon, lat)])
    kmz_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".kmz")
    kml.save(kmz_tmp.name)
    kmz_bytes = Path(kmz_tmp.name).read_bytes()

    # Shapefiles agrupados
    shp_dir = Path(tempfile.mkdtemp(prefix="dxf_shp_"))
    group_key = "layer" if str(shapes_group_by).lower() == "layer" else "type"
    groups: Dict[str, Dict[str, Any]] = {}
    for f in features:
        key = str(f.get("properties", {}).get(group_key, "default"))
        g = f.get("geometry", {})
        typ = g.get("type")
        grp = groups.setdefault(key, {"points": [], "lines": []})
        if typ == "Point":
            grp["points"].append(g.get("coordinates"))
        elif typ == "LineString":
            grp["lines"].append(g.get("coordinates"))

    for key, data in groups.items():
        # Puntos
        if data["points"]:
            w = shapefile.Writer(str(shp_dir / f"{key}_points"), shapeType=shapefile.POINT)
            w.field("Name", "C")
            for idx, (lon, lat) in enumerate(data["points" ]):
                w.point(lon, lat)
                w.record(f"{key}_{idx}")
            w.close()
        # Líneas
        if data["lines"]:
            w = shapefile.Writer(str(shp_dir / f"{key}_lines"), shapeType=shapefile.POLYLINE)
            w.field("Name", "C")
            for idx, line in enumerate(data["lines"]):
                w.line([line])
                w.record(f"{key}_{idx}")
            w.close()
    # PRJ según EPSG salida
    try:
        prj_wkt = pyproj.CRS.from_epsg(int(output_epsg)).to_wkt()
        for f in shp_dir.glob("*.shp"):
            prj_path = f.with_suffix(".prj")
            prj_path.write_text(prj_wkt, encoding="utf-8")
    except Exception:
        pass

    shp_zip_bytes = zip_directory(str(shp_dir))

    return {
        "json_bytes": json_bytes,
        "geojson_bytes": geojson_bytes,
        "kmz_bytes": kmz_bytes,
        "shp_zip_bytes": shp_zip_bytes,
        "shp_dir": str(shp_dir),
        "geojson": geojson,
    }


__all__ = ["export_geojson_to_dxf", "convert_dxf"]
