import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any

import streamlit as st

from app_pkg.core.geojson_utils import strip_z_from_geojson, compute_bounds_from_geojson
from app_pkg.export.html_export import build_project_index_html
from app_pkg.ui.map_render import render_map


def render(cfg: Dict[str, Any]) -> None:
    if "gpx_output_folder" not in st.session_state:
        st.session_state["gpx_output_folder"] = "Proyecto1"
    st.caption("Convierte archivos GPX a DXF, Shapefiles, GeoJSON/JSON, KMZ/KML y HTML")
    col1, col2, col3, col4 = st.columns([2, 7, 6, 5])
    with col2:
        gpx_file = st.file_uploader("Subir archivo GPX", type=["gpx"], key="gpx_upl")
    if "gpx_outputs" not in st.session_state:
        st.session_state["gpx_outputs"] = None
    if gpx_file and "gpx_base_name" not in st.session_state:
        try:
            st.session_state["gpx_base_name"] = Path(gpx_file.name).stem or "Proyecto1"
        except Exception:
            st.session_state["gpx_base_name"] = "Proyecto1"

    if gpx_file is not None:
        st.text("Ruta de salida")
        gpx_output_dir = st.text_input(
            "",
            value=st.session_state.get("output_dir", cfg.get("output_dir", str(Path.home() / "Downloads"))),
            key="gpx_output_dir_input",
            placeholder=str(Path.cwd()),
            disabled=False,
        )
        col_btn, _, _, _ = st.columns([2, 7, 6, 5])
        with col_btn:
            if st.button("Seleccionar carpeta", key="btn_gpx_select_dir"):
                try:
                    import tkinter as tk
                    from tkinter import filedialog
                    root = tk.Tk(); root.withdraw()
                    selected_dir = filedialog.askdirectory()
                    root.destroy()
                    if selected_dir:
                        gpx_output_dir = selected_dir
                        st.session_state["output_dir"] = selected_dir
                        st.rerun()
                except Exception as e:
                    st.warning(f"No se pudo abrir el selector de carpetas: {e}")
        with col2:
            st.text("Ruta de salida")
            gpx_output_dir = st.text_input(
                "",
                value=st.session_state.get("output_dir", cfg.get("output_dir", str(Path.home() / "Downloads"))),
                key="output_dir_input_gpx",
                placeholder=str(Path.cwd()),
                disabled=False,
            )
        with col3:
            st.caption("Usa el botón para elegir la carpeta de salida.")
        if gpx_output_dir:
            st.session_state["output_dir"] = gpx_output_dir

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
            key="output_folder_input_gpx",
            disabled=False,
        )

    if gpx_file and st.button("Convertir GPX"):
        import gpxpy
        import pyproj
        import shapefile
        from simplekml import Kml
        try:
            with st.spinner("Procesando GPX..."):
                gpx = gpxpy.parse(gpx_file.getvalue().decode("utf-8", errors="ignore"))
                features = []
                for w in gpx.waypoints:
                    features.append({
                        "type": "Feature",
                        "properties": {"type": "point", "name": w.name or "", "desc": w.description or ""},
                        "geometry": {"type": "Point", "coordinates": [w.longitude, w.latitude]},
                    })
                for trk in gpx.tracks:
                    for seg in trk.segments:
                        coords = [[pt.longitude, pt.latitude] for pt in seg.points]
                        if len(coords) >= 2:
                            features.append({
                                "type": "Feature",
                                "properties": {"type": "track", "name": trk.name or "Track"},
                                "geometry": {"type": "LineString", "coordinates": coords},
                            })
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
                json_bytes = json.dumps({"layers": {"GPX": {"points": [], "lines": [], "polylines": [], "texts": [], "circles": [], "shapes": [], "blocks": []}}}, indent=2).encode("utf-8")
                geojson_bytes = json.dumps(geojson, indent=2).encode("utf-8")
                kml = Kml()
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
                shp_dir = Path(tempfile.mkdtemp(prefix="gpx_shp_"))
                if any(f["geometry"]["type"] == "Point" for f in features):
                    wpt = shapefile.Writer(str(shp_dir / "points"), shapeType=shapefile.POINT)
                    wpt.field("Name", "C")
                    for f in features:
                        if f["geometry"]["type"] == "Point":
                            lon, lat = f["geometry"]["coordinates"]
                            wpt.point(lon, lat)
                            wpt.record(f["properties"].get("name", ""))
                    wpt.close()
                if any(f["geometry"]["type"] == "LineString" for f in features):
                    lns = shapefile.Writer(str(shp_dir / "lines"), shapeType=shapefile.POLYLINE)
                    lns.field("Name", "C")
                    for f in features:
                        if f["geometry"]["type"] == "LineString":
                            lns.line([f["geometry"]["coordinates"]])
                            lns.record(f["properties"].get("name", ""))
                    lns.close()
                try:
                    import pyproj
                    prj_wkt = pyproj.CRS.from_epsg(int(cfg.get("output_epsg", 4326))).to_wkt()
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
        try:
            geojson_emb = st.session_state["gpx_outputs"]["geojson"]
            html_map_type = st.session_state.get("html_map_type", cfg.get("html_map_type", "normal"))
            st.session_state["project_geojson"] = geojson_emb
            st.session_state["project_folder_name"] = st.session_state.get("gpx_output_folder", cfg.get("output_folder", "Proyecto"))
            st.session_state["project_title"] = "GPX - Map Viewer"
            b = compute_bounds_from_geojson(geojson_emb) or [[-2, -79], [-2, -79]]
            st.session_state["project_map_html"] = build_project_index_html(
                strip_z_from_geojson(geojson_emb),
                map_type=html_map_type,
                bounds=b,
                title="GPX - Map Viewer",
                folder_name=st.session_state.get("gpx_output_folder", "Proyecto"),
            )
        except Exception:
            pass
        if st.button("Descargar Resultados GPX"):
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
                shp_src = Path(st.session_state["gpx_outputs"]["shp_dir"])
                for ext in ("*.shp", "*.shx", "*.dbf", "*.prj", "*.cpg"):
                    for f in shp_src.glob(ext):
                        shutil.copy2(f, shapes_dir / f.name)
                geojson_emb = strip_z_from_geojson(st.session_state["gpx_outputs"]["geojson"]) 
                bounds = compute_bounds_from_geojson(geojson_emb) or [[-2, -79], [-2, -79]]
                html_map_type = st.session_state.get("html_map_type", cfg.get("html_map_type", "normal"))
                index_html = build_project_index_html(
                    geojson_emb,
                    map_type=html_map_type,
                    bounds=bounds,
                    title="GPX - Map Viewer",
                    folder_name=base_name,
                )
                (dest_dir / "index.html").write_text(index_html, encoding="utf-8")
                st.success(f"Resultados guardados en: {dest_dir}")
            except Exception as exc:
                st.error(f"No se pudieron guardar los resultados: {exc}")

        # Quitar render del mapa en esta pestaña (se muestra en pestaña Mapa del proyecto)


__all__ = ["render"]
