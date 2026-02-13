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

def render_gpx_tab():
    st.caption("Convierte archivos GPX a múltiples formatos con estilización personalizada")
    
    # Layout de 3 columnas persistente: 35% - 35% - 30%
    col1, col2, col3 = st.columns([0.35, 0.35, 0.30])
    
    with col1:
        st.markdown("📂 **Entrada**")
        uploaded = st.file_uploader("Subir GPX", type=["gpx"], key="gpx_uploader")
        if uploaded:
            st.success(f"Cargado: {uploaded.name}")

    with col2:
        st.markdown("🎨 **Estilos**")
        p_color = st.color_picker("Color Puntos", "#e31a1c", key="gpx_p_color")
        l_color = st.color_picker("Color Líneas", "#1f78b4", key="gpx_l_color")
        l_width = st.number_input("Ancho Línea", 0.5, 10.0, 2.5, 0.5, key="gpx_l_width")

    with col3:
        st.markdown("⚙️ **Configuración**")
        folder_name = st.text_input("Nombre de carpeta", value="Levantamiento_GPX", key="gpx_folder_name")
        btn_convert = st.button("🚀 Generar Paquete", use_container_width=True, disabled=not uploaded, key="gpx_btn_convert")

    if uploaded and btn_convert:
        with st.spinner("Procesando..."):
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
                
                geojson = {"type": "FeatureCollection", "features": features}
                st.session_state["project_geojson"] = geojson
                
                # Generación de paquete ZIP profesional
                from src.core.converters.universal_exporter import export_geojson_to_all_formats
                
                zip_bytes = export_geojson_to_all_formats(
                    geojson, 
                    folder_name,
                    point_color=p_color,
                    line_color=l_color,
                    line_width=l_width
                )
                
                st.success("✅ ¡Paquete generado!")
                st.download_button(
                    label="📦 Descargar ZIP PROFESIONAL",
                    data=zip_bytes,
                    file_name=f"{folder_name}.zip",
                    mime="application/zip",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error: {e}")
