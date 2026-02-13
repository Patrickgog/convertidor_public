import streamlit as st
import tempfile
import io
import os
import zipfile
import json
import shutil
from pathlib import Path
from src.core.converters.dxf_converter import convert_dxf
from src.generators.map_generators import create_mapbox_html, create_leaflet_grouped_html, create_normal_html
from src.core.geometry.coordinate_utils import compute_bounds_from_geojson, strip_z_from_geojson

def render_dxf_tab():
    IS_CLOUD = os.path.exists("/mount")
    
    # Inicializar todas las variables de session_state
    for key in ["dxf_uploaded_bytes", "dxf_uploaded_name", "dxf_last_uploaded", 
                "outputs", "base_name", "output_folder", "dxf_output_folder", "output_dir"]:
        if key not in st.session_state:
            st.session_state[key] = None
    
    # Crear las 3 columnas: 35-35-30
    col_entrada, col_config, col_resultados = st.columns([35, 35, 30])
    
    # ==========================================
    # COLUMNA 1: ENTRADA (35%)
    # ==========================================
    with col_entrada:
        st.markdown("### Entrada")
        
        uploaded = st.file_uploader("Subir archivo DXF", type=["dxf"], key="dxf_uploader")
        
        # GUARDAR ARCHIVO EN SESSION_STATE
        if uploaded is not None:
            file_details = f"{uploaded.name}-{uploaded.size}"
            if st.session_state["dxf_last_uploaded"] != file_details:
                st.session_state["dxf_last_uploaded"] = file_details
                st.session_state["dxf_uploaded_bytes"] = uploaded.getvalue()
                st.session_state["dxf_uploaded_name"] = uploaded.name
                st.session_state["base_name"] = Path(uploaded.name).stem or "Proyecto1"
                st.session_state["outputs"] = None
                
                # Calcular nombre de carpeta sugerido
                base_dir = Path(st.session_state.get("output_dir") or str(Path.home() / "Downloads"))
                suggested = st.session_state["base_name"]
                candidate = suggested
                idx = 0
                while (base_dir / candidate).exists():
                    idx += 1
                    candidate = f"{suggested}_{idx}"
                
                st.session_state["output_folder"] = candidate
                st.session_state["dxf_output_folder"] = candidate
        
        # Determinar si tenemos archivo
        has_uploaded = uploaded is not None
        has_session = st.session_state["dxf_uploaded_bytes"] is not None
        has_file = has_uploaded or has_session
        
        # Mostrar info del archivo cargado
        if has_file:
            archivo_nombre = uploaded.name if uploaded else st.session_state.get("dxf_uploaded_name", "Desconocido")
            st.success(f"Archivo cargado: **{archivo_nombre}**")
    
    # ==========================================
    # COLUMNA 2: CONFIGURACIÓN (35%)
    # ==========================================
    with col_config:
        st.markdown("### Configuración de Salida")
        
        if has_file:
            # Valores por defecto
            default_output_dir = st.session_state.get("output_dir") or str(Path.home() / "Downloads")
            default_folder = st.session_state.get("dxf_output_folder") or st.session_state.get("output_folder") or st.session_state.get("base_name") or "Proyecto1"
            
            output_dir = st.text_input(
                "Ruta de salida",
                value=default_output_dir,
                key="dxf_output_dir_input"
            )
            st.session_state["output_dir"] = output_dir
            
            folder_name = st.text_input(
                "Nombre de carpeta", 
                value=default_folder,
                key="dxf_output_folder_input"
            )
            st.session_state["output_folder"] = folder_name
            st.session_state["dxf_output_folder"] = folder_name
            
            # Botón Convertir
            st.markdown("---")
            convert_clicked = st.button(
                "Convertir", 
                disabled=not has_file, 
                key="dxf_convert_btn",
                type="primary",
                use_container_width=True
            )
            
            # PROCESAR CONVERSIÓN
            if convert_clicked and has_file:
                with st.spinner("Convirtiendo..."):
                    with tempfile.TemporaryDirectory() as tmp:
                        # Decidir qué archivo usar
                        if uploaded is not None:
                            dxf_path = Path(tmp) / uploaded.name
                            data_bytes = uploaded.getvalue()
                            st.session_state["dxf_uploaded_bytes"] = data_bytes
                            st.session_state["dxf_uploaded_name"] = uploaded.name
                        else:
                            dxf_path = Path(tmp) / st.session_state.get("dxf_uploaded_name", "archivo.dxf")
                            data_bytes = st.session_state["dxf_uploaded_bytes"]
                        
                        dxf_path.write_bytes(data_bytes)
                        
                        try:
                            outputs = convert_dxf(
                                dxf_path,
                                int(st.session_state.get("input_epsg", 32717)),
                                int(st.session_state.get("output_epsg", 4326)),
                                shapes_group_by=st.session_state.get("group_by", "type")
                            )
                            st.session_state["outputs"] = outputs
                            
                            # Actualizar mapa del proyecto
                            if outputs.get("geojson"):
                                st.session_state["project_geojson"] = outputs["geojson"]
                                st.session_state["project_title"] = f"{st.session_state.get('base_name', 'Proyecto')} - DXF"
                                st.session_state["project_folder_name"] = st.session_state.get("output_folder") or st.session_state.get("base_name") or "Proyecto"
                                # Limpiar HTML previo para regenerar con el tipo de mapa actual
                                if "project_html" in st.session_state:
                                    del st.session_state["project_html"]
                                if "project_html_map_type" in st.session_state:
                                    del st.session_state["project_html_map_type"]
                            
                            st.success("Conversión exitosa")
                        except Exception as e:
                            st.error(f"Error en conversión: {e}")
                            import traceback
                            st.code(traceback.format_exc())
        else:
            st.info("Carga un archivo DXF para configurar la salida")
    
    # ==========================================
    # COLUMNA 3: RESULTADOS (30%)
    # ==========================================
    with col_resultados:
        st.markdown("### Resultados")
        
        outputs = st.session_state.get("outputs")
        if outputs:
            folder_name = st.session_state.get("dxf_output_folder") or st.session_state.get("output_folder") or st.session_state.get("base_name") or "Proyecto"
            base_name = folder_name
            
            # Crear ZIP
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                if outputs.get("kmz_bytes"): 
                    zf.writestr(f"{base_name}/{base_name}.kmz", outputs["kmz_bytes"])
                if outputs.get("geojson_bytes"): 
                    zf.writestr(f"{base_name}/{base_name}.geojson", outputs["geojson_bytes"].decode('utf-8'))
                
                if outputs.get("shp_zip_bytes"):
                    import io as io_module
                    shp_zip_buf = io_module.BytesIO(outputs["shp_zip_bytes"])
                    with zipfile.ZipFile(shp_zip_buf, "r") as shp_zf:
                        for item in shp_zf.namelist():
                            zf.writestr(f"{base_name}/shapes/{item}", shp_zf.read(item))
                
                geojson_data = outputs.get("geojson")
                if geojson_data:
                    try:
                        map_type = st.session_state.get("html_map_type", "normal")
                        
                        if map_type == "mapbox":
                            html_content = create_mapbox_html(
                                geojson_data, 
                                title=f"Mapa - {base_name}", 
                                folder_name=base_name,
                                grouping_mode=st.session_state.get("group_by", "type")
                            )
                        else:
                            html_content = create_leaflet_grouped_html(
                                geojson_data, 
                                title=f"Mapa - {base_name}",
                                grouping_mode=st.session_state.get("group_by", "type")
                            )
                        
                        zf.writestr(f"{base_name}/Visualizador_Mapa.html", html_content)
                    except Exception as map_err:
                        st.warning(f"Error generando HTML: {map_err}")
            
            # Botón de descarga
            st.download_button(
                "Descargar ZIP", 
                data=zip_buf.getvalue(), 
                file_name=f"{base_name}_salidas.zip", 
                mime="application/zip",
                use_container_width=True
            )
            
            # Guardar archivos sueltos localmente
            output_dir = st.session_state.get("output_dir")
            output_folder = st.session_state.get("dxf_output_folder") or st.session_state.get("output_folder") or base_name
            
            if output_dir and os.path.isdir(output_dir):
                try:
                    full_output_path = Path(output_dir) / output_folder
                    shapes_path = full_output_path / "shapes"
                    full_output_path.mkdir(parents=True, exist_ok=True)
                    shapes_path.mkdir(parents=True, exist_ok=True)
                    
                    files_saved = []
                    
                    if outputs.get("kmz_bytes"):
                        (full_output_path / f"{base_name}.kmz").write_bytes(outputs["kmz_bytes"])
                        files_saved.append(f"{base_name}.kmz")
                    
                    if outputs.get("geojson_bytes"):
                        (full_output_path / f"{base_name}.geojson").write_text(outputs["geojson_bytes"].decode('utf-8'))
                        files_saved.append(f"{base_name}.geojson")
                    
                    if outputs.get("shp_zip_bytes"):
                        import io as io_module
                        shp_zip_buf = io_module.BytesIO(outputs["shp_zip_bytes"])
                        with zipfile.ZipFile(shp_zip_buf, "r") as shp_zf:
                            for item in shp_zf.namelist():
                                (shapes_path / item).write_bytes(shp_zf.read(item))
                        files_saved.append(f"shapes/ (varios archivos)")
                    
                    if outputs.get("geojson"):
                        map_type = st.session_state.get("html_map_type", "normal")
                        if map_type == "mapbox":
                            html_content = create_mapbox_html(outputs["geojson"], title=f"Mapa - {base_name}", folder_name=base_name, grouping_mode=st.session_state.get("group_by", "type"))
                        else:
                            html_content = create_leaflet_grouped_html(outputs["geojson"], title=f"Mapa - {base_name}", grouping_mode=st.session_state.get("group_by", "type"))
                        (full_output_path / "Visualizador_Mapa.html").write_text(html_content, encoding='utf-8')
                        files_saved.append("Visualizador_Mapa.html")
                    
                    st.success(f"Guardado en: {full_output_path}")
                    with st.expander("Ver archivos"):
                        for f in files_saved:
                            st.write(f"- {f}")
                    
                    st.info("Mapa actualizado en 'Mapa del proyecto'")
                
                except Exception as e:
                    st.warning(f"No se pudo guardar localmente: {e}")
        else:
            st.info("Los resultados aparecerán aquí después de convertir")
