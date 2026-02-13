import streamlit as st

def render_manual_tab():
    st.markdown("""
    <div style="text-align: center; padding: 20px;">
        <h1 style="color: #1E88E5; margin-bottom: 10px;">📚 Manual de Usuario</h1>
        <p style="font-size: 18px; color: #666; margin-bottom: 30px;">
            Guía completa para usar el Conversor Universal Profesional
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    manual_tabs = st.tabs([
        "🎯 Introducción", 
        "⚙️ Configuración", 
        "🏗️ DXF", 
        "🚶 GPX", 
        "🌍 KML/KMZ", 
        "📊 Topográfico",
        "🛠️ Problemas"
    ])
    
    with manual_tabs[0]:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("""
            ### 🚀 Conversor Universal Profesional
            Esta aplicación permite convertir archivos geoespaciales entre múltiples formatos.
            **✨ Formatos soportados:**
            - 📐 **DXF**, 🥾 **GPX**, 🌍 **KML/KMZ**, 📊 **Topográfico**
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            ### 🔄 Flujo básico
            1. 📤 Subir archivo
            2. ⚙️ Configurar parámetros
            3. 🔄 Convertir
            4. 💾 Descargar
            """, unsafe_allow_html=True)

    with manual_tabs[1]:
        st.markdown("## ⚙️ Configuración inicial")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            st.markdown("### 🌍 Zona UTM WGS84\n- 🇪🇨 Ecuador: 17S\n- 🇵🇪 Perú: 18S")
        with col2:
            st.markdown("### 🗂️ Agrupación\n- Por Tipo\n- Por Capa")
        with col3:
            st.markdown("### 🗺️ Tipo de mapa\n- Leaflet\n- Mapbox 3D")

    with manual_tabs[2]:
        st.markdown("## 🏗️ Conversor DXF")
        st.markdown("- Soportado: POINT, LINE, POLYLINE, CIRCLE, TEXT, BLOCKS")

    with manual_tabs[3]:
        st.markdown("## 🚶 Conversor GPX")
        st.markdown("- Soportado: Waypoints, Tracks, Routes")

    with manual_tabs[4]:
        st.markdown("## 🌍 Conversor KML/KMZ")
        st.markdown("- Robusto para datos de levantamiento")

    with manual_tabs[5]:
        st.markdown("## 📊 Conversor Topográfico")
        st.markdown("- Formato: No. | X | Y | Cota | Desc")

    with manual_tabs[6]:
        st.markdown("## 🛠️ Resolución de problemas")
        st.markdown("- Soporte: Patricio Sarmiento (+593995959047)")
