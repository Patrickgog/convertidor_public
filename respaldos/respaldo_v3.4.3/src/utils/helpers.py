import io
import os
import zipfile
from pathlib import Path

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

def points_equal(p1, p2, eps=1e-6):
    """Compara dos puntos con tolerancia para flotantes"""
    return abs(p1[0] - p2[0]) < eps and abs(p1[1] - p2[1]) < eps
