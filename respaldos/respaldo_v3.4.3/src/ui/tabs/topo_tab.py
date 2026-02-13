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
    col1, col2, col3, col4 = st.columns([3, 8, 7, 6])
    
    with col4:
        st.markdown("**:orange[MAPAS DE CALOR]**")
        generate_heatmap = st.checkbox("Generar mapa de calor (GeoTIFF)", value=False, key="topo_heatmap_enabled")
        if generate_heatmap:
            st.session_state["topo_heatmap_margin"] = st.slider("Margen (%)", 5, 50, 15, key="topo_heatmap_margin_slider")
            st.session_state["topo_heatmap_resolution"] = st.slider("Resolución", 200, 1000, 500, key="topo_heatmap_res_slider")
            st.session_state["topo_heatmap_method"] = st.selectbox("Método", ["linear", "cubic", "nearest"], index=1, key="topo_heatmap_method_select")
        
        st.markdown("---")
        st.subheader("Configuración DXF")
        # Puntos
        st.markdown("**:red[PUNTOS]**")
        pdmodes = [0, 1, 2, 3, 4, 32, 33, 34, 35, 64, 65, 66, 67, 96, 97, 98, 99]
        pdmode_labels = ["Dot", "Empty", "Plus", "Cross", "Tick", "Circle", "Circle+Plus", "Circle+Cross", "Circle+Tick", "Square", "Square+Plus", "Square+Cross", "Square+Tick", "Circle+Square", "Circle+Square+Plus", "Circle+Square+Cross", "Circle+Square+Tick"]
        pdmode_options = [f"{m} - {l}" for m, l in zip(pdmodes, pdmode_labels)]
        st.session_state["topo_pdmode_select"] = st.selectbox("Tipo de punto (PDMODE)", pdmode_options, index=6)
        st.session_state["topo_h_punto"] = st.number_input("Altura de punto", 0.01, 10.0, 0.3, 0.01)
        st.session_state["topo_color_punto"] = st.selectbox("Color punto", ["azul", "rojo", "amarillo", "verde", "cian", "magenta", "blanco", "negro"], index=0)
        st.session_state["topo_layer_puntos"] = st.text_input("Layer puntos", "PUNTOS")
        
        st.markdown("---")
        # Líneas
        st.markdown("**:blue[LÍNEAS/POLÍGONOS]**")
        st.session_state["topo_color_linea"] = st.selectbox("Color línea", ["rojo", "azul", "amarillo", "verde", "blanco", "negro"], index=0)
        st.session_state["topo_ancho_linea"] = st.number_input("Ancho línea (mm)", 0.01, 10.0, 0.48, 0.01)
        st.session_state["topo_tipo_linea"] = st.selectbox("Tipo línea", ["CONTINUOUS", "DASHED", "DASHDOT", "CENTER", "HIDDEN"], index=0)
        st.session_state["topo_layer_polilineas"] = st.text_input("Layer polílíneas", "POLILINEAS")
        
        st.markdown("---")
        # Textos
        st.markdown("**:green[TEXTOS]**")
        st.session_state["topo_altura_texto"] = st.number_input("Altura texto", 0.01, 10.0, 0.35, 0.01)
        st.session_state["topo_color_texto"] = st.selectbox("Color texto", ["blanco", "rojo", "azul", "amarillo", "verde", "negro"], index=0)
        st.session_state["topo_desplaz_x"] = st.number_input("Desplaz X", -10.0, 10.0, 0.15, 0.01)
        st.session_state["topo_desplaz_y"] = st.number_input("Desplaz Y", -10.0, 10.0, 0.15, 0.01)
        st.session_state["topo_layer_textos"] = st.text_input("Layer textos", "TEXTOS")

    with col2:
        st.header("Sistema Topográfico Profesional")
        modo_topo = st.selectbox("Modo", ["Solo puntos", "Puntos y polilíneas"], index=0, key="topo_modo_selectbox")
        st.session_state["topo_modo"] = modo_topo
        
        modo_3d = st.checkbox("🔺 Modo 3D", value=st.session_state.get("topo_dim", "2D") == "3D", key="topo_dim_checkbox")
        st.session_state["topo_dim"] = "3D" if modo_3d else "2D"
        
        topo_paste = st.text_area("Pegar datos", height=280, key="topo_paste_area", placeholder="No.\tX\tY\tCota\tDesc")
        
        c_btn1, c_btn2, c_btn3 = st.columns(3)
        if c_btn1.button("Insertar datos", key="btn_topo_insert"):
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
                    st.success("✅ Datos insertados")
                except Exception as e:
                    st.error(f"Error: {e}")

        if c_btn2.button("Datos de ejemplo", key="btn_topo_sample"):
            st.session_state["topo_df"] = create_sample_heatmap_data()
            st.success("✅ Ejemplo cargado")

        def clear_topo_data():
            st.session_state["topo_paste_area"] = ""
            st.session_state["topo_df"] = None

        if c_btn3.button("Limpiar", key="btn_topo_clear", on_click=clear_topo_data):
            st.rerun()
            
        st.markdown("---")
        st.session_state["topo_folder"] = st.text_input("Carpeta", value=st.session_state.get("topo_folder", "Trabajo_Topográfico"))
        st.session_state["topo_output_dir"] = st.text_input("Directorío salida", value=st.session_state.get("topo_output_dir", str(Path.home() / "Downloads")))

    with col3:
        st.subheader("Vista previa")
        df = st.session_state.get("topo_df")
        if df is not None:
            st.dataframe(df)
            if st.button("Generar salidas", key="btn_topo_generate", type="primary"):
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
                
                st.success(f"✅ Salidas generadas en: {results['main_folder']}")
                
                # ZIP
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for root, dirs, files in os.walk(results['main_folder']):
                        for file in files:
                            p = Path(root) / file
                            zf.write(p, arcname=p.relative_to(results['main_folder']))
                
                st.download_button(
                    "📥 Descargar todo (ZIP)",
                    data=zip_buf.getvalue(),
                    file_name=f"{options['folder_name']}.zip",
                    mime="application/zip",
                    key="topo_zip_download"
                )
                
                if results.get("html_content"):
                    st.session_state["project_geojson"] = results["geojson"]
                    st.session_state["project_title"] = f"{options['folder_name']} - Topografía"
                    st.info("💡 El mapa ha sido actualizado en la pestaña 'Mapa del proyecto'")
        else:
            st.info("No hay datos.")
