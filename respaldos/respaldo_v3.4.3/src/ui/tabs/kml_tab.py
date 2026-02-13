import streamlit as st
import tempfile
import io
import os
import zipfile
import json
import pyproj
import shapefile
from pathlib import Path
from src.core.converters.kml_converter import parse_kml_via_xml
from src.core.geometry.coordinate_utils import strip_z_from_geojson, transform_geojson, compute_bounds_from_geojson
from src.generators.map_generators import create_mapbox_html, create_leaflet_grouped_html

def render_kml_tab():
    st.caption("Convierte archivos KML/KMZ a múltiples formatos con estilización personalizada")
    
    # Layout de 3 columnas persistente: 35% - 35% - 30%
    col1, col2, col3 = st.columns([0.35, 0.35, 0.30])
    
    with col1:
        st.markdown("📂 **Entrada**")
        uploaded = st.file_uploader("Subir KML/KMZ", type=["kml", "kmz"], key="kml_uploader")
        if uploaded:
            st.success(f"Cargado: {uploaded.name}")

    with col2:
        st.markdown("🎨 **Estilos**")
        p_color = st.color_picker("Color Puntos", "#e31a1c", key="kml_p_color")
        l_color = st.color_picker("Color Líneas", "#1f78b4", key="kml_l_color")
        l_width = st.number_input("Ancho Línea", 0.5, 10.0, 2.5, 0.5, key="kml_l_width")

    with col3:
        st.markdown("⚙️ **Configuración**")
        folder_name = st.text_input("Nombre de carpeta", value="Levantamiento_KML_KMZ", key="kml_folder_name")
        btn_convert = st.button("🚀 Generar Paquete", use_container_width=True, disabled=not uploaded, key="kml_btn_convert")

    if uploaded and btn_convert:
        with st.spinner("Procesando..."):
            try:
                raw_data = uploaded.getvalue()
                if uploaded.name.lower().endswith('.kmz'):
                    try:
                        with zipfile.ZipFile(io.BytesIO(raw_data)) as z:
                            kml_files = [f for f in z.namelist() if f.endswith('.kml')]
                            if not kml_files:
                                raise ValueError("No se encontró archivo KML dentro del KMZ")
                            kml_bytes = z.read(kml_files[0])
                    except zipfile.BadZipFile:
                        # Intento de recuperación: Puede ser un KML renombrado a KMZ
                        try:
                            # Intentar decodificar como utf-8 para verificar si es texto (KML/XML)
                            raw_data.decode('utf-8')
                            kml_bytes = raw_data
                            st.warning("⚠️ El archivo tiene extensión .kmz pero parece ser un KML (texto). Se procesará como KML.")
                        except UnicodeDecodeError:
                            raise zipfile.BadZipFile("El archivo no es un ZIP válido ni un KML de texto legible.")
                else:
                    kml_bytes = raw_data
                
                geojson = parse_kml_via_xml(kml_bytes)
                geojson = strip_z_from_geojson(geojson)
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
                st.error(f"Error detallado: {type(e).__name__}: {e}")
                print(f"DEBUG EXCEPTION: {e}")
