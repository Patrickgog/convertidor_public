import streamlit as st
import os
import json
from pathlib import Path
from src.generators.map_generators import create_mapbox_html
from src.core.geometry.coordinate_utils import strip_z_from_geojson

def render_sidebar():
    # Inyectar CSS profesional y traslúcido acorde al logo azul
    st.markdown("""
    <style>
        /* Estética general del sidebar */
        [data-testid="stSidebar"] {
            background-color: rgba(240, 247, 255, 0.95);
            border-right: 1px solid rgba(33, 150, 243, 0.2);
        }
        
        /* Botones y Radio translucidos con tonos azules */
        div.stButton > button {
            background-color: rgba(33, 150, 243, 0.1);
            color: #0d6efd;
            border: 1px solid rgba(33, 150, 243, 0.3);
            border-radius: 8px;
            backdrop-filter: blur(5px);
            transition: all 0.3s ease;
        }
        div.stButton > button:hover {
            background-color: rgba(33, 150, 243, 0.2);
            border-color: #0d6efd;
            box-shadow: 0 4px 12px rgba(13, 110, 253, 0.15);
        }
        
        /* Estilo para los headers dentro del sidebar */
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: #0d6efd;
            font-weight: 700;
        }

        /* Efecto glassmorphism para expanders */
        .streamlit-expanderHeader {
            background-color: rgba(255, 255, 255, 0.5);
            border-radius: 8px;
            border: 1px solid rgba(33, 150, 243, 0.1);
        }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.header("⚙️ Configuración")
        
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
            # Cambio solicitado: Agrupar por Layer por defecto
            st.session_state["group_by"] = "layer"
        if "html_map_type" not in st.session_state:
            st.session_state["html_map_type"] = "normal"
        if "map_point_size" not in st.session_state:
            st.session_state["map_point_size"] = 3

        # Expander 1: Georreferencia y CRS
        with st.expander("🌍 Configuración de Georreferencia", expanded=False):
            mode = st.radio("Modo CRS", ["UTM WGS84 (Zona)", "EPSG Manual"], index=0, horizontal=False)

            if mode == "UTM WGS84 (Zona)":
                col_z1, col_z2 = st.columns(2)
                with col_z1:
                    st.session_state["utm_zone"] = st.number_input("Zona UTM", value=st.session_state["utm_zone"], min_value=1, max_value=60, step=1)
                with col_z2:
                    st.session_state["utm_hemi"] = st.selectbox("Hemisferio", options=["N", "S"], index=(1 if st.session_state["utm_hemi"] == "S" else 0))
                
                # Calcular EPSG de entrada
                st.session_state["input_epsg"] = (32600 if st.session_state["utm_hemi"] == "N" else 32700) + int(st.session_state["utm_zone"])
                st.code(f"EPSG de entrada: {st.session_state['input_epsg']}", language="bash")
            else:
                st.session_state["input_epsg"] = st.number_input("EPSG de entrada", value=int(st.session_state["input_epsg"]),
                                                                   min_value=2000, max_value=99999, step=1)

            st.session_state["output_epsg"] = st.number_input("EPSG de salida", value=int(st.session_state["output_epsg"]),
                                                              min_value=2000, max_value=99999, step=1)
            
            st.caption("Predeterminado: UTM 17S (32717) → WGS84 (4326)")

        # Expander 2: Organización y Visualización
        with st.expander("📂 Organización y Capas", expanded=True):
            st.session_state["group_by"] = st.selectbox(
                "Agrupar capas por", 
                options=["type", "layer"], 
                index=(0 if st.session_state["group_by"] == "type" else 1), # Adjusted index for new default "layer"
                help="Seleccione cómo se organizarán las capas en el resultado final."
            )
            
            # Información explicativa sobre agrupamiento
            if st.session_state["group_by"] == "type":
                st.info("🔵 **Modo TYPE**: Agrupa elementos por tipo geométrico (Puntos, Líneas, Textos).")
            else:
                st.success("🟡 **Modo LAYER**: Separa elementos según las Capas originales del DXF.")

            st.markdown("---")
            st.markdown("**Visualización en Mapa HTML**")
            
            # Radio button para seleccionar tipo de mapa
            current_map_type = st.session_state.get("html_map_type", "normal")
            map_type_options = ["normal", "mapbox"]
            current_index = 0 if current_map_type == "normal" else 1
            
            map_type_selection = st.radio(
                "Tipo de Mapa:",
                options=map_type_options,
                format_func=lambda x: "Leaflet (Libre)" if x == "normal" else "Mapbox (Premium)",
                index=current_index,
                horizontal=True,
                key="map_type_radio"
            )
            
            # Detectar cambio y limpiar cache
            if st.session_state.get("previous_map_type") != map_type_selection:
                st.session_state["previous_map_type"] = map_type_selection
                if "project_html" in st.session_state:
                    del st.session_state["project_html"]
            
            st.session_state["html_map_type"] = map_type_selection
            
            st.session_state["map_point_size"] = st.slider(
                "Tamaño de Puntos:",
                min_value=1,
                max_value=20,
                value=st.session_state.get("map_point_size", 3),
                step=1,
                key="map_point_size_slider"
            )

        # Versión de la aplicación
        try:
            from src.core.config.settings import APP_VERSION
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background-color:rgba(13, 110, 253, 0.05); padding:10px; border-radius:10px; border: 1px solid rgba(13, 110, 253, 0.1); text-align:center;">
                <span style="color:#666; font-size:12px;">🚀 Versión estable:</span><br>
                <strong style="color:#0d6efd; font-size:16px;">{APP_VERSION}</strong>
            </div>
            """, unsafe_allow_html=True)
        except ImportError:
            pass
