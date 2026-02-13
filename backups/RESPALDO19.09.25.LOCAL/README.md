# App Topografía

Aplicación profesional para la conversión y visualización de archivos topográficos (DXF, GPX, KML/KMZ, GeoJSON, Shapefile) usando Streamlit.

## Características principales
- Conversión de archivos DXF, GPX, KML/KMZ, GeoJSON y Shapefile.
- Exportación de resultados en múltiples formatos.
- Interfaz web moderna y fácil de usar (Streamlit).
- Selección de carpeta de salida y nombre de proyecto.
- Descarga de resultados agrupados por tipo/capa.
- Autenticación de usuario (modo completo y simplificado).

## Requisitos
- Python 3.10+
- Streamlit
- ezdxf
- simplekml
- shapefile
- pyproj
- folium
- streamlit-folium

Instala las dependencias con:
```bash
pip install -r requirements.txt
```

## Uso
1. Clona el repositorio:
   ```bash
   git clone https://github.com/tu-usuario/App_Topografia.git
   cd App_Topografia
   ```
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Ejecuta la aplicación:
   ```bash
   streamlit run app.py
   ```
4. Accede a la interfaz web en tu navegador.

## Estructura del proyecto
- `app.py`: Script principal de la aplicación Streamlit.
- `requirements.txt`: Dependencias del proyecto.
- `auth_system.py`, `auth_simple.py`: Módulos de autenticación.
- `secrets_local.toml`, `secrets_template.toml`: Configuración de claves y secretos.
- `flujo_acceso.html`, `index.html`: Plantillas HTML.
- Archivos de documentación y guía de usuario.

## Contribuir
¡Las contribuciones son bienvenidas! Abre un issue o haz un pull request para sugerir mejoras o reportar errores.

## Licencia
Este proyecto está bajo la licencia MIT.
# Actualización forzada
