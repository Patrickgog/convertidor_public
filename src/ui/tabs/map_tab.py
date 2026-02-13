import streamlit as st
import json
from src.core.geometry.coordinate_utils import strip_z_from_geojson
import src.generators.map_generators as mg

def render_map_tab():
    if st.session_state.get("topo_index_html"):
        st.markdown("### Mapa Topográfico")
        st.components.v1.html(st.session_state["topo_index_html"], height=750)
        st.markdown("---")
    
    pj_geo = st.session_state.get("project_geojson")
    if pj_geo is not None:
        st.markdown("### Mapa del Proyecto General")
        html_map_type = st.session_state.get("html_map_type", "normal")
        
        # Obtener colores y estilos actuales
        point_color = st.session_state.get("project_point_color", "#ff0000")
        line_color = st.session_state.get("project_line_color", "#0000ff")
        line_width = st.session_state.get("project_line_width", 2)
        
        # Verificar si necesitamos regenerar el HTML
        last_map_type = st.session_state.get("project_html_map_type")
        if st.session_state.get("project_html") and last_map_type == html_map_type:
            # Usar HTML cacheado
            html_now = st.session_state["project_html"]
        else:
            # Regenerar HTML con el tipo de mapa y colores actuales
            b = mg.compute_bounds_from_geojson(pj_geo) or [[-2, -79], [-2, -79]]
            
            if html_map_type == "mapbox":
                html_now = mg.create_mapbox_html(
                    strip_z_from_geojson(pj_geo), 
                    title=st.session_state.get("project_title","Mapa del proyecto"), 
                    folder_name=st.session_state.get("project_folder_name","Proyecto"), 
                    grouping_mode=st.session_state.get("group_by","type"),
                    point_color=point_color,
                    line_color=line_color
                )
            else:
                html_now = mg.create_leaflet_grouped_html(
                    pj_geo, 
                    title=st.session_state.get("project_title","Mapa del proyecto"),
                    grouping_mode=st.session_state.get("group_by","type"),
                    point_color=point_color,
                    line_color=line_color,
                    line_width=line_width
                )
            
            # Guardar HTML y tipo de mapa usado
            st.session_state["project_html"] = html_now
            st.session_state["project_html_map_type"] = html_map_type
        
        st.components.v1.html(html_now, height=750)
    elif not st.session_state.get("topo_index_html"):
        st.info("Genera salidas en alguna pestaña para ver aquí el mapa del proyecto.")
