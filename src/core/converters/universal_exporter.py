import os
import zipfile
import io
import json
import tempfile
import shapefile
from pathlib import Path
from src.core.converters.dxf_exporter import export_geojson_to_dxf
from src.generators.map_generators import create_mapbox_html, create_leaflet_grouped_html, get_mapbox_token
from simplekml import Kml

def export_geojson_to_all_formats(geojson_data, base_name, point_color="#ff0000", line_color="#0000ff", line_width=2, output_epsg=4326, map_type="normal"):
    """
    Exporta un GeoJSON a DXF, SHP (en carpeta), KMZ y Mapa HTML con estilos personalizados.
    Retorna un buffer de bytes con el ZIP completo.
    
    Args:
        map_type: "normal" para Leaflet, "mapbox" para Mapbox
    """
    zip_buf = io.BytesIO()
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # 1. DXF
        dxf_file = tmp_path / f"{base_name}.dxf"
        export_geojson_to_dxf(geojson_data, dxf_file, point_color=point_color, line_color=line_color, line_width=line_width)
        
        # 2. Shapefiles
        shp_dir = tmp_path / "shapes"
        shp_dir.mkdir(exist_ok=True)
        try:
            w = shapefile.Writer(str(shp_dir / base_name))
            w.field("NAME", "C", 50)
            w.field("TYPE", "C", 20)
            
            for f in geojson_data.get("features", []):
                geom = f.get("geometry", {})
                props = f.get("properties", {})
                g_type = geom.get("type")
                coords = geom.get("coordinates")
                name = str(props.get("name") or props.get("label") or "")
                etype = str(props.get("type") or g_type)
                
                if g_type == "Point":
                    w.point(coords[0], coords[1])
                    w.record(name, etype)
                elif g_type == "LineString":
                    w.line([coords])
                    w.record(name, etype)
                elif g_type == "Polygon":
                    w.poly(coords)
                    w.record(name, etype)
            w.close()
            # Crear .prj
            with open(shp_dir / f"{base_name}.prj", "w") as prj:
                prj.write('GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]')
        except Exception:
            pass

        # 3. KMZ con Estilos
        kmz_file = tmp_path / f"{base_name}.kmz"
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            # Validar y diagnosticar coordenadas WGS84
            def get_bounds(geojson):
                coords = []
                for f in geojson.get("features", []):
                    g = f.get("geometry", {})
                    c = g.get("coordinates")
                    if c:
                        _collect_coords(c, coords)
                if not coords:
                    return None
                lons = [p[0] for p in coords]
                lats = [p[1] for p in coords]
                return (min(lons), min(lats), max(lons), max(lats))
            
            def _collect_coords(coords, acc):
                if isinstance(coords, (list, tuple)):
                    if len(coords) >= 2 and isinstance(coords[0], (int, float)):
                        acc.append((coords[0], coords[1]))
                    else:
                        for c in coords:
                            _collect_coords(c, acc)
            
            bounds = get_bounds(geojson_data)
            if bounds:
                min_lon, min_lat, max_lon, max_lat = bounds
                logger.info(f"KML/KMZ: Exportando con coordenadas WGS84 (EPSG:4326)")
                logger.info(f"KML/KMZ: Bounds: Lon=[{min_lon:.6f}, {max_lon:.6f}], Lat=[{min_lat:.6f}, {max_lat:.6f}]")
                
                # Validar rangos WGS84
                if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
                    logger.warning(f"KML/KMZ: Longitud fuera de rango WGS84: [{min_lon}, {max_lon}]")
                if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
                    logger.warning(f"KML/KMZ: Latitud fuera de rango WGS84: [{min_lat}, {max_lat}]")
                
                # Verificar si está en rango de Ecuador
                if -81.0 <= min_lon <= -75.0 and -5.0 <= min_lat <= 2.0:
                    logger.info(f"KML/KMZ: Coordenadas dentro del rango de Ecuador continental")
                else:
                    logger.info(f"KML/KMZ: Coordenadas fuera del rango típico de Ecuador")
            
            kml = Kml()
            # Convertir hex color a formato KML (aabbggrr)
            def hex_to_kml_color(hex_str):
                h = hex_str.lstrip('#')
                if len(h) == 6:
                    r, g, b = h[0:2], h[2:4], h[4:6]
                    return f"ff{b}{g}{r}" # Alfa ff + bgr
                return "ff0000ff"

            kml_p_color = hex_to_kml_color(point_color)
            kml_l_color = hex_to_kml_color(line_color)

            feature_count = 0
            for f in geojson_data.get("features", []):
                geom = f.get("geometry", {})
                props = f.get("properties", {})
                g_type = geom.get("type")
                coords = geom.get("coordinates")
                name = props.get("name") or props.get("label") or ""
                
                if g_type == "Point":
                    pnt = kml.newpoint(name=name, coords=[(coords[0], coords[1])])
                    pnt.style.labelstyle.color = kml_p_color
                    pnt.style.iconstyle.color = kml_p_color
                    feature_count += 1
                elif g_type == "LineString":
                    lin = kml.newlinestring(name=name, coords=coords)
                    lin.style.linestyle.color = kml_l_color
                    lin.style.linestyle.width = line_width
                    feature_count += 1
                elif g_type == "Polygon":
                    pol = kml.newpolygon(name=name, outerboundaryis=coords[0])
                    pol.style.linestyle.color = kml_l_color
                    pol.style.linestyle.width = line_width
                    pol.style.polystyle.color = kml_l_color.replace("ff", "4b") # Opacidad 30%
                    feature_count += 1
            
            kml.savekmz(str(kmz_file))
            logger.info(f"KML/KMZ: Exportado exitosamente con {feature_count} features a {kmz_file}")
        except Exception as e:
            logger.error(f"KML/KMZ: Error en exportación: {e}")
            pass

        # 4. HTML Map - Usar el tipo de mapa seleccionado por el usuario
        try:
            if map_type == "mapbox":
                # Generar mapa Mapbox con colores iniciales
                html_content = create_mapbox_html(
                    geojson_data, 
                    title=base_name, 
                    folder_name=base_name,
                    point_color=point_color,
                    line_color=line_color
                )
            else:
                # Generar mapa Leaflet con estilos personalizados
                html_content = create_leaflet_grouped_html(
                    geojson_data, 
                    title=base_name,
                    point_color=point_color,
                    line_color=line_color,
                    line_width=line_width
                )
            
            html_file = tmp_path / "Visualizador_Mapa.html"
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(html_content)
        except Exception:
            pass

        # 5. GeoJSON
        geojson_file = tmp_path / f"{base_name}.geojson"
        with open(geojson_file, "w", encoding="utf-8") as f:
            json.dump(geojson_data, f, indent=2)

        # Crear ZIP final
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(tmp_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = f"{base_name}/" + str(file_path.relative_to(tmp_dir)).replace("\\", "/")
                    zf.write(file_path, arcname)
                    
    return zip_buf.getvalue()
