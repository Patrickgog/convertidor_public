import streamlit as st
import os
import json
from pathlib import Path
from src.generators.map_generators import create_mapbox_html
from src.core.geometry.coordinate_utils import strip_z_from_geojson

def render_sidebar():
    with st.sidebar:
        st.header("Configuración")
        
        # Initialize session state if not present
        if "utm_zone" not in st.session_state:
            st.session_state["utm_zone"] = 17
        if "utm_hemi" not in st.session_state:
            st.session_state["utm_hemi"] = "S"
        if "input_epsg" not in st.session_state:
            st.session_state["input_epsg"] = 32717
        if "output_epsg" not in st.session_state:
            st.session_state["output_epsg"] = 4326
        if "group_by" not in st.session_state:
            st.session_state["group_by"] = "type"
        if "html_map_type" not in st.session_state:
            st.session_state["html_map_type"] = "normal"
        if "map_point_size" not in st.session_state:
            st.session_state["map_point_size"] = 3

        mode = st.radio("Modo CRS", ["UTM WGS84 (Zona)", "EPSG Manual"], index=0, horizontal=False)

        if mode == "UTM WGS84 (Zona)":
            col_z1, col_z2 = st.columns(2)
            with col_z1:
                st.session_state["utm_zone"] = st.number_input("Zona UTM", value=st.session_state["utm_zone"], min_value=1, max_value=60, step=1)
            with col_z2:
                st.session_state["utm_hemi"] = st.selectbox("Hemisferio", options=["N", "S"], index=(1 if st.session_state["utm_hemi"] == "S" else 0))
            # Calcular EPSG de entrada
            st.session_state["input_epsg"] = (32600 if st.session_state["utm_hemi"] == "N" else 32700) + int(st.session_state["utm_zone"])
            st.text(f"EPSG de entrada: {st.session_state['input_epsg']}")
        else:
            st.session_state["input_epsg"] = st.number_input("EPSG de entrada", value=int(st.session_state["input_epsg"]),
                                                               min_value=2000, max_value=99999, step=1)

        st.session_state["output_epsg"] = st.number_input("EPSG de salida", value=int(st.session_state["output_epsg"]),
                                                          min_value=2000, max_value=99999, step=1)
        st.session_state["group_by"] = st.selectbox("Agrupar capas por", options=["type", "layer"], index=(0 if st.session_state["group_by"] == "type" else 1))
        
        # Información explicativa sobre agrupamiento
        if st.session_state["group_by"] == "type":
            st.info("🔵 **Modo TYPE**: Agrupa elementos por tipo geométrico:\n- **Puntos**: POINT, INSERT (bloques)\n- **Líneas**: LINE, POLYLINE, LWPOLYLINE\n- **Textos**: TEXT, MTEXT")
        else:
            st.info("🟡 **Modo LAYER**: Agrupa elementos por capa del DXF:\n- Cada capa del archivo DXF se muestra por separado")
        
        st.markdown("**Tipo de Mapa HTML**")
        
        # Radio button para seleccionar tipo de mapa
        map_type_selection = st.radio(
            "Seleccione el tipo de mapa:",
            options=["normal", "mapbox"],
            format_func=lambda x: "Mapa Normal (Leaflet)" if x == "normal" else "Mapa Mapbox",
            index=0 if st.session_state["html_map_type"] == "normal" else 1,
            horizontal=True,
            key="map_type_radio"
        )
        
        # Logic to handle map type change
        if map_type_selection != st.session_state.get("previous_map_type", "normal"):
            st.session_state["previous_map_type"] = map_type_selection
            st.session_state["active_tab"] = 1
            # Special case for regenerating project map if exists
            if st.session_state.get("topo_index_html") and st.session_state.get("project_geojson"):
                try:
                    geojson_data = st.session_state["project_geojson"]
                    folder_name = st.session_state.get("project_folder_name", "Proyecto")
                    point_size = st.session_state.get("map_point_size", 3)
                    
                    if map_type_selection == "mapbox":
                        st.session_state["topo_index_html"] = create_mapbox_html(
                            strip_z_from_geojson(geojson_data), 
                            title=f"{folder_name} - Visor de Mapa Topográfico", 
                            folder_name=folder_name, 
                            grouping_mode="type"
                        )
                    else:
                        # Leaflet regeneration logic - Simplified for now or kept as is
                        # This would need more dependencies if fully moved
                        pass
                except Exception as e:
                    st.warning(f"Error regenerando mapa topográfico: {e}")
            st.rerun()

        st.session_state["html_map_type"] = map_type_selection
        
        st.markdown("**🎯 Configuración de Puntos:**")
        point_size = st.slider(
            "Tamaño de puntos en el mapa",
            min_value=1,
            max_value=20,
            value=st.session_state.get("map_point_size", 3),
            step=1,
            key="map_point_size_slider"
        )
        st.session_state["map_point_size"] = point_size
        
        if map_type_selection == "mapbox":
            st.info("💡 **Mapa Mapbox**: Requiere API Key de Mapbox.")
        else:
            st.info("🗺️ **Mapa Normal**: Usa Leaflet.")
        
        st.caption("Por defecto, entrada UTM 17S (EPSG:32717) y salida WGS84 (EPSG:4326).")

        # Versión de la aplicación (Protocolo de Versionado Automático)
        try:
            from src.core.config.settings import APP_VERSION
            st.markdown("---")
            st.caption(f"🚀 Versión: {APP_VERSION}")
        except ImportError:
            pass
