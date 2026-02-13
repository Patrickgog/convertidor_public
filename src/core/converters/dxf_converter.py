import io
import math
import tempfile
import json
from pathlib import Path
import ezdxf
from simplekml import Kml
import shapefile
import pyproj
from src.core.geometry.coordinate_utils import build_transformer, utm_to_latlon_coords, calculate_text_angle
from src.utils.helpers import zip_directory
from src.core.converters.geojson_converter import convert_to_geojson

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
    # Usar tempfile para el KMZ
    with tempfile.TemporaryDirectory() as tmp_dir:
        kmz_path = Path(tmp_dir) / "export.kmz"
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
