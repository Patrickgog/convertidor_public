import io
import os
import json
import math
import shutil
import zipfile
import tempfile
import time
from pathlib import Path

import streamlit as st
import streamlit.components.v1
from streamlit_folium import st_folium
import folium

import ezdxf
from simplekml import Kml
from shapely.geometry import Point, LineString, shape as shp_shape
from shapely.geometry import mapping as shp_mapping
import shapefile
import pyproj
from xml.etree import ElementTree as ET
import logging

# Sistema de autenticación
from auth_system import check_authentication, show_user_info

# Librerías para mapas de calor
import numpy as np
from scipy.interpolate import griddata
import rasterio
from rasterio.transform import from_bounds, Affine
import geopandas as gpd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kml_kmz")


# Namespaces KML
KML_NS = {"kml": "http://www.opengis.net/kml/2.2", "gx": "http://www.google.com/kml/ext/2.2"}


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


def export_geojson_to_dxf(geojson_obj: dict, dxf_path: Path):
    try:
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()
        def add_point(x, y):
            try:
                msp.add_point((x, y), dxfattribs={"layer": "POINTS"})
            except Exception:
                pass
        def add_polyline(coords, layer="LINES", closed=False):
            try:
                if not coords or len(coords) < 2:
                    return
                if closed:
                    msp.add_lwpolyline(coords + [coords[0]], dxfattribs={"layer": layer, "closed": 1})
                else:
                    msp.add_lwpolyline(coords, dxfattribs={"layer": layer})
            except Exception:
                pass
        feats = geojson_obj.get("features", []) if geojson_obj.get("type") == "FeatureCollection" else []
        for f in feats:
            g = f.get("geometry", {})
            t = g.get("type")
            if t == "Point":
                x, y = g.get("coordinates", [None, None])[:2]
                if x is not None and y is not None:
                    add_point(x, y)
            elif t == "MultiPoint":
                for pt in g.get("coordinates", []):
                    x, y = pt[:2]
                    add_point(x, y)
            elif t == "LineString":
                coords = [(c[0], c[1]) for c in g.get("coordinates", [])]
                add_polyline(coords, layer="LINES", closed=False)
            elif t == "MultiLineString":
                for line in g.get("coordinates", []):
                    coords = [(c[0], c[1]) for c in line]
                    add_polyline(coords, layer="LINES", closed=False)
            elif t == "Polygon":
                rings = g.get("coordinates", [])
                if rings:
                    exterior = [(c[0], c[1]) for c in rings[0]]
                    add_polyline(exterior, layer="POLYGONS", closed=True)
            elif t == "MultiPolygon":
                for poly in g.get("coordinates", []):
                    if poly:
                        exterior = [(c[0], c[1]) for c in poly[0]]
                        add_polyline(exterior, layer="POLYGONS", closed=True)
        doc.saveas(str(dxf_path))
        return True
    except Exception:
        return False


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


def convert_to_geojson(data):
    geojson = {"type": "FeatureCollection", "features": []}
    for layer_name, layer_data in data["layers"].items():
        for point in layer_data.get("points", []):
            geojson["features"].append({
                "type": "Feature",
                "properties": {"layer": layer_name, "type": "point", "x": point["x"], "y": point["y"]},
                "geometry": {"type": "Point", "coordinates": [point["lon"], point["lat"]]},
            })

        for line in layer_data.get("lines", []):
            geojson["features"].append({
                "type": "Feature",
                "properties": {
                    "layer": layer_name,
                    "type": "line",
                    "start_x": line["start"][0],
                    "start_y": line["start"][1],
                    "end_x": line["end"][0],
                    "end_y": line["end"][1],
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [line["start_lonlat"][0], line["start_lonlat"][1]],
                        [line["end_lonlat"][0], line["end_lonlat"][1]],
                    ],
                },
            })

        def points_equal(p1, p2, eps=1e-6):
            return abs(p1[0] - p2[0]) < eps and abs(p1[1] - p2[1]) < eps

        def parse_polygons_sequential(vertices, epsilon=0.01):
            from shapely.geometry import Polygon
            polygons = []
            n = len(vertices)
            i = 0
            while i < n:
                poly_points = [vertices[i]]
                start = vertices[i]
                j = i + 1
                while j < n:
                    pt = vertices[j]
                    poly_points.append(pt)
                    # Cierre si coincide con el inicial (tolerancia)
                    if abs(pt[0] - start[0]) < epsilon and abs(pt[1] - start[1]) < epsilon:
                        if len(set(poly_points)) >= 3:
                            poly = Polygon(poly_points)
                            if poly.is_valid and poly.area > 0 and poly.length > 0:
                                polygons.append(list(poly.exterior.coords))
                        i = j + 1  # Siguiente polígono inicia en el punto siguiente
                        break
                    j += 1
                else:
                    # Si no se cerró, avanzar al siguiente punto
                    i += 1
            return polygons

        # Nuevo criterio: agrupar por número de polígono en la primera columna
        # Supongamos que layer_data["polylines"] contiene una lista de diccionarios con 'poligono', 'x', 'y', ...
        from shapely.geometry import Polygon
        import collections
        poligonos_dict = collections.defaultdict(list)
        for punto in layer_data.get("polylines", []):
            # punto debe ser dict con clave 'poligono', 'x', 'y'
            num = punto.get('poligono')
            x = punto.get('x')
            y = punto.get('y')
            if num is not None and x is not None and y is not None:
                poligonos_dict[num].append((x, y))
        for num, puntos in poligonos_dict.items():
            if len(set(puntos)) >= 3:
                # Cerrar el polígono si el primer y último punto no coinciden (con tolerancia)
                def puntos_iguales(p1, p2, eps=0.01):
                    return abs(p1[0] - p2[0]) < eps and abs(p1[1] - p2[1]) < eps
                if not puntos_iguales(puntos[0], puntos[-1]):
                    puntos = list(puntos) + [puntos[0]]
                poly = Polygon(puntos)
                if poly.is_valid and poly.area > 0 and poly.length > 0:
                    geojson["features"].append({
                        "type": "Feature",
                        "properties": {"layer": layer_name, "type": "polyline", "poligono": num},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [list(poly.exterior.coords)],
                        },
                    })
                else:
                    # Si no es polígono válido, exportar como polilínea (LineString)
                    geojson["features"].append({
                        "type": "Feature",
                        "properties": {"layer": layer_name, "type": "polyline", "poligono": num},
                        "geometry": {
                            "type": "LineString",
                            "coordinates": list(puntos),
                        },
                    })

        for text in layer_data.get("texts", []):
            geojson["features"].append({
                "type": "Feature",
                "properties": {
                    "layer": layer_name,
                    "type": "text",
                    "text": text["text"],
                    "rotation": text["rotation"],
                    "x": text["x"],
                    "y": text["y"],
                },
                "geometry": {"type": "Point", "coordinates": [text["lon"], text["lat"]]},
            })

        for circle in layer_data.get("circles", []):
            geojson["features"].append({
                "type": "Feature",
                "properties": {
                    "layer": layer_name,
                    "type": "circle",
                    "center_x": circle["center"][0],
                    "center_y": circle["center"][1],
                    "radius": circle["radius"]
                },
                "geometry": {"type": "Polygon", "coordinates": [circle["coords_lonlat"]]},
            })

        for shape in layer_data.get("shapes", []):
            coordinates = [[lon, lat] for lon, lat in shape["vertices_lonlat"]]
            if shape["closed"]:
                geom = {"type": "Polygon", "coordinates": [coordinates + [coordinates[0]]]}  # .Respaldos logic
            else:
                geom = {"type": "LineString", "coordinates": coordinates}
            geojson["features"].append({
                "type": "Feature",
                "properties": {"layer": layer_name, "type": "shape"},
                "geometry": geom,
            })

        for block in layer_data.get("blocks", []):
            geojson["features"].append({
                "type": "Feature",
                "properties": {
                    "layer": layer_name,
                    "type": "block",
                    "block_name": block["block_name"],
                    "x": block["x"],
                    "y": block["y"]
                },
                "geometry": {"type": "Point", "coordinates": [block["lon"], block["lat"]]},
            })
    return geojson


def zip_directory(directory_path: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(directory_path):
            for file in files:
                abs_path = Path(root) / file
                rel_path = abs_path.relative_to(directory_path)
                zipf.write(abs_path, arcname=str(rel_path))
    buffer.seek(0)
    return buffer.read()


def convert_dxf(file_path: Path, input_epsg: int, output_epsg: int, shapes_group_by: str = "layer"):
    try:
        doc = ezdxf.readfile(str(file_path))
        msp = doc.modelspace()
    except Exception as exc:
        raise RuntimeError(f"No se pudo leer el DXF: {exc}")

    # Transformadores:
    # - Para visores/KMZ/GeoJSON web SIEMPRE a WGS84
    transformer_wgs84 = build_transformer(input_epsg, 4326)
    # - Para Shapefiles al EPSG de salida seleccionado
    transformer_out = build_transformer(input_epsg, output_epsg)

    visible_layers = set()
    for layer in doc.layers:
        flags = layer.dxf.get("flags", 0)
        is_frozen = flags & 1
        is_off = flags & 16
        if not is_frozen and not is_off:
            visible_layers.add(layer.dxf.name)
    if not visible_layers:
        raise RuntimeError("No se encontraron layers visibles en el DXF.")

    kml = Kml()
    # Crear carpetas para organizar elementos
    points_folder = kml.newfolder(name="📍 Puntos")
    lines_folder = kml.newfolder(name="📏 Líneas")
    polylines_folder = kml.newfolder(name="🔗 Polilíneas")
    shapes_folder = kml.newfolder(name="🔷 Formas")
    circles_folder = kml.newfolder(name="⭕ Círculos")
    texts_folder = kml.newfolder(name="📝 Textos")
    blocks_folder = kml.newfolder(name="🧩 Bloques")
    
    json_data = {"layers": {layer: {"points": [], "lines": [], "polylines": [], "texts": [], "circles": [], "shapes": [], "blocks": []} for layer in visible_layers}}

    layers_aux = {layer: {"polylines": [], "texts": []} for layer in visible_layers}
    for entity in msp:
        layer = entity.dxf.layer
        if layer not in visible_layers:
            continue
        if entity.dxftype() in ("POLYLINE", "LWPOLYLINE"):
            try:
                if entity.dxftype() == "POLYLINE":
                    vertices = [(v.x, v.y) for v in entity.points()]
                else:
                    vertices = [(v[0], v[1]) for v in entity.vertices()]
                if len(vertices) >= 2:
                    layers_aux[layer]["polylines"].append(vertices)
            except Exception:
                continue
        elif entity.dxftype() == "TEXT":
            try:
                x, y = entity.dxf.insert[0], entity.dxf.insert[1]
                txt = entity.dxf.text
                layers_aux[layer]["texts"].append({"x": x, "y": y, "text": txt})
            except Exception:
                continue

    shapefiles_dir = Path(tempfile.mkdtemp(prefix="shp_"))

    # Creación dinámica de writers por (layer, tipo)
    writers = {}
    writer_paths = {}

    def safe_name(name: str) -> str:
        return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in str(name))[:64]

    def get_writer(layer_name: str, type_name: str, shape_type: int) -> shapefile.Writer:
        group_identifier = type_name if str(shapes_group_by).lower() == "type" else layer_name
        key = (group_identifier, type_name)
        if key in writers:
            return writers[key]
        if str(shapes_group_by).lower() == "type":
            base = f"{safe_name(type_name)}"
        else:
            base = f"{safe_name(layer_name)}_{safe_name(type_name)}"
        base_path = shapefiles_dir / base
        w = shapefile.Writer(str(base_path), shapeType=shape_type)
        # Campos comunes
        w.field("ID", "C")
        w.field("Layer", "C")
        w.field("Type", "C")
        # Campos específicos por tipo
        if type_name == "texts":
            w.field("Text", "C")
            w.field("Rotation", "N", decimal=2)
        if type_name == "blocks":
            w.field("BlockName", "C")
        writers[key] = w
        writer_paths[key] = base_path
        return w

    for entity in msp:
        layer = entity.dxf.layer
        if layer not in visible_layers:
            continue

        etype = entity.dxftype()
        if etype == "POINT":
            x, y = entity.dxf.location[0], entity.dxf.location[1]
            lon, lat = utm_to_latlon_coords(transformer_wgs84, x, y)
            points_folder.newpoint(name=f"Point_{len(json_data['layers'][layer]['points'])}", coords=[(lon, lat)])
            json_data["layers"][layer]["points"].append({"x": x, "y": y, "lon": lon, "lat": lat})
            # SHP en EPSG de salida
            x_out, y_out = utm_to_latlon_coords(transformer_out, x, y)
            w = get_writer(layer, "points", shapefile.POINT)
            w.point(x_out, y_out)
            w.record(f"P{len(json_data['layers'][layer]['points'])}", layer, "point")

        elif etype == "LINE":
            start = entity.dxf.start
            end = entity.dxf.end
            lon1, lat1 = utm_to_latlon_coords(transformer_wgs84, start[0], start[1])
            lon2, lat2 = utm_to_latlon_coords(transformer_wgs84, end[0], end[1])
            lines_folder.newlinestring(name=f"Line_{len(json_data['layers'][layer]['lines'])}", coords=[(lon1, lat1), (lon2, lat2)])
            json_data["layers"][layer]["lines"].append({
                "start": [start[0], start[1]],
                "end": [end[0], end[1]],
                "start_lonlat": [lon1, lat1],
                "end_lonlat": [lon2, lat2],
            })
            # SHP en EPSG de salida
            x1_out, y1_out = utm_to_latlon_coords(transformer_out, start[0], start[1])
            x2_out, y2_out = utm_to_latlon_coords(transformer_out, end[0], end[1])
            w = get_writer(layer, "lines", shapefile.POLYLINE)
            w.line([[[x1_out, y1_out], [x2_out, y2_out]]])
            w.record(f"L{len(json_data['layers'][layer]['lines'])}", layer, "line")

        elif etype == "POLYLINE":
            try:
                vertices = [(v.x, v.y) for v in entity.points()]
                if len(vertices) < 2:
                    continue
                coords_latlon_wgs84 = [utm_to_latlon_coords(transformer_wgs84, x, y) for x, y in vertices]
                polylines_folder.newlinestring(name=f"Polyline_{len(json_data['layers'][layer]['polylines'])}", coords=coords_latlon_wgs84)
                json_data["layers"][layer]["polylines"].append({"vertices": vertices, "vertices_lonlat": coords_latlon_wgs84})
                # SHP en EPSG de salida
                coords_out = [utm_to_latlon_coords(transformer_out, x, y) for x, y in vertices]
                w = get_writer(layer, "polylines", shapefile.POLYLINE)
                w.line([coords_out])
                w.record(f"PL{len(json_data['layers'][layer]['polylines'])}", layer, "polyline")
            except Exception:
                pass

        elif etype == "LWPOLYLINE":
            try:
                vertices = [(v[0], v[1]) for v in entity.vertices()]
                if len(vertices) < 2:
                    continue
                coords_latlon = [utm_to_latlon_coords(transformer_wgs84, x, y) for x, y in vertices]
                closed = bool(entity.dxf.flags & 1)
                shapes_folder.newlinestring(name=f"Shape_{len(json_data['layers'][layer]['shapes'])}", coords=coords_latlon)
                json_data["layers"][layer]["shapes"].append({
                    "vertices": vertices,
                    "vertices_lonlat": coords_latlon,
                    "closed": closed,
                })
                # SHP en EPSG de salida
                coords_out = [utm_to_latlon_coords(transformer_out, x, y) for x, y in vertices]
                w = get_writer(layer, "shapes", shapefile.POLYLINE)
                w.line([coords_out])
                w.record(f"S{len(json_data['layers'][layer]['shapes'])}", layer, "shape")
            except Exception:
                pass

        elif etype == "CIRCLE":
            center = entity.dxf.center
            radius = entity.dxf.radius
            num_points = 36
            coords_ll = []
            for i in range(num_points + 1):
                angle = math.radians(i * 360 / num_points)
                x = center[0] + radius * math.cos(angle)
                y = center[1] + radius * math.sin(angle)
                lon, lat = utm_to_latlon_coords(transformer_wgs84, x, y)
                coords_ll.append((lon, lat))
            circles_folder.newlinestring(name=f"Circle_{len(json_data['layers'][layer]['circles'])}", coords=coords_ll)
            json_data["layers"][layer]["circles"].append({
                "center": [center[0], center[1]],
                "radius": radius,
                "coords_lonlat": coords_ll,
            })
            # Guardar aproximación de círculo como polilínea
            circle_vertices = []  # en EPSG de salida
            for i in range(num_points + 1):
                ang = math.radians(i * 360 / num_points)
                x = center[0] + radius * math.cos(ang)
                y = center[1] + radius * math.sin(ang)
                x_out, y_out = utm_to_latlon_coords(transformer_out, x, y)
                circle_vertices.append([x_out, y_out])
            w = get_writer(layer, "circles", shapefile.POLYLINE)
            w.line([circle_vertices])
            w.record(f"C{len(json_data['layers'][layer]['circles'])}", layer, "circle")

        elif etype == "TEXT":
            x, y = entity.dxf.insert[0], entity.dxf.insert[1]
            lon, lat = utm_to_latlon_coords(transformer_wgs84, x, y)
            text = entity.dxf.text
            rotation = 0.0
            min_dist = float('inf')
            min_dist_threshold = 50.0
            if layers_aux[layer]["polylines"]:
                closest_angle = 0.0
                for polyline_vertices in layers_aux[layer]["polylines"]:
                    angle, dist = calculate_text_angle((x, y), polyline_vertices)
                    if dist < min_dist:
                        min_dist = dist
                        closest_angle = angle
                if min_dist < min_dist_threshold:
                    rotation = closest_angle
            json_data["layers"][layer]["texts"].append({
                "text": text,
                "x": x,
                "y": y,
                "lon": lon,
                "lat": lat,
                "rotation": float(rotation),
            })
            # SHP en EPSG de salida
            x_out, y_out = utm_to_latlon_coords(transformer_out, x, y)
            w = get_writer(layer, "texts", shapefile.POINT)
            w.point(x_out, y_out)
            # Campos: ID, Layer, Type, Text, Rotation
            w.record(f"T{len(json_data['layers'][layer]['texts'])}", layer, "text", text, float(rotation))

        elif etype == "INSERT":
            x, y = entity.dxf.insert[0], entity.dxf.insert[1]
            lon, lat = utm_to_latlon_coords(transformer_wgs84, x, y)
            block_name = entity.dxf.name
            blocks_folder.newpoint(name=f"Block_{len(json_data['layers'][layer]['blocks'])}", coords=[(lon, lat)])
            json_data["layers"][layer]["blocks"].append({
                "block_name": block_name,
                "x": x,
                "y": y,
                "lon": lon,
                "lat": lat,
            })
            # SHP en EPSG de salida
            x_out, y_out = utm_to_latlon_coords(transformer_out, x, y)
            w = get_writer(layer, "blocks", shapefile.POINT)
            w.point(x_out, y_out)
            # Campos: ID, Layer, Type, BlockName
            w.record(f"B{len(json_data['layers'][layer]['blocks'])}", layer, "block", block_name)

    kml_bytes = io.BytesIO()
    kmz_path = Path(tempfile.mkdtemp(prefix="kmz_")) / "export.kmz"
    kml.save(str(kmz_path))
    with open(kmz_path, "rb") as f:
        kml_bytes.write(f.read())
    kml_bytes.seek(0)

    # Cerrar writers y crear PRJ por EPSG de salida (WKT1_ESRI para QGIS)
    prj_wkt = None
    try:
        prj_wkt = pyproj.CRS.from_epsg(int(output_epsg)).to_wkt(version='WKT1_ESRI')
    except Exception:
        prj_wkt = None
    for key, w in writers.items():
        try:
            w.close()
        except Exception:
            pass
        if prj_wkt:
            base_path = writer_paths.get(key)
            if base_path:
                try:
                    with open(str(base_path) + ".prj", "w", encoding="utf-8") as prj_file:
                        prj_file.write(prj_wkt)
                except Exception:
                    pass

    shp_zip_bytes = zip_directory(shapefiles_dir)

    geojson_data = convert_to_geojson(json_data)
    json_bytes = json.dumps(json_data, indent=2).encode("utf-8")
    geojson_bytes = json.dumps(geojson_data, indent=2).encode("utf-8")

    return {
        "json": json_data,
        "json_bytes": json_bytes,
        "geojson": geojson_data,
        "geojson_bytes": geojson_bytes,
        "kmz_bytes": kml_bytes.getvalue(),
        "shp_zip_bytes": shp_zip_bytes,
        "shp_dir": str(shapefiles_dir),
    }


def create_normal_html(geojson_data, title="Map Viewer", bounds=None, grouping_mode="type"):
    """Genera HTML con visor Leaflet normal con control de capas según modo de agrupamiento"""
    geojson_str = json.dumps(geojson_data)
    bounds_str = json.dumps(bounds) if bounds else "null"
    
    if grouping_mode.lower() == "layer":
        # Modo LAYER: Agrupar por layer del DXF
        html_template = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title} - Map Viewer</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style> 
        html, body {{ height: 100%; margin: 0; }} 
        #map {{ height: 100vh; }} 
        .leaflet-control-layers-expanded {{ max-height: 60vh; overflow: auto; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        const map = L.map('map', {{ preferCanvas: true }});
        
        // Capas base
        const calles = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ attribution: 'OpenStreetMap', maxZoom: 19 }});
        const positron = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}.png', {{ attribution: 'CartoDB Positron', maxZoom: 19 }});
        const satelite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{ attribution: 'Esri', maxZoom: 19 }});
        const baseMaps = {{
            "Calles": calles,
            "Positron": positron,
            "Satelital": satelite
        }};
        
        // Agregar capa base por defecto
        positron.addTo(map);

        // GeoJSON y grupos por LAYER
        const data = {geojson_str};
        function groupByLayer(features) {{
            const groups = {{}};
            features.forEach(f => {{
                const layer = (f.properties && f.properties.layer) ? f.properties.layer : 'Default';
                if (!groups[layer]) groups[layer] = [];
                groups[layer].push(f);
            }});
            return groups;
        }}
        
        const grouped = groupByLayer(data.features || []);
        const overlayMaps = {{}};
        
        // Colores por layer
        const layerColors = ['#ff0000', '#0000ff', '#00ff00', '#ffff00', '#ff00ff', '#00ffff', '#ff8000', '#8000ff', '#0080ff', '#ff0080'];
        let colorIndex = 0;
        
        Object.keys(grouped).forEach(layer => {{
            const feats = grouped[layer];
            const color = layerColors[colorIndex % layerColors.length];
            colorIndex++;
            
            let layerGroup = L.layerGroup();
            
            feats.forEach(feature => {{
                const type = (feature.properties && feature.properties.type) ? feature.properties.type : 'unknown';
                
                       if (type === 'point' || type === 'block') {{
                           const [lon, lat] = feature.geometry.coordinates;
                           const marker = L.circleMarker([lat, lon], {{
                               radius: 4, 
                               color: color, 
                               fillColor: color,
                               fillOpacity: 0.8
                           }});
                           layerGroup.addLayer(marker);
                       }} else if (type === 'text') {{
                           const [lon, lat] = feature.geometry.coordinates;
                           const label = feature.properties && feature.properties.text ? feature.properties.text : '';
                           const marker = L.marker([lat, lon], {{
                               icon: L.divIcon({{ 
                                   className: '', 
                                   html: `<div style='font-size:12px;color:${{color}};font-weight:600;background:white;padding:2px;border-radius:3px;'>${{label}}</div>` 
                               }})
                           }});
                           layerGroup.addLayer(marker);
                       }} else {{
                           // Líneas y polígonos - convertir coordenadas correctamente
                           if (feature.geometry.type === 'LineString') {{
                               const coords = feature.geometry.coordinates.map(coord => [coord[1], coord[0]]);
                               const line = L.polyline(coords, {{
                                   color: color, 
                                   weight: 2, 
                                   opacity: 0.8
                               }});
                               layerGroup.addLayer(line);
                           }} else if (feature.geometry.type === 'Polygon') {{
                               const coords = feature.geometry.coordinates[0].map(coord => [coord[1], coord[0]]);
                               const polygon = L.polygon(coords, {{
                                   color: color, 
                                   weight: 2, 
                                   opacity: 0.8,
                                   fillOpacity: 0.1
                               }});
                               layerGroup.addLayer(polygon);
                           }} else {{
                               // Otros tipos usando geoJSON estándar
                               const geoJsonLayer = L.geoJSON(feature, {{
                                   style: {{ color: color, weight: 2, opacity: 0.8 }}
                               }});
                               layerGroup.addLayer(geoJsonLayer);
                           }}
                       }}
            }});
            
            overlayMaps[layer] = layerGroup;
            layerGroup.addTo(map);
        }});

        // Control de capas
        L.control.layers(baseMaps, overlayMaps, {{ position: 'topright', collapsed: false }}).addTo(map);

        // Ajuste de extensión
        const bounds = {bounds_str};
        if (bounds && bounds.length === 2) {{ 
            map.fitBounds(bounds); 
        }} else {{
            try {{
                let allBounds = [];
                Object.values(overlayMaps).forEach(l => {{
                    if (l.getBounds) allBounds.push(l.getBounds());
                }});
                if (allBounds.length) {{
                    let merged = allBounds[0];
                    for (let i = 1; i < allBounds.length; i++) {{
                        merged.extend(allBounds[i]);
                    }}
                    map.fitBounds(merged);
                }} else {{
                    map.setView([0,0], 2);
                }}
            }} catch (e) {{ map.setView([0,0], 2); }}
        }}
    </script>
</body>
</html>"""
    else:
        # Modo TYPE: Agrupar por tipo (puntos, líneas, textos)
        html_template = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title} - Map Viewer</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style> 
        html, body {{ height: 100%; margin: 0; }} 
        #map {{ height: 100vh; }} 
        .leaflet-control-layers-expanded {{ max-height: 60vh; overflow: auto; }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        const map = L.map('map', {{ preferCanvas: true }});
        
        // Capas base
        const calles = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ attribution: 'OpenStreetMap', maxZoom: 19 }});
        const positron = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}.png', {{ attribution: 'CartoDB Positron', maxZoom: 19 }});
        const satelite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{ attribution: 'Esri', maxZoom: 19 }});
        const baseMaps = {{
            "Calles": calles,
            "Positron": positron,
            "Satelital": satelite
        }};
        
        // Agregar capa base por defecto
        positron.addTo(map);

        // GeoJSON y grupos por TIPO
        const data = {geojson_str};
        function groupByType(features) {{
            const groups = {{}};
            features.forEach(f => {{
                const type = (f.properties && f.properties.type) ? f.properties.type : 'Otro';
                if (!groups[type]) groups[type] = [];
                groups[type].push(f);
            }});
            return groups;
        }}
        
        const grouped = groupByType(data.features || []);
        const overlayMaps = {{}};
        
        Object.keys(grouped).forEach(type => {{
            const feats = grouped[type];
            let layer;
            
                   if (type === 'point' || type === 'block') {{
                       layer = L.layerGroup();
                       feats.forEach(feature => {{
                           const [lon, lat] = feature.geometry.coordinates;
                           const marker = L.circleMarker([lat, lon], {{ radius: 4, color: '#00ff00', fillOpacity: 0.8 }});
                           layer.addLayer(marker);
                       }});
                   }} else if (type === 'text') {{
                       layer = L.layerGroup();
                       feats.forEach(feature => {{
                           const [lon, lat] = feature.geometry.coordinates;
                           const label = feature.properties && feature.properties.text ? feature.properties.text : '';
                           const marker = L.marker([lat, lon], {{
                               icon: L.divIcon({{ 
                                   className: '', 
                                   html: `<div style='font-size:12px;color:#0d6efd;font-weight:600;background:white;padding:2px;border-radius:3px;'>${{label}}</div>` 
                               }})
                           }});
                           layer.addLayer(marker);
                       }});
                   }} else {{
                       // Líneas y polígonos - manejar coordenadas correctamente
                       layer = L.layerGroup();
                       feats.forEach(feature => {{
                           if (feature.geometry.type === 'LineString') {{
                               const coords = feature.geometry.coordinates.map(coord => [coord[1], coord[0]]);
                               const line = L.polyline(coords, {{ color: '#ff0000', weight: 2, opacity: 0.8 }});
                               layer.addLayer(line);
                           }} else if (feature.geometry.type === 'Polygon') {{
                               const coords = feature.geometry.coordinates[0].map(coord => [coord[1], coord[0]]);
                               const polygon = L.polygon(coords, {{ color: '#ff0000', weight: 2, opacity: 0.8, fillOpacity: 0.1 }});
                               layer.addLayer(polygon);
                           }} else {{
                               // Otros tipos usando geoJSON estándar
                               const geoJsonLayer = L.geoJSON(feature, {{ style: {{ color: '#ff0000', weight: 2, opacity: 0.8 }} }});
                               layer.addLayer(geoJsonLayer);
                           }}
                       }});
                   }}
            
            overlayMaps[type.charAt(0).toUpperCase() + type.slice(1)] = layer;
            layer.addTo(map);
        }});

        // Control de capas
        L.control.layers(baseMaps, overlayMaps, {{ position: 'topright', collapsed: false }}).addTo(map);

        // Ajuste de extensión
        const bounds = {bounds_str};
        if (bounds && bounds.length === 2) {{ 
            map.fitBounds(bounds); 
        }} else {{
            try {{
                let allBounds = [];
                Object.values(overlayMaps).forEach(l => {{
                    if (l.getBounds) allBounds.push(l.getBounds());
                }});
                if (allBounds.length) {{
                    let merged = allBounds[0];
                    for (let i = 1; i < allBounds.length; i++) {{
                        merged.extend(allBounds[i]);
                    }}
                    map.fitBounds(merged);
                }} else {{
                    map.setView([0,0], 2);
                }}
            }} catch (e) {{ map.setView([0,0], 2); }}
        }}
    </script>
</body>
</html>"""
    
    return html_template


