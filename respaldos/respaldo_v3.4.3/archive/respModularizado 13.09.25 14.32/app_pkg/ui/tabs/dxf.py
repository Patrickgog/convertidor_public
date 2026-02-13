import os
import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any

import streamlit as st

from app_pkg.core.dxf_converter import convert_dxf
from app_pkg.core.geojson_utils import compute_bounds_from_geojson, strip_z_from_geojson
from app_pkg.export.html_export import build_project_index_html
from app_pkg.ui.map_render import render_map


def render(cfg: Dict[str, Any]) -> None:
    col1, col2, col3, col4 = st.columns([2, 7, 6, 5])
    with col2:
        uploaded = st.file_uploader("Subir archivo DXF", type=["dxf"]) 

    if "outputs" not in st.session_state:
        st.session_state["outputs"] = None
    if "base_name" not in st.session_state:
        st.session_state["base_name"] = "Proyecto1"

    if uploaded is not None:
        try:
            st.session_state["base_name"] = Path(uploaded.name).stem or "Proyecto1"
        except Exception:
            st.session_state["base_name"] = "Proyecto1"

    if uploaded is not None:
        st.text("Ruta de salida")
        new_output_dir = st.text_input(
            "",
            value=cfg.get("output_dir", str(Path.cwd())),
            key="output_dir_input_dxf_tab",
            placeholder=str(Path.cwd()),
            disabled=False,
        )
        col_btn, _, _, _ = st.columns([2, 7, 6, 5])
        with col_btn:
            if st.button("Seleccionar carpeta"):
                try:
                    import tkinter as tk
                    from tkinter import filedialog
                    root = tk.Tk(); root.withdraw()
                    selected_dir = filedialog.askdirectory()
                    root.destroy()
                    if selected_dir:
                        new_output_dir = selected_dir
                        st.session_state["output_dir"] = selected_dir
                        st.rerun()
                except Exception as e:
                    st.warning(f"No se pudo abrir el selector de carpetas: {e}")
        with col2:
            st.text("Ruta de salida")
            new_output_dir = st.text_input(
                "",
                value=st.session_state.get("output_dir", cfg.get("output_dir", str(Path.cwd()))),
                key="output_dir_input_dxf_value",
                placeholder=str(Path.cwd()),
                disabled=False,
            )
        with col3:
            st.caption("Usa el botón para elegir la carpeta de salida.")
        if new_output_dir:
            st.session_state["output_dir"] = new_output_dir

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
            key="output_folder_input_dxf",
            disabled=False,
        )

    convert_clicked = st.button("Convertir", disabled=uploaded is None)
    if convert_clicked:
        if not uploaded:
            st.warning("Sube un archivo DXF primero.")
            st.stop()
        with st.spinner("Convirtiendo DXF..."):
            with tempfile.TemporaryDirectory(prefix="dxf_") as tmpdir:
                tmpdir_path = Path(tmpdir)
                base_name_local = Path(uploaded.name).stem or "archivo"
                dxf_path = (tmpdir_path / base_name_local).with_suffix(".dxf")
                with open(dxf_path, "wb") as f:
                    f.write(uploaded.read())
                try:
                    shapes_group_by = st.session_state.get("group_by", cfg.get("group_by", "type"))
                    outputs = convert_dxf(
                        str(dxf_path),
                        int(cfg.get("input_epsg", 32717)),
                        int(cfg.get("output_epsg", 4326)),
                        shapes_group_by=str(shapes_group_by).lower(),
                    )
                except Exception as exc:
                    st.error(f"Error en la conversión: {exc}")
                    st.stop()
        st.session_state["outputs"] = outputs

    outputs_local = st.session_state.get("outputs")
    if outputs_local:
        st.success("Conversión completada")
        # Diagnóstico rápido
        try:
            summary = json.loads(outputs_local.get("json_bytes", b"{}").decode("utf-8"))
            st.caption("Resumen de entidades extraídas")
            st.json(summary)
            if summary.get("counts", {}).get("types", {}):
                total = sum(summary["counts"]["types"].values())
                if total == 0:
                    st.warning("No se detectaron entidades en el DXF. Verifica EPSG de entrada o el contenido del archivo.")
        except Exception:
            pass
        try:
            html_map_type = st.session_state.get("html_map_type", cfg.get("html_map_type", "normal"))
            geojson_emb = outputs_local["geojson"]
            st.session_state["project_geojson"] = geojson_emb
            st.session_state["project_folder_name"] = st.session_state.get("output_folder", cfg.get("output_folder", "Proyecto"))
            st.session_state["project_title"] = f"{st.session_state.get('base_name','Proyecto')} - Map Viewer"
            bounds = compute_bounds_from_geojson(geojson_emb) or [[-2, -79], [-2, -79]]
            st.session_state["project_map_html"] = build_project_index_html(
                strip_z_from_geojson(geojson_emb),
                map_type=html_map_type,
                bounds=bounds,
                title=st.session_state["project_title"],
                folder_name=st.session_state["project_folder_name"],
            )
        except Exception:
            pass

        if st.button("Descargar Resultados", key="btn_save_all_dxf"):
            base_dir = Path(st.session_state.get("output_dir") or Path.cwd())
            folder_name = st.session_state.get("output_folder") or "Proyecto1"
            dest_dir = base_dir / folder_name
            shapes_dir = dest_dir / "Shapes"
            mapbox_dir = dest_dir / "MapBox"
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                shapes_dir.mkdir(parents=True, exist_ok=True)
                mapbox_dir.mkdir(parents=True, exist_ok=True)
                base_name_save = st.session_state.get("base_name", "Proyecto1")
                (mapbox_dir / f"{base_name_save}.json").write_bytes(outputs_local.get("json_bytes", b"{}"))
                (mapbox_dir / f"{base_name_save}.geojson").write_bytes(outputs_local.get("geojson_bytes", b"{}"))
                if outputs_local.get("kmz_bytes"):
                    (dest_dir / f"{base_name_save}.kmz").write_bytes(outputs_local["kmz_bytes"]) 
                shp_src = Path(outputs_local.get("shp_dir") or "")
                if shp_src and shp_src.exists():
                    for ext in ("*.shp", "*.shx", "*.dbf", "*.prj", "*.cpg"):
                        for f in shp_src.glob(ext):
                            shutil.copy2(f, shapes_dir / f.name)
                geojson_emb = strip_z_from_geojson(outputs_local.get("geojson", {"type": "FeatureCollection", "features": []}))
                bounds = compute_bounds_from_geojson(geojson_emb) or [[-2, -79], [-2, -79]]
                html_map_type = st.session_state.get("html_map_type", cfg.get("html_map_type", "normal"))
                index_html = build_project_index_html(
                    geojson_emb,
                    map_type=html_map_type,
                    bounds=bounds,
                    title=f"{base_name_save} - Map Viewer",
                    folder_name=base_name_save,
                )
                (dest_dir / "index.html").write_text(index_html, encoding="utf-8")
                st.success(f"Resultados guardados en: {dest_dir}")
            except Exception as exc:
                st.error(f"No se pudieron guardar los resultados: {exc}")

        # Quitar render del mapa en esta pestaña (se muestra en pestaña Mapa del proyecto)


__all__ = ["render"]
