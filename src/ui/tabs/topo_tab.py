import streamlit as st
import pandas as pd
import io
import os
import zipfile
from pathlib import Path
from src.core.converters.topo_processor import process_topo_data
from src.core.geometry.coordinate_utils import strip_z_from_geojson
from src.core.converters.heatmap_converter import create_sample_heatmap_data

def render_topo_tab():
    # ==========================================
    # MANEJO DE LIMPIEZA (antes de crear widgets)
    # ==========================================
    if st.session_state.get("clear_topo_requested", False):
        st.session_state["topo_df"] = None
        # Limpiar el valor del text_area en session_state
        if "topo_paste_area" in st.session_state:
            del st.session_state["topo_paste_area"]
        st.session_state["clear_topo_requested"] = False
        st.rerun()
    
    # Layout de 3 columnas: 35% - 35% - 30%
    col_entrada, col_config, col_resultados = st.columns([0.35, 0.35, 0.30])
    
    # ==========================================
    # COLUMNA 1: ENTRADA (35%)
    # ==========================================
    with col_entrada:
        st.markdown("### Entrada de Datos")
        
        # Modo de trabajo
        modo_topo = st.selectbox("Modo", ["Solo puntos", "Puntos y polilíneas"], index=0, key="topo_modo_selectbox")
        st.session_state["topo_modo"] = modo_topo
        
        # Modo 2D/3D
        modo_3d = st.checkbox("Modo 3D", value=st.session_state.get("topo_dim", "2D") == "3D", key="topo_dim_checkbox")
        st.session_state["topo_dim"] = "3D" if modo_3d else "2D"
        
        st.markdown("---")
        
        # Área de pegar datos
        topo_paste = st.text_area(
            "Pegar datos (No. X Y Cota Desc)", 
            height=200, 
            key="topo_paste_area",
            placeholder="Ejemplo:\n1\t500\t600\t100\tPunto A"
        )
        
        # Botones de acción
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Insertar datos", key="btn_topo_insert", use_container_width=True):
                if topo_paste:
                    try:
                        df = pd.read_csv(io.StringIO(topo_paste), sep=r'\t|,|;', engine='python', header=None)
                        if df.shape[1] < 5:
                            while df.shape[1] < 5: 
                                if df.shape[1] == 3: df[df.shape[1]] = 0 
                                else: df[df.shape[1]] = ""
                        df.columns = ["No.", "x", "y", "cota", "desc"]
                        df["cota"] = pd.to_numeric(df["cota"].astype(str).str.replace(',', '.'), errors="coerce").fillna(0)
                        df["x"] = pd.to_numeric(df["x"], errors="coerce")
                        df["y"] = pd.to_numeric(df["y"], errors="coerce")
                        st.session_state["topo_df"] = df.dropna(subset=["x", "y"])
                        st.success("Datos insertados")
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        with col_btn2:
            if st.button("Datos ejemplo", key="btn_topo_sample", use_container_width=True):
                st.session_state["topo_df"] = create_sample_heatmap_data()
                st.success("Ejemplo cargado")
        
        # Botón para limpiar usando callback
        def clear_data():
            st.session_state["clear_topo_requested"] = True
        
        st.button("Limpiar datos", key="btn_topo_clear", use_container_width=True, on_click=clear_data)
    
    # ==========================================
    # COLUMNA 2: CONFIGURACIÓN (35%)
    # ==========================================
    with col_config:
        st.markdown("### Configuración")
        
        # Configuración de Puntos
        with st.expander("CONFIGURACIÓN DE PUNTOS", expanded=True):
            pdmodes = [0, 1, 2, 3, 4, 32, 33, 34, 35, 64, 65, 66, 67, 96, 97, 98, 99]
            pdmode_labels = ["Dot", "Empty", "Plus", "Cross", "Tick", "Circle", "Circle+Plus", "Circle+Cross", "Circle+Tick", "Square", "Square+Plus", "Square+Cross", "Square+Tick", "Circle+Square", "Circle+Square+Plus", "Circle+Square+Cross", "Circle+Square+Tick"]
            pdmode_options = [f"{m} - {l}" for m, l in zip(pdmodes, pdmode_labels)]
            st.session_state["topo_pdmode_select"] = st.selectbox("Tipo de punto (PDMODE)", pdmode_options, index=6)
            st.session_state["topo_h_punto"] = st.number_input("Altura de punto", 0.01, 10.0, 0.3, 0.01)
            st.session_state["topo_color_punto"] = st.selectbox("Color punto", ["azul", "rojo", "amarillo", "verde", "cian", "magenta", "blanco", "negro"], index=0)
            st.session_state["topo_layer_puntos"] = st.text_input("Layer puntos", "PUNTOS")
        
        # Configuración de Líneas
        with st.expander("CONFIGURACIÓN DE LÍNEAS", expanded=False):
            st.session_state["topo_color_linea"] = st.selectbox("Color línea", ["rojo", "azul", "amarillo", "verde", "blanco", "negro"], index=0)
            st.session_state["topo_ancho_linea"] = st.number_input("Ancho línea (mm)", 0.01, 10.0, 0.48, 0.01)
            st.session_state["topo_tipo_linea"] = st.selectbox("Tipo línea", ["CONTINUOUS", "DASHED", "DASHDOT", "CENTER", "HIDDEN"], index=0)
            st.session_state["topo_layer_polilineas"] = st.text_input("Layer polilíneas", "POLILINEAS")
        
        # Configuración de Textos
        with st.expander("CONFIGURACIÓN DE TEXTOS", expanded=False):
            st.session_state["topo_altura_texto"] = st.number_input("Altura texto", 0.01, 10.0, 0.35, 0.01)
            st.session_state["topo_color_texto"] = st.selectbox("Color texto", ["blanco", "rojo", "azul", "amarillo", "verde", "negro"], index=0)
            col_txt1, col_txt2 = st.columns(2)
            with col_txt1:
                st.session_state["topo_desplaz_x"] = st.number_input("Desplaz X", -10.0, 10.0, 0.15, 0.01)
            with col_txt2:
                st.session_state["topo_desplaz_y"] = st.number_input("Desplaz Y", -10.0, 10.0, 0.15, 0.01)
            st.session_state["topo_layer_textos"] = st.text_input("Layer textos", "TEXTOS")
        
        st.markdown("---")
        
        # Configuración de salida
        st.session_state["topo_folder"] = st.text_input("Carpeta", value=st.session_state.get("topo_folder", "Trabajo_Topografico"))
        st.session_state["topo_output_dir"] = st.text_input("Directorio salida", value=st.session_state.get("topo_output_dir", str(Path.home() / "Downloads")))
        
        # Mapa de calor
        st.markdown("---")
        generate_heatmap = st.checkbox("Generar mapa de calor (GeoTIFF)", value=False, key="topo_heatmap_enabled")
        if generate_heatmap:
            st.session_state["topo_heatmap_margin"] = st.slider("Margen (%)", 5, 50, 15, key="topo_heatmap_margin_slider")
            st.session_state["topo_heatmap_resolution"] = st.slider("Resolución", 200, 1000, 500, key="topo_heatmap_res_slider")
            st.session_state["topo_heatmap_method"] = st.selectbox("Método", ["linear", "cubic", "nearest"], index=1, key="topo_heatmap_method_select")
    
    # ==========================================
    # COLUMNA 3: RESULTADOS (30%)
    # ==========================================
    with col_resultados:
        st.markdown("### Resultados")
        
        df = st.session_state.get("topo_df")
        if df is not None:
            # Vista previa compacta
            with st.expander("Vista previa datos", expanded=True):
                st.dataframe(df, height=150)
            
            # Botón Generar
            if st.button("Generar salidas", key="btn_topo_generate", type="primary", use_container_width=True):
                # Opciones
                options = {
                    "folder_name": st.session_state.get("topo_folder"),
                    "output_dir": st.session_state.get("topo_output_dir"),
                    "dim": st.session_state.get("topo_dim"),
                    "modo": st.session_state.get("topo_modo"),
                    "pdmode": int(st.session_state.get("topo_pdmode_select", "33").split(" - ")[0]),
                    "h_punto": st.session_state.get("topo_h_punto"),
                    "color_punto": st.session_state.get("topo_color_punto"),
                    "layer_puntos": st.session_state.get("topo_layer_puntos"),
                    "color_linea": st.session_state.get("topo_color_linea"),
                    "ancho_linea": st.session_state.get("topo_ancho_linea"),
                    "tipo_linea": st.session_state.get("topo_tipo_linea"),
                    "layer_polilineas": st.session_state.get("topo_layer_polilineas"),
                    "altura_texto": st.session_state.get("topo_altura_texto"),
                    "color_texto": st.session_state.get("topo_color_texto"),
                    "desplaz_x": st.session_state.get("topo_desplaz_x"),
                    "desplaz_y": st.session_state.get("topo_desplaz_y"),
                    "layer_textos": st.session_state.get("topo_layer_textos"),
                    "heatmap_enabled": st.session_state.get("topo_heatmap_enabled"),
                    "heatmap_margin": st.session_state.get("topo_heatmap_margin_slider"),
                    "heatmap_resolution": st.session_state.get("topo_heatmap_res_slider"),
                    "heatmap_method": st.session_state.get("topo_heatmap_method_select"),
                    "html_map_type": st.session_state.get("html_map_type", "normal")
                }
                
                with st.spinner("Generando..."):
                    results = process_topo_data(
                        df, 
                        st.session_state.get("input_epsg", 32717),
                        st.session_state.get("output_epsg", 4326),
                        options
                    )
                
                st.success(f"Guardado en: {results['main_folder']}")
                
                # ZIP
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for root, dirs, files in os.walk(results['main_folder']):
                        for file in files:
                            p = Path(root) / file
                            zf.write(p, arcname=p.relative_to(results['main_folder']))
                
                st.download_button(
                    "Descargar todo (ZIP)",
                    data=zip_buf.getvalue(),
                    file_name=f"{options['folder_name']}.zip",
                    mime="application/zip",
                    key="topo_zip_download",
                    use_container_width=True
                )
                
                if results.get("html_content"):
                    st.session_state["project_geojson"] = results["geojson"]
                    st.session_state["project_title"] = f"{options['folder_name']} - Topografia"
                    st.session_state["project_folder_name"] = options['folder_name']
                    # Limpiar HTML cacheado para regenerar con el tipo de mapa actual
                    if "project_html" in st.session_state:
                        del st.session_state["project_html"]
                    if "project_html_map_type" in st.session_state:
                        del st.session_state["project_html_map_type"]
                    st.info("Mapa actualizado en 'Mapa del proyecto'")
        else:
            st.info("Carga datos para ver resultados")