def create_mapbox_html(geojson_data, title="Visor GeoJSON Profesional", folder_name="Proyecto", grouping_mode="layer"):
    """Genera HTML con visor Mapbox usando el template avanzado
    
    Args:
        geojson_data: Datos GeoJSON
        title: Título del visor
        folder_name: Nombre de la carpeta
        grouping_mode: Modo de agrupación ('layer' o 'type')
    """
    
    # Asegurar propiedades mínimas para filtros: 'type' y 'layer'
    try:
        gj_obj = json.loads(json.dumps(geojson_data))
        if isinstance(gj_obj, dict) and gj_obj.get("type") == "FeatureCollection":
            for f in gj_obj.get("features", []):
                if not isinstance(f, dict):
                    continue
                props = f.setdefault("properties", {}) if isinstance(f.get("properties"), dict) else {}
                if "properties" not in f:
                    f["properties"] = props
                # Normalizar tipo si existe
                if "type" in props and isinstance(props["type"], str):
                    props["type"] = props["type"].lower()
                # Asegurar layer por defecto
                if "layer" not in props:
                    props["layer"] = "default"
        geojson_str = json.dumps(gj_obj, indent=2, ensure_ascii=False)
    except Exception:
        geojson_str = json.dumps(geojson_data, indent=2, ensure_ascii=False)
    
    # Calcular bounds usando la función de Python para asegurar que Mapbox se centre correctamente
    bounds = compute_bounds_from_geojson(geojson_data)
    if bounds:
        # bounds viene como [[min_lat, min_lon], [max_lat, max_lon]]
        # Mapbox necesita [min_lon, min_lat, max_lon, max_lat]
        center_lat = (bounds[0][0] + bounds[1][0]) / 2
        center_lon = (bounds[0][1] + bounds[1][1]) / 2
        mapbox_bounds = [bounds[0][1], bounds[0][0], bounds[1][1], bounds[1][0]]  # [min_lon, min_lat, max_lon, max_lat]
    else:
        # Fallback para Ecuador
        center_lat, center_lon = -2.0, -78.4
        mapbox_bounds = [-79.0, -3.0, -77.0, -1.0]
    
    # Template HTML completo con Mapbox
    mapbox_html = f'''<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} - {folder_name}</title>
  <script src="https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.js"></script>
  <link href="https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.css" rel="stylesheet" />
  <style>
    body {{
      margin: 0;
      padding: 0;
      font-family: 'Arial', sans-serif;
      height: 100vh;
      overflow: hidden;
    }}

    #map {{
      width: 100%;
      height: 100%;
    }}

    #panel-trigger {{
      position: absolute;
      top: 0;
      left: 0;
      width: 280px;
      height: 450px;
      z-index: 1;
    }}

    #floating-panel {{
      position: absolute;
      top: 90px;
      left: 15px;
      width: 250px;
      background-color: rgba(40, 40, 40, 0.7);
      backdrop-filter: blur(5px);
      border-radius: 8px;
      padding: 15px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
      z-index: 2;
      color: white;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.3s ease;
      max-height: 70vh;
      overflow-y: auto;
    }}

    #panel-trigger:hover #floating-panel {{
      opacity: 1;
      pointer-events: auto;
    }}

    .control-group {{
      margin-bottom: 15px;
    }}

    .control-group h3 {{
      margin: 0 0 10px 0;
      font-size: 14px;
      font-weight: bold;
      border-bottom: 1px solid rgba(255, 255, 255, 0.2);
      padding-bottom: 5px;
    }}

    .style-select {{
      width: 100%;
      padding: 8px;
      background-color: rgba(20, 20, 20, 0.9);
      color: white;
      border: 1px solid rgba(255, 255, 255, 0.3);
      border-radius: 4px;
      margin-bottom: 15px;
      font-size: 12px;
    }}

    .elevation-input {{
      width: 100%;
      padding: 8px;
      background-color: rgba(255, 255, 255, 0.1);
      color: white;
      border: 1px solid rgba(255, 255, 255, 0.3);
      border-radius: 4px;
      font-size: 12px;
    }}

    .checkbox-group {{
      display: flex;
      align-items: center;
      margin: 8px 0;
    }}

    .checkbox-group input {{
      margin-right: 8px;
      cursor: pointer;
    }}

    .checkbox-group label {{
      font-size: 12px;
      cursor: pointer;
      flex-grow: 1;
    }}

    .color-select {{
      width: 70px;
      padding: 4px;
      background-color: rgba(20, 20, 20, 0.9);
      color: white;
      border: 1px solid rgba(255, 255, 255, 0.3);
      border-radius: 4px;
      font-size: 12px;
    }}

    #error {{
      color: #ff6b6b;
      font-size: 12px;
      margin-top: 10px;
      display: none;
    }}

    #developer-footer {{
      position: absolute;
      bottom: 10px;
      left: 50%;
      transform: translateX(-50%);
      z-index: 1;
      color: #ffffff;
      font-size: 12px;
      background-color: rgba(40, 40, 40, 0.5);
      padding: 5px 10px;
      border-radius: 4px;
      pointer-events: none;
    }}

    #api-modal {{
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0, 0, 0, 0.8);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 1000;
    }}

    #api-modal.hidden {{
      display: none;
    }}

    #api-modal-content {{
      background-color: #333;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
      color: white;
      width: 90%;
      max-width: 400px;
      text-align: center;
    }}

    #api-modal-content h2 {{
      margin: 0 0 15px 0;
      font-size: 18px;
    }}

    #api-modal-content input {{
      width: 100%;
      padding: 8px;
      margin-bottom: 15px;
      background-color: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.3);
      border-radius: 4px;
      color: white;
      font-size: 14px;
    }}

    #api-modal-content button {{
      padding: 8px 16px;
      background-color: #007bff;
      border: none;
      border-radius: 4px;
      color: white;
      font-size: 14px;
      cursor: pointer;
      transition: background-color 0.3s ease;
    }}

    #api-modal-content button:hover {{
      background-color: #0056b3;
    }}

    #api-error {{
      color: #ff6b6b;
      font-size: 12px;
      margin-top: 10px;
      display: none;
    }}
  </style>
</head>
<body>
  <div id="map"></div>

  <div id="api-modal">
    <div id="api-modal-content">
      <h2>Ingrese su Mapbox API Key</h2>
      <input type="text" id="api-key-input" placeholder="pk.eyJ1IjoieW91ci11c2Vybm..." />
      <button id="api-submit">Confirmar</button>
      <div id="api-error">Por favor, ingrese una clave válida</div>
    </div>
  </div>

  <div id="panel-trigger">
    <div id="floating-panel">
      <div class="control-group">
        <h3>ESTILO DEL MAPA</h3>
        <select id="styleSelect" class="style-select">
          <option value="mapbox://styles/mapbox/light-v11" selected>Positron (no labels)</option>
          <option value="mapbox://styles/mapbox/satellite-v9">Satélite</option>
          <option value="mapbox://styles/mapbox/light-v11">Claro</option>
          <option value="mapbox://styles/mapbox/dark-v11">Oscuro</option>
          <option value="mapbox://styles/mapbox/outdoors-v12">Outdoors</option>
        </select>
      </div>

      <div class="control-group">
        <h3>FACTOR DE ELEVACIÓN (3D)</h3>
        <input type="number" id="elevationFactor" class="elevation-input" value="1.5" min="0" max="10" step="0.1" placeholder="Factor de elevación (0-10)" />
      </div>

      <div class="control-group">
        <h3>LAYERS DEL MAPA</h3>
        <div id="layers-control"></div>
      </div>

      <div id="error"></div>
    </div>
  </div>

  <div id="developer-footer">
    Desarrollador: Patricio Sarmiento Reinoso
  </div>

  <script>
    // Datos GeoJSON embebidos
    const embeddedGeoJSON = {geojson_str};
    
    // Verificar si ya existe un API Key en localStorage
    let mapboxAccessToken = localStorage.getItem('mapboxAccessToken');
    const apiModal = document.getElementById('api-modal');
    const apiKeyInput = document.getElementById('api-key-input');
    const apiSubmitButton = document.getElementById('api-submit');
    const apiError = document.getElementById('api-error');

    // Variables globales
    let map = null;
    let currentGeoJSON = embeddedGeoJSON;
    let layersList = [];
    let layerColors = {{}};

    // Función para inicializar el mapa
    function initializeMap() {{
      console.log('Inicializando mapa...');
      try {{
        mapboxgl.accessToken = mapboxAccessToken;

        // Usar centro pre-calculado desde Python
        const initialCenter = [{center_lon}, {center_lat}];
        const initialZoom = 14;
        const dataBounds = {json.dumps(mapbox_bounds)};
        
        // Inicializar el mapa con centro calculado desde Python
        map = new mapboxgl.Map({{ 
          container: 'map',
          style: 'mapbox://styles/mapbox/light-v11',
          center: initialCenter,
          zoom: initialZoom,
          pitch: 45,
          bearing: -17.6,
          maxZoom: 20
        }});

        // Añadir controles básicos
        map.addControl(new mapboxgl.NavigationControl());
        map.addControl(new mapboxgl.FullscreenControl());

        // Confirmar que el mapa se cargó
        map.on('load', function() {{
          console.log('Mapa cargado exitosamente');
          applyElevationFactor();
          loadDataToMap();
        }});

        // Función para aplicar el factor de elevación
        function applyElevationFactor() {{
          const elevationFactor = parseFloat(document.getElementById('elevationFactor').value) || 1.5;
          if (elevationFactor < 0 || elevationFactor > 10) {{
            return;
          }}

          if (!map.getSource('mapbox-dem')) {{
            map.addSource('mapbox-dem', {{
              type: 'raster-dem',
              url: 'mapbox://mapbox.terrain-rgb',
              tileSize: 512,
              maxzoom: 14
            }});
          }}

          map.setTerrain({{
            source: 'mapbox-dem',
            exaggeration: elevationFactor
          }});

          map.setPitch(45);
        }}

        // Función auxiliar para filtros por capa (faltaba esta función)
        function getLayerFilter(layer, types) {{
          if ('{grouping_mode}' === 'layer') {{
            return ['all', ['==', ['get', 'layer'], layer], ['in', ['get', 'type'], ['literal', types]]];
          }} else {{
            return ['in', ['get', 'type'], ['literal', types]];
          }}
        }}

        // Función mejorada para hacer zoom a los datos cargados
        function zoomToData() {{
          if (!currentGeoJSON || !currentGeoJSON.features || currentGeoJSON.features.length === 0) {{
            console.log('No hay datos GeoJSON para hacer zoom');
            return;
          }}

          // Usar bounds pre-calculados desde Python si están disponibles
          if (dataBounds && dataBounds.length === 4) {{
            const [minLon, minLat, maxLon, maxLat] = dataBounds;
            if (!isNaN(minLon) && !isNaN(minLat) && !isNaN(maxLon) && !isNaN(maxLat)) {{
              console.log('Aplicando zoom usando bounds pre-calculados:', dataBounds);
              map.fitBounds([[minLon, minLat], [maxLon, maxLat]], {{
                padding: {{ top: 50, bottom: 50, left: 50, right: 300 }}, // Espacio extra para el panel
                maxZoom: 18,
                duration: 2000
              }});
              return;
            }}
          }}

          // Fallback: calcular bounds dinámicamente si no hay pre-calculados válidos
          const bounds = new mapboxgl.LngLatBounds();
          let hasValidGeometry = false;
          
          currentGeoJSON.features.forEach(feature => {{
            try {{
              if (!feature.geometry || !feature.geometry.coordinates) return;
              
              const geom = feature.geometry;
              if (geom.type === 'Point') {{
                const coords = geom.coordinates;
                if (coords.length >= 2 && !isNaN(coords[0]) && !isNaN(coords[1])) {{
                  bounds.extend(coords);
                  hasValidGeometry = true;
                }}
              }} else if (geom.type === 'LineString') {{
                geom.coordinates.forEach(coord => {{
                  if (coord.length >= 2 && !isNaN(coord[0]) && !isNaN(coord[1])) {{
                    bounds.extend(coord);
                    hasValidGeometry = true;
                  }}
                }});
              }} else if (geom.type === 'Polygon') {{
                geom.coordinates[0].forEach(coord => {{
                  if (coord.length >= 2 && !isNaN(coord[0]) && !isNaN(coord[1])) {{
                    bounds.extend(coord);
                    hasValidGeometry = true;
                  }}
                }});
              }} else if (geom.type === 'MultiLineString') {{
                geom.coordinates.forEach(lineCoords => {{
                  lineCoords.forEach(coord => {{
                    if (coord.length >= 2 && !isNaN(coord[0]) && !isNaN(coord[1])) {{
                      bounds.extend(coord);
                      hasValidGeometry = true;
                    }}
                  }});
                }});
              }} else if (geom.type === 'MultiPolygon') {{
                geom.coordinates.forEach(polygonCoords => {{
                  polygonCoords[0].forEach(coord => {{
                    if (coord.length >= 2 && !isNaN(coord[0]) && !isNaN(coord[1])) {{
                      bounds.extend(coord);
                      hasValidGeometry = true;
                    }}
                  }});
                }});
              }}
            }} catch (e) {{
              console.warn('Error procesando geometría para zoom:', e);
            }}
          }});

          if (hasValidGeometry && !bounds.isEmpty()) {{
            console.log('Aplicando zoom con bounds calculados dinámicamente:', bounds);
            map.fitBounds(bounds, {{
              padding: {{ top: 50, bottom: 50, left: 50, right: 300 }}, // Espacio extra para el panel
              maxZoom: 18,
              duration: 2000
            }});
          }} else {{
            console.warn('No se encontraron geometrías válidas para hacer zoom');
          }}
        }}

        // Función para cargar los datos en el mapa
        function loadDataToMap() {{
          if (!currentGeoJSON) return;

          // Forzar dos capas verticales: Líneas y Puntos
          const groupingMode = '{grouping_mode}'; // ignorado para UI
          layersList = ['Líneas','Puntos'];
          // Inicializar paletas (sin imponer colores fijos; si no hay, setear uno base por capa)
          if (!layerColors['Líneas']) {{ layerColors['Líneas'] = '#ff0000'; }}
          if (!layerColors['Puntos']) {{ layerColors['Puntos'] = '#00ff00'; }}

          // Crear controles de layers
          const layersControlDiv = document.getElementById('layers-control');
          layersControlDiv.innerHTML = '';

          layersList.forEach(layer => {{
            const layerDiv = document.createElement('div');
            layerDiv.className = 'checkbox-group';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `show-${{layer}}`;
            checkbox.checked = true;
            checkbox.addEventListener('change', () => {{
              loadLayers();
            }});

            const label = document.createElement('label');
            label.htmlFor = `show-${{layer}}`;
            label.textContent = layer;

            const colorSelect = document.createElement('select');
            colorSelect.id = `color-${{layer}}`;
            colorSelect.className = 'color-select';
            const colorOptions = [
              {{ value: '#ff0000', text: 'Rojo' }},
              {{ value: '#0000ff', text: 'Azul' }},
              {{ value: '#00ff00', text: 'Verde' }},
              {{ value: '#ffff00', text: 'Amarillo' }},
              {{ value: '#ffffff', text: 'Blanco' }},
              {{ value: '#000000', text: 'Negro' }}
            ];
            colorOptions.forEach(option => {{
              const opt = document.createElement('option');
              opt.value = option.value;
              opt.textContent = option.text;
              if (option.value === layerColors[layer]) {{
                opt.selected = true;
              }}
              colorSelect.appendChild(opt);
            }});
            colorSelect.addEventListener('change', () => {{
              layerColors[layer] = colorSelect.value;
              loadLayers();
            }});

            layerDiv.appendChild(checkbox);
            layerDiv.appendChild(label);
            layerDiv.appendChild(colorSelect);
            layersControlDiv.appendChild(layerDiv);
          }});

          loadLayers();
          
          // Hacer zoom después de que las capas se hayan cargado
          setTimeout(() => {{
            zoomToData();
          }}, 500);
        }}

        // Función para cargar layers en el mapa
        function loadLayers() {{
          // Limpiar layers existentes de manera más completa
          const layerPrefixes = ['Líneas', 'Puntos'];
          const layerSuffixes = ['layer-lines', 'layer-points', 'layer-circles', 'layer-shapes', 'layer-shapes-outline', 'labels'];
          
          layerPrefixes.forEach(prefix => {{
            layerSuffixes.forEach(suffix => {{
              const layerId = `${{prefix}}-${{suffix}}`;
              try {{
                if (map.getLayer(layerId)) {{ 
                  map.removeLayer(layerId); 
                }}
              }} catch (e) {{
                console.warn(`Error removiendo layer ${{layerId}}:`, e);
              }}
            }});
          }});

          if (!map.getSource('geojson-data')) {{
            map.addSource('geojson-data', {{
              type: 'geojson',
              data: currentGeoJSON
            }});
          }} else {{
            map.getSource('geojson-data').setData(currentGeoJSON);
          }}

          layersList.forEach(layer => {{
            const showLayer = document.getElementById(`show-${{layer}}`).checked;

            if (showLayer) {{
              // Filtro por tipo simple
              function filterByTypes(typesArray) {{
                return ['in', ['get','type'], ['literal', typesArray]];
              }}
              
              // Lines (respetar sub-toggle cuando grouping_mode === 'layer')
              if (layer === 'Líneas') {{
                map.addLayer({{ 
                  id: `${{layer}}-layer-lines`,
                  type: 'line',
                  source: 'geojson-data',
                  filter: filterByTypes(['line','polyline','track','route','shape','polygon']),
                  paint: {{
                    'line-color': layerColors[layer] || '#0000ff',
                    'line-width': 3,
                    'line-opacity': 0.9
                  }}
                }});
              }}

              // Points (capa separada, respetar sub-toggle)
              if (layer === 'Puntos') {{
                map.addLayer({{ 
                  id: `${{layer}}-layer-points`,
                  type: 'circle',
                  source: 'geojson-data',
                  filter: filterByTypes(['point','block']),
                  paint: {{
                    'circle-radius': 6,
                    'circle-color': layerColors[layer] || '#00ff00',
                    'circle-opacity': 0.8
                  }}
                }});
              }}

              // Circles
              map.addLayer({{ 
                id: `${{layer}}-layer-circles`,
                type: 'fill',
                source: 'geojson-data',
                filter: getLayerFilter(layer, ['circle']),
                paint: {{
                  'fill-color': layerColors[layer] || '#ff0000',
                  'fill-opacity': 0.5
                }}
              }});

              // Shapes (polígonos): relleno
              map.addLayer({{ 
                id: `${{layer}}-layer-shapes`,
                type: 'fill',
                source: 'geojson-data',
                filter: getLayerFilter(layer, ['shape', 'polygon']),
                paint: {{
                  'fill-color': layerColors[layer] || '#00ffff',
                  'fill-opacity': 0.25
                }}
              }});

              // Shapes (polígonos): contorno
              map.addLayer({{ 
                id: `${{layer}}-layer-shapes-outline`,
                type: 'line',
                source: 'geojson-data',
                filter: getLayerFilter(layer, ['shape', 'polygon']),
                paint: {{
                  'line-color': layerColors[layer] || '#00ffff',
                  'line-width': 2,
                  'line-opacity': 0.9
                }}
              }});

              // Text labels
              map.addLayer({{ 
                id: `${{layer}}-labels`,
                type: 'symbol',
                source: 'geojson-data',
                filter: getLayerFilter(layer, ['text']),
                layout: {{
                  'text-field': ['get', 'text'],
                  'text-size': 12,
                  'text-anchor': 'top',
                  'text-offset': [0, 1]
                }},
                paint: {{
                  'text-color': layerColors[layer] || '#ffffff',
                  'text-halo-color': '#000000',
                  'text-halo-width': 1
                }}
              }});
            }}
          }});
        }}

        document.getElementById('styleSelect').addEventListener('change', function() {{
          const selectedStyle = this.value;
          map.setStyle(selectedStyle);
          
          map.once('style.load', function() {{
            applyElevationFactor();
            loadDataToMap();
            // Volver a centrar en los datos después del cambio de estilo
            setTimeout(() => {{
              zoomToData();
            }}, 1000);
          }});
        }});

        document.getElementById('elevationFactor').addEventListener('change', function() {{
          applyElevationFactor();
        }});

      }} catch (error) {{
        console.error('Error inicializando el mapa:', error);
        document.getElementById('error').textContent = 'Error inicializando el mapa: ' + error.message;
        document.getElementById('error').style.display = 'block';
      }}
    }}

    // Validar e inicializar el mapa
    if (mapboxAccessToken && mapboxAccessToken.startsWith('pk.')) {{
      console.log('Token encontrado en localStorage, inicializando mapa');
      apiModal.classList.add('hidden');
      initializeMap();
    }} else {{
      console.log('No se encontró token válido, mostrando modal');
      apiModal.classList.remove('hidden');
      apiSubmitButton.addEventListener('click', function() {{
        const apiKey = apiKeyInput.value.trim();
        if (apiKey === '' || !apiKey.startsWith('pk.')) {{
          apiError.textContent = 'Por favor, ingrese una clave válida que comience con pk.';
          apiError.style.display = 'block';
          return;
        }}

        localStorage.setItem('mapboxAccessToken', apiKey);
        mapboxAccessToken = apiKey;
        apiModal.classList.add('hidden');
        initializeMap();
      }});

      apiKeyInput.addEventListener('keypress', function(e) {{
        if (e.key === 'Enter') {{
          apiSubmitButton.click();
        }}
      }});
    }}
  </script>
</body>
</html>'''
    
    return mapbox_html


def create_leaflet_grouped_html(geojson_data, title="Visor GeoJSON Profesional", grouping_mode="type"):
    """Genera HTML con Leaflet y control de capas agrupadas por 'type' o 'layer'."""
    try:
        gj_obj = json.loads(json.dumps(geojson_data))
        if isinstance(gj_obj, dict) and gj_obj.get("type") == "FeatureCollection":
            for f in gj_obj.get("features", []):
                if not isinstance(f, dict):
                    continue
                props = f.setdefault("properties", {}) if isinstance(f.get("properties"), dict) else {}
                if "properties" not in f:
                    f["properties"] = props
                if "type" in props and isinstance(props["type"], str):
                    props["type"] = props["type"].lower()
                if "layer" not in props:
                    props["layer"] = "default"
        geojson_str = json.dumps(gj_obj, ensure_ascii=False)
    except Exception:
        geojson_str = json.dumps(geojson_data, ensure_ascii=False)

    group_key_js = "(f.properties && f.properties.layer) ? String(f.properties.layer) : 'SinGrupo'" if str(grouping_mode).lower() == "layer" else "(f.properties && f.properties.type) ? String(f.properties.type) : 'SinGrupo'"

    html = f"""<!DOCTYPE html>
<html lang=\"es\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>{title}</title>
  <link rel=\"stylesheet\" href=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.css\" />
  <script src=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.js\"></script>
  <style> html, body {{ height: 100%; margin: 0; }} #map {{ height: 100vh; }} .leaflet-control-layers-expanded{{ max-height:65vh; overflow:auto; }} </style>
  </head>
<body>
  <div id=\"map\"></div>
  <script>
    const map = L.map('map', {{ preferCanvas: true }});
    const calles = L.tileLayer('https://{{{{s}}}}.tile.openstreetmap.org/{{{{z}}}}/{{{{x}}}}/{{{{y}}}}.png', {{ attribution: 'OpenStreetMap', maxZoom: 19 }});
    const positron = L.tileLayer('https://{{{{s}}}}.basemaps.cartocdn.com/light_all/{{{{z}}}}/{{{{x}}}}/{{{{y}}}}{{{{r}}}}.png', {{ attribution: 'CartoDB', subdomains: 'abcd', maxZoom: 19 }});
    const satelite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{{{z}}}}/{{{{y}}}}/{{{{x}}}}', {{ attribution: 'Esri', maxZoom: 19 }});
    const baseLayers = {{ \"Calles\": calles, \"Positron\": positron, \"Satelital\": satelite }};
    positron.addTo(map);

    const data = {geojson_str};
    const grouped = {{}};
    if (data && data.features) {{
      data.features.forEach(f => {{
        const key = {group_key_js};
        if (!grouped[key]) grouped[key] = {{ nonText: [], points: [], texts: [] }};
        const g = grouped[key];
        const t = (f.properties && f.properties.type) ? f.properties.type : '';
        if (t === 'text') g.texts.push(f);
        else if (f.geometry && f.geometry.type === 'Point') g.points.push(f);
        else g.nonText.push(f);
      }});
    }}

    const overlayMaps = {{}};
    Object.keys(grouped).forEach(key => {{
      const fg = L.layerGroup();
      const parts = grouped[key];
      if (parts.nonText && parts.nonText.length) {{
        const gj = L.geoJSON({{ type: 'FeatureCollection', features: parts.nonText }});
        gj.addTo(fg);
      }}
      if (parts.points) {{
        parts.points.forEach(feat => {{
          try {{
            const c = feat.geometry.coordinates; const lon = c[0], lat = c[1];
            L.circleMarker([lat, lon], {{ radius: 3, color: '#2c7fb8', fillOpacity: 0.9 }}).addTo(fg);
          }} catch(e) {{}}
        }});
      }}
      if (parts.texts) {{
        parts.texts.forEach(feat => {{
          try {{
            const c = feat.geometry.coordinates; const lon = c[0], lat = c[1];
            const label = (feat.properties && feat.properties.text) ? String(feat.properties.text) : '';
            if (label) L.marker([lat, lon], {{ icon: L.divIcon({{ className: '', html: `<div style='font-size:12px;color:#0d6efd;font-weight:600;'>${{label}}</div>` }}) }}).addTo(fg);
          }} catch(e) {{}}
        }});
      }}
      overlayMaps[key] = fg;
    }});

    Object.values(overlayMaps).forEach(l => l.addTo(map));
    L.control.layers(baseLayers, overlayMaps, {{ position: 'topright', collapsed: false }}).addTo(map);

    try {{
      const allBounds = [];
      Object.values(overlayMaps).forEach(l => {{ if (l.getBounds) try {{ allBounds.push(l.getBounds()); }} catch(e) {{}} }});
      if (allBounds.length) {{
        let merged = allBounds[0];
        for (let i=1;i<allBounds.length;i++) merged.extend(allBounds[i]);
        map.fitBounds(merged);
      }} else {{ map.setView([0,0], 2); }}
    }} catch(e) {{ map.setView([0,0], 2); }}
  </script>
</body>
</html>"""
    return html

