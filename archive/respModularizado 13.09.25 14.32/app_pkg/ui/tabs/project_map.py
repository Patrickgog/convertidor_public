import streamlit as st
from typing import Dict, Any

from app_pkg.ui.map_render import render_map


def render(cfg: Dict[str, Any]) -> None:
    st.header("🗺️ Mapa del proyecto")

    geojson = st.session_state.get("project_geojson")
    if geojson and geojson.get("features"):
        st.subheader("Vista Folium (rápida)")
        render_map(geojson, group_by=cfg.get("group_by", "type"))
    else:
        st.info("Aún no hay GeoJSON de proyecto disponible.")

    html = st.session_state.get("project_map_html")
    if html and isinstance(html, str) and len(html) > 100:
        st.subheader("Visor HTML embebido")
        st.components.v1.html(html, height=640, scrolling=True)
    else:
        st.caption("Genera resultados en DXF/GPX/Topo para ver el visor HTML aquí.")


__all__ = ["render"]
