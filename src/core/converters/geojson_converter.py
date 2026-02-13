import json
import collections
from shapely.geometry import Polygon

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

        # Criterio: agrupar por número de polígono en la primera columna
        poligonos_dict = collections.defaultdict(list)
        for punto in layer_data.get("polylines", []):
            # En DXF, vertices puede venir como list de coords. 
            # Si viene del conversor topográfico, viene con 'poligono'.
            if isinstance(punto, dict):
                num = punto.get('poligono')
                x = punto.get('x')
                y = punto.get('y')
                if num is not None and x is not None and y is not None:
                    poligonos_dict[num].append((x, y))
            elif isinstance(punto, list):
                # Caso de DXF tradicional donde ya son coordenadas
                geojson["features"].append({
                    "type": "Feature",
                    "properties": {"layer": layer_name, "type": "polyline"},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": punto.get("vertices_lonlat", []) if isinstance(punto, dict) else []
                    },
                })

        for num, puntos in poligonos_dict.items():
            if len(set(puntos)) >= 3:
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
                    
        # Para DXF polylines que ya procesamos en dict
        for poly in layer_data.get("polylines", []):
            if isinstance(poly, dict) and "vertices_lonlat" in poly:
                geojson["features"].append({
                    "type": "Feature",
                    "properties": {"layer": layer_name, "type": "polyline"},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": poly["vertices_lonlat"]
                    },
                })
        
        for shape in layer_data.get("shapes", []):
            if "vertices_lonlat" in shape:
                geojson["features"].append({
                    "type": "Feature",
                    "properties": {"layer": layer_name, "type": "shape", "closed": shape.get("closed", False)},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": shape["vertices_lonlat"]
                    },
                })

        for circle in layer_data.get("circles", []):
            if "coords_lonlat" in circle:
                geojson["features"].append({
                    "type": "Feature",
                    "properties": {"layer": layer_name, "type": "circle", "radius": circle.get("radius")},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [circle["coords_lonlat"]]
                    },
                })

        for text in layer_data.get("texts", []):
            geojson["features"].append({
                "type": "Feature",
                "properties": {"layer": layer_name, "type": "text", "text": text["text"], "rotation": text.get("rotation", 0)},
                "geometry": {"type": "Point", "coordinates": [text["lon"], text["lat"]]},
            })
            
        for block in layer_data.get("blocks", []):
            geojson["features"].append({
                "type": "Feature",
                "properties": {"layer": layer_name, "type": "block", "block_name": block["block_name"]},
                "geometry": {"type": "Point", "coordinates": [block["lon"], block["lat"]]},
            })

    return geojson