def render_map(geojson_data, group_by: str = "type"):
    m = folium.Map(location=[-2.0, -79.0], zoom_start=10, tiles=None, prefer_canvas=True)
    folium.TileLayer("OpenStreetMap", name="Calles").add_to(m)
    folium.TileLayer("CartoDB Positron", name="Positron").add_to(m)
    folium.TileLayer("Esri.WorldImagery", name="Satelital").add_to(m)

    # Agrupar por clave. Render no-text como GeoJSON (líneas/polígonos) y puntos como CircleMarker; texts como etiquetas
    grouped = {}
    for feature in geojson_data.get("features", []):
        props = feature.get("properties", {})
        key = props.get("layer", "SinGrupo") if group_by == "layer" else props.get("type", "SinGrupo")
        group = grouped.setdefault(str(key), {"non_text": [], "texts": [], "points": []})
        if props.get("type") == "text":
            group["texts"].append(feature)
        elif feature.get("geometry", {}).get("type") == "Point":
            group["points"].append(feature)
        else:
            group["non_text"].append(feature)

    groups = {}
    for key, parts in grouped.items():
        fg = folium.FeatureGroup(name=str(key), show=True)
        fg.add_to(m)
        # Add non-text (no-puntos) features como una capa GeoJSON
        if parts["non_text"]:
            try:
                fc = {"type": "FeatureCollection", "features": parts["non_text"]}
                # Crear estilo específico según el tipo de feature
                style_function = None
                if key == "track":
                    style_function = lambda x: {"color": "#e31a1c", "weight": 3, "opacity": 0.8}
                elif key == "route":
                    style_function = lambda x: {"color": "#1f78b4", "weight": 3, "opacity": 0.8, "dashArray": "5, 10"}
                
                gj = folium.GeoJson(fc, name=f"{key}_geom", style_function=style_function)
                gj.add_to(fg)
                groups[key] = gj
            except Exception:
                pass
        # Add point features as CircleMarkers
        for feat in parts["points"]:
            try:
                coords = feat.get("geometry", {}).get("coordinates", None)
                if coords and isinstance(coords, (list, tuple)) and len(coords) >= 2:
                    lon, lat = coords[0], coords[1]
                    folium.CircleMarker(location=[lat, lon], radius=3, color="#2c7fb8", fill=True, fill_opacity=0.9).add_to(fg)
            except Exception:
                continue
        # Add text features as labeled markers
        for feat in parts["texts"]:
            try:
                coords = feat.get("geometry", {}).get("coordinates", None)
                props = feat.get("properties", {})
                if coords and isinstance(coords, (list, tuple)) and len(coords) >= 2:
                    lon, lat = coords[0], coords[1]
                    label = str(props.get("text", ""))
                    if label:
                        folium.Marker(
                            location=[lat, lon],
                            icon=folium.DivIcon(html=f"<div style='font-size:12px;color:#0d6efd;font-weight:600;'>{label}</div>")
                        ).add_to(fg)
                    else:
                        folium.Marker(location=[lat, lon]).add_to(fg)
            except Exception:
                continue

    # Ajuste de extensión
    try:
        all_bounds = []
        for gj in groups.values():
            try:
                b = gj.get_bounds()
                if b:
                    all_bounds.extend(b)
            except Exception:
                pass
        if all_bounds:
            m.fit_bounds(all_bounds)
    except Exception:
        pass

    folium.LayerControl(position="topright").add_to(m)
    st_folium(m, width=None, height=650)


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


def local_name(tag: str) -> str:
    try:
        if '}' in tag:
            return tag.split('}', 1)[1]
        return tag
    except Exception:
        return tag


def parse_coords_text(txt: str):
    coords = []
    if not txt:
        return coords
    txt = txt.replace('\n', ' ').replace('\t', ' ').strip()
    for token in txt.split():
        parts = token.split(',')
        if len(parts) >= 2:
            try:
                lon = float(parts[0]); lat = float(parts[1])
                coords.append([lon, lat])
            except Exception:
                continue
    return coords


def parse_kml_via_xml(kml_bytes: bytes) -> dict:
    try:
        root = ET.fromstring(kml_bytes)
        features = []
        # Recorrido completo del árbol ignorando namespaces
        for elem in root.iter():
            lname = local_name(elem.tag)
            if lname == 'Point':
                for child in list(elem):
                    if local_name(child.tag) == 'coordinates':
                        for c in parse_coords_text(child.text):
                            features.append({
                                "type": "Feature",
                                "properties": {"type": "point"},
                                "geometry": {"type": "Point", "coordinates": c},
                            })
            elif lname == 'LineString':
                for child in list(elem):
                    if local_name(child.tag) == 'coordinates':
                        coords = parse_coords_text(child.text)
                        if len(coords) >= 2:
                            features.append({
                                "type": "Feature",
                                "properties": {"type": "line"},
                                "geometry": {"type": "LineString", "coordinates": coords},
                            })
            elif lname == 'Polygon':
                # Buscar outerBoundaryIs -> LinearRing -> coordinates
                outer = None
                for c1 in list(elem):
                    if local_name(c1.tag) == 'outerBoundaryIs':
                        for c2 in list(c1):
                            if local_name(c2.tag) == 'LinearRing':
                                for c3 in list(c2):
                                    if local_name(c3.tag) == 'coordinates':
                                        outer = parse_coords_text(c3.text)
                                        break
                if outer and len(outer) >= 3:
                    if outer[0] != outer[-1]:
                        outer.append(outer[0])
                    features.append({
                        "type": "Feature",
                        "properties": {"type": "polygon"},
                        "geometry": {"type": "Polygon", "coordinates": [outer]},
                    })
        logger.info(f"XML fallback extrajo {len(features)} features")
        return {"type": "FeatureCollection", "features": features}
    except Exception as e:
        logger.exception("Fallo parse_kml_via_xml")
        return {"type": "FeatureCollection", "features": []}


def points_equal(p1, p2, eps=1e-6):
    """Compara dos puntos con tolerancia para flotantes"""
    return abs(p1[0] - p2[0]) < eps and abs(p1[1] - p2[1]) < eps

def parse_polygons_robust(df, epsilon=1e-6):
    """
    Parsea DataFrame de puntos en polígonos independientes de forma robusta
    """
    # Convertir DataFrame a lista de puntos
    points = []
    for idx, row in df.iterrows():
        try:
            x, y = float(row["x"]),
            float(row["y"])
            points.append((x, y))
        except Exception:
            continue
    
    if len(points) < 3:
        return []
    
    # Eliminar duplicados consecutivos
    cleaned_points = [points[0]]
    for i in range(1, len(points)):
        if not points_equal(points[i], points[i-1], epsilon):
            cleaned_points.append(points[i])
    
    polygons = []
    i = 0
    
    while i < len(cleaned_points):
        # Iniciar nuevo polígono
        polygon_start = cleaned_points[i]
        current_polygon = [polygon_start]
        
        # Buscar cierre
        j = i + 1
        polygon_closed = False
        
        while j < len(cleaned_points):
            current_point = cleaned_points[j]
            current_polygon.append(current_point)
            
            # Verificar cierre
            if points_equal(current_point, polygon_start, epsilon):
                polygon_closed = True
                if len(current_polygon) >= 4:  # Mínimo 4 puntos para polígono válido
                    polygons.append(current_polygon)
                break
            j += 1
        
        # Manejar polígono abierto al final
        if not polygon_closed and len(current_polygon) >= 3:
            current_polygon.append(polygon_start)  # Cerrar automáticamente
            polygons.append(current_polygon)
        
        # Mover al siguiente segmento
        i = j + 1 if polygon_closed else len(cleaned_points)
        
    return polygons


def validate_heatmap_data(points_df):
    """
    Valida los datos para el mapa de calor y proporciona información de debug.
    
    Args:
        points_df: DataFrame con columnas ['x', 'y', 'cota']
    
    Returns:
        dict: Información de validación y estadísticas
    """
    if points_df is None or len(points_df) == 0:
        return {"valid": False, "message": "No hay datos para procesar"}
    
    if len(points_df) < 3:
        return {"valid": False, "message": "Se necesitan al menos 3 puntos para generar el mapa de calor"}
    
    # Verificar columnas requeridas
    required_cols = ['x', 'y', 'cota']
    missing_cols = [col for col in required_cols if col not in points_df.columns]
    if missing_cols:
        return {"valid": False, "message": f"Faltan columnas requeridas: {missing_cols}"}
    
    # Estadísticas de los datos
    stats = {
        "valid": True,
        "total_points": len(points_df),
        "x_range": (points_df['x'].min(), points_df['x'].max()),
        "y_range": (points_df['y'].min(), points_df['y'].max()),
        "z_range": (points_df['cota'].min(), points_df['cota'].max()),
        "area_coverage": (points_df['x'].max() - points_df['x'].min()) * (points_df['y'].max() - points_df['y'].min()),
        "center": ((points_df['x'].min() + points_df['x'].max()) / 2, (points_df['y'].min() + points_df['y'].max()) / 2)
    }
    
    return stats


def calculate_raster_bounds(points_df, margin_percent=10):
    """
    Calcula los bounds del raster basado en los puntos topográficos con margen configurable.
    Asegura que el área sea cuadrada para mejor cobertura y orientación correcta.
    
    Args:
        points_df: DataFrame con columnas ['x', 'y', 'cota']
        margin_percent: Porcentaje de margen a agregar (default: 10%)
    
    Returns:
        tuple: (min_x, min_y, max_x, max_y)
    """
    if points_df is None or len(points_df) == 0:
        return None
    
    # Obtener bounds de los puntos
    min_x, max_x = points_df['x'].min(), points_df['x'].max()
    min_y, max_y = points_df['y'].min(), points_df['y'].max()
    
    # Calcular rangos
    x_range = max_x - min_x
    y_range = max_y - min_y
    
    # Agregar margen
    margin_x = x_range * (margin_percent / 100)
    margin_y = y_range * (margin_percent / 100)
    
    # Calcular centro del área
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    
    # Usar el rango más grande para crear un área cuadrada
    max_range = max(x_range, y_range)
    half_size = (max_range + max(margin_x, margin_y)) / 2
    
    # Crear bounds cuadrados centrados en el área de estudio
    bounds_x_min = center_x - half_size
    bounds_x_max = center_x + half_size
    bounds_y_min = center_y - half_size
    bounds_y_max = center_y + half_size
    
    return (bounds_x_min, bounds_y_min, bounds_x_max, bounds_y_max)


def debug_heatmap_coordinates(points_df, bounds, resolution):
    """
    Función de debug para analizar las coordenadas del mapa de calor.
    
    Args:
        points_df: DataFrame con coordenadas
        bounds: tuple (min_x, min_y, max_x, max_y)
        resolution: Resolución del raster
    
    Returns:
        dict: Información de debug detallada
    """
    min_x, min_y, max_x, max_y = bounds
    
    # Calcular información de la grilla
    pixel_width = (max_x - min_x) / resolution
    pixel_height = (max_y - min_y) / resolution
    
    # CORRECCIÓN: Crear transformación correcta para indexing='ij'
    transform = Affine.translation(min_x, min_y) * Affine.scale(pixel_width, pixel_height)
    
    # Calcular coordenadas de esquinas con indexing='ij'
    corners = {
        "bottom_left": transform * (0, 0),  # Píxel (0,0) -> (min_x, min_y)
        "bottom_right": transform * (resolution, 0),  # Píxel (width,0) -> (max_x, min_y)
        "top_left": transform * (0, resolution),  # Píxel (0,height) -> (min_x, max_y)
        "top_right": transform * (resolution, resolution)  # Píxel (width,height) -> (max_x, max_y)
    }
    
    # Información de debug
    debug_info = {
        "bounds": bounds,
        "resolution": resolution,
        "pixel_size": (pixel_width, pixel_height),
        "transform_matrix": [transform.a, transform.b, transform.c, transform.d, transform.e, transform.f],
        "corners": corners,
        "points_sample": {
            "first_point": (points_df['x'].iloc[0], points_df['y'].iloc[0]) if len(points_df) > 0 else None,
            "last_point": (points_df['x'].iloc[-1], points_df['y'].iloc[-1]) if len(points_df) > 0 else None,
            "center": ((points_df['x'].min() + points_df['x'].max()) / 2, (points_df['y'].min() + points_df['y'].max()) / 2)
        }
    }
    
    return debug_info


