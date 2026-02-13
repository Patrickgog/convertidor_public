import streamlit as st
import os
import json
import logging
from pathlib import Path

# Configuración y Constantes (v3.4.3)
from src.core.config.settings import APP_VERSION, DEVELOPER, APP_NAME

# Page config - DEBE SER LO PRIMERO (antes de importar auth que usa widgets)
st.set_page_config(
    page_title="CONVERSOR UNIVERSAL PROFESIONAL",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sistema de autenticación
try:
    from src.core.auth.auth_system import check_authentication, show_user_info
except ImportError as e:
    st.error(f"❌ Error crítico de importación en el sistema de autenticación: {e}")
    st.info("Intentando diagnóstico... Verificando rutas de módulos.")
    import sys
    # st.write(f"DEBUG sys.path: {sys.path}")
    st.stop()

# UI Components
from src.ui.sidebar import render_sidebar
from src.ui.tabs.dxf_tab import render_dxf_tab
from src.ui.tabs.gpx_tab import render_gpx_tab
from src.ui.tabs.kml_tab import render_kml_tab
from src.ui.tabs.topo_tab import render_topo_tab
from src.ui.tabs.map_tab import render_map_tab
from src.ui.tabs.manual_tab import render_manual_tab

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app_universal")

def main():
    # Authentication check
    if not check_authentication():
        st.stop()
    
    # Hide GitHub toolbar buttons in Cloud
    st.markdown("""
    <style>
        div[data-testid="stToolbar"] a[href*="github.com"] { display: none !important; }
        div[data-testid="stToolbar"] button[title="View source"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)
    
    # Global title
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;margin:10px 0 4px 0;">
      <span style="font-size:28px;">📡</span>
      <h1 style="margin:0;color:#0d6efd;">{APP_NAME} <span style="font-size:16px;color:#666;font-weight:normal;">{APP_VERSION}</span></h1>
    </div>
    <div style="color:#666;margin-bottom:12px;">Carga archivos, define el sistema de referencia y descarga resultados geoespaciales.</div>
    """, unsafe_allow_html=True)

    # Sidebar
    render_sidebar()

    # Main Tabs
    tab_dxf, tab_gpx, tab_kmz, tab_topo, tab_map, tab_manual = st.tabs([
        "📐 DXF Profesional",
        "🥾 GPX Profesional", 
        "🌍 KML/KMZ Profesional",
        "📊 Topográfico Profesional",
        "🗺️ Mapa del proyecto",
        "📚 Manual de Usuario"
    ])

    with tab_dxf:
        render_dxf_tab()
    
    with tab_gpx:
        render_gpx_tab()
        
    with tab_kmz:
        render_kml_tab()
        
    with tab_topo:
        render_topo_tab()
        
    with tab_map:
        render_map_tab()
        
    with tab_manual:
        render_manual_tab()

    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align:center;color:#666;font-size:14px;padding:10px;">
        <strong>{APP_NAME}</strong> | Versión: {APP_VERSION} | <strong>Desarrollador:</strong> {DEVELOPER}
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()