import ezdxf
import logging
import json
import pyproj
from pathlib import Path

logger = logging.getLogger(__name__)

def export_geojson_to_dxf(geojson_obj: dict, dxf_path: Path, point_color="#ff0000", line_color="#0000ff", line_width=0.2):
    """
    Exporta GeoJSON a DXF transformando coordenadas WGS84 a UTM Zona 17 Sur (EPSG:32717).
    
    AutoCAD/CivilCAD requieren coordenadas UTM (X, Y en metros), no lat/lon en grados.
    Esta función detecta si las coordenadas están en WGS84 y las transforma automáticamente a UTM.
    """
    try:
        # Detectar si las coordenadas están en WGS84 (grados decimales)
        def get_bounds(geojson):
            coords = []
            for f in geojson.get("features", []):
                g = f.get("geometry", {})
                c = g.get("coordinates")
                if c:
                    _collect_coords(c, coords)
            if not coords:
                return None
            xs = [p[0] for p in coords]
            ys = [p[1] for p in coords]
            return (min(xs), min(ys), max(xs), max(ys))
        
        def _collect_coords(coords, acc):
            if isinstance(coords, (list, tuple)):
                if len(coords) >= 2 and isinstance(coords[0], (int, float)):
                    acc.append((coords[0], coords[1]))
                else:
                    for c in coords:
                        _collect_coords(c, acc)
        
        bounds = get_bounds(geojson_obj)
        needs_transformation = False
        transformer = None
        
        if bounds:
            min_x, min_y, max_x, max_y = bounds
            # Detectar WGS84: valores entre -180 y 180 para X, -90 y 90 para Y
            if -180 <= min_x <= 180 and -180 <= max_x <= 180 and -90 <= min_y <= 90 and -90 <= max_y <= 90:
                needs_transformation = True
                # Crear transformador de WGS84 (EPSG:4326) a UTM Zona 17 Sur (EPSG:32717)
                # UTM Zona 17 Sur es el sistema correcto para Ecuador
                transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32717", always_xy=True)
                logger.info(f"DXF: Coordenadas WGS84 detectadas. Transformando a UTM Zona 17 Sur (EPSG:32717)")
                logger.info(f"DXF: Bounds originales: X=[{min_x:.6f}, {max_x:.6f}], Y=[{min_y:.6f}, {max_y:.6f}]")
        
        # Transformar GeoJSON si es necesario
        if needs_transformation and transformer:
            geojson_transformed = transform_geojson_coords(geojson_obj, transformer)
            # Logging de coordenadas transformadas para verificación
            bounds_transformed = get_bounds(geojson_transformed)
            if bounds_transformed:
                min_x_t, min_y_t, max_x_t, max_y_t = bounds_transformed
                logger.info(f"DXF: Bounds UTM: X=[{min_x_t:.2f}, {max_x_t:.2f}], Y=[{min_y_t:.2f}, {max_y_t:.2f}]")
        else:
            geojson_transformed = geojson_obj
            logger.info(f"DXF: Coordenadas ya proyectadas, sin transformación")
        
        # Crear DXF con coordenadas transformadas
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()
        
        # Convert hex colors to integer TrueColor
        def hex_to_int(hex_str):
            try:
                return int(hex_str.lstrip('#'), 16)
            except:
                return 0

        p_color_int = hex_to_int(point_color)
        l_color_int = hex_to_int(line_color)
        
        # Ajustar line_width para coordenadas proyectadas (metros)
        # En Web Mercator, 1 metro = 1 unidad
        adjusted_line_width = float(line_width) if not needs_transformation else float(line_width) * 0.5
        adjusted_text_height = 5.0  # Altura fija en metros para texto
        text_offset = 2.0  # Offset fijo en metros
        
        def add_point(x, y):
            try:
                msp.add_point((x, y), dxfattribs={
                    "layer": "POINTS",
                    "true_color": p_color_int
                })
            except Exception:
                pass
                
        def add_polyline(coords, layer="LINES", closed=False):
            try:
                if not coords or len(coords) < 2:
                    return
                valid_coords = []
                for c in coords:
                    if len(c) >= 2 and all(isinstance(v, (int, float)) for v in c[:2]):
                        valid_coords.append((float(c[0]), float(c[1])))
                if len(valid_coords) < 2:
                    return
                
                attribs = {
                    "layer": layer,
                    "true_color": l_color_int,
                }
                if closed:
                    attribs["closed"] = 1
                
                line = msp.add_lwpolyline(valid_coords, dxfattribs=attribs)
                line.dxf.const_width = adjusted_line_width
            except Exception:
                pass

        feats = geojson_transformed.get("features", []) if geojson_transformed.get("type") == "FeatureCollection" else []
        for f in feats:
            props = f.get("properties", {})
            g = f.get("geometry", {})
            t = g.get("type")
            
            label = props.get("name") or props.get("text") or props.get("label")
            
            if t == "Point":
                coords = g.get("coordinates")
                if coords and len(coords) >= 2:
                    add_point(coords[0], coords[1])
                    if label:
                        try:
                            msp.add_text(str(label), dxfattribs={
                                "layer": "TEXT_LABELS",
                                "height": adjusted_text_height,
                                "true_color": p_color_int
                            }).set_placement((coords[0] + text_offset, coords[1] + text_offset))
                        except Exception:
                            pass
            elif t == "MultiPoint":
                for pt in g.get("coordinates", []):
                    if pt and len(pt) >= 2:
                        add_point(pt[0], pt[1])
            elif t == "LineString":
                coords = g.get("coordinates", [])
                add_polyline(coords, layer="LINES", closed=False)
            elif t == "MultiLineString":
                for line in g.get("coordinates", []):
                    add_polyline(line, layer="LINES", closed=False)
            elif t == "Polygon":
                rings = g.get("coordinates", [])
                if rings:
                    add_polyline(rings[0], layer="POLYGONS", closed=True)
            elif t == "MultiPolygon":
                for poly in g.get("coordinates", []):
                    if poly:
                        add_polyline(poly[0], layer="POLYGONS", closed=True)
        
        doc.saveas(str(dxf_path))
        logger.info(f"DXF exportado exitosamente a {dxf_path}")
        return True
    except Exception as e:
        logger.error(f"Error exportando DXF: {e}")
        return False


def transform_geojson_coords(geojson_obj: dict, transformer: pyproj.Transformer) -> dict:
    """
    Transforma todas las coordenadas de un GeoJSON usando el transformador proporcionado.
    """
    def transform_coords(coords):
        if isinstance(coords, (list, tuple)):
            if len(coords) >= 2 and isinstance(coords[0], (int, float)) and isinstance(coords[1], (int, float)):
                # Es un par de coordenadas [lon, lat]
                x, y = transformer.transform(coords[0], coords[1])
                return [x, y]
            else:
                # Es una lista de coordenadas
                return [transform_coords(c) for c in coords]
        return coords
    
    # Crear copia profunda del GeoJSON
    result = json.loads(json.dumps(geojson_obj))
    
    if result.get("type") == "FeatureCollection":
        for f in result.get("features", []):
            g = f.get("geometry")
            if g and isinstance(g, dict) and "coordinates" in g:
                g["coordinates"] = transform_coords(g["coordinates"])
    elif result.get("type") == "Feature":
        g = result.get("geometry")
        if g and isinstance(g, dict) and "coordinates" in g:
            g["coordinates"] = transform_coords(g["coordinates"])
    elif result.get("type") in ("Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon"):
        if "coordinates" in result:
            result["coordinates"] = transform_coords(result["coordinates"])
    
    return result
