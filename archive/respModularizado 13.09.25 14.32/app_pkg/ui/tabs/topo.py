import io
import os
from pathlib import Path
from typing import Dict, Any

import streamlit as st
import pandas as pd
import ezdxf
import pyproj
from simplekml import Kml

from app_pkg.core.geojson_utils import strip_z_from_geojson, compute_bounds_from_geojson
from app_pkg.export.html_export import build_project_index_html


def render(cfg: Dict[str, Any]) -> None:
    col1, col2, col3, col4 = st.columns([2, 7, 6, 5])
    with col4:
        st.subheader("Configuración DXF")
        pdmodes = [0, 1, 2, 3, 4, 32, 33, 34, 35, 64, 65, 66, 67, 96, 97, 98, 99]
        pdmode_labels = [
            "Dot", "Empty", "Plus", "Cross", "Tick", "Circle", "Circle+Plus", "Circle+Cross", "Circle+Tick",
            "Square", "Square+Plus", "Square+Cross", "Square+Tick", "Circle+Square", "Circle+Square+Plus", "Circle+Square+Cross", "Circle+Square+Tick",
        ]
        pdmode_options = [f"{mode} - {label}" for mode, label in zip(pdmodes, pdmode_labels)]
        pdmode_selected = st.selectbox("Tipo de punto (PDMODE)", pdmode_options, index=6, key="topo_pdmode_select")
        pdmode = int(pdmode_selected.split(" - ")[0])
        st.session_state["topo_pdmode"] = pdmode
        st.session_state["topo_h_punto"] = st.number_input("Altura de punto", min_value=0.01, max_value=10.0, value=0.3, step=0.01, key="topo_h_punto")
        st.session_state["topo_color_punto"] = st.selectbox("Color de punto", ["azul", "rojo", "amarillo", "verde", "cian", "magenta", "blanco", "gris", "naranja", "negro"], index=0, key="topo_color_punto")
        st.session_state["topo_layer_puntos"] = st.text_input("Layer de puntos", value="PUNTOS", key="topo_layer_puntos")
        st.markdown("---")
        st.markdown("**:blue[LÍNEAS/POLÍGONOS]**")
        st.session_state["topo_color_linea"] = st.selectbox("Color de línea", ["rojo", "azul", "amarillo", "verde", "cian", "magenta", "blanco", "gris", "naranja", "negro"], index=0, key="topo_color_linea")
        st.session_state["topo_ancho_linea"] = st.number_input("Ancho de línea (mm)", min_value=0.01, max_value=10.0, value=0.48, step=0.01, key="topo_ancho_linea")
        st.session_state["topo_tipo_linea"] = st.selectbox("Tipo de línea", [
            "CONTINUOUS", "DASHED", "DASHDOT", "CENTER", "HIDDEN", "PHANTOM", "DOT", "DIVIDE", "BORDER", "WAVE"
        ], index=0, key="topo_tipo_linea")
        st.session_state["topo_layer_polilineas"] = st.text_input("Layer de polílíneas", value="POLILINEAS", key="topo_layer_polilineas")
        st.markdown("---")
        st.markdown("**:green[TEXTOS]**")
        st.session_state["topo_altura_texto"] = st.number_input("Altura de texto", min_value=0.01, max_value=10.0, value=0.35, step=0.01, key="topo_altura_texto")
        st.session_state["topo_color_texto"] = st.selectbox("Color de texto", ["blanco", "rojo", "azul", "amarillo", "verde", "cian", "magenta", "gris", "naranja", "negro"], index=0, key="topo_color_texto")
        st.session_state["topo_desplaz_x"] = st.number_input("Desplazamiento X", min_value=-10.0, max_value=10.0, value=0.15, step=0.01, key="topo_desplaz_x")
        st.session_state["topo_desplaz_y"] = st.number_input("Desplazamiento Y", min_value=-10.0, max_value=10.0, value=0.15, step=0.01, key="topo_desplaz_y")
        st.session_state["topo_layer_textos"] = st.text_input("Layer de textos", value="TEXTOS", key="topo_layer_textos")

    with col2:
        st.header("Sistema Topográfico Profesional")
        st.caption("Pega los datos de puntos topográficos en el área de texto.")
        st.session_state["topo_modo"] = st.radio("Modo de generación", ["Solo puntos", "Puntos y polilíneas"], key="topo_modo")
        st.session_state["topo_dim"] = st.radio("Dimensión", options=["2D", "3D"], index=0, horizontal=True, key="topo_dim")
        if "topo_df" not in st.session_state:
            st.session_state["topo_df"] = None
        if "topo_paste" not in st.session_state:
            st.session_state.topo_paste = ""
        st.session_state.topo_paste = st.text_area("Pegar datos (No., x, y, cota, descripcion)", value=st.session_state.topo_paste, height=200, key="topo_paste_area")

        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if st.button("Insertar datos", key="btn_topo_paste"):
                pasted = st.session_state.get("topo_paste", "")
                try:
                    df_paste = pd.read_csv(io.StringIO(pasted), sep="\t|,|;", engine="python", header=None)
                    while df_paste.shape[1] < 5:
                        if df_paste.shape[1] == 3:
                            df_paste[df_paste.shape[1]] = 0
                        else:
                            df_paste[df_paste.shape[1]] = ""
                    df_paste.columns = ["No.", "x", "y", "cota", "desc"]
                    df_paste["cota"] = pd.to_numeric(df_paste["cota"], errors="coerce").fillna(0)
                    st.session_state["topo_df"] = df_paste
                    st.success("Datos pegados insertados.")
                except Exception as e:
                    st.error(f"Error al procesar los datos pegados: {e}")
        with col_btn2:
            if st.button("Limpiar", key="btn_topo_clear_paste"):
                st.session_state.topo_paste = ""
                if "topo_df" in st.session_state:
                    st.session_state.topo_df = None
                st.rerun()
        with col_btn3:
            if st.button("Pegar del portapapeles"):
                try:
                    df_clipboard = pd.read_clipboard(header=None, sep="\s*[,;\t]\s*")
                    pasted_text = df_clipboard.to_csv(sep='\t', index=False, header=False)
                    st.session_state.topo_paste = pasted_text
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo pegar desde el portapapeles: {e}")

        st.text_input("Nombre de carpeta", value=st.session_state.get("topo_folder", "Trabajo_Topográfico"), key="topo_folder")
        st.text_input("Ruta de descarga", value=st.session_state.get("topo_output_dir", str(Path.home() / "Downloads")), key="topo_output_dir")

        if st.button("Seleccionar carpeta de descarga", key="btn_topo_select_dir"):
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk(); root.withdraw()
                selected_dir = filedialog.askdirectory()
                root.destroy()
                if selected_dir:
                    st.session_state["topo_output_dir"] = selected_dir
                    st.success(f"Carpeta seleccionada: {selected_dir}")
            except Exception as e:
                st.warning(f"No se pudo abrir el selector de carpetas: {e}")

        if st.button("Limpiar tabla", key="btn_topo_clear"):
            st.session_state["topo_df"] = None

    with col3:
        st.subheader("Vista previa de la tabla")
        headers = ["No.", "x", "y", "cota", "desc"]
        df = st.session_state.get("topo_df")
        if df is not None:
            df = df.copy(); df.columns = headers[:len(df.columns)]
            st.dataframe(df)
        else:
            st.info("No hay datos cargados.")
        if df is not None:
            col_btn1, col_btn2 = st.columns([2, 2])
            gen_clicked = col_btn1.button("Generar salidas", key="btn_topo_generate")
            open_folder_clicked = col_btn2.button("Abrir carpeta de salida", key="btn_topo_open_folder")
            if open_folder_clicked:
                base_dir = st.session_state["topo_output_dir"]
                folder_name = st.session_state["topo_folder"]
                idx_folder = 1
                main_folder = os.path.join(base_dir, folder_name)
                while os.path.exists(main_folder):
                    idx_folder += 1
                    main_folder = os.path.join(base_dir, f"{folder_name}_{idx_folder}")
                if idx_folder > 1:
                    main_folder = os.path.join(base_dir, f"{folder_name}_{idx_folder-1}")
                import webbrowser
                webbrowser.open(f"file://{main_folder}")
            if gen_clicked:
                try:
                    input_epsg = int(cfg.get("input_epsg", 32717))
                    output_epsg = int(cfg.get("output_epsg", 4326))
                    transformer = pyproj.Transformer.from_crs(f"EPSG:{input_epsg}", f"EPSG:{output_epsg}", always_xy=True)
                    base_dir = st.session_state["topo_output_dir"]
                    folder_name = st.session_state["topo_folder"]
                    main_folder = os.path.join(base_dir, folder_name)
                    idx_folder = 1
                    while os.path.exists(main_folder):
                        main_folder = os.path.join(base_dir, f"{folder_name}_{idx_folder}")
                        idx_folder += 1
                    os.makedirs(main_folder, exist_ok=True)
                    dxf_path = os.path.join(main_folder, f"{folder_name}.dxf")
                    doc = ezdxf.new(dxfversion="R2000")
                    doc.saveas(dxf_path)
                    geojson_serializable = {"type": "FeatureCollection", "features": []}
                    # Preparar HTML para la pestaña de Mapa del proyecto (no renderizar aquí)
                    bounds = compute_bounds_from_geojson(geojson_serializable) or [[-2, -79], [-2, -79]]
                    html_map_type = st.session_state.get("html_map_type", cfg.get("html_map_type", "normal"))
                    index_html_content = build_project_index_html(
                        strip_z_from_geojson(geojson_serializable),
                        map_type=html_map_type,
                        bounds=bounds,
                        title=f"{folder_name} - Visor de Mapa Topográfico",
                        folder_name=folder_name,
                    )
                    st.session_state["project_geojson"] = geojson_serializable
                    st.session_state["project_map_html"] = index_html_content
                    with open(os.path.join(main_folder, "index.html"), "w", encoding="utf-8") as f:
                        f.write(index_html_content)
                except Exception as e:
                    st.error(f"Error al generar salidas topográficas: {e}")


__all__ = ["render"]
