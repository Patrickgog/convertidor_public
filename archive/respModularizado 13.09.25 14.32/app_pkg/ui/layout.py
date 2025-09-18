import streamlit as st
from pathlib import Path
from typing import Dict, Any


def setup_layout() -> Dict[str, Any]:
    """Configure page and sidebar, set defaults, and return a config dict."""
    st.set_page_config(page_title="Conversor Profesional", layout="wide")

    st.markdown(
        """
        <div style='display:flex;align-items:center;gap:12px;'>
          <img src='https://cdn-icons-png.flaticon.com/512/2906/2906318.png' width='38'/>
          <h2 style='margin:0;'>Conversor Profesional</h2>
        </div>
        <span style='color:#0d6efd;font-weight:600;'>Patricio Sarmiento Reinoso</span>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Carga archivos, define el sistema de referencia y descarga resultados geoespaciales.")

    # Defaults in session_state
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
    if "output_dir" not in st.session_state:
        default_downloads = Path.home() / "Downloads"
        st.session_state["output_dir"] = str(default_downloads if default_downloads.exists() else Path.cwd())
    if "output_folder" not in st.session_state:
        st.session_state["output_folder"] = "Proyecto1"

    with st.sidebar:
        st.header("Configuración")
        mode = st.radio("Modo CRS", ["UTM WGS84 (Zona)", "EPSG Manual"], index=0, horizontal=False)
        if mode == "UTM WGS84 (Zona)":
            col_z1, col_z2 = st.columns(2)
            with col_z1:
                st.session_state["utm_zone"] = st.number_input("Zona UTM", value=st.session_state["utm_zone"], min_value=1, max_value=60, step=1)
            with col_z2:
                st.session_state["utm_hemi"] = st.selectbox("Hemisferio", options=["N", "S"], index=(1 if st.session_state["utm_hemi"] == "S" else 0))
            st.session_state["input_epsg"] = (32600 if st.session_state["utm_hemi"] == "N" else 32700) + int(st.session_state["utm_zone"])
            st.text(f"EPSG de entrada: {st.session_state['input_epsg']}")
        else:
            st.session_state["input_epsg"] = st.number_input("EPSG de entrada", value=int(st.session_state["input_epsg"]), min_value=2000, max_value=99999, step=1)

        st.session_state["output_epsg"] = st.number_input("EPSG de salida", value=int(st.session_state["output_epsg"]), min_value=2000, max_value=99999, step=1)
        st.session_state["group_by"] = st.selectbox("Agrupar capas por", options=["type", "layer"], index=(0 if st.session_state["group_by"] == "type" else 1))

        st.markdown("**Tipo de Mapa HTML**")
        map_type_selection = st.radio(
            "Seleccione el tipo de mapa:",
            options=["normal", "mapbox"],
            format_func=lambda x: "Mapa Normal (Leaflet)" if x == "normal" else "Mapa Mapbox",
            index=0 if st.session_state["html_map_type"] == "normal" else 1,
            horizontal=True,
        )
        st.session_state["html_map_type"] = map_type_selection
        if map_type_selection == "mapbox":
            st.info("💡 Mapa Mapbox: requiere API Key (se pedirá al abrir el HTML).")
        else:
            st.info("🗺️ Mapa Normal: usa Leaflet, sin configuración adicional.")

    cfg: Dict[str, Any] = {
        "utm_zone": st.session_state["utm_zone"],
        "utm_hemi": st.session_state["utm_hemi"],
        "input_epsg": int(st.session_state["input_epsg"]),
        "output_epsg": int(st.session_state["output_epsg"]),
        "group_by": str(st.session_state["group_by"]),
        "html_map_type": str(st.session_state["html_map_type"]),
        "output_dir": str(st.session_state["output_dir"]),
        "output_folder": str(st.session_state["output_folder"]),
    }
    return cfg


__all__ = ["setup_layout"]
