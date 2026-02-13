import logging
import json
from xml.etree import ElementTree as ET
from src.utils.helpers import local_name, parse_coords_text

logger = logging.getLogger(__name__)

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
