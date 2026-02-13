# Manual de Usuario - Conversor Universal Profesional

## 📋 Índice
1. [Introducción](#introducción)
2. [Configuración inicial](#configuración-inicial)
3. [Conversor DXF](#conversor-dxf)
4. [Conversor GPX](#conversor-gpx)
5. [Conversor KML/KMZ](#conversor-kmlkmz)
6. [Conversor Topográfico](#conversor-topográfico)
7. [Resolución de problemas](#resolución-de-problemas)

---

## 🎯 Introducción

El Conversor Universal Profesional es una aplicación web que permite convertir archivos geoespaciales entre múltiples formatos con visualización interactiva. Soporta conversión entre DXF, GPX, KML/KMZ y generación de datos topográficos.

### ✨ Formatos de salida disponibles:
- **JSON/GeoJSON**: Para análisis y desarrollo
- **KML/KMZ**: Para Google Earth y sistemas GIS
- **Shapefiles**: Para AutoCAD Civil 3D y ArcGIS
- **DXF**: Para AutoCAD y CAD en general
- **HTML**: Visores interactivos (Leaflet/Mapbox)

---

## ⚙️ Configuración inicial

Antes de usar cualquier conversor, configure los parámetros globales en el panel lateral:

### 🌍 **Zona UTM WGS84**
1. **Hemisferio**: Norte (N) o Sur (S)
2. **Zona**: Número de zona UTM (1-60)
   - **Ecuador**: Zona 17S (EPSG 32717) - *por defecto*
   - **Perú**: Zona 18S (EPSG 32718)
   - **Colombia**: Zona 18N (EPSG 32618)

### 📐 **EPSG Personalizado**
- **Entrada**: EPSG del archivo origen (automático para KML/GPX)
- **Salida**: EPSG para shapefiles (por defecto 4326)

### 🗂️ **Agrupación de capas**
- **Por Tipo**: Agrupa geometrías similares (Puntos, Líneas, etc.)
- **Por Capa**: Mantiene estructura original del archivo

### 🗺️ **Tipo de mapa HTML**
- **Normal**: Visor Leaflet ligero y compatible
- **Mapbox**: Visor 3D avanzado con terreno y múltiples estilos

### 📂 **Carpeta de salida**
1. Clic en "📁 Seleccionar carpeta"
2. Elegir ubicación en el explorador
3. Definir nombre de carpeta de proyecto

---

## 🏗️ Conversor DXF

### 📤 **Paso 1: Subir archivo**
1. Navegar a pestaña **"📐 DXF Profesional"**
2. Arrastrar archivo DXF o hacer clic para seleccionar
3. Verificar que el archivo se cargue correctamente

### ⚙️ **Paso 2: Configurar parámetros**
- **Zona UTM**: Configurar según ubicación geográfica del proyecto
- **Agrupación**: 
  - *Por Tipo*: Ideal para análisis de elementos
  - *Por Capa*: Mantiene organización del DXF original

### 🔄 **Paso 3: Convertir**
1. Clic en **"Convertir"**
2. Esperar procesamiento (aparece spinner)
3. Revisar mapa de vista previa

### 📋 **Elementos soportados:**
- **📍 Puntos**: Entidades POINT
- **📏 Líneas**: Entidades LINE
- **🔗 Polilíneas**: Entidades POLYLINE/LWPOLYLINE
- **⭕ Círculos**: Entidades CIRCLE (convertidos a polígonos)
- **📝 Textos**: Entidades TEXT/MTEXT con atributos
- **🧩 Bloques**: Referencias de bloque con coordenadas

### 💾 **Paso 4: Descargar**
1. Clic en **"Descargar Resultados"**
2. Los archivos se guardan en la carpeta configurada

---

## 🚶 Conversor GPX

### 📤 **Paso 1: Subir archivo**
1. Navegar a pestaña **"🥾 GPX Profesional"**
2. Subir archivo GPX desde dispositivo GPS o aplicación

### 🔄 **Paso 2: Convertir**
1. Clic en **"Convertir GPX"**
2. El sistema procesa automáticamente:
   - **Puntos de paso**: Como puntos
   - **Pistas**: Como líneas rojas (rutas grabadas)
   - **Rutas**: Como líneas azules (rutas planificadas)

### 📋 **Elementos procesados:**
- **📍 Puntos GPX**: Puntos de paso con nombres y descripciones
- **🛤️ Pistas**: Rutas grabadas durante actividad
- **🗺️ Rutas**: Rutas planificadas o calculadas

### 🎨 **Visualización en mapa:**
- **Pistas**: Líneas rojas sólidas
- **Rutas**: Líneas azules punteadas
- **Puntos de paso**: Marcadores verdes

### 💾 **Paso 3: Descargar**
1. Revisar vista previa del mapa
2. Clic en **"Descargar Resultados GPX"**

---

## 🌍 Conversor KML/KMZ

### 📤 **Paso 1: Subir archivo**
1. Navegar a pestaña **"🌍 KML/KMZ Profesional"**
2. Subir archivo KML o KMZ (comprimido)

### 🔧 **Procesamiento automático:**
- **Detección de formato**: KMZ se descomprime automáticamente
- **Parsing inteligente**: Usa `fastkml` con fallback XML
- **Limpieza de datos**: Elimina coordenadas Z innecesarias
- **Validación**: Verifica rangos de coordenadas

### 📋 **Geometrías soportadas:**
- **Puntos**: Point
- **Líneas**: LineString
- **Polígonos**: Polygon con límites exteriores
- **Colecciones**: MultiGeometry expandido

### 🔄 **Paso 2: Convertir y descargar**
1. El archivo se procesa automáticamente al subir
2. Revisar elementos en el mapa
3. Clic en **"Descargar Resultados KML/KMZ"**

---

## 📊 Conversor Topográfico

### 📋 **Paso 1: Configurar proyecto**
1. Navegar a pestaña **"📊 Topográfico"**
2. **Nombre del proyecto**: Definir identificador
3. **Modo topográfico**:
   - *Solo puntos*: Genera únicamente puntos con cotas
   - *Puntos y polilíneas*: Incluye áreas calculadas

### 📈 **Paso 2: Ingresar datos**

#### Para puntos topográficos:
```
No.    | X (UTM)  | Y (UTM)   | Cota | Descripción
P001   | 500000   | 9800000   | 2450 | Esquina NE
P002   | 500100   | 9800000   | 2445 | Esquina SE
```

#### Para polígonos (modo polilíneas):
```
No.    | X (UTM)  | Y (UTM)   | Cota | Descripción
A1-P1  | 500000   | 9800000   | 2450 | Inicio área 1
A1-P2  | 500100   | 9800000   | 2445 | Punto 2 área 1
A1-P3  | 500100   | 9800100   | 2440 | Punto 3 área 1
---    | ---      | ---       | ---  | ---
A2-P1  | 500200   | 9800000   | 2460 | Inicio área 2
```

### 🔄 **Paso 3: Generar**
1. Clic en **"Generar archivos topográficos"**
2. El sistema calcula automáticamente:
   - **Transformación de coordenadas** UTM → WGS84
   - **Áreas de polígonos** en m²
   - **Perímetros** en metros lineales

### 📁 **Salida especializada:**
- **DXF topográfico**: Puntos con bloques de texto
- **Shapefiles**: Separados por geometría
- **KML estructurado**: Carpetas organizadas
- **Visor HTML**: Con información de cotas

---

## 🔍 Resolución de problemas

### ❌ **Shapefiles desplazados**

**Síntomas**: Los archivos SHP aparecen en ubicación incorrecta

**Soluciones**:
1. ✅ Verificar zona UTM correcta:
   - **Norte**: EPSG 326XX (ej: 32618)
   - **Sur**: EPSG 327XX (ej: 32717)
2. ✅ Confirmar EPSG de entrada para archivos KML/GPX (debe ser 4326)
3. ✅ Revisar mensajes en consola del navegador

### ❌ **Archivo KML/KMZ vacío**

**Síntomas**: No aparecen elementos en el mapa

**Soluciones**:
1. ✅ Verificar que contenga geometrías (no solo overlays)
2. ✅ Probar con KML sin comprimir
3. ✅ Revisar si tiene NetworkLinks externos

### ❌ **Visor HTML en blanco**

**Síntomas**: index.html no carga el mapa

**Soluciones**:
1. ✅ Abrir con servidor local:
   ```bash
   python -m http.server 8000
   ```
2. ✅ Acceder a `http://localhost:8000/index.html`
3. ✅ Verificar que el navegador permita archivos locales

### ❌ **Error de importación**

**Síntomas**: "cannot access local variable"

**Soluciones**:
1. ✅ Reiniciar la aplicación Streamlit
2. ✅ Verificar instalación de dependencias:
   ```bash
   pip install -r requirements.txt
   ```

### ❌ **Mapbox no funciona**

**Síntomas**: Mapa Mapbox no carga

**Soluciones**:
1. ✅ Obtener API key gratuita en [mapbox.com](https://mapbox.com)
2. ✅ Introducir API key en el modal del visor
3. ✅ La API key se guarda automáticamente en navegador

---

## 📞 Soporte técnico

**Desarrollador**: Patricio Sarmiento Reinoso  
**WhatsApp**: +593995959047  
**Email**: Disponible por WhatsApp  

### 🕐 Horarios de atención:
- **Lunes a Viernes**: 8:00 AM - 6:00 PM (GMT-5)
- **Sábados**: 9:00 AM - 2:00 PM (GMT-5)

---

*Manual actualizado: Septiembre 2025 - Versión 3.0 Professional*
