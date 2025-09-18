from typing import Any, Dict, List
from xml.etree import ElementTree as ET


def local_name(tag: str) -> str:
    try:
        if '}' in tag:
            return tag.split('}', 1)[1]
        return tag
    except Exception:
        return tag


def parse_coords_text(txt: str) -> List[List[float]]:
    coords: List[List[float]] = []
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


def parse_kml_via_xml(kml_bytes: bytes) -> Dict[str, Any]:
    try:
        root = ET.fromstring(kml_bytes)
        features: List[Dict[str, Any]] = []
        for elem in root.iter():
            lname = local_name(elem.tag)
            if lname == 'Point':
                for child in list(elem):
                    if local_name(child.tag) == 'coordinates':
                        for c in parse_coords_text(child.text or ""):
                            features.append({
                                "type": "Feature",
                                "properties": {"type": "point"},
                                "geometry": {"type": "Point", "coordinates": c},
                            })
            elif lname == 'LineString':
                for child in list(elem):
                    if local_name(child.tag) == 'coordinates':
                        coords = parse_coords_text(child.text or "")
                        if len(coords) >= 2:
                            features.append({
                                "type": "Feature",
                                "properties": {"type": "line"},
                                "geometry": {"type": "LineString", "coordinates": coords},
                            })
            elif lname == 'Polygon':
                outer = None
                for c1 in list(elem):
                    if local_name(c1.tag) == 'outerBoundaryIs':
                        for c2 in list(c1):
                            if local_name(c2.tag) == 'LinearRing':
                                for c3 in list(c2):
                                    if local_name(c3.tag) == 'coordinates':
                                        outer = parse_coords_text(c3.text or "")
                                        break
                if outer and len(outer) >= 3:
                    if outer[0] != outer[-1]:
                        outer.append(outer[0])
                    features.append({
                        "type": "Feature",
                        "properties": {"type": "polygon"},
                        "geometry": {"type": "Polygon", "coordinates": [outer]},
                    })
        return {"type": "FeatureCollection", "features": features}
    except Exception:
        return {"type": "FeatureCollection", "features": []}


__all__ = [
    "local_name",
    "parse_coords_text",
    "parse_kml_via_xml",
]