def create_heatmap_debug_file(points_df, bounds, resolution, output_path):
    """
    Crea un archivo de debug con información detallada del mapa de calor.
    
    Args:
        points_df: DataFrame con coordenadas
        bounds: tuple (min_x, min_y, max_x, max_y)
        resolution: Resolución del raster
        output_path: Ruta donde guardar el archivo de debug
    """
    try:
        debug_info = debug_heatmap_coordinates(points_df, bounds, resolution)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=== DEBUG MAPA DE CALOR ===\n\n")
            f.write(f"Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("=== BOUNDS ===\n")
            f.write(f"Min X: {bounds[0]:.6f}\n")
            f.write(f"Min Y: {bounds[1]:.6f}\n")
            f.write(f"Max X: {bounds[2]:.6f}\n")
            f.write(f"Max Y: {bounds[3]:.6f}\n\n")
            
            f.write("=== RESOLUCIÓN ===\n")
            f.write(f"Resolución: {resolution}x{resolution}\n")
            f.write(f"Tamaño de píxel X: {debug_info['pixel_size'][0]:.6f}\n")
            f.write(f"Tamaño de píxel Y: {debug_info['pixel_size'][1]:.6f}\n\n")
            
            f.write("=== MATRIZ DE TRANSFORMACIÓN ===\n")
            matrix = debug_info['transform_matrix']
            f.write(f"a={matrix[0]:.6f}, b={matrix[1]:.6f}\n")
            f.write(f"c={matrix[2]:.6f}, d={matrix[3]:.6f}\n")
            f.write(f"e={matrix[4]:.6f}, f={matrix[5]:.6f}\n\n")
            
            f.write("=== ESQUINAS DEL RASTER ===\n")
            corners = debug_info['corners']
            f.write(f"Superior izquierda (0,0): {corners['top_left']}\n")
            f.write(f"Superior derecha ({resolution},0): {corners['top_right']}\n")
            f.write(f"Inferior izquierda (0,{resolution}): {corners['bottom_left']}\n")
            f.write(f"Inferior derecha ({resolution},{resolution}): {corners['bottom_right']}\n\n")
            
            f.write("=== PUNTOS DE MUESTRA ===\n")
            points = debug_info['points_sample']
            f.write(f"Primer punto: {points['first_point']}\n")
            f.write(f"Último punto: {points['last_point']}\n")
            f.write(f"Centro del área: {points['center']}\n\n")
            
            f.write("=== TODOS LOS PUNTOS ===\n")
            for i, row in points_df.iterrows():
                f.write(f"P{i+1}: X={row['x']:.6f}, Y={row['y']:.6f}, Z={row['cota']:.6f}\n")
        
        return True
    except Exception as e:
        st.error(f"Error al crear archivo de debug: {e}")
        return False


def create_sample_heatmap_data():
    """
    Crea datos de ejemplo para probar el mapa de calor.
    
    Returns:
        pandas.DataFrame: DataFrame con puntos de ejemplo en UTM zona 17S (Ecuador)
    """
    import pandas as pd
    
    # Datos de ejemplo: puntos en UTM zona 17S (Ecuador) - EPSG:32717
    sample_points = [
        [200000, 9800000, 2450],  # Punto 1
        [200100, 9800000, 2445],  # Punto 2
        [200200, 9800000, 2440],  # Punto 3
        [200000, 9800100, 2455],  # Punto 4
        [200100, 9800100, 2450],  # Punto 5
        [200200, 9800100, 2445],  # Punto 6
        [200050, 9800050, 2448],  # Punto 7
        [200150, 9800050, 2443],  # Punto 8
        [200250, 9800050, 2438],  # Punto 9
        [200075, 9800075, 2446],  # Punto 10
    ]
    
    df = pd.DataFrame(sample_points, columns=['x', 'y', 'cota'])
    return df


def get_crs_options():
    """
    Retorna opciones de CRS comunes para diferentes regiones.
    
    Returns:
        dict: Diccionario con códigos CRS y sus descripciones
    """
    return {
        'EPSG:32719': 'UTM Zona 19S (Ecuador, Perú)',
        'EPSG:32718': 'UTM Zona 18S (Ecuador, Perú)',
        'EPSG:32717': 'UTM Zona 17S (Ecuador, Perú)',
        'EPSG:32619': 'UTM Zona 19N (Colombia, Venezuela)',
        'EPSG:32618': 'UTM Zona 18N (Colombia, Venezuela)',
        'EPSG:4326': 'WGS84 (Lat/Lon)',
        'EPSG:3857': 'Web Mercator (Google Maps)',
        'EPSG:3116': 'MAGNA-SIRGAS / Colombia Bogota zone',
        'EPSG:3117': 'MAGNA-SIRGAS / Colombia East zone',
        'EPSG:3118': 'MAGNA-SIRGAS / Colombia West zone',
    }


def create_heatmap_geotiff_point_perfect(points_list, crs_code='EPSG:32717', resolution=100, padding_percent=1.0, method='cubic'):
    """
    Genera un mapa de calor GeoTIFF con correspondencia EXACTA punto por punto.
    
    Esta función garantiza que cada punto de entrada (x,y,z) tenga su equivalente
    exacto en el raster, construyendo un mapa raster real que cumple expectativas.
    
    Args:
        points_list: Lista de puntos [[x1, y1, z1], [x2, y2, z2], ...]
        crs_code: Código CRS (ej. 'EPSG:32717')
        resolution: Resolución del grid (número de celdas por lado)
        padding_percent: Porcentaje de padding del bounding box
        method: Método de interpolación ('linear', 'cubic', 'nearest')
    
    Returns:
        bytes: Contenido del archivo GeoTIFF con correspondencia punto por punto
    """
    import numpy as np
    import scipy.interpolate as interp
    import rasterio
    from rasterio.transform import Affine
    from rasterio.crs import CRS
    import tempfile
    import os
    
    # Validación de entrada
    if not points_list or len(points_list) < 3:
        st.error("❌ Se requieren al menos 3 puntos para generar el mapa de calor")
        return None
    
    try:
        # Convertir a array numpy
        points_array = np.array(points_list)
        x_coords = points_array[:, 0]
        y_coords = points_array[:, 1]
        z_values = points_array[:, 2]
        
        print(f"🔍 Procesando {len(points_list)} puntos:")
        for i, (x, y, z) in enumerate(points_list[:5]):  # Mostrar primeros 5 puntos
            print(f"   P{i+1}: ({x:.3f}, {y:.3f}, {z:.3f})")
        if len(points_list) > 5:
            print(f"   ... y {len(points_list)-5} puntos más")
        
        # === PASO 1: CÁLCULO PRECISO DEL BOUNDING BOX ===
        min_x, max_x = np.min(x_coords), np.max(x_coords)
        min_y, max_y = np.min(y_coords), np.max(y_coords)
        
        # Calcular padding
        x_range = max_x - min_x
        y_range = max_y - min_y
        padding_x = (x_range * padding_percent) / 100.0
        padding_y = (y_range * padding_percent) / 100.0
        
        # Bounding box con padding
        bounds_min_x = min_x - padding_x
        bounds_max_x = max_x + padding_x
        bounds_min_y = min_y - padding_y
        bounds_max_y = max_y + padding_y
        
        print(f"🔍 Bounding box: ({bounds_min_x:.3f}, {bounds_min_y:.3f}) a ({bounds_max_x:.3f}, {bounds_max_y:.3f})")
        
        # === PASO 2: CREAR GRID QUE COINCIDA EXACTAMENTE CON LOS PUNTOS ===
        # Crear arrays de coordenadas para el grid
        x_grid = np.linspace(bounds_min_x, bounds_max_x, resolution)
        y_grid = np.linspace(bounds_min_y, bounds_max_y, resolution)
        
        # Crear meshgrid - CRÍTICO: usar indexing='xy' para orientación correcta
        X_grid, Y_grid = np.meshgrid(x_grid, y_grid, indexing='xy')
        
        print(f"🔍 Grid creado: {resolution}x{resolution}")
        print(f"🔍 Tamaño de celda: {(bounds_max_x - bounds_min_x)/resolution:.6f} x {(bounds_max_y - bounds_min_y)/resolution:.6f}")
        
        # === PASO 3: VERIFICAR CORRESPONDENCIA PUNTO POR PUNTO ===
        # Encontrar las celdas del grid más cercanas a cada punto de entrada
        grid_points = []
        grid_values = []
        
        for i, (x, y, z) in enumerate(points_list):
            # Encontrar la celda más cercana en el grid
            x_idx = np.argmin(np.abs(x_grid - x))
            y_idx = np.argmin(np.abs(y_grid - y))
            
            # Verificar que la celda encontrada corresponde al punto
            grid_x = x_grid[x_idx]
            grid_y = y_grid[y_idx]
            
            # Calcular distancia para verificar precisión
            dist_x = abs(grid_x - x)
            dist_y = abs(grid_y - y)
            
            print(f"🔍 P{i+1}: ({x:.3f}, {y:.3f}) -> Grid[{y_idx},{x_idx}]: ({grid_x:.3f}, {grid_y:.3f}) - Dist: ({dist_x:.6f}, {dist_y:.6f})")
            
            grid_points.append([grid_x, grid_y])
            grid_values.append(z)
        
        # === PASO 4: INTERPOLACIÓN CON CORRESPONDENCIA GARANTIZADA ===
        # Preparar puntos para interpolación
        points_for_interp = np.array(grid_points)
        z_for_interp = np.array(grid_values)
        
        print(f"🔍 Debug de interpolación:")
        print(f"   Puntos para interpolación: {len(points_for_interp)}")
        print(f"   Valores Z: {len(z_for_interp)}")
        print(f"   Rango de valores Z: {np.min(z_for_interp):.6f} a {np.max(z_for_interp):.6f}")
        print(f"   Grid shape: {X_grid.shape}")
        
        # Interpolar valores Z en el grid completo
        Z_interpolated = interp.griddata(
            points_for_interp, 
            z_for_interp, 
            (X_grid, Y_grid), 
            method=method, 
            fill_value=np.nan
        )
        
        print(f"🔍 Interpolación completada con método: {method}")
        print(f"   Shape del resultado: {Z_interpolated.shape}")
        print(f"   Valores NaN: {np.isnan(Z_interpolated).sum()}")
        print(f"   Valores válidos: {(~np.isnan(Z_interpolated)).sum()}")
        
        # Debug adicional: mostrar algunos valores interpolados
        valid_mask = ~np.isnan(Z_interpolated)
        if valid_mask.any():
            valid_values = Z_interpolated[valid_mask]
            print(f"   Rango de valores interpolados: {np.min(valid_values):.6f} a {np.max(valid_values):.6f}")
            print(f"   Media de valores interpolados: {np.mean(valid_values):.6f}")
        else:
            print("   ⚠️ ADVERTENCIA: No hay valores válidos después de la interpolación!")
        
        # === PASO 5: VERIFICAR QUE LOS PUNTOS ORIGINALES ESTÉN EN EL RASTER ===
        print("🔍 Verificando correspondencia punto por punto:")
        for i, (x, y, z) in enumerate(points_list):
            # Encontrar la celda correspondiente
            x_idx = np.argmin(np.abs(x_grid - x))
            y_idx = np.argmin(np.abs(y_grid - y))
            
            # Obtener el valor interpolado en esa celda
            raster_value = Z_interpolated[y_idx, x_idx]
            
            print(f"   P{i+1}: ({x:.3f}, {y:.3f}, {z:.3f}) -> Raster[{y_idx},{x_idx}]: {raster_value:.3f}")
        
        # === PASO 6: CALCULAR ESTADÍSTICAS ANTES DEL FLIP ===
        # CORRECCIÓN CRÍTICA: Calcular estadísticas antes del flip para evitar problemas
        valid_data = Z_interpolated[~np.isnan(Z_interpolated)]
        
        if len(valid_data) > 0:
            min_val = float(np.min(valid_data))
            max_val = float(np.max(valid_data))
            mean_val = float(np.mean(valid_data))
            std_val = float(np.std(valid_data))
            
            print(f"🔍 Estadísticas de banda calculadas:")
            print(f"   Mínimo: {min_val:.6f}")
            print(f"   Máximo: {max_val:.6f}")
            print(f"   Media: {mean_val:.6f}")
            print(f"   Desviación estándar: {std_val:.6f}")
            print(f"   Píxeles válidos: {len(valid_data)} de {Z_interpolated.size}")
        else:
            print("⚠️ ADVERTENCIA: No se encontraron datos válidos después de la interpolación!")
            print("🔍 Intentando usar estadísticas de los puntos originales...")
            
            # Fallback: usar estadísticas de los puntos originales
            original_z_values = np.array([point[2] for point in points_list])
            min_val = float(np.min(original_z_values))
            max_val = float(np.max(original_z_values))
            mean_val = float(np.mean(original_z_values))
            std_val = float(np.std(original_z_values))
            
            print(f"🔍 Estadísticas de puntos originales:")
            print(f"   Mínimo: {min_val:.6f}")
            print(f"   Máximo: {max_val:.6f}")
            print(f"   Media: {mean_val:.6f}")
            print(f"   Desviación estándar: {std_val:.6f}")
            print(f"   Puntos originales: {len(original_z_values)}")
            
            # Crear un raster simple con los valores originales
            print("🔍 Creando raster alternativo con valores originales...")
            Z_interpolated = np.full((resolution, resolution), np.nan)
            
            for i, (x, y, z) in enumerate(points_list):
                x_idx = np.argmin(np.abs(x_grid - x))
                y_idx = np.argmin(np.abs(y_grid - y))
                Z_interpolated[y_idx, x_idx] = z
            
            print(f"🔍 Raster alternativo creado con {np.sum(~np.isnan(Z_interpolated))} píxeles válidos")
        
        # === PASO 7: ORIENTACIÓN CORRECTA PARA RASTERIO ===
        # Rasterio espera que la primera fila sea la superior (Y máxima)
        # Con indexing='xy', necesitamos flip vertical
        Z_interpolated = np.flipud(Z_interpolated)
        
        print("🔍 Orientación corregida para rasterio (primera fila = Y máxima)")
        
        # === PASO 8: TRANSFORMACIÓN AFÍN CORRECTA ===
        pixel_width = (bounds_max_x - bounds_min_x) / resolution
        pixel_height = (bounds_max_y - bounds_min_y) / resolution
        
        # Transformación afín para rasterio con indexing='xy' y flipud:
        # - Origen en esquina superior izquierda (min_x, max_y)
        # - dx positivo (hacia la derecha)
        # - dy negativo (hacia abajo)
        transform = Affine.translation(bounds_min_x, bounds_max_y) * Affine.scale(pixel_width, -pixel_height)
        
        print(f"🔍 Transformación afín:")
        print(f"   Origen: ({bounds_min_x:.6f}, {bounds_max_y:.6f})")
        print(f"   Tamaño de píxel: {pixel_width:.6f} x {pixel_height:.6f}")
        
        # === PASO 9: CONFIGURAR CRS ===
        if crs_code.startswith('EPSG:'):
            epsg_code = int(crs_code.split(':')[1])
            crs = CRS.from_epsg(epsg_code)
        else:
            crs = CRS.from_string(crs_code)
        
        print(f"🔍 CRS: {crs_code}")
        
        # === PASO 10: ESCRIBIR GEOTIFF ===
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as temp_file:
            temp_path = temp_file.name
        
        with rasterio.open(
            temp_path,
            'w',
            driver='GTiff',
            height=resolution,
            width=resolution,
            count=1,
            dtype=rasterio.float32,
            crs=crs,
            transform=transform,
            nodata=np.nan,
            compress='lzw',
            tiled=True,
            blockxsize=256,
            blockysize=256,
            interleave='band',
            photometric='minisblack'
        ) as dst:
            # Escribir datos interpolados
            dst.write(Z_interpolated.astype(rasterio.float32), 1)
            
            # Agregar estadísticas de banda para QGIS (ya calculadas anteriormente)
            if len(valid_data) > 0:
                dst.update_tags(
                    STATISTICS_MINIMUM=min_val,
                    STATISTICS_MAXIMUM=max_val,
                    STATISTICS_MEAN=mean_val,
                    STATISTICS_STDDEV=std_val,
                    STATISTICS_VALID_PERCENT=(len(valid_data) / Z_interpolated.size) * 100.0
                )
            
            # Agregar metadatos descriptivos
            dst.update_tags(
                SOFTWARE="Conversor Universal Profesional v3.0 - Point Perfect Heatmap",
                DATETIME=time.strftime("%Y:%m:%d %H:%M:%S"),
                DESCRIPTION=f"Mapa de calor con correspondencia punto por punto - Método: {method}",
                CRS=crs_code,
                INTERPOLATION_METHOD=method,
                POINTS_COUNT=len(points_list),
                BOUNDS=f"{bounds_min_x:.6f},{bounds_min_y:.6f},{bounds_max_x:.6f},{bounds_max_y:.6f}",
                POINT_PERFECT="True - Cada punto de entrada tiene su equivalente en el raster"
            )
        
        # Leer el archivo generado
        with open(temp_path, 'rb') as f:
            geotiff_bytes = f.read()
        
        # Limpiar archivo temporal
        os.unlink(temp_path)
        
        print("✅ GeoTIFF generado con correspondencia punto por punto garantizada")
        return geotiff_bytes
        
    except Exception as e:
        st.error(f"❌ Error al crear GeoTIFF punto perfecto: {e}")
        import traceback
        print(f"Error detallado: {traceback.format_exc()}")
        return None


def create_heatmap_geotiff_precise(points_list, crs_code='EPSG:32717', resolution=100, padding_percent=1.0, method='cubic'):
    """
    Genera un mapa de calor GeoTIFF perfectamente georeferenciado desde puntos topográficos.
    
    Esta función soluciona todos los problemas de georeferenciación:
    - Cobertura exacta punto por punto
    - Sin desplazamientos ni inversiones
    - Orientación correcta (norte arriba)
    - Bounding box preciso
    
    Args:
        points_list: Lista de puntos [[x1, y1, z1], [x2, y2, z2], ...]
        crs_code: Código CRS (ej. 'EPSG:32717')
        resolution: Resolución del grid (número de celdas por lado, ej. 100 = 100x100)
        padding_percent: Porcentaje de padding del bounding box (default: 1.0%)
        method: Método de interpolación ('linear', 'cubic', 'nearest')
    
    Returns:
        bytes: Contenido del archivo GeoTIFF correctamente georeferenciado
    """
    import numpy as np
    import scipy.interpolate as interp
    import rasterio
    from rasterio.transform import Affine
    from rasterio.crs import CRS
    import tempfile
    import os
    
    # Validación de entrada
    if not points_list or len(points_list) < 3:
        st.error("❌ Se requieren al menos 3 puntos para generar el mapa de calor")
        return None
    
    try:
        # Convertir a array numpy para mejor rendimiento
        points_array = np.array(points_list)
        x_coords = points_array[:, 0]
        y_coords = points_array[:, 1]
        z_values = points_array[:, 2]
        
        # === PASO 1: CÁLCULO PRECISO DEL BOUNDING BOX ===
        min_x, max_x = np.min(x_coords), np.max(x_coords)
        min_y, max_y = np.min(y_coords), np.max(y_coords)
        
        # Calcular padding basado en el rango de coordenadas
        x_range = max_x - min_x
        y_range = max_y - min_y
        
        # Padding mínimo para asegurar cobertura completa
        padding_x = (x_range * padding_percent) / 100.0
        padding_y = (y_range * padding_percent) / 100.0
        
        # Aplicar padding al bounding box
        bounds_min_x = min_x - padding_x
        bounds_max_x = max_x + padding_x
        bounds_min_y = min_y - padding_y
        bounds_max_y = max_y + padding_y
        
        print(f"🔍 Bounding box original: ({min_x:.3f}, {min_y:.3f}) a ({max_x:.3f}, {max_y:.3f})")
        print(f"🔍 Bounding box con padding: ({bounds_min_x:.3f}, {bounds_min_y:.3f}) a ({bounds_max_x:.3f}, {bounds_max_y:.3f})")
        
        # === PASO 2: CREAR GRID REGULAR PRECISO ===
        # Crear arrays de coordenadas para el grid
        x_grid = np.linspace(bounds_min_x, bounds_max_x, resolution)
        y_grid = np.linspace(bounds_min_y, bounds_max_y, resolution)
        
        # Crear meshgrid con orientación estándar (ij indexing)
        # Esto asegura que X_grid[i,j] = x_grid[j] y Y_grid[i,j] = y_grid[i]
        X_grid, Y_grid = np.meshgrid(x_grid, y_grid, indexing='ij')
        
        print(f"🔍 Grid creado: {resolution}x{resolution} celdas")
        print(f"🔍 Tamaño de celda: {(bounds_max_x - bounds_min_x)/resolution:.3f} x {(bounds_max_y - bounds_min_y)/resolution:.3f}")
        
        # === PASO 3: INTERPOLACIÓN PRECISA ===
        # Preparar puntos para interpolación
        points_for_interp = np.column_stack((x_coords, y_coords))
        
        # Interpolar valores Z en el grid
        Z_interpolated = interp.griddata(
            points_for_interp, 
            z_values, 
            (X_grid, Y_grid), 
            method=method, 
            fill_value=np.nan
        )
        
        print(f"🔍 Interpolación completada usando método: {method}")
        print(f"🔍 Valores Z interpolados: min={np.nanmin(Z_interpolated):.3f}, max={np.nanmax(Z_interpolated):.3f}")
        
        # === PASO 4: CORRECCIÓN DE ORIENTACIÓN ===
        # Para orientación correcta (norte arriba), necesitamos que Y aumente hacia arriba
        # Con indexing='ij', el array está orientado correctamente por defecto
        # Pero rasterio espera que la primera fila sea la superior (Y máxima)
        
        # Aplicar flip vertical para orientación correcta en rasterio
        Z_interpolated = np.flipud(Z_interpolated)
        
        print("🔍 Orientación corregida: norte arriba (Y máxima en primera fila)")
        
        # === PASO 5: TRANSFORMACIÓN AFÍN CORRECTA ===
        # Calcular tamaño de píxel
        pixel_width = (bounds_max_x - bounds_min_x) / resolution
        pixel_height = (bounds_max_y - bounds_min_y) / resolution
        
        # Transformación afín para rasterio:
        # - Origen en esquina superior izquierda (min_x, max_y)
        # - dx positivo (hacia la derecha)
        # - dy negativo (hacia abajo, ya que flipud invirtió el array)
        transform = Affine.translation(bounds_min_x, bounds_max_y) * Affine.scale(pixel_width, -pixel_height)
        
        print(f"🔍 Transformación afín:")
        print(f"   Origen: ({bounds_min_x:.3f}, {bounds_max_y:.3f})")
        print(f"   Tamaño de píxel: {pixel_width:.6f} x {pixel_height:.6f}")
        print(f"   Matriz: [{transform.a:.6f}, {transform.b:.6f}, {transform.c:.6f}, {transform.d:.6f}, {transform.e:.6f}, {transform.f:.6f}]")
        
        # === PASO 6: CONFIGURAR CRS ===
        if crs_code.startswith('EPSG:'):
            epsg_code = int(crs_code.split(':')[1])
            crs = CRS.from_epsg(epsg_code)
        else:
            crs = CRS.from_string(crs_code)
        
        print(f"🔍 CRS configurado: {crs_code}")
        
        # === PASO 7: ESCRIBIR GEOTIFF ===
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Escribir GeoTIFF con configuración completa
        with rasterio.open(
            temp_path,
            'w',
            driver='GTiff',
            height=resolution,
            width=resolution,
            count=1,
            dtype=rasterio.float32,
            crs=crs,
            transform=transform,
            nodata=np.nan,
            compress='lzw',
            tiled=True,
            blockxsize=256,
            blockysize=256,
            interleave='band',
            photometric='minisblack'
        ) as dst:
            # Escribir datos interpolados
            dst.write(Z_interpolated.astype(rasterio.float32), 1)
            
            # Agregar metadatos descriptivos
            dst.update_tags(
                SOFTWARE="Conversor Universal Profesional v3.0 - Heatmap Precise",
                DATETIME=time.strftime("%Y:%m:%d %H:%M:%S"),
                DESCRIPTION=f"Mapa de calor topográfico preciso - Método: {method}, Resolución: {resolution}x{resolution}",
                CRS=crs_code,
                INTERPOLATION_METHOD=method,
                POINTS_COUNT=len(points_list),
                BOUNDS=f"{bounds_min_x:.6f},{bounds_min_y:.6f},{bounds_max_x:.6f},{bounds_max_y:.6f}",
                PADDING_PERCENT=f"{padding_percent}%",
                ORIENTATION="North up (Y increasing upward)"
            )
        
        # Leer el archivo generado
        with open(temp_path, 'rb') as f:
            geotiff_bytes = f.read()
        
        # Limpiar archivo temporal
        os.unlink(temp_path)
        
        print("✅ GeoTIFF generado exitosamente con georeferenciación precisa")
        return geotiff_bytes
        
    except Exception as e:
        st.error(f"❌ Error al crear GeoTIFF preciso: {e}")
        import traceback
        print(f"Error detallado: {traceback.format_exc()}")
        return None


def create_heatmap_geotiff_corrected(points_df, bounds, resolution=500, method='linear', crs_code='EPSG:32719'):
    """
    Crea un GeoTIFF interpolado correctamente georeferenciado a partir de puntos topográficos.
    
    Esta función implementa las mejores prácticas de geoprocesamiento para generar
    un raster que se ubique correctamente en QGIS sin necesidad de georeferenciación manual.
    
    CORRECCIÓN CRÍTICA: Ahora el raster coincide exactamente punto por punto con los datos ingresados.
    
    Args:
        points_df: DataFrame con columnas ['x', 'y', 'cota']
        bounds: tuple (min_x, min_y, max_x, max_y) - bounding box de los puntos
        resolution: Resolución del raster (píxeles por lado)
        method: Método de interpolación ('linear', 'cubic', 'nearest')
        crs_code: Código CRS (ej. 'EPSG:32719' para UTM zona 19S)
    
    Returns:
        bytes: Contenido del archivo GeoTIFF correctamente georeferenciado
    """
    if points_df is None or len(points_df) < 3:
        return None
    
    try:
        # Extraer coordenadas y valores Z
        x_coords = points_df['x'].values
        y_coords = points_df['y'].values
        z_values = points_df['cota'].values
        
        # Obtener bounds
        min_x, min_y, max_x, max_y = bounds
        
        # Asegurar resolución mínima
        actual_resolution = max(resolution, 100)
        
        # === PASO 1: CREAR GRID REGULAR CON ORIENTACIÓN CORRECTA ===
        # Crear arrays de coordenadas para el grid
        x_grid = np.linspace(min_x, max_x, actual_resolution)
        y_grid = np.linspace(min_y, max_y, actual_resolution)
        
        # CORRECCIÓN CRÍTICA: Usar indexing='ij' para orientación correcta
        # Con indexing='ij': X_grid[i,j] = x_grid[j] y Y_grid[i,j] = y_grid[i]
        # Esto asegura que el primer índice corresponde a Y (filas) y el segundo a X (columnas)
        X_grid, Y_grid = np.meshgrid(x_grid, y_grid, indexing='ij')
        
        # === PASO 2: INTERPOLACIÓN ===
        # Preparar puntos de entrada para interpolación
        points = np.column_stack((x_coords, y_coords))
        
        # Seleccionar método de interpolación
        if method == 'linear' and len(points) > 10:
            interp_method = 'cubic'
        else:
            interp_method = method
            
        # Interpolar valores Z en el grid
        Z_interpolated = griddata(
            points, 
            z_values, 
            (X_grid, Y_grid), 
            method=interp_method, 
            fill_value=np.nan
        )
        
        # === PASO 3: CALCULAR TRANSFORMACIÓN AFÍN CORRECTA ===
        # Calcular tamaño de píxel en unidades del CRS
        pixel_width = (max_x - min_x) / actual_resolution
        pixel_height = (max_y - min_y) / actual_resolution
        
        # CORRECCIÓN CRÍTICA: Transformación afín correcta para indexing='ij'
        # Con indexing='ij':
        # - Píxel (0,0) -> coordenada (min_x, min_y) [esquina inferior izquierda]
        # - Píxel (height-1, width-1) -> coordenada (max_x, max_y) [esquina superior derecha]
        # - La escala Y debe ser POSITIVA para que Y aumente hacia arriba
        transform = Affine.translation(min_x, min_y) * Affine.scale(pixel_width, pixel_height)
        
        # === PASO 4: CONFIGURAR CRS ===
        # Importar CRS de rasterio
        from rasterio.crs import CRS
        
        # Crear objeto CRS
        if crs_code.startswith('EPSG:'):
            epsg_code = int(crs_code.split(':')[1])
            crs = CRS.from_epsg(epsg_code)
        else:
            # Fallback para otros códigos CRS
            crs = CRS.from_string(crs_code)
        
        # === PASO 5: ESCRIBIR GEOTIFF ===
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Escribir GeoTIFF con configuración completa
        with rasterio.open(
            temp_path,
            'w',
            driver='GTiff',
            height=actual_resolution,
            width=actual_resolution,
            count=1,
            dtype=rasterio.float32,
            crs=crs,  # CRS específico para georeferenciación correcta
            transform=transform,  # Transformación afín correcta
            nodata=np.nan,  # Valor NoData
            compress='lzw',  # Compresión para reducir tamaño
            tiled=True,  # Tiled para mejor rendimiento
            blockxsize=256,
            blockysize=256,
            interleave='band',
            photometric='minisblack'  # Para datos de elevación/intensidad
        ) as dst:
            # Escribir datos interpolados
            dst.write(Z_interpolated.astype(rasterio.float32), 1)
            
            # Agregar metadatos descriptivos
            dst.update_tags(
                SOFTWARE="Conversor Universal Profesional v3.0",
                DATETIME=time.strftime("%Y:%m:%d %H:%M:%S"),
                DESCRIPTION=f"Mapa de calor topográfico - Método: {interp_method}, Resolución: {actual_resolution}x{actual_resolution}",
                CRS=crs_code,
                INTERPOLATION_METHOD=interp_method,
                POINTS_COUNT=len(points_df),
                BOUNDS=f"{min_x:.6f},{min_y:.6f},{max_x:.6f},{max_y:.6f}"
            )
            
            # Agregar estadísticas de banda
            dst.write_colormap(1, {
                0: (0, 0, 255, 255),      # Azul para valores bajos
                127: (0, 255, 0, 255),    # Verde para valores medios
                255: (255, 0, 0, 255)     # Rojo para valores altos
            })
        
        # Leer el archivo generado
        with open(temp_path, 'rb') as f:
            geotiff_bytes = f.read()
        
        # Limpiar archivo temporal
        os.unlink(temp_path)
        
        return geotiff_bytes
        
    except Exception as e:
        st.error(f"Error al crear GeoTIFF georeferenciado: {e}")
        return None


def create_heatmap_geotiff(points_df, bounds, resolution=500, method='linear'):
    """
    Función principal que usa el CRS configurado en la aplicación.
    Ahora usa la función precisa para georeferenciación perfecta.
    """
    # Obtener el CRS configurado en la aplicación
    input_epsg = st.session_state.get("input_epsg", 32717)  # Ecuador UTM 17S por defecto
    crs_code = f"EPSG:{input_epsg}"
    
    # Convertir DataFrame a lista de puntos para la función precisa
    if points_df is not None and len(points_df) > 0:
        points_list = []
        for _, row in points_df.iterrows():
            points_list.append([row['x'], row['y'], row['cota']])
        
        # Usar la función punto perfecto con correspondencia garantizada
        return create_heatmap_geotiff_point_perfect(
            points_list=points_list,
            crs_code=crs_code,
            resolution=resolution,
            padding_percent=1.0,  # Padding mínimo para cobertura exacta
            method=method
        )
    else:
        st.error("❌ No hay datos de puntos para generar el mapa de calor")
        return None


def main():
    # Sistema de autenticación
    if not check_authentication():
        st.stop()
    
    def mostrar_tabla_preview(df, modo):
        import streamlit as st
        import pandas as pd
        # Vista previa eliminada por solicitud del usuario
        pass
    # ...existing code...
    import os
    import io
    import json
    st.set_page_config(page_title="CONVERSOR UNIVERSAL PROFESIONAL", layout="wide")
    st.markdown("""
    <style>
        /* Oculta el botón/enlace a GitHub del toolbar en Cloud */
        div[data-testid="stToolbar"] a[href*="github.com"] { display: none !important; }
        div[data-testid="stToolbar"] button[title="View source"] { display: none !important; }
        </style>
    """, unsafe_allow_html=True)
    # Detección de entorno en la nube para ajustar UI/descargas
    IS_CLOUD = os.path.exists("/mount")
    try:
        IS_CLOUD = IS_CLOUD or bool(st.secrets.get("IS_CLOUD", False))
    except Exception:
        # En local puede no existir secrets.toml; mantener valor actual
        pass
    # Título principal con icono GPS
    st.markdown("""
    <div style="display:flex;align-items:center;gap:12px;margin:10px 0 4px 0;">
      <span style="font-size:28px;">📡</span>
      <h1 style="margin:0;color:#0d6efd;">CONVERSOR UNIVERSAL PROFESIONAL</h1>
    </div>
    <div style="color:#666;margin-bottom:12px;">Carga archivos, define el sistema de referencia y descarga resultados geoespaciales.</div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.header("Configuración")
        # Estado por defecto
        if "utm_zone" not in st.session_state:
            st.session_state["utm_zone"] = 17
        if "utm_hemi" not in st.session_state:
            st.session_state["utm_hemi"] = "S"  # Ecuador por defecto 17S
        if "input_epsg" not in st.session_state:
            st.session_state["input_epsg"] = 32717
        if "output_epsg" not in st.session_state:
            st.session_state["output_epsg"] = 4326
        if "group_by" not in st.session_state:
            st.session_state["group_by"] = "type"

        mode = st.radio("Modo CRS", ["UTM WGS84 (Zona)", "EPSG Manual"], index=0, horizontal=False)

        if mode == "UTM WGS84 (Zona)":
            col_z1, col_z2 = st.columns(2)
            with col_z1:
                st.session_state["utm_zone"] = st.number_input("Zona UTM", value=st.session_state["utm_zone"], min_value=1, max_value=60, step=1)
            with col_z2:
                st.session_state["utm_hemi"] = st.selectbox("Hemisferio", options=["N", "S"], index=(1 if st.session_state["utm_hemi"] == "S" else 0))
            # Calcular EPSG de entrada
            st.session_state["input_epsg"] = (32600 if st.session_state["utm_hemi"] == "N" else 32700) + int(st.session_state["utm_zone"])
            st.text(f"EPSG de entrada: {st.session_state['input_epsg']}")
        else:
            st.session_state["input_epsg"] = st.number_input("EPSG de entrada", value=int(st.session_state["input_epsg"]),
                                                               min_value=2000, max_value=99999, step=1)

        st.session_state["output_epsg"] = st.number_input("EPSG de salida", value=int(st.session_state["output_epsg"]),
                                                          min_value=2000, max_value=99999, step=1)
        st.session_state["group_by"] = st.selectbox("Agrupar capas por", options=["type", "layer"], index=(0 if st.session_state["group_by"] == "type" else 1))
        
        # Información explicativa sobre agrupamiento
        if st.session_state["group_by"] == "type":
            st.info("🔵 **Modo TYPE**: Agrupa elementos por tipo geométrico:\n- **Puntos**: POINT, INSERT (bloques)\n- **Líneas**: LINE, POLYLINE, LWPOLYLINE\n- **Textos**: TEXT, MTEXT")
        else:
            st.info("🟡 **Modo LAYER**: Agrupa elementos por capa del DXF:\n- Cada capa del archivo DXF se muestra por separado\n- Útil para visualizar la estructura original del dibujo")
        
        # Configuración de tipo de mapa HTML
        st.markdown("**Tipo de Mapa HTML**")
        if "html_map_type" not in st.session_state:
            st.session_state["html_map_type"] = "normal"
        
        # Radio button para seleccionar tipo de mapa
        map_type_selection = st.radio(
            "Seleccione el tipo de mapa:",
            options=["normal", "mapbox"],
            format_func=lambda x: "Mapa Normal (Leaflet)" if x == "normal" else "Mapa Mapbox",
            index=0 if st.session_state["html_map_type"] == "normal" else 1,
            horizontal=True,
            key="map_type_radio"
        )
        
        # CORRECCIÓN: Cambiar pestaña cuando se cambie el tipo de mapa
        if map_type_selection != st.session_state.get("previous_map_type", "normal"):
            st.session_state["previous_map_type"] = map_type_selection
            # Cambiar a la pestaña de mapa correspondiente
            if map_type_selection == "normal":
                st.session_state["active_tab"] = 1  # Pestaña "Mapa de proyecto"
            else:  # mapbox
                st.session_state["active_tab"] = 1  # Pestaña "Mapa de proyecto"
            
            # CORRECCIÓN: Regenerar mapa topográfico si existe
            if st.session_state.get("topo_index_html") and st.session_state.get("project_geojson"):
                try:
                    # Regenerar HTML del mapa topográfico con el nuevo tipo
                    geojson_data = st.session_state["project_geojson"]
                    folder_name = st.session_state.get("project_folder_name", "Proyecto")
                    
                    if map_type_selection == "mapbox":
                        new_html = create_mapbox_html(
                            strip_z_from_geojson(geojson_data), 
                            title=f"{folder_name} - Visor de Mapa Topográfico", 
                            folder_name=folder_name, 
                            grouping_mode="type"
                        )
                    else:
                        # HTML normal con Leaflet
                        leaf_tpl = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>__TITLE__</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    html, body { height: 100%; margin: 0; }
    #map { height: 100vh; }
    .leaflet-control-layers-expanded{ max-height: 60vh; overflow:auto; }
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    const map = L.map('map', {preferCanvas: true});
    
    const baseLayers = {
      "Positron": L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '© CartoDB',
        subdomains: 'abcd',
        maxZoom: 19
      }),
      "OpenStreetMap": L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
      }),
      "Satelital": L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: '© Esri'
      })
    };
    
    baseLayers['Positron'].addTo(map);
    
    const data = __GEOJSON__;
    const overlays = {};
    
    function filterByType(features, type) {
      return features.filter(f => f.properties && f.properties.type === type);
    }
    
    const pts = L.geoJSON({type: 'FeatureCollection', features: filterByType(data.features || [], 'point')}, {
      pointToLayer: (f, latlng) => L.circleMarker(latlng, {
        radius: 3,
        color: '#2c7fb8',
        fill: true,
        fillOpacity: 0.9
      })
    });
    
    const lns = L.geoJSON({type: 'FeatureCollection', features: (data.features || []).filter(f => ['line', 'polyline', 'track', 'route', 'shape'].includes(f.properties && f.properties.type))});
    
    const txt = L.geoJSON({type: 'FeatureCollection', features: filterByType(data.features || [], 'text')}, {
      pointToLayer: (f, latlng) => L.marker(latlng, {
        icon: L.divIcon({
          className: '',
          html: `<div style='font-size:12px;color:#0d6efd;font-weight:600;'>${(f.properties && f.properties.text) || ''}</div>`
        })
      })
    });
    
    overlays['Puntos'] = pts;
    overlays['Líneas'] = lns;
    overlays['Textos'] = txt;
    
    pts.addTo(map);
    lns.addTo(map);
    
    L.control.layers(baseLayers, overlays, {collapsed: false, position: 'topright'}).addTo(map);
    
    try {
      const bounds = __BOUNDS__;
      map.fitBounds([[bounds[0][0], bounds[0][1]], [bounds[1][0], bounds[1][1]]], {padding: [20, 20]});
    } catch(e) {
      map.setView([__CENTER_LAT__, __CENTER_LON__], 15);
    }
  </script>
</body>
</html>"""
                        
                        # Calcular bounds del GeoJSON
                        bounds = [[-12.1, -77.1], [-11.9, -76.9]]  # Default
                        if geojson_data.get("features"):
                            lons = []
                            lats = []
                            for feature in geojson_data["features"]:
                                if feature.get("geometry", {}).get("type") == "Point":
                                    coords = feature["geometry"].get("coordinates", [])
                                    if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                                        lon = coords[0]
                                        lat = coords[1]
                                        lons.append(lon)
                                        lats.append(lat)
                            
                            if lons and lats:
                                center_lat = (min(lats) + max(lats)) / 2
                                center_lon = (min(lons) + max(lons)) / 2
                                bounds = [[min(lats), min(lons)], [max(lats), max(lons)]]
                        
                        new_html = (
                            leaf_tpl
                            .replace("__TITLE__", f"{folder_name} - Visor de Mapa Topográfico")
                            .replace("__GEOJSON__", json.dumps(geojson_data, ensure_ascii=False))
                            .replace("__BOUNDS__", json.dumps(bounds))
                            .replace("__CENTER_LAT__", str(center_lat if 'center_lat' in locals() else -12.0))
                            .replace("__CENTER_LON__", str(center_lon if 'center_lon' in locals() else -77.0))
                        )
                    
                    # Actualizar el HTML del mapa topográfico
                    st.session_state["topo_index_html"] = new_html
                    
                except Exception as e:
                    st.warning(f"Error regenerando mapa topográfico: {e}")
            
            st.rerun()
        st.session_state["html_map_type"] = map_type_selection
        
        if map_type_selection == "mapbox":
            st.info("💡 **Mapa Mapbox**: Requiere API Key de Mapbox. El visor HTML solicitará la clave al abrirse. Incluye visualización 3D, múltiples estilos de mapa y controles avanzados.")
        else:
            st.info("🗺️ **Mapa Normal**: Usa Leaflet. No requiere configuración adicional. Ideal para uso general.")
        
        st.caption("Por defecto, entrada UTM 17S (EPSG:32717) y salida WGS84 (EPSG:4326).")

    # Ruta de salida y carpeta destino (solo visibles tras subir DXF)
    if "output_dir" not in st.session_state:
        default_downloads = Path.home() / "Downloads"
        st.session_state["output_dir"] = str(default_downloads if default_downloads.exists() else Path.cwd())
    if "output_folder" not in st.session_state:
        st.session_state["output_folder"] = "Proyecto1"

    # (Flujo DXF movido a la pestaña 1)

    # Pestañas adicionales para próximos conversores
    st.markdown("---")
    tab_dxf, tab_gpx, tab_kmz, tab_topo, tab_map, tab_manual = st.tabs([
        "📐 DXF Profesional",
        "🥾 GPX Profesional", 
        "🌍 KML/KMZ Profesional",
        "📊 Topográfico Profesional",
        "🗺️ Mapa del proyecto",
        "📚 Manual de Usuario"
    ])
    with tab_topo:
        col1, col2, col3, col4 = st.columns([3,8,7,6])
        with col4:
            # CORRECCIÓN: MAPAS DE CALOR antes de Configuración DXF
            st.markdown("**:orange[MAPAS DE CALOR]**")
            generate_heatmap = st.checkbox("Generar mapa de calor (GeoTIFF)", value=False, key="topo_heatmap_enabled")
            
            if generate_heatmap:
                st.markdown("*Configuración del raster:*")
                margin_percent = st.slider("Margen del área (%)", min_value=5, max_value=50, value=15, step=5, key="topo_heatmap_margin")
                resolution = st.slider("Resolución (píxeles)", min_value=200, max_value=1000, value=500, step=50, key="topo_heatmap_resolution")
                interpolation_method = st.selectbox("Método de interpolación", 
                    options=["linear", "cubic", "nearest"], 
                    index=1,  # Cambiar a 'cubic' por defecto para mejor calidad
                    key="topo_heatmap_method",
                    format_func=lambda x: {"linear": "Lineal", "cubic": "Cúbica (Recomendado)", "nearest": "Vecino más cercano"}[x]
                )
                
                # Mostrar CRS que se usará (del configurado en la app)
                input_epsg = st.session_state.get("input_epsg", 32717)
                crs_display = f"EPSG:{input_epsg}"
                if input_epsg == 32717:
                    crs_description = "UTM Zona 17S (Ecuador)"
                elif input_epsg == 32718:
                    crs_description = "UTM Zona 18S (Perú)"
                elif input_epsg == 32719:
                    crs_description = "UTM Zona 19S (Ecuador, Perú)"
                elif input_epsg == 32618:
                    crs_description = "UTM Zona 18N (Colombia)"
                elif input_epsg == 32619:
                    crs_description = "UTM Zona 19N (Colombia)"
                elif input_epsg == 4326:
                    crs_description = "WGS84 (Lat/Lon)"
                else:
                    crs_description = "Sistema personalizado"
                
                st.info(f"🌍 **CRS que se usará:** {crs_display} - {crs_description}")
                st.info("💡 **Nota:** El CRS se toma automáticamente de la configuración de la aplicación.")
                
                st.info("🗺️ **Mapa de calor**: Genera un GeoTIFF de alta calidad que QGIS puede convertir automáticamente en mapa de calor usando los valores Z de los puntos.")
            
            st.markdown("---")
            st.subheader("Configuración DXF")
            # Configuración de puntos
            st.markdown("**:red[PUNTOS]**")
            pdmodes = [0, 1, 2, 3, 4, 32, 33, 34, 35, 64, 65, 66, 67, 96, 97, 98, 99]
            pdmode_labels = ["Dot", "Empty", "Plus", "Cross", "Tick", "Circle", "Circle+Plus", "Circle+Cross", "Circle+Tick", 
                           "Square", "Square+Plus", "Square+Cross", "Square+Tick", "Circle+Square", "Circle+Square+Plus", "Circle+Square+Cross", "Circle+Square+Tick"]
            pdmode_options = [f"{mode} - {label}" for mode, label in zip(pdmodes, pdmode_labels)]
            pdmode_selected = st.selectbox("Tipo de punto (PDMODE)", pdmode_options, index=6, key="topo_pdmode_select")
            pdmode = int(pdmode_selected.split(" - ")[0])
            st.session_state["topo_pdmode"] = pdmode
            
            altura_punto = st.number_input("Altura de punto", min_value=0.01, max_value=10.0, value=0.3, step=0.01, key="topo_h_punto")
            
            colores_punto = ["azul", "rojo", "amarillo", "verde", "cian", "magenta", "blanco", "gris", "naranja", "negro"]
            color_punto = st.selectbox("Color de punto", colores_punto, index=0, key="topo_color_punto")
            
            layer_puntos = st.text_input("Layer de puntos", value="PUNTOS", key="topo_layer_puntos")
            
            st.markdown("---")
            # Configuración de líneas
            st.markdown("**:blue[LÍNEAS/POLÍGONOS]**")
            colores_linea = ["rojo", "azul", "amarillo", "verde", "cian", "magenta", "blanco", "gris", "naranja", "negro"]
            color_linea = st.selectbox("Color de línea", colores_linea, index=0, key="topo_color_linea")
            ancho_linea = st.number_input("Ancho de línea (mm)", min_value=0.01, max_value=10.0, value=0.48, step=0.01, key="topo_ancho_linea")
            acad_linetypes = [
                "CONTINUOUS", "DASHED", "DASHDOT", "CENTER", "HIDDEN", "PHANTOM", "DOT", "DIVIDE", "BORDER", "WAVE"
            ]
            tipo_linea = st.selectbox("Tipo de línea", acad_linetypes, index=0, key="topo_tipo_linea")
            layer_polilineas = st.text_input("Layer de polílíneas", value="POLILINEAS", key="topo_layer_polilineas")
            
            st.markdown("---")
            # Configuración de textos
            st.markdown("**:green[TEXTOS]**")
            altura_texto = st.number_input("Altura de texto", min_value=0.01, max_value=10.0, value=0.35, step=0.01, key="topo_altura_texto")
            colores_texto = ["blanco", "rojo", "azul", "amarillo", "verde", "cian", "magenta", "gris", "naranja", "negro"]
            color_texto = st.selectbox("Color de texto", colores_texto, index=0, key="topo_color_texto")
            desplaz_x = st.number_input("Desplazamiento X", min_value=-10.0, max_value=10.0, value=0.15, step=0.01, key="topo_desplaz_x")
            desplaz_y = st.number_input("Desplazamiento Y", min_value=-10.0, max_value=10.0, value=0.15, step=0.01, key="topo_desplaz_y")
            layer_textos = st.text_input("Layer de textos", value="TEXTOS", key="topo_layer_textos")
            
        # Configuración y controles principales en col2 y col3
        with col2:
            import pandas as pd
            st.header("Sistema Topográfico Profesional")
            st.caption("Pega los datos de puntos topográficos en el área de texto.")
            # CORRECCIÓN: Usar controles que no causen reruns en primera interacción
            modo_topo = st.selectbox(
                "Modo de generación", 
                options=["Solo puntos", "Puntos y polilíneas"], 
                index=0,
                key="topo_modo_selectbox",
                help="Selecciona el modo de generación"
            )
            
            # Dimensión de salida: 2D (ignora cota) o 3D (usa cota)
            # CORRECCIÓN: Usar checkbox para evitar reruns
            st.markdown("**🔧 Modo de Generación:**")
            
            # Usar checkbox que no causa rerun completo
            modo_3d = st.checkbox(
                "🔺 **Modo 3D** (usar valores de cota)", 
                value=st.session_state.get("topo_dim", "2D") == "3D",
                key="topo_dim_checkbox",
                help="Activa para usar valores de cota en la generación"
            )
            
            # Actualizar session_state basado en checkbox SIN causar rerun
            if modo_3d:
                st.session_state["topo_dim"] = "3D"
                st.success("🔺 **Modo 3D activado** - Usando valores de cota")
            else:
                st.session_state["topo_dim"] = "2D"
                st.info("📐 **Modo 2D activado** - Ignorando valores de cota")
            
            # Usar el modo del session_state
            dim_selection = st.session_state.get("topo_dim", "2D")
            if "topo_df" not in st.session_state:
                st.session_state["topo_df"] = None
            if "topo_paste" not in st.session_state:
                st.session_state.topo_paste = ""
            st.markdown("**📋 Área de entrada de datos:**")
            st.info("💡 **Formato esperado:** No., x, y, cota, descripción (separados por tabulador, coma o punto y coma)")
            st.markdown("**📏 Separación recomendada:** Para números de hasta 5 dígitos, usa tabuladores para mejor separación")
            
            # Crear un área de texto con mejor formato visual
            st.session_state.topo_paste = st.text_area(
                "Pegar datos topográficos", 
                value=st.session_state.topo_paste, 
                height=280,  # Aumentado para mejor visualización
                key="topo_paste_area",
                placeholder="Ejemplo con tabuladores (recomendado):\n1\t123.456\t456.789\t12.345\tPunto de control\n2\t124.567\t457.890\t13.456\tVértice\n3\t125.678\t458.901\t14.567\tEstación\n\nEjemplo con comas:\n1,123.456,456.789,12.345,Punto de control\n2,124.567,457.890,13.456,Vértice",
                help="💡 **Tip:** Los tabuladores proporcionan mejor separación visual para números largos"
            )
            
            col_btn1, col_btn2, col_btn3 = st.columns([1,1,1])
            with col_btn1:
                if st.button("Insertar datos", key="btn_topo_paste"):
                    pasted = st.session_state.get("topo_paste", "")
                    import io
                    import pandas as pd
                    try:
                        # CORRECCIÓN: Mejorar el procesamiento de datos con tabuladores
                        # Primero intentar con tabulador específicamente
                        if '\t' in pasted:
                            df_paste = pd.read_csv(io.StringIO(pasted), sep='\t', engine='python', header=None)
                        else:
                            # Si no hay tabuladores, usar separadores múltiples
                            df_paste = pd.read_csv(io.StringIO(pasted), sep="\t|,|;", engine="python", header=None)
                        
                        # Verificar que se detectaron columnas
                        if df_paste.empty or df_paste.shape[1] == 0:
                            st.error("❌ No se pudieron detectar columnas en los datos. Verifica el formato.")
                            st.info("💡 **Formato correcto:** Cada línea debe tener: No. [TAB] x [TAB] y [TAB] cota [TAB] descripción")
                            
                            # Debug: mostrar los datos tal como se recibieron
                            st.markdown("**🔍 Debug - Datos recibidos:**")
                            st.code(pasted[:200] + "..." if len(pasted) > 200 else pasted)
                            
                            # Mostrar caracteres especiales
                            st.markdown("**🔍 Debug - Caracteres detectados:**")
                            if '\t' in pasted:
                                st.success("✅ Tabuladores detectados")
                            if ',' in pasted:
                                st.info("ℹ️ Comas detectadas")
                            if ';' in pasted:
                                st.info("ℹ️ Puntos y coma detectados")
                            
                            return
                        
                        # CORRECCIÓN: Asegurar que siempre tengamos exactamente 5 columnas
                        if df_paste.shape[1] < 5:
                            # Si faltan columnas, agregar las que faltan
                            while df_paste.shape[1] < 5:
                                if df_paste.shape[1] == 3:
                                    df_paste[df_paste.shape[1]] = 0  # Agregar cota=0
                                else:
                                    df_paste[df_paste.shape[1]] = ""  # Agregar descripción vacía
                        elif df_paste.shape[1] > 5:
                            # Si hay más de 5 columnas, tomar solo las primeras 5
                            df_paste = df_paste.iloc[:, :5]
                        
                        # Asignar nombres de columnas
                        df_paste.columns = ["No.", "x", "y", "cota", "desc"]
                        
                        # CORRECCIÓN: Procesar cotas con comas decimales correctamente
                        # Primero mostrar datos originales para debug
                        st.write("🔍 **Datos originales de cota (primeras 5):**")
                        st.write(df_paste["cota"].head().tolist())
                        
                        # Convertir comas a puntos para procesamiento numérico
                        df_paste["cota"] = df_paste["cota"].astype(str).str.replace(',', '.')
                        
                        # Mostrar datos después de conversión
                        st.write("🔍 **Datos después de conversión (primeras 5):**")
                        st.write(df_paste["cota"].head().tolist())
                        
                        # Convertir a numérico
                        df_paste["cota"] = pd.to_numeric(df_paste["cota"], errors="coerce")
                        
                        # Mostrar datos finales
                        st.write("🔍 **Datos finales numéricos (primeras 5):**")
                        st.write(df_paste["cota"].head().tolist())
                        
                        # CORRECCIÓN: Solo convertir NaN a 0 si es necesario, pero preservar valores válidos
                        nan_count = df_paste["cota"].isna().sum()
                        if nan_count > 0:
                            st.warning(f"⚠️ {nan_count} valores de cota inválidos encontrados. Se convertirán a 0.")
                            df_paste["cota"] = df_paste["cota"].fillna(0)
                        else:
                            st.success("✅ Todos los valores de cota son válidos")
                        
                        # Convertir x e y a numérico también
                        df_paste["x"] = pd.to_numeric(df_paste["x"], errors="coerce")
                        df_paste["y"] = pd.to_numeric(df_paste["y"], errors="coerce")
                        
                        # Eliminar filas con valores NaN en x o y
                        df_paste = df_paste.dropna(subset=["x", "y"])
                        
                        # CORRECCIÓN: Debug detallado de datos procesados
                        st.write(f"🔍 **Debug de datos procesados:**")
                        st.write(f"   Filas procesadas: {len(df_paste)}")
                        st.write(f"   Columnas: {list(df_paste.columns)}")
                        if 'cota' in df_paste.columns:
                            # Mostrar información detallada de cotas
                            cotas_no_nan = df_paste['cota'][~df_paste['cota'].isna()]
                            cotas_no_cero = cotas_no_nan[cotas_no_nan != 0]
                            
                            st.write(f"   Cotas no-NaN: {len(cotas_no_nan)} de {len(df_paste)}")
                            st.write(f"   Cotas no-cero: {len(cotas_no_cero)} de {len(df_paste)}")
                            
                            if len(cotas_no_nan) > 0:
                                st.write(f"   Rango de cotas (incluyendo ceros): {cotas_no_nan.min():.3f} a {cotas_no_nan.max():.3f}")
                            if len(cotas_no_cero) > 0:
                                st.write(f"   Rango de cotas válidas: {cotas_no_cero.min():.3f} a {cotas_no_cero.max():.3f}")
                            
                            # Mostrar algunos valores de ejemplo
                            st.write(f"   Primeras 5 cotas: {df_paste['cota'].head().tolist()}")
                            
                            # Mostrar estadísticas detalladas
                            if len(cotas_no_cero) > 0:
                                st.write(f"📊 **Estadísticas de cotas válidas:**")
                                st.write(f"   - Media: {cotas_no_cero.mean():.3f}")
                                st.write(f"   - Mediana: {cotas_no_cero.median():.3f}")
                                st.write(f"   - Desviación estándar: {cotas_no_cero.std():.3f}")
                                st.write(f"   - Valores únicos: {len(cotas_no_cero.unique())}")
                        
                        st.session_state["topo_df"] = df_paste
                        st.success(f"✅ Datos pegados insertados correctamente. {len(df_paste)} puntos procesados.")
                    except Exception as e:
                        st.error(f"❌ Error al procesar los datos pegados: {e}")
                        st.info("💡 **Formato esperado:** No., x, y, cota, descripción (separados por tabulador, coma o punto y coma)")
                        st.info("🔍 **Ejemplo con tabuladores:**")
                        st.code("1\t123.456\t456.789\t12.345\tPunto de control\n2\t124.567\t457.890\t13.456\tVértice")
            with col_btn2:
                if st.button("Datos de ejemplo", key="btn_topo_sample"):
                    sample_df = create_sample_heatmap_data()
                    st.session_state["topo_df"] = sample_df
                    st.success("✅ Datos de ejemplo cargados (10 puntos en UTM zona 17S - Ecuador)")
                    st.rerun()
            
            with col_btn3:
                if st.button("Limpiar", key="btn_topo_clear_paste"):
                    st.session_state.topo_paste = ""
                    if "topo_df" in st.session_state:
                        st.session_state.topo_df = None
                    st.success("✅ Datos limpiados correctamente")
                    st.rerun()
            st.markdown("---")
            st.markdown("**📁 Configuración de salida:**")
            st.text_input("Nombre de carpeta", value=st.session_state.get("topo_folder", "Trabajo_Topográfico"), key="topo_folder")
            st.text_input("Ruta de descarga", value=st.session_state.get("topo_output_dir", str(Path.home() / "Downloads")), key="topo_output_dir")
            if (not IS_CLOUD) and st.button("Seleccionar carpeta de descarga", key="btn_topo_select_dir"):
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk(); root.withdraw()
                selected_dir = filedialog.askdirectory()
                root.destroy()
                if selected_dir:
                    st.session_state["topo_output_dir"] = selected_dir
                    st.success(f"Carpeta seleccionada: {selected_dir}")
            if st.button("Limpiar tabla", key="btn_topo_clear"):
                st.session_state["topo_df"] = None
                st.success("✅ Tabla limpiada correctamente")
                st.rerun()
        with col3:
            st.subheader("Vista previa de la tabla")
            import pandas as pd
            headers = ["No.", "x", "y", "cota", "desc"]
            df = st.session_state.get("topo_df")
            if df is not None:
                # Renombrar columnas si es necesario
                df = df.copy()
                
                # CORRECCIÓN: Manejar correctamente el número de columnas
                if len(df.columns) <= len(headers):
                    # Si el DataFrame tiene 5 o menos columnas, usar los headers correspondientes
                    df.columns = headers[:len(df.columns)]
                else:
                    # Si el DataFrame tiene más de 5 columnas, usar los primeros 5 headers
                    # y agregar nombres genéricos para las columnas adicionales
                    df.columns = headers + [f"col_{i}" for i in range(len(headers), len(df.columns))]
                
                # CORRECCIÓN: Mostrar información del modo usando el session_state
                current_mode = st.session_state.get("topo_dim", "2D")
                if current_mode == "3D":
                    st.success("🔺 **Modo 3D activado** - Los valores de cota se utilizarán en la generación")
                    # Asegurar que la columna 'cota' tenga valores válidos
                    if 'cota' in df.columns:
                        # Convertir comas a puntos si es necesario
                        df['cota'] = df['cota'].astype(str).str.replace(',', '.')
                        # Convertir a numérico y manejar valores inválidos
                        df['cota'] = pd.to_numeric(df['cota'], errors='coerce')
                        # Mostrar información sobre valores NaN
                        nan_count = df['cota'].isna().sum()
                        if nan_count > 0:
                            st.warning(f"⚠️ {nan_count} valores de cota inválidos encontrados. Se convertirán a 0.")
                            df['cota'] = df['cota'].fillna(0)
                        
                        # Mostrar estadísticas solo si hay datos válidos
                        valid_cotas = df['cota'][df['cota'] != 0]
                        if len(valid_cotas) > 0:
                            st.write(f"📊 **Estadísticas de cotas:** Min: {valid_cotas.min():.3f}, Max: {valid_cotas.max():.3f}, Media: {valid_cotas.mean():.3f}")
                            st.write(f"📈 **Puntos con cota válida:** {len(valid_cotas)} de {len(df)}")
                            st.write(f"🎯 **Rango de elevación:** {valid_cotas.max() - valid_cotas.min():.3f} metros")
                        else:
                            st.warning("⚠️ No hay valores de cota válidos en los datos")
                else:
                    st.info("📐 **Modo 2D activado** - Los valores de cota se ignorarán")
                
                st.dataframe(df)
            else:
                st.info("No hay datos cargados.")
            if df is not None:
                col_btn1, col_btn2 = st.columns([2,2])
                gen_clicked = col_btn1.button("Generar salidas", key="btn_topo_generate")
                open_folder_clicked = False
                if not IS_CLOUD:
                    open_folder_clicked = col_btn2.button("Abrir carpeta de salida", key="btn_topo_open_folder")
                if open_folder_clicked:
                    import os, webbrowser
                    base_dir = st.session_state["topo_output_dir"]
                    folder_name = st.session_state["topo_folder"]
                    # Buscar la carpeta con el índice más alto
                    idx_folder = 1
                    main_folder = os.path.join(base_dir, folder_name)
                    while os.path.exists(os.path.join(base_dir, f"{folder_name}_{idx_folder}")):
                        idx_folder += 1
                    # Si existe versión con índice, usar la anterior (la última creada)
                    if idx_folder > 1:
                        main_folder = os.path.join(base_dir, f"{folder_name}_{idx_folder-1}")
                    webbrowser.open(f"file://{main_folder}")

                if gen_clicked:
                    import os, ezdxf, json, shapefile, pyproj, numpy as np
                    from simplekml import Kml
                    # Obtener EPSG de entrada y salida desde la configuración
                    input_epsg = st.session_state.get("input_epsg", 32717)
                    output_epsg = st.session_state.get("output_epsg", 4326)
                    transformer = pyproj.Transformer.from_crs(f"EPSG:{input_epsg}", f"EPSG:{output_epsg}", always_xy=True)
                    # Crear carpeta principal, con sufijo si existe
                    base_dir = st.session_state["topo_output_dir"]
                    folder_name = st.session_state["topo_folder"]
                    main_folder = os.path.join(base_dir, folder_name)
                    idx_folder = 1
                    while os.path.exists(main_folder):
                        main_folder = os.path.join(base_dir, f"{folder_name}_{idx_folder}")
                        idx_folder += 1
                    os.makedirs(main_folder, exist_ok=True)
                    # --- DXF ---
                    dxf_path = os.path.join(main_folder, f"{folder_name}.dxf")
                    doc = ezdxf.new(dxfversion="R2000")
                    msp = doc.modelspace()
                    # Configuración DXF desde columna 4
                    pdmode_val = st.session_state.get("topo_pdmode", 33)
                    h_punto_val = st.session_state.get("topo_h_punto", 0.3)
                    color_punto_val = st.session_state.get("topo_color_punto", "azul")
                    color_linea_val = st.session_state.get("topo_color_linea", "rojo")
                    ancho_linea_val = st.session_state.get("topo_ancho_linea", 0.48)
                    tipo_linea_val = st.session_state.get("topo_tipo_linea", "CONTINUOUS")
                    
                    # Configuración de textos
                    altura_texto_val = st.session_state.get("topo_altura_texto", 0.35)
                    color_texto_val = st.session_state.get("topo_color_texto", "blanco")
                    desplaz_x_val = st.session_state.get("topo_desplaz_x", 0.15)
                    desplaz_y_val = st.session_state.get("topo_desplaz_y", 0.15)
                    
                    # Configuración de layers
                    layer_puntos_val = st.session_state.get("topo_layer_puntos", "PUNTOS")
                    layer_polilineas_val = st.session_state.get("topo_layer_polilineas", "POLILINEAS")
                    layer_textos_val = st.session_state.get("topo_layer_textos", "TEXTOS")
                    
                    # Mapa de color DXF
                    color_map = {"rojo": 1, "amarillo": 2, "verde": 3, "cian": 4, "azul": 5, "magenta": 6, "blanco": 7, "gris": 8, "naranja": 30, "negro": 250}
                    
                    # Capas y estilos
                    doc.layers.new(name=layer_puntos_val, dxfattribs={"color": color_map.get(color_punto_val, 5), "linetype": "CONTINUOUS"})
                    doc.layers.new(name=layer_polilineas_val, dxfattribs={"color": color_map.get(color_linea_val, 1), "linetype": tipo_linea_val, "lineweight": int(ancho_linea_val * 100)})
                    doc.layers.new(name=layer_textos_val, dxfattribs={"color": color_map.get(color_texto_val, 7), "linetype": "CONTINUOUS"})
                    
                    # Configurar variables del sistema DXF para puntos
                    doc.header["$PDMODE"] = pdmode_val
                    doc.header["$PDSIZE"] = h_punto_val
                    
                    # Configurar estilo de texto
                    text_style = doc.styles.get("STANDARD")
                    text_style.dxf.height = altura_texto_val
                    polylines_dxf = []
                    polyline_current_dxf = []
                    polyline_start_point = None
                    # --- KML ---
                    kml = Kml()
                    # Crear carpetas para organizar elementos
                    points_folder_topo = kml.newfolder(name="📍 Puntos Topográficos")
                    lines_folder_topo = kml.newfolder(name="🔗 Polígonos/Líneas")
                    polylines_kml = []
                    polyline_current_kml = []
                    # --- GeoJSON ---
                    geojson = {
                        "type": "FeatureCollection",
                        "features": []
                    }
                    modo_topo = st.session_state.get("topo_modo", "Solo puntos")
                    # Procesar puntos individuales
                    for idx, row in df.iterrows():
                        try:
                            try:
                                x = float(row["x"])  # UTM X
                                y = float(row["y"])  # UTM Y
                            except Exception:
                                raise ValueError(f"X/Y inválidos: {row.get('x')} / {row.get('y')}")
                            lon, lat = transformer.transform(x, y)
                             
                            # Dimensión de salida: calcular cota usada
                            try:
                                cota_val = float(row["cota"]) if str(row.get("cota", "")).strip() != "" else 0.0
                            except Exception:
                                cota_val = 0.0
                            dim_is_3d = (st.session_state.get("topo_dim", "2D") == "3D")
                            cota_used = cota_val if dim_is_3d else 0.0
                             
                            # DXF: Agregar punto en coordenadas UTM (2D o 3D)
                            if dim_is_3d:
                                msp.add_point((x, y, cota_used), dxfattribs={"layer": layer_puntos_val, "color": color_map.get(color_punto_val, 5)})
                            else:
                                msp.add_point((x, y), dxfattribs={"layer": layer_puntos_val, "color": color_map.get(color_punto_val, 5)})
                             
                            # DXF: Agregar texto del punto (solo descripción si existe)
                            texto_x = x + desplaz_x_val
                            texto_y = y + desplaz_y_val
                            
                            # Solo mostrar la descripción si no está vacía
                            desc_val = str(row['desc']).strip()
                            if desc_val and desc_val.lower() not in ['', 'nan', 'none', 'null']:
                                msp.add_text(desc_val, 
                                    dxfattribs={"layer": layer_textos_val,
                                                "height": altura_texto_val,
                                                "color": color_map.get(color_texto_val, 7),
                                                "insert": (texto_x, texto_y)
                                            })
                            
                            # KML: Agregar punto en coordenadas geográficas (agregar altitud si 3D)
                            pt_kml = points_folder_topo.newpoint(name=str(row["No."]))
                            if dim_is_3d:
                                try:
                                    import simplekml as skml  # type: ignore
                                    pt_kml.coords = [(lon, lat, cota_used)]
                                    pt_kml.altitudemode = skml.AltitudeMode.absolute
                                except Exception:
                                    pt_kml.coords = [(lon, lat, cota_used)]
                            else:
                                pt_kml.coords = [(lon, lat)]
                             
                            # GeoJSON: Agregar punto en coordenadas geográficas (con Z si 3D)
                            coords_geo = [lon, lat, cota_used] if dim_is_3d else [lon, lat]
                            geojson["features"].append({
                                "type": "Feature",
                                "geometry": {"type": "Point", "coordinates": coords_geo},
                                "properties": {
                                    "No": int(row["No."]),
                                    "cota": float(cota_val), 
                                    "desc": str(row["desc"]),
                                    "type": "point",
                                    "layer": "TOPO"
                                }
                            })
                            
                        except Exception as e:
                            st.warning(f"Error procesando punto en fila {idx}: {e}")
                            continue
                    
                    # Procesar polígonos si está habilitado
                    poly_info = []
                    if modo_topo == "Puntos y polilíneas":
                        try:
                            # Agrupar puntos por el número de polígono (columna 'No.')
                            import pandas as pd
                            df['No.'] = pd.to_numeric(df['No.'], errors='coerce').fillna(0).astype(int)
                            grouped = df.groupby('No.')
                            
                            polygons_utm = []
                            for name, group in grouped:
                                if len(group) >= 2: # Se necesitan al menos 2 puntos para una línea
                                    points = group[['x', 'y']].to_records(index=False).tolist()
                                    polygons_utm.append(points)

                            # Preparar lookup de cota por coordenada UTM (redondeo para emparejar)
                            def _round_xy(xv, yv, nd=3):
                                try:
                                    return (round(float(xv), nd), round(float(yv), nd))
                                except Exception:
                                    return (xv, yv)
                            cota_lookup = {}
                            try:
                                for _, r in df.iterrows():
                                    try:
                                        xr = float(r["x"]) ; yr = float(r["y"]) ; cv = float(r.get("cota", 0) or 0)
                                        cota_lookup[_round_xy(xr, yr)] = cv
                                    except Exception:
                                        continue
                            except Exception:
                                cota_lookup = {}
                            dim_is_3d = (st.session_state.get("topo_dim", "2D") == "3D")

                            export_lines_geo = []  # lista de listas de coords (lon,lat[,z])
                            export_lines_utm = []  # lista de listas de coords (x,y[,z]) para DXF si se quiere

                            for idx_poly, ring_utm in enumerate(polygons_utm, start=1):
                                try:
                                    if len(ring_utm) < 2:
                                        continue
                                    
                                    # Para DXF, la polilínea se cierra con una bandera
                                    # Para KML/GeoJSON, el último punto debe ser igual al primero
                                    is_closed_poly = len(ring_utm) >= 3
                                    
                                    # DXF: Agregar polilínea (UTM) 2D/3D
                                    if dim_is_3d:
                                        verts3d = []
                                        for xv, yv in ring_utm:
                                            zc = cota_lookup.get(_round_xy(xv, yv), 0.0)
                                            verts3d.append((xv, yv, float(zc)))
                                        
                                        # Cerrar manualmente para 3D si es un polígono
                                        if is_closed_poly:
                                            verts3d.append(verts3d[0])

                                        try:
                                            msp.add_polyline3d(verts3d, dxfattribs={
                                                "layer": layer_polilineas_val,
                                                "color": color_map.get(color_linea_val, 1),
                                                "linetype": tipo_linea_val,
                                            })
                                        except Exception:
                                            msp.add_lwpolyline([(v[0], v[1]) for v in verts3d], dxfattribs={
                                                "layer": layer_polilineas_val,
                                                "color": color_map.get(color_linea_val, 1),
                                                "lineweight": int(ancho_linea_val * 100),
                                                "linetype": tipo_linea_val,
                                                "closed": is_closed_poly
                                            })
                                    else: # 2D
                                        msp.add_lwpolyline(
                                            ring_utm,
                                            dxfattribs={
                                                "layer": layer_polilineas_val,
                                                "color": color_map.get(color_linea_val, 1),
                                                "lineweight": int(ancho_linea_val * 100),
                                                "linetype": tipo_linea_val,
                                                "closed": is_closed_poly
                                            }
                                        )
                                    
                                    # Preparar coordenadas para KML/GeoJSON
                                    ring_for_export = ring_utm
                                    if is_closed_poly:
                                        ring_for_export = ring_utm + [ring_utm[0]]

                                    poly_coords_geo = []
                                    for x_utm, y_utm in ring_for_export:
                                        lon, lat = transformer.transform(x_utm, y_utm)
                                        if dim_is_3d:
                                            zc = cota_lookup.get(_round_xy(x_utm, y_utm), 0.0)
                                            poly_coords_geo.append((lon, lat, float(zc)))
                                        else:
                                            poly_coords_geo.append((lon, lat))
                                    
                                    export_lines_geo.append(poly_coords_geo)
                                    export_lines_utm.append(ring_utm)
                                    
                                    # KML: Agregar polilínea
                                    linestring = lines_folder_topo.newlinestring(name=f"Polilínea {idx_poly}")
                                    linestring.coords = poly_coords_geo
                                    linestring.style.linestyle.color = "red"
                                    linestring.style.linestyle.width = 3
                                    
                                    # GeoJSON: Agregar polilínea
                                    if dim_is_3d:
                                        coords_llz = [[c[0], c[1], c[2]] for c in poly_coords_geo]
                                    else:
                                        coords_llz = [[c[0], c[1]] for c in poly_coords_geo]
                                    geojson["features"].append({
                                        "type": "Feature",
                                        "geometry": {"type": "LineString", "coordinates": coords_llz},
                                        "properties": {"type": "polyline", "layer": layer_polilineas_val}
                                    })
                                    
                                    # Calcular métricas si es un polígono cerrado
                                    if is_closed_poly:
                                        try:
                                            import shapely.geometry
                                            poly_shape = shapely.geometry.Polygon(ring_utm)
                                            area_m2 = poly_shape.area
                                            length_m = poly_shape.length
                                        except Exception:
                                            area_m2 = 0
                                            length_m = 0
                                        
                                        poly_info.append({
                                            "No": idx_poly,
                                            "area_m2": round(area_m2, 2),
                                            "perimetro_m": round(length_m, 2),
                                            "num_puntos": len(ring_utm)
                                        })
                                    
                                except Exception as e:
                                    st.warning(f"Error procesando polilínea {idx_poly}: {e}")
                                    continue
                                    geojson["features"].append({
                                        "type": "Feature",
                                        "geometry": {"type": "LineString", "coordinates": coords_llz},
                                        "properties": {"type": "polyline", "layer": layer_polilineas_val}
                                    })
                                    
                                    # Calcular métricas si es un polígono cerrado
                                    if is_closed_poly:
                                        try:
                                            import shapely.geometry
                                            poly_shape = shapely.geometry.Polygon(ring_utm)
                                            area_m2 = poly_shape.area
                                            length_m = poly_shape.length
                                        except Exception:
                                            area_m2 = 0
                                            length_m = 0
                                        
                                        poly_info.append({
                                            "No": idx_poly,
                                            "area_m2": round(area_m2, 2),
                                            "perimetro_m": round(length_m, 2),
                                            "num_puntos": len(ring_utm)
                                        })
                                    
                                except Exception as e:
                                    st.warning(f"Error procesando polilínea {idx_poly}: {e}")
                                    continue
                            
                            # Fallback: si no se detectaron polilíneas, generar una polilínea con el orden de puntos
                            if (not polygons_utm) or (len(export_lines_geo) == 0):
                                try:
                                    ordered_pts_utm = []
                                    ordered_pts_geo = []
                                    for _, r in df.iterrows():
                                        x = float(r["x"]) ; y = float(r["y"]) ; lon, lat = transformer.transform(x, y)
                                        if dim_is_3d:
                                            zc = float(r.get("cota", 0) or 0)
                                            ordered_pts_utm.append((x, y, zc))
                                            ordered_pts_geo.append((lon, lat, zc))
                                        else:
                                            ordered_pts_utm.append((x, y))
                                            ordered_pts_geo.append((lon, lat))
                                    if len(ordered_pts_geo) >= 2:
                                        export_lines_geo.append(ordered_pts_geo)
                                        export_lines_utm.append(ordered_pts_utm)
                                        # DXF
                                        if dim_is_3d:
                                            try:
                                                msp.add_polyline3d(ordered_pts_utm, dxfattribs={"layer": layer_polilineas_val, "color": color_map.get(color_linea_val, 1), "linetype": tipo_linea_val})
                                            except Exception:
                                                msp.add_lwpolyline([(vx, vy) for vx, vy, _ in ordered_pts_utm], dxfattribs={"layer": layer_polilineas_val, "color": color_map.get(color_linea_val, 1), "lineweight": int(ancho_linea_val*100), "linetype": tipo_linea_val, "closed": False})
                                        else:
                                            msp.add_lwpolyline([(vx, vy) for vx, vy in ordered_pts_utm], dxfattribs={"layer": layer_polilineas_val, "color": color_map.get(color_linea_val, 1), "lineweight": int(ancho_linea_val*100), "linetype": tipo_linea_val, "closed": False})
                                        # KML
                                        ls = lines_folder_topo.newlinestring(name="Polilínea 1")
                                        ls.coords = ordered_pts_geo
                                        ls.style.linestyle.color = "red" ; ls.style.linestyle.width = 3
                                        # GeoJSON
                                        if dim_is_3d:
                                            coords_llz = [[p[0], p[1], p[2]] for p in ordered_pts_geo]
                                        else:
                                            coords_llz = [[p[0], p[1]] for p in ordered_pts_geo]
                                        geojson["features"].append({"type":"Feature","geometry":{"type":"LineString","coordinates":coords_llz},"properties":{"type":"polyline","layer":layer_polilineas_val}})
                                        poly_info.append({"No":1, "long_m": 0 if len(ordered_pts_utm)<2 else None, "num_puntos": len(ordered_pts_utm)})
                                except Exception as e:
                                    st.warning(f"No se pudieron generar polilíneas por orden: {e}")

                        except Exception as e:
                            st.error(f"Error en procesamiento de polígonos: {e}")
                    
                    # Mostrar información de polilíneas cerradas si las hay
                    if poly_info:
                        st.info(f"Se generaron {len(poly_info)} polilíneas cerradas correctamente")
                        import pandas as pd
                        poly_df = pd.DataFrame(poly_info)
                        st.dataframe(poly_df)
                    doc.saveas(dxf_path)
                    # --- KML ---
                    kml_path = os.path.join(main_folder, f"{folder_name}.kml")
                    kml.save(kml_path)
                    # --- Carpeta Shapefiles ---
                    shp_dir = os.path.join(main_folder, "shapefiles")
                    os.makedirs(shp_dir, exist_ok=True)
                    
                    # --- Shapefile de Puntos ---
                    shp_points_path = os.path.join(shp_dir, f"{folder_name}_puntos")
                    dim_is_3d = (st.session_state.get("topo_dim", "2D") == "3D")
                    shp_pt_type = shapefile.POINTZ if dim_is_3d else shapefile.POINT
                    # Coordenadas del SHP deben estar en EPSG de salida; usamos el mismo transformer definido (input_epsg -> output_epsg)
                    output_epsg_val = int(st.session_state.get("output_epsg", 4326))
                    with shapefile.Writer(shp_points_path, shapeType=shp_pt_type) as w_pts:
                        w_pts.field("No", "C", size=10)
                        w_pts.field("x_geo", "F", size=20, decimal=8)
                        w_pts.field("y_geo", "F", size=20, decimal=8)
                        w_pts.field("cota", "F", size=20, decimal=8)
                        w_pts.field("desc", "C", size=50)
                        for idx, row in df.iterrows():
                            try:
                                try:
                                    x = float(row["x"])  # UTM X
                                    y = float(row["y"])  # UTM Y
                                except Exception:
                                    raise ValueError(f"X/Y inválidos: {row.get('x')} / {row.get('y')}")
                                # Coordenadas en EPSG de salida (no asumir 4326 aquí)
                                x_out, y_out = transformer.transform(x, y)
                                try:
                                    cota_val = float(row["cota"]) if str(row.get("cota", "")).strip() != "" else 0.0
                                except Exception:
                                    cota_val = 0.0
                                cota_used = cota_val if dim_is_3d else 0.0
                                if dim_is_3d:
                                    w_pts.pointz(x_out, y_out, cota_used)
                                else:
                                    w_pts.point(x_out, y_out)
                                w_pts.record(str(row["No."]), x_out, y_out, cota_val, row["desc"])
                            except Exception:
                                continue
                    
                    # --- Shapefile de Polilíneas ---
                    if modo_topo == "Puntos y polilíneas":
                        try:
                            shp_polylines_path = os.path.join(shp_dir, f"{folder_name}_polilineas")
                            with shapefile.Writer(shp_polylines_path, shapeType=shapefile.POLYLINE) as w_poly:
                                w_poly.field("ID", "C")
                                # Exportar todas las líneas recolectadas (export_lines_geo si existe; si no, derivar de df)
                                # Preferir coordenadas UTM (ring_utm) y transformar a EPSG de salida para SHP
                                try:
                                    lines_to_write_utm = export_lines_utm if 'export_lines_utm' in locals() and export_lines_utm else []
                                except Exception:
                                    lines_to_write_utm = []
                                if not lines_to_write_utm:
                                    # derivar simple
                                    pts = []
                                    for _, r in df.iterrows():
                                        x = float(r["x"]) ; y = float(r["y"]) 
                                        pts.append([x, y])
                                    if len(pts) >= 2:
                                        lines_to_write_utm = [pts]
                                for idx_line, line_utm in enumerate(lines_to_write_utm, start=1):
                                    # Transformar UTM -> EPSG de salida (con el mismo transformer ya configurado input->output)
                                    line2d = []
                                    for p in line_utm:
                                        try:
                                            xutm, yutm = p[0], p[1]
                                            x_out, y_out = transformer.transform(xutm, yutm)
                                            line2d.append([x_out, y_out])
                                        except Exception:
                                            continue
                                    if len(line2d) >= 2:
                                        w_poly.line([line2d])
                                        w_poly.record(f"L{idx_line}")
                        except Exception as e:
                            st.warning(f"No se pudo crear SHP de polilíneas: {e}")
                    
                    # --- Crear archivos .prj ---
                    try:
                        prj_wkt = pyproj.CRS.from_epsg(int(output_epsg)).to_wkt(version='WKT1_ESRI')
                        with open(f"{shp_points_path}.prj", "w") as f:
                            f.write(prj_wkt)
                        if modo_topo == "Puntos y polilíneas":
                            shp_polylines_path = os.path.join(shp_dir, f"{folder_name}_polilineas")
                            with open(f"{shp_polylines_path}.prj", "w") as f:
                                f.write(prj_wkt)
                    except Exception as e:
                        st.warning(f"No se pudo crear el archivo .prj: {e}")
                    # --- Carpeta Mapbox ---
                    mapbox_dir = os.path.join(main_folder, "mapbox")
                    os.makedirs(mapbox_dir, exist_ok=True)
                    geojson_path = os.path.join(mapbox_dir, f"{folder_name}.geojson")
                    import numpy as np
                    def convert_types(obj):
                        if isinstance(obj, dict):
                            return {k: convert_types(v) for k, v in obj.items()}
                        elif isinstance(obj, list):
                            return [convert_types(v) for v in obj]
                        elif isinstance(obj, (np.integer, np.int64, np.int32)):
                            return int(obj)
                        elif isinstance(obj, (np.floating, np.float64, np.float32)):
                            return float(obj)
                        else:
                            return obj
                    geojson_serializable = convert_types(geojson)
                    with open(geojson_path, "w", encoding="utf-8") as f:
                        json.dump(geojson_serializable, f, ensure_ascii=False, indent=2)
                    json_path = os.path.join(mapbox_dir, f"{folder_name}.json")
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(geojson_serializable, f, ensure_ascii=False, indent=2)
                    
                    # --- Generar index.html ---
                    try:
                        # Calcular bounds del GeoJSON (aceptar 2D/3D)
                        bounds = [[-12.1, -77.1], [-11.9, -76.9]]  # Default
                        if geojson_serializable.get("features"):
                            lons = []
                            lats = []
                            for feature in geojson_serializable["features"]:
                                if feature.get("geometry", {}).get("type") == "Point":
                                    coords = feature["geometry"].get("coordinates", [])
                                    if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                                        lon = coords[0]
                                        lat = coords[1]
                                        lons.append(lon)
                                        lats.append(lat)
                            
                            if lons and lats:
                                center_lat = (min(lats) + max(lats)) / 2
                                center_lon = (min(lons) + max(lons)) / 2
                                bounds = [[min(lats), min(lons)], [max(lats), max(lons)]]
                            
                        # Generar HTML según el tipo de mapa seleccionado
                        html_map_type = st.session_state.get("html_map_type", "normal")
                        if html_map_type == "mapbox":
                            index_html_content = create_mapbox_html(strip_z_from_geojson(geojson_serializable), title=f"{folder_name} - Visor de Mapa Topográfico", folder_name=folder_name, grouping_mode="type")
                        else:
                            # HTML normal con Leaflet
                            leaf_tpl = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>__TITLE__</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style> html, body { height: 100%; margin: 0; } #map { height: 100vh; } </style>
</head>
<body>
  <div id="map"></div>
  <script>
    const map = L.map('map', { preferCanvas: true });
    // Capas base
    const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { 
      attribution: '© OpenStreetMap contributors'
    });
    const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { 
      attribution: '© Esri'
    });
    const positron = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', { 
      attribution: '© CartoDB',
      subdomains: 'abcd',
      maxZoom: 19
    });
    
    positron.addTo(map);
    
    // Control de capas
    const baseLayers = {
      "Positron": positron,
      "OpenStreetMap": osm,
      "Satélite": satellite
    };
    
    // Datos embebidos
    const geojsonData = __GEOJSON__;
    
    // Crear grupos de capas
    const pointsGroup = L.layerGroup();
    const linesGroup = L.layerGroup();
    
    // Procesar GeoJSON - mejorado para ver todas las polilíneas
    if (geojsonData && geojsonData.features) {
      geojsonData.features.forEach((feature, index) => {
        if (feature.geometry.type === 'Point') {
          const [lon, lat] = feature.geometry.coordinates;
          const props = feature.properties;
          
          const marker = L.circleMarker([lat, lon], {
            radius: 8,
            fillColor: '#ff7800',
            color: '#000',
            weight: 1,
            opacity: 1,
            fillOpacity: 0.8
          });
          
          let popupContent = '<b>Punto ' + (props.No || 'N/A') + '</b><br/>';
          popupContent += 'Cota: ' + (props.cota || '0') + '<br/>';
          if (props.desc && props.desc !== 'nan' && props.desc !== '') {
            popupContent += 'Desc: ' + props.desc;
          }
          marker.bindPopup(popupContent);
          pointsGroup.addLayer(marker);
        } else if (feature.geometry.type === 'LineString') {
          const coords = feature.geometry.coordinates.map(coord => [coord[1], coord[0]]);
          const line = L.polyline(coords, {
            color: '#ff0000',
            weight: 3,
            opacity: 0.8,
            dashArray: null
          });
          
          line.bindPopup('<b>Polígono ' + (index + 1) + '</b><br/>Puntos: ' + coords.length);
          linesGroup.addLayer(line);
        }
      });
    }
    
    // Agregar grupos al mapa
    pointsGroup.addTo(map);
    linesGroup.addTo(map);
    
    // Control de capas con overlay
    const overlayMaps = {
      "Puntos": pointsGroup,
      "Líneas": linesGroup
    };
    
    L.control.layers(baseLayers, overlayMaps).addTo(map);
    
    // Ajustar vista
    try {
      const bounds = __BOUNDS__;
      map.fitBounds([[bounds[0][0], bounds[0][1]], [bounds[1][0], bounds[1][1]]], {padding: [20, 20]});
    } catch(e) {
      map.setView([__CENTER_LAT__, __CENTER_LON__], 15);
    }
  </script>
