# 📘 Resumen Diario de Desarrollo

📅 **Fecha**: 2026-02-13
📦 **Versión actual**: v3.5.9

---

## 🎯 Objetivos de la sesión
1. Corregir problemas con la pestaña DXF (nombre de carpeta, shapefiles, GeoJSON)
2. Implementar soporte para Mapbox en el sidebar
3. Reorganizar el layout de todas las pestañas (35-35-30)
4. Implementar actualización de mapas en tiempo real

---

## ✅ Cambios realizados

### 1. Pestaña DXF Profesional
- **Corregido nombre de carpeta**: Ahora usa el valor del input correctamente
- **Shapefiles**: Corregida generación usando `shp_zip_bytes`
- **GeoJSON**: Corregida decodificación UTF-8
- **Layout**: Reorganizado en 3 columnas (35-35-30)
- **Mapbox**: Agregado soporte para generar mapas Mapbox
- **Guardado local**: Guarda archivos sueltos sin comprimir

### 2. Sidebar
- **Mapbox**: Corregido el cambio de tipo de mapa que causaba pérdida de archivo cargado
- **Sin rerun**: Eliminado `st.rerun()` que causaba problemas
- **Persistencia**: Archivo DXF ahora se guarda en session_state

### 3. Mapa Mapbox
- **Líneas de GPX/KML**: Corregido filtro para mostrar líneas (agregado 'track', 'LineString')
- **Agrupación**: Corregida lógica para capas sin propiedad 'layer'
- **Filtros**: Mejorado para verificar tanto 'layer' como 'type'
- **Textos**: Agregado checkbox para mostrar/ocultar textos

### 4. GPX Profesional
- **Procesamiento inmediato**: Procesa el archivo al cargarlo
- **Colores en tiempo real**: Actualiza el mapa al cambiar colores
- **Layout**: Reorganizado en 3 columnas (35-35-30)
- **Mapbox**: Genera mapa Mapbox con colores seleccionados

### 5. KML/KMZ Profesional
- **Procesamiento inmediato**: Procesa el archivo al cargarlo
- **Colores en tiempo real**: Actualiza el mapa al cambiar colores
- **Layout**: Reorganizado en 3 columnas (35-35-30)
- **Mapbox**: Genera mapa Mapbox con colores seleccionados

### 6. Topográfico Profesional
- **Layout**: Reorganizado en 3 columnas (35-35-30)
- **Error corregido**: Corregido error de `session_state` con `text_area`

### 7. Mapa del Proyecto
- **Actualización dinámica**: Lee colores de session_state
- **Mapbox**: Aplica colores de líneas y puntos
- **Leaflet**: Aplica colores seleccionados
- **Cache**: Limpia HTML cacheado al cambiar tipo de mapa

### 8. Universal Exporter
- **Mapbox**: Ahora acepta parámetro `map_type` para generar HTML Mapbox
- **Colores**: Pasa colores seleccionados al generar HTML

---

## 🐛 Problemas corregidos
1. Error "charmap codec" al guardar HTML con emojis
2. Pestañas GPX/KML no mostraban líneas en Mapbox
3. HTML descargado siempre era Leaflet aunque seleccionara Mapbox
4. Cambios de color no se aplicaban en tiempo real

---

## 📝 Historial de versiones del día

### v3.5.9 — 13/Feb/2026
- Actualización de colores en tiempo real para GPX/KML
- Mapa del proyecto usa colores dinámicos

### v3.5.8 — 13/Feb/2026
- Colores aplicados a Mapbox

### v3.5.7 — 13/Feb/2026
- Corrección de filtros para mostrar líneas de GPX/KML en Mapbox

### v3.5.6 — 13/Feb/2026
- Cache de HTML limpiado al cambiar tipo de mapa

### v3.5.5 — 13/Feb/2026
- Regeneración de HTML al cambiar tipo de mapa

### v3.5.4 — 13/Feb/2026
- Mapa del proyecto se actualiza desde cualquier pestaña

### v3.5.3 — 13/Feb/2026
- Layout reorganizado en GPX y KML

### v3.5.2 — 13/Feb/2026
- Error corregido en topo_tab con session_state

### v3.5.1 — 13/Feb/2026
- Layout reorganizado en Topográfico

### v3.5.0 — 13/Feb/2026
- Layout reorganizado en 3 columnas para DXF

---

## 🔜 Siguientes pasos (para mañana)
1. ✅ Verificar que los colores se apliquen correctamente en tiempo real
2. ⏳ Probar la generación de paquetes ZIP con Mapbox
3. ⏳ Verificar funcionamiento en todas las pestañas
4. ⏳ Testing general de la aplicación

---

## 📁 Archivos modificados
- `src/ui/tabs/dxf_tab.py`
- `src/ui/tabs/gpx_tab.py`
- `src/ui/tabs/kml_tab.py`
- `src/ui/tabs/topo_tab.py`
- `src/ui/tabs/map_tab.py`
- `src/ui/sidebar.py`
- `src/core/config/settings.py`
- `src/core/converters/universal_exporter.py`
- `src/generators/map_generators.py`
