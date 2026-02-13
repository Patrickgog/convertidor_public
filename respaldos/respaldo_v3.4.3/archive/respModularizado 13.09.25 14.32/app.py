import streamlit as st
from pathlib import Path

# Honrar preferencia de modo desde config/auth_mode.txt
mode_pref = None
try:
    mode_file = Path(__file__).resolve().parent / "config" / "auth_mode.txt"
    if mode_file.exists():
        mode_pref = mode_file.read_text(encoding="utf-8").strip().lower()
except Exception:
    mode_pref = None

# Sistema de autenticación (modo conmutado: completo con email / simplificado)
try:
    if mode_pref == "complete":
        from app_pkg.auth.system import check_authentication, show_user_info  # type: ignore
        AUTH_MODE = "complete"
    elif mode_pref == "simple":
        from app_pkg.auth.simple import (
            check_simple_authentication as check_authentication,
            show_simple_user_info as show_user_info,
        )  # type: ignore
        AUTH_MODE = "simple"
        st.write("🔧 Modo desarrollo: Autenticación simplificada activa")
    else:
        from app_pkg.auth.system import check_authentication, show_user_info  # type: ignore
        AUTH_MODE = "complete"
except Exception:
    try:
        from app_pkg.auth.simple import (
            check_simple_authentication as check_authentication,
            show_simple_user_info as show_user_info,
        )  # type: ignore
        AUTH_MODE = "simple"
        st.write("🔧 Modo desarrollo: Autenticación simplificada activa")
    except Exception:
        from auth_system import check_authentication, show_user_info  # type: ignore
        AUTH_MODE = "complete"

from app_pkg.ui.layout import setup_layout
from app_pkg.ui.tabs import dxf as tab_dxf
from app_pkg.ui.tabs import gpx as tab_gpx
from app_pkg.ui.tabs import topo as tab_topo
from app_pkg.ui.tabs import project_map as tab_project_map


if not check_authentication():
    st.stop()
show_user_info()

cfg = setup_layout()

st.markdown("---")

t_dxf, t_gpx, t_kmz, t_topo, t_map, t_manual = st.tabs([
    "📐 DXF Profesional",
    "🥾 GPX Profesional",
    "🌍 KML/KMZ Profesional",
    "📊 Topográfico Profesional",
    "🗺️ Mapa del proyecto",
    "📚 Manual de Usuario",
])

with t_dxf:
    tab_dxf.render(cfg)
with t_gpx:
    tab_gpx.render(cfg)
with t_topo:
    tab_topo.render(cfg)
with t_map:
    tab_project_map.render(cfg)
with t_kmz:
    st.info("Pestaña KML/KMZ pendiente de migración.")
with t_manual:
    st.info("Manual de usuario disponible en docs/.")
