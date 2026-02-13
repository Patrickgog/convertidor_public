import os
import json
import ezdxf
import pyproj
import pandas as pd
import numpy as np
import io
import zipfile
from pathlib import Path
from simplekml import Kml, AltitudeMode
import shapefile
from src.core.geometry.coordinate_utils import build_transformer, strip_z_from_geojson
from src.core.converters.heatmap_converter import create_heatmap_geotiff, validate_heatmap_data, calculate_raster_bounds, create_heatmap_debug_file
import src.generators.map_generators as mg

import logging

logger = logging.getLogger(__name__)

def process_topo_data(df, input_epsg, output_epsg, options):
    """
    Procesamiento integral de datos topográficos para generar múltiples salidas.
    """
    folder_name = options.get("folder_name", "Trabajo_Topográfico")
    output_dir = options.get("output_dir", str(Path.home() / "Downloads"))
    main_folder = Path(output_dir) / folder_name
    
    # Manejar colisión de nombres de carpeta
    idx = 1
    while main_folder.exists():
        main_folder = Path(output_dir) / f"{folder_name}_{idx}"
        idx += 1
    
    main_folder.mkdir(parents=True, exist_ok=True)
    
    transformer = build_transformer(input_epsg, output_epsg)
    dim_is_3d = options.get("dim", "2D") == "3D"
    modo_topo = options.get("modo", "Solo puntos")
    
    # Colores DXF
    color_map = {
        "rojo": 1, "amarillo": 2, "verde": 3, "cian": 4, 
        "azul": 5, "magenta": 6, "blanco": 7, "gris": 8, 
        "naranja": 30, "negro": 250
    }
    
    # 1. DXF
    dxf_path = main_folder / f"{folder_name}.dxf"
    doc = ezdxf.new(dxfversion="R2000")
    msp = doc.modelspace()
    
    layer_puntos = options.get("layer_puntos", "PUNTOS")
    layer_polilineas = options.get("layer_polilineas", "POLILINEAS")
    layer_textos = options.get("layer_textos", "TEXTOS")
    
    color_punto = color_map.get(options.get("color_punto", "azul"), 5)
    color_linea = color_map.get(options.get("color_linea", "rojo"), 1)
    color_texto = color_map.get(options.get("color_texto", "blanco"), 7)
    
    doc.layers.new(name=layer_puntos, dxfattribs={"color": color_punto})
    doc.layers.new(name=layer_polilineas, dxfattribs={
        "color": color_linea, 
        "linetype": options.get("tipo_linea", "CONTINUOUS"),
        "lineweight": int(options.get("ancho_linea", 0.48) * 100)
    })
    doc.layers.new(name=layer_textos, dxfattribs={"color": color_texto})
    
    doc.header["$PDMODE"] = options.get("pdmode", 33)
    doc.header["$PDSIZE"] = options.get("h_punto", 0.3)
    
    text_style = doc.styles.get("STANDARD")
    text_style.dxf.height = options.get("altura_texto", 0.35)
    
    # 2. KML
    kml = Kml()
    points_folder = kml.newfolder(name="📍 Puntos Topográficos")
    lines_folder = kml.newfolder(name="🔗 Polígonos/Líneas")
    
    # 3. GeoJSON
    features = []
    
    # Almacén para polilíneas
    poly_info = []
    
    # Procesar puntos
    for idx, row in df.iterrows():
        try:
            x, y = float(row["x"]), float(row["y"])
            cota = float(row.get("cota", 0))
            desc = str(row.get("desc", ""))
            
            lon, lat = transformer.transform(x, y)
            cota_used = cota if dim_is_3d else 0.0
            
            # DXF Punto
            point_coords = (x, y, cota_used) if dim_is_3d else (x, y)
            msp.add_point(point_coords, dxfattribs={"layer": layer_puntos})
            
            # DXF Texto
            if desc and desc.lower() not in ['', 'nan', 'none', 'null']:
                txt_x = x + options.get("desplaz_x", 0.15)
                txt_y = y + options.get("desplaz_y", 0.15)
                msp.add_text(desc, dxfattribs={
                    "layer": layer_textos,
                    "height": options.get("altura_texto", 0.35),
                    "insert": (txt_x, txt_y, cota_used) if dim_is_3d else (txt_x, txt_y)
                })
            
            # KML Punto
            p_kml = points_folder.newpoint(name=str(row.get("No.", idx)))
            if dim_is_3d:
                p_kml.coords = [(lon, lat, cota_used)]
                p_kml.altitudemode = AltitudeMode.absolute
            else:
                p_kml.coords = [(lon, lat)]
            
            # GeoJSON Feature
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point", 
                    "coordinates": [lon, lat, cota_used] if dim_is_3d else [lon, lat]
                },
                "properties": {
                    "No": row.get("No.", idx),
                    "cota": cota,
                    "desc": desc,
                    "type": "point",
                    "layer": "TOPO"
                }
            })
            
        except Exception as e:
            continue

    # Procesar Polilíneas
    if modo_topo == "Puntos y polilíneas":
        try:
            # Agrupar por 'No.' si se usa como ID de grupo, o usar orden secuencial
            # El código original hacía df.groupby('No.')
            df_poly = df.copy()
            df_poly['No.'] = pd.to_numeric(df_poly['No.'], errors='coerce').fillna(0).astype(int)
            grouped = df_poly.groupby('No.')
            
            idx_poly = 1
            for name, group in grouped:
                if len(group) >= 2:
                    pts_utm = []
                    pts_geo = []
                    for _, r in group.iterrows():
                        xv, yv = float(r['x']), float(r['y'])
                        zv = float(r.get('cota', 0)) if dim_is_3d else 0.0
                        lv, lav = transformer.transform(xv, yv)
                        pts_utm.append((xv, yv, zv) if dim_is_3d else (xv, yv))
                        pts_geo.append((lv, lav, zv) if dim_is_3d else (lv, lav))
                    
                    is_closed = len(pts_utm) >= 3 # Simplificación: si tiene 3+, cerrar
                    
                    # DXF Línea
                    if dim_is_3d:
                        if is_closed: pts_utm.append(pts_utm[0])
                        msp.add_polyline3d(pts_utm, dxfattribs={"layer": layer_polilineas})
                    else:
                        msp.add_lwpolyline(pts_utm, dxfattribs={
                            "layer": layer_polilineas,
                            "closed": is_closed
                        })
                    
                    # KML Línea
                    ls = lines_folder.newlinestring(name=f"Polilínea {idx_poly}")
                    ls.coords = pts_geo + ([pts_geo[0]] if is_closed else [])
                    ls.style.linestyle.color = "red"
                    ls.style.linestyle.width = 3
                    
                    # GeoJSON Línea
                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [list(p) for p in (pts_geo + ([pts_geo[0]] if is_closed else []))]
                        },
                        "properties": {"type": "polyline", "layer": layer_polilineas}
                    })
                    
                    # Info para resumen
                    poly_info.append({"ID": idx_poly, "Puntos": len(pts_utm), "Cerrada": is_closed})
                    idx_poly += 1
                    
        except Exception:
            pass

    # Guardar DXF y KML
    doc.saveas(str(dxf_path))
    kml_path = main_folder / f"{folder_name}.kml"
    kml.save(str(kml_path))
    
    # GeoJSON final
    geojson = {"type": "FeatureCollection", "features": features}
    
    # 4. Shapefiles
    shp_dir = main_folder / "shapefiles"
    shp_dir.mkdir(exist_ok=True)
    shp_points_path = shp_dir / f"{folder_name}_puntos"
    
    try:
        shp_pt_type = shapefile.POINTZ if dim_is_3d else shapefile.POINT
        with shapefile.Writer(str(shp_points_path), shapeType=shp_pt_type) as w:
            w.field("No", "C", size=10)
            w.field("cota", "F", size=20, decimal=8)
            w.field("desc", "C", size=50)
            for f in [feat for feat in features if feat["properties"].get("type") == "point"]:
                coords = f["geometry"]["coordinates"]
                if dim_is_3d:
                    w.pointz(coords[0], coords[1], coords[2])
                else:
                    w.point(coords[0], coords[1])
                w.record(str(f["properties"]["No"]), f["properties"]["cota"], f["properties"]["desc"])
        
        # .prj file
        try:
            prj_wkt = pyproj.CRS.from_epsg(output_epsg).to_wkt(version='WKT1_ESRI')
            with open(f"{shp_points_path}.prj", "w") as f:
                f.write(prj_wkt)
        except: pass
    except: pass

    # 4b. Mapbox Folder (JSON/GeoJSON)
    mapbox_dir = main_folder / "mapbox"
    mapbox_dir.mkdir(exist_ok=True)
    
    def convert_numpy_types(obj):
        if isinstance(obj, dict):
            return {k: convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(v) for v in obj]
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        else:
            return obj

    geojson_serializable = convert_numpy_types(geojson)
    
    geojson_path = mapbox_dir / f"{folder_name}.geojson"
    with open(geojson_path, "w", encoding="utf-8") as f:
        json.dump(geojson_serializable, f, ensure_ascii=False, indent=2)
        
    json_export_path = mapbox_dir / f"{folder_name}.json"
    with open(json_export_path, "w", encoding="utf-8") as f:
        json.dump(geojson_serializable, f, ensure_ascii=False, indent=2)

    # 5. Heatmap (GeoTIFF)
    geotiff_bytes = None
    if options.get("heatmap_enabled", False):
        try:
            bounds = calculate_raster_bounds(df, options.get("heatmap_margin", 15))
            geotiff_bytes = create_heatmap_geotiff(
                df, bounds, 
                resolution=options.get("heatmap_resolution", 500),
                method=options.get("heatmap_method", "cubic")
            )
            if geotiff_bytes:
                with open(main_folder / f"{folder_name}_heatmap.tif", "wb") as f:
                    f.write(geotiff_bytes)
        except: pass

    # 6. HTML Viewers
    html_content = ""
    try:
        html_map_type = options.get("html_map_type", "normal")
        # Usar una copia para no quitar la Z del GeoJSON principal si se requiere después
        gj_for_html = json.loads(json.dumps(geojson_serializable))
        gj_2d = strip_z_from_geojson(gj_for_html)
        
        if html_map_type == "mapbox":
            html_content = mg.create_mapbox_html(gj_2d, title=f"{folder_name} View", folder_name=folder_name)
        else:
            html_content = mg.create_leaflet_grouped_html(gj_2d, title=f"{folder_name} View")
        
        with open(main_folder / "index.html", "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception as e:
        logger.error(f"Error generando HTML: {e}")

    # Retornar resultados
    return {
        "main_folder": main_folder,
        "geojson": geojson,
        "dxf_path": dxf_path,
        "kml_path": kml_path,
        "geotiff_bytes": geotiff_bytes,
        "html_content": html_content,
        "poly_info": poly_info
    }
