# 📘 Guía para el Usuario - Conversor Universal Profesional v3.4.4

## 🎯 Bienvenido

Esta guía te ayudará a utilizar todas las funcionalidades del **Conversor Universal Profesional**, una aplicación para convertir y visualizar archivos geoespaciales en múltiples formatos.

---

## 📋 Índice de Pestañas

1. [📐 DXF Profesional](#dxf-profesional)
2. [🥾 GPX Profesional](#gpx-profesional)
3. [🌍 KML/KMZ Profesional](#kmlkmz-profesional)
4. [📊 Topográfico Profesional](#topográfico-profesional)
5. [🗺️ Mapa del proyecto](#mapa-del-proyecto)
6. [📚 Manual de Usuario](#manual-de-usuario)

---

## 📐 DXF Profesional

### Descripción
Convierte archivos DXF (Drawing Exchange Format) de AutoCAD a múltiples formatos geoespaciales.

### ¿Qué formatos de salida genera?
- **KMZ** - Para Google Earth
- **GeoJSON** - Formato estándar web
- **Shapefile** - Para GIS profesional (carpeta `shapes/`)
- **HTML** - Visualizador de mapa interactivo

### Paso a paso

#### 1. **Subir archivo DXF**
- Haz clic en "Subir archivo DXF"
- Selecciona un archivo con extensión `.dxf`
- El sistema detectará automáticamente el nombre del proyecto

#### 2. **Configurar salida**
- **Ruta de salida**: Carpeta donde se guardarán los resultados
- **Nombre de carpeta**: Nombre de la subcarpeta del proyecto (se autocompleta)

#### 3. **Configurar en el Sidebar (panel lateral)**
Antes de convertir, configura:
- **Zona UTM de entrada**: Código EPSG de origen (ej: 32717 para Ecuador)
- **Zona UTM de salida**: Código EPSG de destino (ej: 4326 para WGS84)
- **Agrupar por**: 
  - `Tipo` - Agrupa puntos, líneas y polígonos
  - `Capa` - Agrupa por capas del DXF

#### 4. **Convertir**
- Haz clic en el botón **"Convertir"**
- Espera el mensaje "✅ Conversión exitosa"

#### 5. **Descargar resultados**
- **Botón "Descargar ZIP"**: Descarga un archivo comprimido con todos los formatos
- Los archivos también se guardan automáticamente en la ruta configurada

#### 6. **Contenido del ZIP**
```
NombreProyecto/
├── NombreProyecto.kmz          → Google Earth
├── NombreProyecto.geojson      → Datos en formato GeoJSON
├── shapes/                     → Archivos Shapefile
│   ├── NombreProyecto.shp
│   ├── NombreProyecto.shx
│   ├── NombreProyecto.dbf
│   └── NombreProyecto.prj
└── Visualizador_Mapa.html      → Mapa interactivo
```

### Elementos soportados
- POINT (Puntos)
- LINE (Líneas)
- POLYLINE/LWPOLYLINE (Polilíneas)
- CIRCLE (Círculos)
- TEXT/MTEXT (Textos)
- BLOCKS (Bloques)

---

## 🥾 GPX Profesional

### Descripción
Convierte archivos GPX (GPS Exchange Format) utilizados en dispositivos GPS y aplicaciones de navegación.

### ¿Qué formatos de salida genera?
- **KMZ** - Google Earth
- **GeoJSON** - Estándar web
- **Shapefile** - GIS profesional
- **DXF** - AutoCAD
- **KML** - Google Earth (archivo individual)

### Paso a paso

#### 1. **Subir archivo GPX**
- Haz clic en "Subir GPX"
- Selecciona un archivo `.gpx`
- Verás confirmación: "✅ Cargado: nombre.gpx"

#### 2. **Personalizar estilos** (Columna central)
- **Color Puntos**: Color para waypoints (predeterminado: rojo #e31a1c)
- **Color Líneas**: Color para tracks/rutas (predeterminado: azul #1f78b4)
- **Ancho Línea**: Grosor de las líneas en píxeles (0.5 - 10.0)

#### 3. **Configurar salida** (Columna derecha)
- **Nombre de carpeta**: Nombre del proyecto (ej: "Levantamiento_GPX")
- **Directorio salida**: Ruta donde se guardará el archivo

#### 4. **Generar paquete**
- Haz clic en **"🚀 Generar Paquete"**
- Espera el mensaje "✅ ¡Paquete generado!"

#### 5. **Descargar**
- Usa el botón **"📦 Descargar ZIP PROFESIONAL"**
- El archivo también se guarda automáticamente en el directorio configurado

### Elementos soportados
- **Waypoints** (Puntos de referencia)
- **Tracks** (Rastros/Tracks GPS)
- **Routes** (Rutas)

### Tip
Los archivos GPX de dispositivos Garmin, teléfonos móviles y aplicaciones como Strava, Wikiloc son totalmente compatibles.

---

## 🌍 KML/KMZ Profesional

### Descripción
Convierte archivos KML (Keyhole Markup Language) y KMZ (KML comprimido) de Google Earth a otros formatos.

### ¿Qué formatos de salida genera?
- **GeoJSON** - Estándar web
- **Shapefile** - GIS profesional
- **DXF** - AutoCAD
- **KMZ** - Google Earth optimizado

### Paso a paso

#### 1. **Subir archivo**
- Haz clic en "Subir KML/KMZ"
- Selecciona archivos `.kml` o `.kmz`
- El sistema detecta automáticamente el formato

#### 2. **Personalizar estilos** (Columna central)
- **Color Puntos**: Color para marcadores/placemarks
- **Color Líneas**: Color para líneas y polígonos
- **Ancho Línea**: Grosor de las líneas (0.5 - 10.0)

#### 3. **Configurar salida** (Columna derecha)
- **Nombre de carpeta**: Nombre del proyecto (ej: "Levantamiento_KML")
- **Directorio salida**: Ruta de guardado

#### 4. **Generar paquete**
- Haz clic en **"🚀 Generar Paquete"**
- Espera la confirmación

#### 5. **Descargar**
- Usa el botón **"📦 Descargar ZIP PROFESIONAL"**

### Elementos soportados
- Placemarks (Marcadores)
- LineStrings (Líneas)
- Polygons (Polígonos)
- MultiGeometry (Geometrías múltiples)
- Estilos básicos

### Nota especial
Si subes un archivo `.kmz` que realmente es un KML (texto plano), el sistema lo detectará y procesará correctamente.

---

## 📊 Topográfico Profesional

### Descripción
Herramienta especializada para procesar datos de levantamientos topográficos y generar archivos CAD y geoespaciales.

### ¿Qué formatos de salida genera?
- **DXF** - AutoCAD con puntos, líneas y textos configurables
- **CSV** - Datos tabulares
- **GeoJSON** - Para visualización web
- **KMZ** - Google Earth
- **Mapa de calor (GeoTIFF)** - Análisis de elevaciones (opcional)

### Paso a paso

#### 1. **Ingresar datos**
Puedes ingresar datos de dos formas:

**Opción A: Pegar desde Excel/CSV**
- Copia tus datos desde Excel, Google Sheets o archivo CSV
- El formato debe ser: `No. | X | Y | Cota | Descripción`
- Pega en el área de texto "Pegar datos"
- Haz clic en **"Insertar datos"**

**Opción B: Usar datos de ejemplo**
- Haz clic en **"Datos de ejemplo"** para cargar datos de prueba

#### 2. **Seleccionar modo de trabajo**
- **Solo puntos**: Genera solo los puntos topográficos
- **Puntos y polilíneas**: Conecta los puntos con líneas según su orden

#### 3. **Configurar dimensiones**
- **Modo 2D**: Ignora la cota (Z=0)
- **Modo 3D**: Incluye la cota en la coordenada Z

#### 4. **Configurar estilos DXF** (Panel derecho)

**🔴 CONFIGURACIÓN DE PUNTOS**
- **Tipo de punto (PDMODE)**: Estilo del marcador
  - Opciones: Dot, Plus, Cross, Circle, Square, combinaciones
  - Recomendado: "33 - Circle+Plus"
- **Altura de punto**: Tamaño del punto (0.01 - 10.0)
- **Color punto**: azul, rojo, amarillo, verde, etc.
- **Layer puntos**: Nombre de la capa (ej: "PUNTOS")

**🔵 CONFIGURACIÓN DE LÍNEAS/POLÍGONOS**
- **Color línea**: rojo, azul, amarillo, verde, etc.
- **Ancho línea**: Grosor en milímetros (0.01 - 10.0)
- **Tipo línea**: CONTINUOUS, DASHED, DASHDOT, CENTER, HIDDEN
- **Layer polilíneas**: Nombre de la capa (ej: "POLILINEAS")

**🟢 CONFIGURACIÓN DE TEXTOS**
- **Altura texto**: Tamaño de la etiqueta (0.01 - 10.0)
- **Color texto**: blanco, rojo, azul, etc.
- **Desplaz X/Y**: Offset del texto respecto al punto
- **Layer textos**: Nombre de la capa (ej: "TEXTOS")

#### 5. **Configurar mapa de calor** (Opcional)
- Activa **"Generar mapa de calor (GeoTIFF)"**
- Configura:
  - **Margen (%)**: Extensión adicional del mapa (5-50%)
  - **Resolución**: Calidad del raster (200-1000 píxeles)
  - **Método**: Interpolación (linear, cubic, nearest)

#### 6. **Generar salidas**
- Haz clic en **"Generar salidas"** (botón azul)
- Espera la confirmación con la ruta de salida

#### 7. **Descargar**
- Usa **"📥 Descargar todo (ZIP)"** para obtener todos los archivos
- El mapa se actualiza automáticamente en la pestaña "Mapa del proyecto"

### Formato de datos de entrada
```
1	5000.00	6000.00	100.50	Punto A
2	5100.00	6050.00	102.30	Punto B
3	5200.00	6100.00	101.80	Punto C
```
- Columna 1: Número de punto
- Columna 2: Coordenada X (Este)
- Columna 3: Coordenada Y (Norte)
- Columna 4: Cota/Z (Elevación)
- Columna 5: Descripción

### Separadores soportados
- Tabulaciones (\t)
- Comas (,)
- Punto y coma (;)

---

## 🗺️ Mapa del proyecto

### Descripción
Visualizador interactivo de todos los datos procesados en las otras pestañas.

### Funcionamiento
- **Automático**: El mapa se actualiza automáticamente cuando generas salidas en otras pestañas
- **Múltiples capas**: Puedes ver tanto el mapa topográfico como el proyecto general

### Qué muestra
1. **Mapa Topográfico**: Aparece si usaste la pestaña "Topográfico Profesional"
2. **Mapa del Proyecto General**: Muestra los datos del último archivo procesado (DXF, GPX, KML)

### Tipos de mapa
- **Leaflet**: Mapa 2D estándar con capas agrupadas
- **Mapbox 3D**: Visualización 3D (requiere token configurado)

### Controles del mapa
- Zoom con rueda del ratón
- Pan (arrastrar) para moverse
- Capas para activar/desactivar grupos
- Popups con información al hacer clic

---

## 📚 Manual de Usuario

### Descripción
Manual integrado con información de referencia rápida.

### Secciones disponibles
1. **🎯 Introducción**: Visión general de la aplicación
2. **⚙️ Configuración**: Zonas UTM y opciones
3. **🏗️ DXF**: Guía específica para archivos DXF
4. **🚶 GPX**: Guía para archivos GPX
5. **🌍 KML/KMZ**: Guía para archivos KML/KMZ
6. **📊 Topográfico**: Guía para datos topográficos
7. **🛠️ Problemas**: Solución de problemas y contacto de soporte

---

## ⚙️ Configuración General (Sidebar)

Antes de usar cualquier pestaña, configura en el panel lateral:

### Sistema de Coordenadas
- **Zona UTM de entrada**: EPSG de origen
  - Ecuador: 32717 (Zona 17S), 32718 (Zona 18S)
  - Perú: 32718 (Zona 18S), 32719 (Zona 19S)
  - Colombia: 32718, 32719
- **Zona UTM de salida**: EPSG de destino
  - 4326: WGS84 (Lat/Lon) - Predeterminado

### Agrupación
- **Por Tipo**: Separa puntos, líneas y polígonos
- **Por Capa**: Mantiene las capas originales del archivo

### Tipo de Mapa HTML
- **Normal**: Leaflet 2D básico
- **Mapbox**: Visualización avanzada 3D (si hay token configurado)

---

## 💡 Consejos y Buenas Prácticas

### Antes de empezar
1. ✅ Verifica que tus archivos no estén corruptos
2. ✅ Asegúrate de conocer el sistema de coordenadas de origen
3. ✅ Configura la zona UTM correcta en el sidebar

### Durante el proceso
1. 💾 Usa nombres de proyecto descriptivos
2. 📁 Organiza tus archivos en carpetas por proyecto
3. 🎨 Personaliza los colores según tus necesidades

### Después de convertir
1. 📥 Descarga siempre el ZIP como respaldo
2. 🗺️ Verifica el resultado en la pestaña "Mapa del proyecto"
3. 📂 Revisa los archivos generados en la carpeta de salida

---

## 🔧 Solución de Problemas

### Error: "Email no autorizado"
- Contacta al administrador para agregar tu email a la lista de usuarios autorizados

### Error: "Código inválido o expirado"
- Solicita un nuevo código
- Los códigos expiran en 10 minutos

### Error al convertir archivo
- Verifica que el archivo no esté corrupto
- Comprueba que el formato sea compatible
- Revisa que la zona UTM sea correcta

### El mapa no se muestra
- Asegúrate de haber generado salidas primero
- Verifica que el GeoJSON no esté vacío

---

## 📞 Soporte

**Desarrollador:** Patricio Sarmiento Reinoso  
**WhatsApp:** +593 995 959 047  
**Horario de atención:** Lunes-Viernes 8AM-6PM, Sábados 9AM-2PM (GMT-5)

---

## 📋 Resumen Rápido por Pestaña

| Pestaña | Entrada | Salidas | Uso Principal |
|---------|---------|---------|---------------|
| **DXF** | Archivo .dxf | KMZ, GeoJSON, Shapefile, HTML | Conversión CAD a GIS |
| **GPX** | Archivo .gpx | KMZ, GeoJSON, Shapefile, DXF, KML | Datos GPS/GNSS |
| **KML/KMZ** | Archivo .kml/.kmz | GeoJSON, Shapefile, DXF, KMZ | Google Earth a otros formatos |
| **Topográfico** | Datos pegados (X,Y,Z) | DXF, CSV, GeoJSON, KMZ, GeoTIFF | Levantamientos topográficos |
| **Mapa** | - | Visualización | Ver resultados interactivos |
| **Manual** | - | Documentación | Ayuda y referencia |

---

**Versión:** 3.4.4  
**Última actualización:** 2026