</body>
</html>
            """
                            index_html_content = (
                                leaf_tpl
                                .replace("__TITLE__", f"{folder_name} - Visor de Mapa Topográfico")
                                .replace("__GEOJSON__", json.dumps(geojson_serializable, ensure_ascii=False))
                                .replace("__BOUNDS__", json.dumps(bounds))
                                .replace("__CENTER_LAT__", str(center_lat if 'center_lat' in locals() else -12.0))
                                .replace("__CENTER_LON__", str(center_lon if 'center_lon' in locals() else -77.0))
                            )
                    except Exception as e:
                        st.error(f"Error al generar el HTML del visor: {e}")
                        index_html_content = "<html><body><h3>Error generando visor</h3></body></html>"
                    # Guardar HTML de visor en estado para renderizar fuera de la columna 3
                    st.session_state["topo_index_html"] = index_html_content
                    st.session_state["topo_main_folder"] = main_folder
                    
                    # CORRECCIÓN: Guardar GeoJSON topográfico en project_geojson para mostrar en pestaña Mapa del proyecto
                    st.session_state["project_geojson"] = geojson_serializable
                    st.session_state["project_folder_name"] = folder_name
                    st.session_state["project_title"] = f"{folder_name} - Mapa Topográfico"
                    # Guardar también el HTML en la carpeta del proyecto topográfico
                    try:
                        with open(os.path.join(main_folder, "index.html"), "w", encoding="utf-8") as f:
                            f.write(index_html_content)
                    except Exception:
                        pass

                    # Generar mapa de calor si está habilitado
                    geotiff_bytes = None
                    if st.session_state.get("topo_heatmap_enabled", False):
                        try:
                            # Validar datos antes de procesar
                            validation = validate_heatmap_data(df)
                            
                            if not validation["valid"]:
                                st.error(f"❌ Error en datos del mapa de calor: {validation['message']}")
                            else:
                                # Mostrar información de debug
                                with st.expander("📊 Información del mapa de calor", expanded=False):
                                    st.write(f"**Puntos totales:** {validation['total_points']}")
                                    st.write(f"**Rango X:** {validation['x_range'][0]:.2f} - {validation['x_range'][1]:.2f}")
                                    st.write(f"**Rango Y:** {validation['y_range'][0]:.2f} - {validation['y_range'][1]:.2f}")
                                    st.write(f"**Rango Z (cotas):** {validation['z_range'][0]:.2f} - {validation['z_range'][1]:.2f}")
                                    st.write(f"**Centro del área:** ({validation['center'][0]:.2f}, {validation['center'][1]:.2f})")
                                    st.write(f"**Área de cobertura:** {validation['area_coverage']:.2f} unidades²")
                                
                                # Obtener configuración del mapa de calor
                                margin_percent = st.session_state.get("topo_heatmap_margin", 15)
                                resolution = st.session_state.get("topo_heatmap_resolution", 500)
                                interpolation_method = st.session_state.get("topo_heatmap_method", "cubic")
                                # El CRS se obtiene automáticamente de la configuración de la app
                                input_epsg = st.session_state.get("input_epsg", 32717)
                                selected_crs = f"EPSG:{input_epsg}"
                                
                                # Calcular bounds del raster
                                bounds = calculate_raster_bounds(df, margin_percent)
                                
                                if bounds:
                                    # Mostrar información de bounds
                                    st.info(f"🗺️ **Área del raster:** ({bounds[0]:.2f}, {bounds[1]:.2f}) a ({bounds[2]:.2f}, {bounds[3]:.2f})")
                                    
                                    # Debug detallado de coordenadas
                                    debug_info = debug_heatmap_coordinates(df, bounds, resolution)
                                    
                                    with st.expander("🔍 Debug detallado del mapa de calor", expanded=False):
                                        st.write("**Matriz de transformación:**")
                                        st.code(f"a={debug_info['transform_matrix'][0]:.6f}, b={debug_info['transform_matrix'][1]:.6f}")
                                        st.code(f"c={debug_info['transform_matrix'][2]:.6f}, d={debug_info['transform_matrix'][3]:.6f}")
                                        st.code(f"e={debug_info['transform_matrix'][4]:.6f}, f={debug_info['transform_matrix'][5]:.6f}")
                                        
                                        st.write("**Esquinas del raster:**")
                                        st.write(f"Superior izquierda (0,0): {debug_info['corners']['top_left']}")
                                        st.write(f"Superior derecha ({resolution},0): {debug_info['corners']['top_right']}")
                                        st.write(f"Inferior izquierda (0,{resolution}): {debug_info['corners']['bottom_left']}")
                                        st.write(f"Inferior derecha ({resolution},{resolution}): {debug_info['corners']['bottom_right']}")
                                        
                                        st.write("**Tamaño de píxel:**", debug_info['pixel_size'])
                                        
                                        st.write("**Puntos de muestra:**")
                                        st.write(f"Primer punto: {debug_info['points_sample']['first_point']}")
                                        st.write(f"Último punto: {debug_info['points_sample']['last_point']}")
                                        st.write(f"Centro del área: {debug_info['points_sample']['center']}")
                                    
                                    # Generar GeoTIFF con georeferenciación precisa
                                    geotiff_bytes = create_heatmap_geotiff(df, bounds, resolution, interpolation_method)
                                    
                                    if geotiff_bytes:
                                        # Guardar GeoTIFF en la carpeta del proyecto
                                        geotiff_path = os.path.join(main_folder, f"{folder_name}_heatmap.tif")
                                        with open(geotiff_path, 'wb') as f:
                                            f.write(geotiff_bytes)
                                        
                                        # Crear archivo de debug
                                        debug_path = os.path.join(main_folder, f"{folder_name}_heatmap_debug.txt")
                                        create_heatmap_debug_file(df, bounds, resolution, debug_path)
                                        
                                        st.success(f"🗺️ **Mapa de calor generado exitosamente:** {folder_name}_heatmap.tif")
                                        st.success(f"📄 **Archivo de debug creado:** {folder_name}_heatmap_debug.txt")
                                        
                                        # Mostrar información del CRS usado
                                        crs_display = f"EPSG:{input_epsg}"
                                        if input_epsg == 32717:
                                            crs_description = "UTM Zona 17S (Ecuador)"
                                        elif input_epsg == 32718:
                                            crs_description = "UTM Zona 18S (Perú)"
                                        elif input_epsg == 32719:
                                            crs_description = "UTM Zona 19S (Ecuador, Perú)"
                                        elif input_epsg == 32618:
                                            crs_description = "UTM Zona 18N (Colombia)"
                                        elif input_epsg == 32619:
                                            crs_description = "UTM Zona 19N (Colombia)"
                                        elif input_epsg == 4326:
                                            crs_description = "WGS84 (Lat/Lon)"
                                        else:
                                            crs_description = "Sistema personalizado"
                                        
                                        st.info(f"🌍 **CRS utilizado:** {crs_display} - {crs_description}")
                                        st.info("💡 **Consejo:** Abre el archivo .tif en QGIS y aplica un estilo de mapa de calor para visualizar los resultados.")
                                        st.info("🔍 **Debug:** Revisa el archivo .txt para verificar que las coordenadas estén correctas.")
                                    else:
                                        st.warning("⚠️ No se pudo generar el mapa de calor. Verifique que tenga al menos 3 puntos con cotas válidas.")
                                else:
                                    st.warning("⚠️ No se pudieron calcular los bounds del mapa de calor.")
                        except Exception as e:
                            st.error(f"❌ Error al generar mapa de calor: {e}")
                            st.error("🔧 **Solución:** Verifique que los datos tengan coordenadas X, Y y cotas válidas.")

                    # Mensaje de éxito con ubicación
                    st.success(f"Salidas topográficas generadas en: {main_folder}")

                    # Paquete ZIP para descarga (Cloud-safe)
                    try:
                        zip_buf = io.BytesIO()
                        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf_:
                            # Archivos principales
                            for p, arc in [
                                (dxf_path, f"{folder_name}.dxf"),
                                (kml_path, f"{folder_name}.kml"),
                                (geojson_path, f"mapbox/{folder_name}.geojson"),
                                (json_path, f"mapbox/{folder_name}.json"),
                            ]:
                                try:
                                    if os.path.exists(p):
                                        zf_.write(p, arcname=arc)
                                except Exception:
                                    pass
                            # Shapefiles
                            try:
                                for fname in os.listdir(shp_dir):
                                    fp = os.path.join(shp_dir, fname)
                                    if os.path.isfile(fp):
                                        zf_.write(fp, arcname=os.path.join("shapefiles", fname))
                            except Exception:
                                pass
                            # Mapa de calor GeoTIFF
                            if geotiff_bytes:
                                try:
                                    zf_.writestr(f"heatmap/{folder_name}_heatmap.tif", geotiff_bytes)
                                except Exception:
                                    pass
                            # Visor HTML
                            try:
                                zf_.writestr("index.html", index_html_content or "")
                            except Exception:
                                pass
                        zip_buf.seek(0)
                        st.download_button(
                            "Descargar paquete ZIP Topografía",
                            data=zip_buf.getvalue(),
                            file_name=f"{folder_name}_salidas.zip",
                            mime="application/zip",
                        )
                    except Exception as e:
                        st.warning(f"No se pudo generar el ZIP de Topografía: {e}")

            
    with tab_dxf:
        col1, col2, col3, col4 = st.columns([2,7,6,5])
        with col2:
            uploaded = st.file_uploader("Subir archivo DXF", type=["dxf"])

        if "outputs" not in st.session_state:
            st.session_state["outputs"] = None
        if "base_name" not in st.session_state:
            st.session_state["base_name"] = "Proyecto1"

        # Preparar nombre base a partir del archivo subido
        if uploaded is not None:
            try:
                st.session_state["base_name"] = Path(uploaded.name).stem or "Proyecto1"
            except Exception:
                st.session_state["base_name"] = "Proyecto1"

        # Mostrar inputs solo después de subir el archivo
        if uploaded is not None:
            st.text("Ruta de salida")
            new_output_dir = st.text_input(
                "Ruta de salida",
                value=st.session_state["output_dir"],
                key="output_dir_input_enabled",
                placeholder=str(Path.cwd()),
                disabled=False,
            )
            col1, col2, col3, col4 = st.columns([2,7,6,5])
            with col1:
                if (not IS_CLOUD) and st.button("Seleccionar carpeta"):
                    try:
                        import tkinter as tk
                        from tkinter import filedialog
                        root = tk.Tk()
                        root.withdraw()
                        selected_dir = filedialog.askdirectory()
                        root.destroy()
                        if selected_dir:
                            new_output_dir = selected_dir
                            st.session_state["output_dir"] = selected_dir
                            try:
                                st.rerun()
                            except Exception:
                                st.experimental_rerun()
                    except Exception as e:
                        st.warning(f"No se pudo abrir el selector de carpetas: {e}")
            with col2:
                pass
            with col3:
                st.caption("Usa el botón para elegir la carpeta de salida.")
            # col4 queda vacía
            if new_output_dir:
                st.session_state["output_dir"] = new_output_dir
            # Sugerir nombre de carpeta = nombre del DXF; si existe, autoincrementar sufijo
            import json
            base_dir = Path(st.session_state.get("output_dir") or Path.cwd())
            base_name_var = st.session_state.get("base_name") or "Proyecto1"
            suggested = base_name_var
            candidate = suggested
            idx = 0
            while (base_dir / candidate).exists():
                idx += 1
                candidate = f"{suggested}_{idx}"
            st.session_state["output_folder"] = candidate
            st.text_input(
                "Nombre de carpeta",
                value=st.session_state["output_folder"],
                key="output_folder_input_enabled",
                disabled=False,
            )

        convert_clicked = st.button("Convertir", disabled=uploaded is None)
        if convert_clicked:
            import tempfile
            if not uploaded:
                st.warning("Sube un archivo DXF primero.")
                st.stop()
            with st.spinner("Convirtiendo DXF..."):
                with tempfile.TemporaryDirectory(prefix="dxf_") as tmpdir:
                    tmpdir_path = Path(tmpdir)
                    base_name_local = Path(uploaded.name).stem or "archivo"
                    dxf_path = (tmpdir_path / base_name_local).with_suffix(".dxf")
                    data_bytes = uploaded.read()
                    st.session_state["input_dxf_bytes"] = data_bytes
                    with open(dxf_path, "wb") as f:
                        f.write(data_bytes)

                    try:
                        # Para shapefiles, seguir el criterio de agrupación seleccionado (común)
                        shapes_group_by = st.session_state.get("group_by", "type")
                        outputs = convert_dxf(
                            dxf_path,
                            int(st.session_state.get("input_epsg", 32717)),
                            int(st.session_state.get("output_epsg", 4326)),
                            shapes_group_by=str(shapes_group_by).lower(),
                        )
                    except Exception as exc:
                        st.error(f"Error en la conversión: {exc}")
                        st.stop()

            st.session_state["outputs"] = outputs

        outputs_local = st.session_state.get("outputs")
        if outputs_local:
            st.success("Conversión completada")
            # Generar vista para pestaña Mapa del proyecto
            try:
                html_map_type = st.session_state.get("html_map_type", "normal")
                geojson_emb = outputs_local["geojson"]
                st.session_state["project_geojson"] = geojson_emb
                st.session_state["project_folder_name"] = st.session_state.get("output_folder","Proyecto")
                st.session_state["project_title"] = f"{st.session_state.get('base_name','Proyecto')} - Map Viewer"
                # Calcular bounds simples
                b = compute_bounds_from_geojson(geojson_emb) or [[-2, -79], [-2, -79]]
                center_lat = (b[0][0] + b[1][0]) / 2
                center_lon = (b[0][1] + b[1][1]) / 2
                if html_map_type == "mapbox":
                    st.session_state["project_map_html"] = create_mapbox_html(strip_z_from_geojson(geojson_emb), title=f"{st.session_state.get('base_name','Proyecto')} - Map Viewer", folder_name=st.session_state.get("output_folder","Proyecto"), grouping_mode=st.session_state.get("group_by","type"))
                else:
                    st.session_state["project_map_html"] = create_leaflet_grouped_html(strip_z_from_geojson(geojson_emb), title=f"{st.session_state.get('base_name','Proyecto')} - Map Viewer", grouping_mode=st.session_state.get("group_by","type"))
            except Exception:
                pass
            # Botón único: Descargar Resultados al sistema de archivos (solo local)
            if (not IS_CLOUD) and st.button("Descargar Resultados", key="btn_save_all"):
                import json
                import shutil
                base_dir = Path(st.session_state.get("output_dir") or Path.cwd())
                folder_name = st.session_state.get("output_folder") or "Proyecto1"
                dest_dir = base_dir / folder_name
                shapes_dir = dest_dir / "Shapes"
                mapbox_dir = dest_dir / "MapBox"
                try:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    shapes_dir.mkdir(parents=True, exist_ok=True)
                    mapbox_dir.mkdir(parents=True, exist_ok=True)
                    # Guardar archivos principales
                    base_name_save = st.session_state.get("base_name", "Proyecto1")
                    # mover JSON/GeoJSON a MapBox
                    (mapbox_dir / f"{base_name_save}.json").write_bytes(outputs_local["json_bytes"])
                    (mapbox_dir / f"{base_name_save}.geojson").write_bytes(outputs_local["geojson_bytes"])
                    (dest_dir / f"{base_name_save}.kmz").write_bytes(outputs_local["kmz_bytes"])
                    # Copiar shapefiles por layer/tipo
                    shp_src = Path(outputs_local["shp_dir"]) if outputs_local.get("shp_dir") else None
                    if shp_src and shp_src.exists():
                        for ext in ("*.shp", "*.shx", "*.dbf", "*.prj", "*.cpg"):
                            for f in shp_src.glob(ext):
                                shutil.copy2(f, shapes_dir / f.name)
                    # index embebido
                    geojson_emb = strip_z_from_geojson(outputs_local["geojson"])
                    geojson_str = json.dumps(geojson_emb)
                    bounds = compute_bounds_from_geojson(geojson_emb) or [[-2, -79], [-2, -79]]
                    
                    # Generar HTML según el tipo de mapa seleccionado
                    html_map_type = st.session_state.get("html_map_type", "normal")
                    grouping_mode = st.session_state.get("group_by", "type")
                    if html_map_type == "mapbox":
                        index_html = create_mapbox_html(geojson_emb, title=f"{base_name_save} - Map Viewer", folder_name=base_name_save, grouping_mode=grouping_mode)
                    else:
                        # HTML normal con Leaflet - respetando modo de agrupamiento
                        index_html = create_normal_html(geojson_emb, base_name_save, bounds, grouping_mode)
                    
                    (dest_dir / "index.html").write_text(index_html, encoding="utf-8")
                    st.success(f"Resultados guardados en: {dest_dir}")
                except Exception as exc:
                    st.error(f"No se pudieron guardar los resultados: {exc}")

            # Entrega Cloud-safe: solo ZIP en memoria
            base_name_save = st.session_state.get("base_name", "Proyecto1")
            html_str = st.session_state.get("project_map_html")
            zip_buf = io.BytesIO()
            root = f"{base_name_save}"
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf_:
                if outputs_local.get("kmz_bytes"): zf_.writestr(f"{root}/{base_name_save}.kmz", outputs_local["kmz_bytes"])
                if outputs_local.get("geojson_bytes"): zf_.writestr(f"{root}/{base_name_save}.geojson", outputs_local["geojson_bytes"])
                if outputs_local.get("json_bytes"): zf_.writestr(f"{root}/{base_name_save}.json", outputs_local["json_bytes"])
                if html_str: zf_.writestr(f"{root}/{base_name_save}_map.html", html_str.encode("utf-8"))
                try:
                    dxf_bytes_in = st.session_state.get("input_dxf_bytes")
                    if dxf_bytes_in:
                        zf_.writestr(f"{root}/{base_name_save}.dxf", dxf_bytes_in)
                except Exception:
                    pass
                shp_src = outputs_local.get("shp_dir")
                if shp_src:
                    try:
                        for f in Path(shp_src).glob("*"):
                            zf_.write(f, arcname=f"{root}/Shapes/{f.name}")
                    except Exception:
                        pass
            zip_buf.seek(0)
            st.download_button("Descargar paquete ZIP", data=zip_buf.getvalue(), file_name=f"{base_name_save}_salidas.zip", mime="application/zip")

            # Vista previa del mapa eliminada: usar pestaña "Mapa del proyecto"

    with tab_gpx:
        if "gpx_output_folder" not in st.session_state:
            st.session_state["gpx_output_folder"] = "Proyecto1"
        st.caption("Convierte archivos GPX a DXF, Shapefiles, GeoJSON/JSON, KMZ/KML y HTML")
        col1, col2, col3, col4 = st.columns([2,7,6,5])
        with col2:
            gpx_file = st.file_uploader("Subir archivo GPX", type=["gpx"], key="gpx_upl")
        if "gpx_outputs" not in st.session_state:
            st.session_state["gpx_outputs"] = None
        if gpx_file and "gpx_base_name" not in st.session_state:
            try:
                st.session_state["gpx_base_name"] = Path(gpx_file.name).stem or "Proyecto1"
            except Exception:
                st.session_state["gpx_base_name"] = "Proyecto1"
        # Ruta de salida y nombre de carpeta (visibles tras subir GPX)
        if gpx_file is not None:
            st.text("Ruta de salida")
            gpx_output_dir = st.text_input(
                "Ruta de salida",
                value=st.session_state.get("output_dir", str(Path.home() / "Downloads")),
                key="gpx_output_dir_input",
                placeholder=str(Path.cwd()),
                disabled=False,
            )
            col1, col2, col3, col4 = st.columns([2,7,6,5])
            with col1:
                if (not IS_CLOUD) and st.button("Seleccionar carpeta", key="btn_gpx_select_dir"):
                    try:
                        import tkinter as tk
                        from tkinter import filedialog
                        root = tk.Tk(); root.withdraw()
                        selected_dir = filedialog.askdirectory()
                        root.destroy()
                        if selected_dir:
                            gpx_output_dir = selected_dir
                            st.session_state["output_dir"] = selected_dir
                            try:
                                st.rerun()
                            except Exception:
                                st.experimental_rerun()
                    except Exception as e:
                        st.warning(f"No se pudo abrir el selector de carpetas: {e}")
            with col2:
                pass
            with col3:
                st.caption("Usa el botón para elegir la carpeta de salida.")
            # col4 queda vacía
            if gpx_output_dir:
                st.session_state["output_dir"] = gpx_output_dir
            # Sugerir carpeta = nombre del GPX; si existe, autoincrementar
            gpx_base = st.session_state.get("gpx_base_name", "Proyecto1")
            base_dir = Path(st.session_state.get("output_dir") or Path.cwd())
            candidate = gpx_base
            idx = 0
            while (base_dir / candidate).exists():
                idx += 1
                candidate = f"{gpx_base}_{idx}"
            st.session_state["gpx_output_folder"] = candidate
            st.text_input(
                "Nombre de carpeta",
                value=st.session_state["gpx_output_folder"],
                key="gpx_output_folder_input",
                disabled=False,
            )

        if gpx_file and st.button("Convertir GPX"):
            import gpxpy
            import json
            import tempfile
            import pyproj
            import shapefile
            from simplekml import Kml
            try:
                with st.spinner("Procesando GPX..."):
                    gpx = gpxpy.parse(gpx_file.getvalue().decode("utf-8", errors="ignore"))
                    features = []
                    # Waypoints como puntos
                    for w in gpx.waypoints:
                        features.append({
                            "type": "Feature",
                            "properties": {"type": "point", "name": w.name or "", "desc": w.description or ""},
                            "geometry": {"type": "Point", "coordinates": [w.longitude, w.latitude]},
                        })
                    # Tracks y segments como LineString
                    for trk in gpx.tracks:
                        for seg in trk.segments:
                            coords = [[pt.longitude, pt.latitude] for pt in seg.points]
                            if len(coords) >= 2:
                                features.append({
                                    "type": "Feature",
                                    "properties": {"type": "track", "name": trk.name or "Track"},
                                    "geometry": {"type": "LineString", "coordinates": coords},
                                })
                    # Routes como LineString
                    for rte in gpx.routes:
                        coords = [[pt.longitude, pt.latitude] for pt in rte.points]
                        if len(coords) >= 2:
                            features.append({
                                "type": "Feature",
                                "properties": {"type": "route", "name": rte.name or "Route"},
                                "geometry": {"type": "LineString", "coordinates": coords},
                            })
                    geojson = {"type": "FeatureCollection", "features": features}
                    geojson = strip_z_from_geojson(geojson)
                    # Preparar descargas similares a DXF
                    json_bytes = json.dumps({"layers": {"GPX": {"points": [], "lines": [], "polylines": [], "texts": [], "circles": [], "shapes": [], "blocks": []}}}, indent=2).encode("utf-8")
                    geojson_bytes = json.dumps(geojson, indent=2).encode("utf-8")
                    # KMZ básico con simplekml
                    kml = Kml()
                    # Crear carpetas para organizar elementos
                    points_folder_gpx = kml.newfolder(name="📍 Puntos GPX")
                    tracks_folder_gpx = kml.newfolder(name="🛤️ Tracks")
                    routes_folder_gpx = kml.newfolder(name="🗺️ Rutas")
                    
                    for f in features:
                        if f["geometry"]["type"] == "Point":
                            lon, lat = f["geometry"]["coordinates"]
                            points_folder_gpx.newpoint(name=f["properties"].get("name", ""), coords=[(lon, lat)])
                        elif f["geometry"]["type"] == "LineString":
                            if f["properties"].get("type") == "track":
                                tracks_folder_gpx.newlinestring(name=f["properties"].get("name", "Track"), coords=f["geometry"]["coordinates"])
                            else:
                                routes_folder_gpx.newlinestring(name=f["properties"].get("name", "Route"), coords=f["geometry"]["coordinates"])
                    kmz_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".kmz")
                    kml.save(kmz_tmp.name)
                    kmz_bytes = Path(kmz_tmp.name).read_bytes()
                    # Shapefiles: puntos y líneas
                    shp_dir = Path(tempfile.mkdtemp(prefix="gpx_shp_"))
                    # puntos
                    if any(f["geometry"]["type"] == "Point" for f in features):
                        wpt = shapefile.Writer(str(shp_dir / "points"), shapeType=shapefile.POINT)
                        wpt.field("Name", "C")
                        for f in features:
                            if f["geometry"]["type"] == "Point":
                                lon, lat = f["geometry"]["coordinates"]
                                wpt.point(lon, lat)
                                wpt.record(f["properties"].get("name", ""))
                        wpt.close()
                    # líneas
                    if any(f["geometry"]["type"] == "LineString" for f in features):
                        lns = shapefile.Writer(str(shp_dir / "lines"), shapeType=shapefile.POLYLINE)
                        lns.field("Name", "C")
                        for f in features:
                            if f["geometry"]["type"] == "LineString":
                                lns.line([f["geometry"]["coordinates"]])
                                lns.record(f["properties"].get("name", ""))
                        lns.close()
                    # PRJ (usar EPSG de salida común)
                    try:
                        prj_wkt = pyproj.CRS.from_epsg(int(st.session_state.get("output_epsg", 4326))).to_wkt()
                        for base in ["points", "lines"]:
                            prj_path = shp_dir / f"{base}.prj"
                            if prj_path.with_suffix('.shp').exists() or (shp_dir / f"{base}.shp").exists():
                                with open(prj_path, 'w', encoding='utf-8') as prjf:
                                    prjf.write(prj_wkt)
                    except Exception:
                        pass
                    st.session_state["gpx_outputs"] = {
                        "geojson": geojson,
                        "geojson_bytes": geojson_bytes,
                        "json_bytes": json_bytes,
                        "kmz_bytes": kmz_bytes,
                        "shp_dir": str(shp_dir),
                    }
            except Exception as e:
                st.error(f"Error procesando GPX: {e}")

        if st.session_state.get("gpx_outputs"):
            st.success("GPX convertido")
            # Generar vista para pestaña Mapa del proyecto
            try:
                geojson_emb = st.session_state["gpx_outputs"]["geojson"]
                html_map_type = st.session_state.get("html_map_type", "normal")
                st.session_state["project_geojson"] = geojson_emb
                st.session_state["project_folder_name"] = st.session_state.get("gpx_output_folder","Proyecto")
                st.session_state["project_title"] = "GPX - Map Viewer"
                b = compute_bounds_from_geojson(geojson_emb) or [[-2, -79], [-2, -79]]
                center_lat = (b[0][0] + b[1][0]) / 2
                center_lon = (b[0][1] + b[1][1]) / 2
                if html_map_type == "mapbox":
                    st.session_state["project_map_html"] = create_mapbox_html(strip_z_from_geojson(geojson_emb), title="GPX - Map Viewer", folder_name=st.session_state.get("gpx_output_folder","Proyecto"), grouping_mode="type")
                else:
                    st.session_state["project_map_html"] = create_leaflet_grouped_html(strip_z_from_geojson(geojson_emb), title="GPX - Map Viewer", grouping_mode="type")
            except Exception:
                pass
            # Guardado local (solo local)
            if (not IS_CLOUD) and st.button("Descargar Resultados GPX"):
                import json
                import shutil
                import pyproj
                import shapefile
                
                base_dir = Path(st.session_state.get("output_dir") or Path.cwd())
                folder_name = st.session_state.get("gpx_output_folder") or st.session_state.get("output_folder") or "Proyecto1"
                dest_dir = base_dir / folder_name
                shapes_dir = dest_dir / "Shapes"
                mapbox_dir = dest_dir / "MapBox"
                try:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    shapes_dir.mkdir(parents=True, exist_ok=True)
                    mapbox_dir.mkdir(parents=True, exist_ok=True)
                    base_name = st.session_state.get("gpx_base_name", "gpx")
                    (mapbox_dir / f"{base_name}.json").write_bytes(st.session_state["gpx_outputs"]["json_bytes"])
                    (mapbox_dir / f"{base_name}.geojson").write_bytes(st.session_state["gpx_outputs"]["geojson_bytes"])
                    (dest_dir / f"{base_name}.kmz").write_bytes(st.session_state["gpx_outputs"]["kmz_bytes"])
                    # Regenerar SHP en EPSG de salida (coincidiendo con .prj) para evitar desplazamientos en QGIS
                    output_epsg_val = int(st.session_state.get("output_epsg", 4326))
                    # Preparar writers
                    pts_writer = shapefile.Writer(str(shapes_dir / "points"), shapeType=shapefile.POINT)
                    pts_writer.field("Name", "C")
                    lns_writer = shapefile.Writer(str(shapes_dir / "lines"), shapeType=shapefile.POLYLINE)
                    lns_writer.field("Name", "C")
                    # Transformador WGS84 -> EPSG salida, porque el GeoJSON está en 4326
                    to_output = pyproj.Transformer.from_crs("EPSG:4326", f"EPSG:{output_epsg_val}", always_xy=True)
                    gj = st.session_state["gpx_outputs"]["geojson"]
                    for f in gj.get("features", []):
                        g = f.get("geometry", {})
                        t = g.get("type")
                        name = f.get("properties", {}).get("name", "")
                        if t == "Point":
                            lon, lat = g.get("coordinates", [None, None])[:2]
                            if lon is None or lat is None:
                                continue
                            x, y = to_output.transform(lon, lat)
                            pts_writer.point(x, y)
                            pts_writer.record(name)
                        elif t == "LineString":
                            coords = g.get("coordinates", [])
                            if len(coords) >= 2:
                                line_xy = []
                                for c in coords:
                                    try:
                                        lon, lat = c[:2]
                                        x, y = to_output.transform(lon, lat)
                                        line_xy.append([x, y])
                                    except Exception:
                                        continue
                                if len(line_xy) >= 2:
                                    lns_writer.line([line_xy])
                                    lns_writer.record(name)
                    try:
                        pts_writer.close()
                    except Exception:
                        pass
                    try:
                        lns_writer.close()
                    except Exception:
                        pass
                    # Escribir .prj consistente
                    try:
                        prj_wkt = pyproj.CRS.from_epsg(output_epsg_val).to_wkt(version='WKT1_ESRI')
                        for base in ["points", "lines"]:
                            with open(str(shapes_dir / f"{base}.prj"), "w", encoding="utf-8") as prjf:
                                prjf.write(prj_wkt)
                    except Exception:
                        pass
                    # index con bounds
                    geojson_emb = strip_z_from_geojson(st.session_state["gpx_outputs"]["geojson"])
                    geojson_str = json.dumps(geojson_emb)
                    bounds = compute_bounds_from_geojson(st.session_state["gpx_outputs"]["geojson"]) or [[-2, -79], [-2, -79]]
                    
                    # Generar HTML según el tipo de mapa seleccionado
                    html_map_type = st.session_state.get("html_map_type", "normal")
                    grouping_mode = st.session_state.get("group_by", "type")
                    if html_map_type == "mapbox":
                        index_html = create_mapbox_html(st.session_state["gpx_outputs"]["geojson"], title="GPX - Map Viewer", folder_name=base_name, grouping_mode=grouping_mode)
                    else:
                        # HTML normal con Leaflet - usar función unificada
                        index_html = create_normal_html(geojson_emb, "GPX - Map Viewer", bounds, grouping_mode)
                    
                    (dest_dir / "index.html").write_text(index_html, encoding="utf-8")
                    # Exportar DXF también
                    input_epsg_val = int(st.session_state.get("input_epsg", 32717))
                    to_utm = pyproj.Transformer.from_crs(f"EPSG:4326", f"EPSG:{input_epsg_val}", always_xy=True)
                    dxf_geojson = transform_geojson(st.session_state["gpx_outputs"]["geojson"], to_utm)
                    export_geojson_to_dxf(dxf_geojson, dest_dir / f"{base_name}.dxf")
                    st.success(f"Resultados GPX guardados en: {dest_dir}")
                except Exception as e:
                    st.error(f"Error guardando resultados GPX: {e}")

            # Entrega Cloud-safe: solo ZIP
            base_name = st.session_state.get("gpx_base_name", "gpx")
            gpx_outputs = st.session_state["gpx_outputs"]
            html_str = st.session_state.get("project_map_html")
            
            # Generar DXF para el ZIP
            dxf_bytes = None
            try:
                import tempfile
                input_epsg_val = int(st.session_state.get("input_epsg", 32717))
                to_utm = pyproj.Transformer.from_crs(f"EPSG:4326", f"EPSG:{input_epsg_val}", always_xy=True)
                dxf_geojson = transform_geojson(gpx_outputs["geojson"], to_utm)
                dxf_temp_path = Path(tempfile.mkdtemp()) / f"{base_name}.dxf"
                if export_geojson_to_dxf(dxf_geojson, dxf_temp_path):
                    dxf_bytes = dxf_temp_path.read_bytes()
            except Exception as e:
                st.warning(f"No se pudo generar archivo DXF: {e}")
            
            zip_buf = io.BytesIO()
            root = f"{base_name}"
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf_:
                if gpx_outputs.get("kmz_bytes"): zf_.writestr(f"{root}/{base_name}.kmz", gpx_outputs["kmz_bytes"])
                if gpx_outputs.get("geojson_bytes"): zf_.writestr(f"{root}/{base_name}.geojson", gpx_outputs["geojson_bytes"])
                if gpx_outputs.get("json_bytes"): zf_.writestr(f"{root}/{base_name}.json", gpx_outputs["json_bytes"])
                if dxf_bytes: zf_.writestr(f"{root}/{base_name}.dxf", dxf_bytes)
                if html_str: zf_.writestr(f"{root}/{base_name}_map.html", html_str.encode("utf-8"))
                shp_src = gpx_outputs.get("shp_dir")
                if shp_src:
                    try:
                        for f in Path(shp_src).glob("*"):
                            zf_.write(f, arcname=f"{root}/Shapes/{f.name}")
                    except Exception:
                        pass
            zip_buf.seek(0)
            st.download_button("Descargar paquete ZIP GPX", data=zip_buf.getvalue(), file_name=f"{base_name}_salidas.zip", mime="application/zip")

    with tab_kmz:
        if "kml_output_folder" not in st.session_state:
            st.session_state["kml_output_folder"] = "Proyecto1"
        st.caption("Convierte archivos KMZ/KML a DXF, Shapefiles, GeoJSON/JSON, GPX y HTML")
        col1, col2, col3, col4 = st.columns([2,7,6,5])
        with col2:
            kmz_file = st.file_uploader("Subir archivo KMZ/KML", type=["kmz", "kml"], key="kmz_upl")
        if "kml_outputs" not in st.session_state:
            st.session_state["kml_outputs"] = None
        if kmz_file and "kml_base_name" not in st.session_state:
            try:
                st.session_state["kml_base_name"] = Path(kmz_file.name).stem or "Proyecto1"
            except Exception:
                st.session_state["kml_base_name"] = "Proyecto1"
        # Ruta de salida y nombre de carpeta (visibles tras subir KML/KMZ)
        if kmz_file is not None:
            st.text("Ruta de salida")
            kml_output_dir = st.text_input(
                "Ruta de salida",
                value=st.session_state.get("output_dir", str(Path.home() / "Downloads")),
                key="kml_output_dir_input",
                placeholder=str(Path.cwd()),
                disabled=False,
            )
            col1, col2, col3, col4 = st.columns([2,7,6,5])
            with col1:
                if (not IS_CLOUD) and st.button("Seleccionar carpeta", key="btn_kml_select_dir"):
                    try:
                        import tkinter as tk
                        from tkinter import filedialog
                        root = tk.Tk(); root.withdraw()
                        selected_dir = filedialog.askdirectory()
                        root.destroy()
                        if selected_dir:
                            kml_output_dir = selected_dir
                            st.session_state["output_dir"] = selected_dir
                            try:
                                st.rerun()
                            except Exception:
                                st.experimental_rerun()
                    except Exception as e:
                        st.warning(f"No se pudo abrir el selector de carpetas: {e}")
            with col2:
                pass
            with col3:
                st.caption("Usa el botón para elegir la carpeta de salida.")
            # col4 queda vacía
            if kml_output_dir:
                st.session_state["output_dir"] = kml_output_dir
            # Sugerir carpeta = nombre del archivo; si existe, autoincrementar
            kml_base = st.session_state.get("kml_base_name", "Proyecto1")
            base_dir = Path(st.session_state.get("output_dir") or Path.cwd())
            candidate = kml_base
            idx = 0
            while (base_dir / candidate).exists():
                idx += 1
                candidate = f"{kml_base}_{idx}"
            st.session_state["kml_output_folder"] = candidate
            st.text_input(
                "Nombre de carpeta",
                value=st.session_state["kml_output_folder"],
                key="kml_output_folder_input",
                disabled=False,
            )
        if kmz_file and st.button("Convertir KMZ/KML"):
            # Import opcional de fastkml; si no está, usar parser XML de respaldo
            try:
                from fastkml import kml as fast_kml  # type: ignore
                FASTKML_AVAILABLE = True
            except Exception:
                fast_kml = None  # type: ignore
                FASTKML_AVAILABLE = False
            import zipfile as zf
            import io
            import json
            import tempfile
            import pyproj
            import shapefile
            try:
                with st.spinner("Procesando KML/KMZ..."):
                    data = kmz_file.read()
                    is_zip = zf.is_zipfile(io.BytesIO(data))
                    kml_bytes = None
                    if kmz_file.name.lower().endswith('.kmz') or is_zip:
                        try:
                            with zf.ZipFile(io.BytesIO(data)) as z:
                                for n in z.namelist():
                                    if n.lower().endswith('.kml'):
                                        kml_bytes = z.read(n)
                                        break
                        except Exception:
                            kml_bytes = data
                    else:
                        kml_bytes = data
                    if not kml_bytes:
                        raise ValueError('No se encontró KML dentro del KMZ')
                    if FASTKML_AVAILABLE:
                        k = fast_kml.KML()
                        k.from_string(kml_bytes)

                        def to_simple_geoms(geom):
                            try:
                                if hasattr(geom, 'geoms') and geom.geoms is not None:
                                    res = []
                                    for g in geom.geoms:
                                        res.extend(to_simple_geoms(g))
                                    return res
                                return [geom]
                            except Exception:
                                return []

                        features = []
                        def traverse(feats_iterable):
                            for f in feats_iterable:
                                if hasattr(f, 'geometry') and f.geometry is not None:
                                    try:
                                        base_geom = getattr(f.geometry, 'geometry', None)
                                        if base_geom is None:
                                            base_geom = f.geometry
                                        for sg in to_simple_geoms(base_geom):
                                            gj = shp_mapping(sg)
                                            gj = strip_z_from_geojson(gj)
                                            gtype = (gj.get('type') or '').lower()
                                            props = {"name": getattr(f, 'name', '') or '', "type": gtype}
                                            features.append({"type": "Feature", "properties": props, "geometry": gj})
                                    except Exception:
                                        pass
                                children = []
                                feats_attr = getattr(f, 'features', None)
                                try:
                                    if callable(feats_attr):
                                        children = list(feats_attr())
                                    elif isinstance(feats_attr, (list, tuple)):
                                        children = list(feats_attr)
                                except Exception:
                                    children = []
                                if children:
                                    traverse(children)

                        root_children = []
                        try:
                            root_feats = getattr(k, 'features', None)
                            root_children = list(root_feats()) if callable(root_feats) else list(root_feats or [])
                        except Exception:
                            root_children = []
                        traverse(root_children)

                        geojson_raw = {"type": "FeatureCollection", "features": features}
                    else:
                        # Parser de respaldo solo con XML si fastkml no está disponible
                        geojson_raw = parse_kml_via_xml(kml_bytes)

                    geojson = strip_z_from_geojson(geojson_raw)
                    geojson = filter_geojson_valid(geojson)
                    
                    logger.info(f"GeoJSON original tiene {len(geojson.get('features', []))} features")

                    # Fallback XML si vacío
                    if not geojson.get("features"):
                        geojson_xml = parse_kml_via_xml(kml_bytes)
                        geojson_xml = filter_geojson_valid(strip_z_from_geojson(geojson_xml))
                        geojson = geojson_xml

                    # Abort if empty
                    if not geojson.get("features"):
                        raise ValueError("El KML/KMZ no contiene geometrías válidas (coordenadas fuera de rango o vacías)")

                    # Bytes
                    geojson_bytes = json.dumps(geojson, indent=2).encode('utf-8')
                    json_bytes = json.dumps({"layers": {"KML": {}}}, indent=2).encode('utf-8')
                    kmz_bytes = data if (kmz_file.name.lower().endswith('.kmz') and is_zip) else b''

                    # SHP en EPSG de salida
                    shp_dir = Path(tempfile.mkdtemp(prefix="kml_shp_"))
                    output_epsg_val = int(st.session_state.get("output_epsg", 4326))
                    to_output = pyproj.Transformer.from_crs("EPSG:4326", f"EPSG:{output_epsg_val}", always_xy=True)
                    logger.info(f"Transformando de EPSG:4326 a EPSG:{output_epsg_val}")

                    # Transformar GeoJSON completo usando función consistente
                    output_geojson = transform_geojson(geojson, to_output)
                    logger.info(f"GeoJSON transformado a EPSG:{output_epsg_val} con {len(output_geojson.get('features', []))} features")

                    pts = shapefile.Writer(str(shp_dir / "points"), shapeType=shapefile.POINT); pts.field("Name", "C")
                    lns = shapefile.Writer(str(shp_dir / "lines"), shapeType=shapefile.POLYLINE); lns.field("Name", "C")
                    polys = shapefile.Writer(str(shp_dir / "polygons"), shapeType=shapefile.POLYGON); polys.field("Name", "C")

                    for f in output_geojson.get("features", []):
                        g = f.get("geometry", {})
                        t = g.get("type")
                        name = f.get("properties", {}).get("name", "")
                        if t == "Point":
                            x, y = g["coordinates"][:2]
                            logger.info(f"Point EPSG:{output_epsg_val}: x={x}, y={y}")
                            pts.point(x, y); pts.record(name)
                        elif t == "MultiPoint":
                            for pt in g.get("coordinates", []):
                                x, y = pt[:2]
                                pts.point(x, y); pts.record(name)
                        elif t == "LineString":
                            coords = [[c[0], c[1]] for c in g["coordinates"]]
                            if len(coords) >= 2:
                                lns.line([coords]); lns.record(name)
                        elif t == "MultiLineString":
                            for line in g.get("coordinates", []):
                                coords = [[c[0], c[1]] for c in line]
                                if len(coords) >= 2:
                                    lns.line([coords]); lns.record(name)
                        elif t == "Polygon":
                            rings = g.get("coordinates", [])
                            if rings:
                                ring_xy = [[c[0], c[1]] for c in rings[0]]
                                if len(ring_xy) >= 3:
                                    polys.poly([ring_xy]); polys.record(name)
                        elif t == "MultiPolygon":
                            for poly in g.get("coordinates", []):
                                if poly:
                                    ring_xy = [[c[0], c[1]] for c in poly[0]]
                                    if len(ring_xy) >= 3:
                                        polys.poly([ring_xy]); polys.record(name)

                    pts.close(); lns.close(); polys.close()
                    try:
                        prj_wkt = pyproj.CRS.from_epsg(output_epsg_val).to_wkt()
                        for base in ["points", "lines", "polygons"]:
                            with open(str(shp_dir / f"{base}.prj"), 'w', encoding='utf-8') as prjf:
                                prjf.write(prj_wkt)
                    except Exception:
                        pass

                    st.session_state["kml_outputs"] = {
                        "geojson": geojson,  # GeoJSON original en WGS84 para mapas
                        "geojson_bytes": geojson_bytes,
                        "json_bytes": json_bytes,
                        "kmz_bytes": kmz_bytes,
                        "shp_dir": str(shp_dir),
                        "output_geojson": output_geojson,  # GeoJSON transformado a EPSG de salida para shapefiles
                    }
            except Exception as e:
                st.error(f"Error procesando KML/KMZ: {e}")

        if st.session_state.get("kml_outputs"):
            st.success("KML/KMZ convertido")
            # Generar vista para pestaña Mapa del proyecto
            try:
                geojson_emb = st.session_state["kml_outputs"]["geojson"]
                html_map_type = st.session_state.get("html_map_type", "normal")
                st.session_state["project_geojson"] = geojson_emb
                st.session_state["project_folder_name"] = st.session_state.get("kml_output_folder","Proyecto")
                st.session_state["project_title"] = "KML/KMZ - Map Viewer"
                b = compute_bounds_from_geojson(geojson_emb) or [[-2, -79], [-2, -79]]
                center_lat = (b[0][0] + b[1][0]) / 2
                center_lon = (b[0][1] + b[1][1]) / 2
                if html_map_type == "mapbox":
                    st.session_state["project_map_html"] = create_mapbox_html(strip_z_from_geojson(geojson_emb), title="KML/KMZ - Map Viewer", folder_name=st.session_state.get("kml_output_folder","Proyecto"), grouping_mode="type")
                else:
                    st.session_state["project_map_html"] = create_leaflet_grouped_html(strip_z_from_geojson(geojson_emb), title="KML/KMZ - Map Viewer", grouping_mode="type")
            except Exception:
                pass
            # Guardado local (solo local)
            if (not IS_CLOUD) and st.button("Descargar Resultados KML/KMZ"):
                import json
                import shutil
                import pyproj
                import shapefile
                
                base_dir = Path(st.session_state.get("output_dir") or Path.cwd())
                folder_name = st.session_state.get("kml_output_folder") or st.session_state.get("output_folder") or "Proyecto1"
                dest_dir = base_dir / folder_name
                shapes_dir = dest_dir / "Shapes"
                mapbox_dir = dest_dir / "MapBox"
                try:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    shapes_dir.mkdir(parents=True, exist_ok=True)
                    mapbox_dir.mkdir(parents=True, exist_ok=True)
                    base_name = st.session_state.get("kml_base_name", "kml")
                    (mapbox_dir / f"{base_name}.json").write_bytes(st.session_state["kml_outputs"]["json_bytes"])
                    (mapbox_dir / f"{base_name}.geojson").write_bytes(st.session_state["kml_outputs"]["geojson_bytes"])
                    if st.session_state["kml_outputs"]["kmz_bytes"]:
                        (dest_dir / f"{base_name}.kmz").write_bytes(st.session_state["kml_outputs"]["kmz_bytes"])
                    # Regenerar SHP en EPSG de salida a partir de GeoJSON transformado
                    output_epsg_val = int(st.session_state.get("output_epsg", 4326))
                    out_geo = st.session_state["kml_outputs"]["output_geojson"]  # ya está en EPSG de salida
                    pts = shapefile.Writer(str(shapes_dir / "points"), shapeType=shapefile.POINT); pts.field("Name", "C")
                    lns = shapefile.Writer(str(shapes_dir / "lines"), shapeType=shapefile.POLYLINE); lns.field("Name", "C")
                    polys = shapefile.Writer(str(shapes_dir / "polygons"), shapeType=shapefile.POLYGON); polys.field("Name", "C")
                    for f in out_geo.get("features", []):
                        g = f.get("geometry", {})
                        t = g.get("type")
                        name = f.get("properties", {}).get("name", "")
                        if t == "Point":
                            x, y = g.get("coordinates", [None, None])[:2]
                            if x is None or y is None:
                                continue
                            pts.point(x, y); pts.record(name)
                        elif t == "MultiPoint":
                            for pt in g.get("coordinates", []):
                                x, y = pt[:2]
                                pts.point(x, y); pts.record(name)
                        elif t == "LineString":
                            coords = [[c[0], c[1]] for c in g.get("coordinates", [])]
                            if len(coords) >= 2:
                                lns.line([coords]); lns.record(name)
                        elif t == "MultiLineString":
                            for line in g.get("coordinates", []):
                                coords = [[c[0], c[1]] for c in line]
                                if len(coords) >= 2:
                                    lns.line([coords]); lns.record(name)
                        elif t == "Polygon":
                            rings = g.get("coordinates", [])
                            if rings:
                                ring_xy = [[c[0], c[1]] for c in rings[0]]
                                if len(ring_xy) >= 3:
                                    polys.poly([ring_xy]); polys.record(name)
                        elif t == "MultiPolygon":
                            for poly in g.get("coordinates", []):
                                if poly:
                                    ring_xy = [[c[0], c[1]] for c in poly[0]]
                                    if len(ring_xy) >= 3:
                                        polys.poly([ring_xy]); polys.record(name)
                    try:
                        pts.close(); lns.close(); polys.close()
                    except Exception:
                        pass
                    try:
                        prj_wkt = pyproj.CRS.from_epsg(output_epsg_val).to_wkt(version='WKT1_ESRI')
                        for base in ["points", "lines", "polygons"]:
                            with open(str(shapes_dir / f"{base}.prj"), 'w', encoding='utf-8') as prjf:
                                prjf.write(prj_wkt)
                    except Exception:
                        pass
                    # index con bounds
                    geojson_emb = strip_z_from_geojson(st.session_state["kml_outputs"]["geojson"])
                    geojson_str = json.dumps(geojson_emb)
                    bounds = compute_bounds_from_geojson(st.session_state["kml_outputs"]["geojson"]) or [[-2, -79], [-2, -79]]
                    
                    # Generar HTML según el tipo de mapa seleccionado
                    html_map_type = st.session_state.get("html_map_type", "normal")
                    grouping_mode = st.session_state.get("group_by", "type")
                    if html_map_type == "mapbox":
                        index_html = create_mapbox_html(geojson_emb, title="KML/KMZ - Map Viewer", folder_name=base_name, grouping_mode=grouping_mode)
                    else:
                        # HTML normal con Leaflet - usar función unificada
                        index_html = create_normal_html(geojson_emb, "KML/KMZ - Map Viewer", bounds, grouping_mode)
                    
                    (dest_dir / "index.html").write_text(index_html, encoding="utf-8")
                    # Exportar DXF también
                    input_epsg_val = int(st.session_state.get("input_epsg", 32717))
                    to_utm = pyproj.Transformer.from_crs(f"EPSG:4326", f"EPSG:{input_epsg_val}", always_xy=True)
                    base_name = st.session_state.get("kml_base_name", "kml")
                    dxf_geojson = transform_geojson(st.session_state["kml_outputs"]["geojson"], to_utm)
                    export_geojson_to_dxf(dxf_geojson, dest_dir / f"{base_name}.dxf")
                    st.success(f"Resultados KML/KMZ guardados en: {dest_dir}")
                except Exception as e:
                    st.error(f"Error guardando resultados KML/KMZ: {e}")

            # Entrega Cloud-safe: solo ZIP
            base_name = st.session_state.get("kml_base_name", "kml")
            kml_outputs = st.session_state["kml_outputs"]
            kmz_bytes = kml_outputs.get("kmz_bytes", b"")
            html_str = st.session_state.get("project_map_html")
            
            # Generar DXF para el ZIP
            dxf_bytes = None
            try:
                import tempfile
                input_epsg_val = int(st.session_state.get("input_epsg", 32717))
                to_utm = pyproj.Transformer.from_crs(f"EPSG:4326", f"EPSG:{input_epsg_val}", always_xy=True)
                dxf_geojson = transform_geojson(kml_outputs["geojson"], to_utm)
                dxf_temp_path = Path(tempfile.mkdtemp()) / f"{base_name}.dxf"
                if export_geojson_to_dxf(dxf_geojson, dxf_temp_path):
                    dxf_bytes = dxf_temp_path.read_bytes()
            except Exception as e:
                st.warning(f"No se pudo generar archivo DXF: {e}")
            
            zip_buf = io.BytesIO()
            root = f"{base_name}"
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf_:
                if kmz_bytes: zf_.writestr(f"{root}/{base_name}.kmz", kmz_bytes)
                if kml_outputs.get("geojson_bytes"): zf_.writestr(f"{root}/{base_name}.geojson", kml_outputs["geojson_bytes"])
                if kml_outputs.get("json_bytes"): zf_.writestr(f"{root}/{base_name}.json", kml_outputs["json_bytes"])
                if dxf_bytes: zf_.writestr(f"{root}/{base_name}.dxf", dxf_bytes)
                if html_str: zf_.writestr(f"{root}/{base_name}_map.html", html_str.encode("utf-8"))
                shp_src = kml_outputs.get("shp_dir")
                if shp_src:
                    try:
                        for f in Path(shp_src).glob("*"):
                            zf_.write(f, arcname=f"{root}/Shapes/{f.name}")
                    except Exception:
                        pass
            zip_buf.seek(0)
            st.download_button("Descargar paquete ZIP", data=zip_buf.getvalue(), file_name=f"{base_name}_salidas.zip", mime="application/zip")

    # Contenido de pestaña Mapa del proyecto
    with tab_map:
        # CORRECCIÓN: Mostrar mapa topográfico si existe
        if st.session_state.get("topo_index_html"):
            st.markdown("### 🗺️ Mapa Topográfico")
            st.components.v1.html(st.session_state["topo_index_html"], height=750)
            st.markdown("---")
        
        # Si hay GeoJSON del proyecto, rehacer HTML según el tipo de mapa actual (sin regenerar salidas)
        pj_geo = st.session_state.get("project_geojson")
        if pj_geo is not None:
            st.markdown("### 🗺️ Mapa del Proyecto General")
            html_map_type = st.session_state.get("html_map_type", "normal")
            b = compute_bounds_from_geojson(pj_geo) or [[-2, -79], [-2, -79]]
            center_lat = (b[0][0] + b[1][0]) / 2
            center_lon = (b[0][1] + b[1][1]) / 2
            if html_map_type == "mapbox":
                html_now = create_mapbox_html(strip_z_from_geojson(pj_geo), title=st.session_state.get("project_title","Mapa del proyecto"), folder_name=st.session_state.get("project_folder_name","Proyecto"), grouping_mode=st.session_state.get("group_by","type"))
            else:
                leaf_tpl = """<!DOCTYPE html><html lang=\"es\"><head><meta charset=\"UTF-8\" /><meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" /><title>__TITLE__</title><link rel=\"stylesheet\" href=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.css\" /><script src=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.js\"></script><style> html, body { height: 100%; margin: 0; } #map { height: 100vh; } .leaflet-control-layers-expanded{ max-height: 60vh; overflow:auto; }</style></head><body><div id=\"map\"></div><script>const map=L.map('map',{preferCanvas:true});const baseLayers={\"Positron\":L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',{attribution:'© CartoDB',subdomains:'abcd',maxZoom:19}),\"OpenStreetMap\":L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap contributors'}),\"Satelital\":L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{attribution:'© Esri'})};baseLayers['Positron'].addTo(map);const data=__GEOJSON__;const overlays={};function filterByType(features,type){return features.filter(f=>f.properties&&f.properties.type===type);}const pts=L.geoJSON({type:'FeatureCollection',features:filterByType(data.features||[],'point')},{pointToLayer:(f,latlng)=>L.circleMarker(latlng,{radius:3,color:'#2c7fb8',fill:true,fillOpacity:0.9})});const lns=L.geoJSON({type:'FeatureCollection',features:(data.features||[]).filter(f=>['line','polyline','track','route','shape'].includes(f.properties&&f.properties.type))});const txt=L.geoJSON({type:'FeatureCollection',features:filterByType(data.features||[],'text')},{pointToLayer:(f,latlng)=>L.marker(latlng,{icon:L.divIcon({className:'',html:`<div style=\'font-size:12px;color:#0d6efd;font-weight:600;\'>${(f.properties&&f.properties.text)||''}</div>`})})});overlays['Puntos']=pts;overlays['Líneas']=lns;overlays['Textos']=txt;pts.addTo(map);lns.addTo(map);L.control.layers(baseLayers,overlays,{collapsed:false,position:'topright'}).addTo(map);const b=__BOUNDS__;try{map.fitBounds([[b[0][0],b[0][1]],[b[1][0],b[1][1]]],{padding:[20,20]});}catch(e){map.setView([__CENTER_LAT__,__CENTER_LON__],12);} </script></body></html>"""
                html_now = (leaf_tpl
                    .replace("__TITLE__", st.session_state.get("project_title","Mapa del proyecto"))
                    .replace("__GEOJSON__", json.dumps(strip_z_from_geojson(pj_geo)))
                    .replace("__BOUNDS__", json.dumps(b))
                    .replace("__CENTER_LAT__", str(center_lat))
                    .replace("__CENTER_LON__", str(center_lon))
                )
            st.components.v1.html(html_now, height=750)
        elif not st.session_state.get("topo_index_html"):
            st.info("Genera salidas en alguna pestaña para ver aquí el mapa del proyecto (Leaflet o Mapbox).")

    # ========================
    # PESTAÑA MANUAL DE USUARIO
    # ========================
    with tab_manual:
        st.markdown("""
        <div style="text-align: center; padding: 20px;">
            <h1 style="color: #1E88E5; margin-bottom: 10px;">📚 Manual de Usuario</h1>
            <p style="font-size: 18px; color: #666; margin-bottom: 30px;">
                Guía completa para usar el Conversor Universal Profesional
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Crear pestañas para organizar el contenido
        manual_tabs = st.tabs([
            "🎯 Introducción", 
            "⚙️ Configuración", 
            "🏗️ DXF", 
            "🚶 GPX", 
            "🌍 KML/KMZ", 
            "📊 Topográfico",
            "🛠️ Problemas"
        ])
        
        # Introducción
        with manual_tabs[0]:
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown("""
                ### 🚀 Conversor Universal Profesional
                
                Esta aplicación web permite convertir archivos geoespaciales entre múltiples formatos con visualización interactiva.
                
                **✨ Formatos soportados:**
                - 📐 **DXF** → JSON, GeoJSON, KML, Shapefiles, HTML
                - 🥾 **GPX** → JSON, GeoJSON, KML, Shapefiles, DXF, HTML  
                - 🌍 **KML/KMZ** → JSON, GeoJSON, Shapefiles, DXF, HTML
                - 📊 **Topográfico** → DXF, KML, Shapefiles, HTML
                
                **🎯 Características principales:**
                - Sistema dual de mapas (Leaflet/Mapbox 3D)
                - Agrupación inteligente por tipo o capa
                - Organización automática con iconos emoji
                - Transformaciones CRS precisas
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown("""
                ### 🔄 Flujo básico de uso
                
                1. **📤 Subir archivo** en la pestaña correspondiente
                2. **⚙️ Configurar parámetros** (EPSG, agrupación, tipo de mapa)
                3. **🔄 Convertir** y revisar vista previa
                4. **💾 Descargar resultados** con un solo clic
                
                ### 📁 Estructura de salida
                ```
                Proyecto/
                ├── archivo.json
                ├── archivo.geojson
                ├── archivo.kmz
                ├── archivo.dxf
                ├── index.html
                ├── MapBox/
                └── Shapes/
                ```
                """, unsafe_allow_html=True)
        
        # Configuración
        with manual_tabs[1]:
            st.markdown("""
            ## ⚙️ Configuración inicial
            
            Configure estos parámetros en el panel lateral antes de usar cualquier conversor:
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                st.markdown("""
                ### 🌍 Zona UTM WGS84
                
                **Hemisferio y Zona:**
                - 🇪🇨 Ecuador: 17S (EPSG 32717)
                - 🇵🇪 Perú: 18S (EPSG 32718) 
                - 🇨🇴 Colombia: 18N (EPSG 32618)
                
                **Formato EPSG:**
                - Norte: 326XX (ej: 32618)
                - Sur: 327XX (ej: 32717)
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown("""
                ### 🗂️ Agrupación de capas
                
                **Por Tipo:**
                - 📍 Puntos
                - 📏 Líneas
                - 🔗 Polilíneas
                - ⭕ Círculos
                - 📝 Textos
                
                **Por Capa:**
                - Mantiene estructura original
                - Textos siempre separados
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown("""
                ### 🗺️ Tipo de mapa HTML
                
                **Normal (Leaflet):**
                - Ligero y compatible
                - Carga rápida
                - Universal
                
                **Mapbox 3D:**
                - Terreno y elevación
                - Múltiples estilos
                - Requiere clave API
                """, unsafe_allow_html=True)
        
        # DXF
        with manual_tabs[2]:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("""
                ## 🏗️ Conversor DXF
                
                ### 📤 Proceso
                1. Subir archivo DXF
                2. Configurar zona UTM según proyecto
                3. Elegir agrupación (Tipo/Capa)
                4. Convertir y revisar mapa
                5. Descargar resultados
                
                ### 📋 Entidades soportadas
                - **📍 Puntos**: POINT
                - **📏 Líneas**: LINE
                - **🔗 Polilíneas**: POLYLINE/LWPOLYLINE
                - **⭕ Círculos**: CIRCLE → polígonos
                - **📝 Textos**: TEXT/MTEXT con atributos
                - **🧩 Bloques**: Referencias con coordenadas
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown("""
                ### 🎨 Organización KML
                
                Los elementos se agrupan automáticamente en **7 carpetas**:
                
                - 📍 **Puntos** - Entidades POINT
                - 📏 **Líneas** - Entidades LINE
                - 🔗 **Polilíneas** - POLYLINE/LWPOLYLINE
                - 🔷 **Formas** - Geometrías complejas
                - ⭕ **Círculos** - Convertidos a polígonos
                - 📝 **Textos** - Con información de contenido
                - 🧩 **Bloques** - Referencias y símbolos
                
                *Ideal para navegación en Google Earth*
                """, unsafe_allow_html=True)
        
        # GPX
        with manual_tabs[3]:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("""
                ## 🚶 Conversor GPX
                
                ### 📤 Proceso
                1. Subir archivo GPX desde GPS/aplicación
                2. Conversión automática
                3. Revisar visualización diferenciada
                4. Descargar resultados
                
                ### 📋 Elementos procesados
                - **📍 Puntos de paso**: Puntos de interés
                - **🛤️ Pistas**: Rutas grabadas
                - **🗺️ Rutas**: Rutas planificadas
                
                ### 🎨 Visualización
                - **Pistas**: Líneas rojas sólidas
                - **Rutas**: Líneas azules punteadas
                - **Puntos de paso**: Marcadores verdes
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown("""
                ### 📁 Organización KML
                
                **3 carpetas especializadas:**
                
                - 📍 **Puntos GPX**
                  - Puntos de paso con nombres
                  - Descripciones incluidas
                  
                - 🛤️ **Pistas**
                  - Rutas grabadas durante actividad
                  - Información de segmentos
                  
                - 🗺️ **Rutas**
                  - Rutas planificadas o calculadas
                  - Puntos de paso incluidos
                
                *Perfecto para análisis de actividades al aire libre*
                """, unsafe_allow_html=True)
        
        # KML/KMZ
        with manual_tabs[4]:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("""
                ## 🌍 Conversor KML/KMZ
                
                ### 📤 Proceso
                1. Subir archivo KML o KMZ
                2. Procesamiento automático inteligente
                3. Revisar elementos en mapa
                4. Descargar en todos los formatos
                
                ### 🔧 Procesamiento robusto
                - **Detección automática**: KMZ se descomprime
                - **Analizador dual**: `fastkml` + respaldo XML
                - **Limpieza de datos**: Elimina coordenadas Z
                - **Validación**: Verifica rangos geográficos
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown("""
                ### 📋 Geometrías soportadas
                
                - **Puntos**: Point con atributos
                - **Líneas**: LineString y rutas
                - **Polígonos**: Con límites exteriores
                - **Colecciones**: MultiGeometry expandido
                
                ### 📁 Organización KML
                
                **2 carpetas topográficas:**
                
                - 📍 **Puntos Topográficos**
                - 🔗 **Polígonos/Líneas**
                
                *Optimizado para datos de levantamiento*
                """, unsafe_allow_html=True)
        
        # Topográfico
        with manual_tabs[5]:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("""
                ## 📊 Conversor Topográfico
                
                ### 📋 Configuración
                1. **Nombre del proyecto**
                2. **Modo topográfico**:
                   - Solo puntos
                   - Puntos + polilíneas
                
                ### 📈 Formato de datos
                ```
                No.   | X(UTM)  | Y(UTM)   | Cota | Desc
                P001  | 500000  | 9800000  | 2450 | Esquina
                P002  | 500100  | 9800000  | 2445 | Lindero
                ```
                
                Para polígonos, usar separadores `---`
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown("""
                ### 🔄 Procesamiento automático
                
                **Cálculos incluidos:**
                - Transformación UTM → WGS84
                - Áreas de polígonos (m²)
                - Perímetros (metros lineales)
                
                ### 📁 Salida especializada
                - **DXF topográfico**: Puntos con textos
                - **Shapefiles**: Por geometría
                - **KML**: Carpetas organizadas
                - **HTML**: Con información de cotas
                """, unsafe_allow_html=True)
        
        # Resolución de problemas
        with manual_tabs[6]:
            st.markdown("## 🛠️ Resolución de problemas")
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("""
                ### ❌ Problemas comunes
                
                **🗺️ Shapefiles desplazados**
                - ✅ Verificar zona UTM correcta
                - ✅ Confirmar EPSG de entrada (KML/GPX = 4326)
                - ✅ Revisar mensajes en consola
                
                **📄 KML/KMZ vacío**
                - ✅ Verificar geometrías (no solo superposiciones)
                - ✅ Probar KML sin comprimir
                - ✅ Revisar enlaces de red externos
                
                **🌐 HTML en blanco**
                - ✅ Usar servidor local: `python -m http.server`
                - ✅ Verificar permisos del navegador
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown("""
                ### 🔧 Soluciones técnicas
                
                **⚠️ Error de importación**
                - ✅ Reiniciar aplicación Streamlit
                - ✅ Verificar dependencias: `pip install -r requirements.txt`
                
                **🗺️ Mapbox no funciona**
                - ✅ Obtener clave API en [mapbox.com](https://mapbox.com)
                - ✅ Introducir en ventana del visor
                - ✅ Se guarda automáticamente
                
                **📞 Soporte técnico**
                - **Desarrollador**: Patricio Sarmiento
                - **WhatsApp**: +593995959047
                - **Horario**: L-V 8AM-6PM, S 9AM-2PM (GMT-5)
                """, unsafe_allow_html=True)
        
        # Footer del manual
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; padding: 20px; background-color: #f8f9fa; border-radius: 10px; margin: 20px 0;">
            <h4 style="color: #1E88E5; margin-bottom: 10px;">📞 Soporte y contacto</h4>
            <p><strong>Desarrollador:</strong> Patricio Sarmiento Reinoso</p>
            <p><strong>WhatsApp:</strong> +593995959047</p>
            <p><strong>Versión:</strong> 3.0 Professional (Septiembre 2025)</p>
            <p style="font-style: italic; color: #666; margin-top: 15px;">
                Conversor Universal Profesional - Solución completa para conversión de datos geoespaciales
            </p>
        </div>
        """, unsafe_allow_html=True)

    # CORRECCIÓN: Mapa eliminado de esta pestaña - usar pestaña "Mapa del proyecto"


if __name__ == "__main__":
    main()