import streamlit as st
import gpxpy
import json
import tempfile
import io
import os
import zipfile
from pathlib import Path
import shapefile
from simplekml import Kml
from src.core.geometry.coordinate_utils import strip_z_from_geojson, build_transformer
from src.generators.map_generators import create_mapbox_html, create_leaflet_grouped_html

def render_gpx_tab():
    # Layout de 3 columnas: 35% - 35% - 30%
    col_entrada, col_estilos, col_config = st.columns([0.35, 0.35, 0.30])
    
    # ==========================================
    # COLUMNA 1: ENTRADA (35%)
    # ==========================================
    with col_entrada:
        st.markdown("### Entrada")
        
        uploaded = st.file_uploader("Subir archivo GPX", type=["gpx"], key="gpx_uploader")
        
        if uploaded:
            st.success(f"Cargado: **{uploaded.name}**")
        
        # Procesar archivo GPX inmediatamente al cargar
        if uploaded:
            file_details = f"{uploaded.name}-{uploaded.size}"
            if st.session_state.get("gpx_last_file") != file_details:
                st.session_state["gpx_last_file"] = file_details
                suggested = Path(uploaded.name).stem
                st.session_state["gpx_folder_name"] = suggested
                
                # Procesar GPX y guardar en session_state
                try:
                    gpx = gpxpy.parse(uploaded.getvalue().decode("utf-8", errors="ignore"))
                    features = []
                    for w in gpx.waypoints:
                        features.append({
                            "type": "Feature",
                            "properties": {"type": "point", "name": w.name or ""},
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
                    
                    st.session_state["gpx_geojson"] = {"type": "FeatureCollection", "features": features}
                    st.session_state["project_geojson"] = st.session_state["gpx_geojson"]
                    st.session_state["project_title"] = f"{suggested} - GPX"
                    st.session_state["project_folder_name"] = suggested
                    # Limpiar cache de mapa
                    if "project_html" in st.session_state:
                        del st.session_state["project_html"]
                    if "project_html_map_type" in st.session_state:
                        del st.session_state["project_html_map_type"]
                except Exception as e:
                    st.error(f"Error procesando GPX: {e}")
    
    # ==========================================
    # COLUMNA 2: ESTILOS (35%)
    # ==========================================
    with col_estilos:
        st.markdown("### Estilos de Visualización")
        
        p_color = st.color_picker("Color de Puntos", "#e31a1c", key="gpx_p_color")
        l_color = st.color_picker("Color de Líneas", "#1f78b4", key="gpx_l_color")
        l_width = st.slider("Ancho de Línea", 0.5, 10.0, 2.5, 0.5, key="gpx_l_width")
        
        # Actualizar mapa en tiempo real cuando cambian los estilos
        if st.session_state.get("gpx_geojson"):
            # Guardar colores actuales
            st.session_state["gpx_point_color"] = p_color
            st.session_state["gpx_line_color"] = l_color
            st.session_state["gpx_line_width"] = l_width
            
            # Actualizar mapa del proyecto con los nuevos colores
            st.session_state["project_geojson"] = st.session_state["gpx_geojson"]
            st.session_state["project_point_color"] = p_color
            st.session_state["project_line_color"] = l_color
            st.session_state["project_line_width"] = l_width
            # Limpiar cache para forzar regeneración
            if "project_html" in st.session_state:
                del st.session_state["project_html"]
    
    # ==========================================
    # COLUMNA 3: CONFIGURACIÓN Y RESULTADOS (30%)
    # ==========================================
    with col_config:
        st.markdown("### Configuración")
        
        folder_name = st.text_input("Nombre de carpeta", key="gpx_folder_name")
        output_dir = st.text_input("Directorio de salida", value=st.session_state.get("topo_output_dir", str(Path.home() / "Downloads")), key="gpx_output_dir")
        
        st.markdown("---")
        
        btn_convert = st.button(
            "Generar Paquete", 
            use_container_width=True, 
            disabled=not uploaded, 
            key="gpx_btn_convert",
            type="primary"
        )
    
    # ==========================================
    # GENERACIÓN DE PAQUETE ZIP
    # ==========================================
    if uploaded and btn_convert and st.session_state.get("gpx_geojson"):
        with st.spinner("Generando paquete..."):
            try:
                geojson = st.session_state["gpx_geojson"]
                
                # Generación de paquete ZIP
                from src.core.converters.universal_exporter import export_geojson_to_all_formats
                
                # Obtener tipo de mapa seleccionado en el sidebar
                map_type = st.session_state.get("html_map_type", "normal")
                
                zip_bytes = export_geojson_to_all_formats(
                    geojson, 
                    folder_name,
                    point_color=p_color,
                    line_color=l_color,
                    line_width=l_width,
                    map_type=map_type
                )
                
                # Guardado Local
                try:
                    save_path = Path(output_dir) / f"{folder_name}.zip"
                    Path(output_dir).mkdir(parents=True, exist_ok=True)
                    with open(save_path, "wb") as f:
                        f.write(zip_bytes)
                    st.success(f"Guardado en: {save_path}")
                except Exception as save_err:
                    st.warning(f"No se pudo guardar localmente: {save_err}")
                
                # Botón de descarga
                st.download_button(
                    label="Descargar ZIP",
                    data=zip_bytes,
                    file_name=f"{folder_name}.zip",
                    mime="application/zip",
                    use_container_width=True
                )
                
            except Exception as e:
                st.error(f"Error: {e}")
