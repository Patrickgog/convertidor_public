# 📋 Guía Paso a Paso - Conversor Universal Profesional

## 👨‍💻 PARA EL DESARROLLADOR (TÚ)

### 🚀 **FASE 1: Configuración inicial del entorno**

#### 1️⃣ **Verificar instalación**
```bash
# Verificar Python (recomendado 3.11 o superior)
python --version

# Navegar al directorio del proyecto
cd "c:\PythonProjects\7_Universal_Converter_Proyecto - Licencia\DXF CONVERTIDOR\Streamlit"

# Instalar dependencias
pip install -r requirements.txt
```

#### 2️⃣ **Configurar autenticación para desarrollo**
```bash
# Ejecutar configuración automática
python setup_local.py

# Cambiar a modo simplificado (sin email)
python switch_auth.py simple

# Verificar compilación
python -m py_compile app.py
```

#### 3️⃣ **Primera ejecución de prueba**
```bash
# Ejecutar aplicación
streamlit run app.py

# Debería abrir: http://localhost:8501
# Usar estos códigos de prueba:
# Email: test@gmail.com → Código: TEST01
# Email: patricio@example.com → Código: DEMO02
```

### 🔧 **FASE 2: Testing y desarrollo**

#### 1️⃣ **Probar todos los convertidores**
```bash
# Preparar archivos de prueba en cada pestaña:
# - DXF: Subir archivo .dxf de CAD
# - GPX: Archivo de GPS (.gpx)
# - KML/KMZ: Archivo de Google Earth
# - Topográfico: Crear datos manualmente
```

#### 2️⃣ **Configurar parámetros según región**
```
Sidebar → Configuración:
- Zona UTM: 17S (Ecuador), 18S (Perú), 18N (Colombia)
- EPSG salida: 4326 (WGS84)
- Agrupación: "Type" (recomendado)
- Mapa HTML: "Normal" para compatibilidad
```

#### 3️⃣ **Verificar salidas**
```bash
# Cada conversión debe generar:
├── archivo.json
├── archivo.geojson
├── archivo.kmz
├── archivo.dxf
├── index.html
├── MapBox/ (si está configurado)
└── Shapes/ (shapefiles organizados)
```

### 🌐 **FASE 3: Preparación para distribución**

#### 1️⃣ **Configurar Gmail para producción**
```bash
# 1. Ir a Google Account → Security
# 2. Activar verificación en 2 pasos
# 3. App passwords → Generate → Mail
# 4. Copiar contraseña de 16 caracteres

# 5. Editar secrets_local.toml:
ADMIN_EMAIL = "tu_email_real@gmail.com"
ADMIN_PASSWORD = "abcd efgh ijkl mnop"  # App password
AUTHORIZED_EMAILS = "cliente1@empresa.com,cliente2@gmail.com"
```

#### 2️⃣ **Cambiar a sistema completo**
```bash
# Cambiar a autenticación con email
python switch_auth.py complete

# Probar envío de códigos
streamlit run app.py
# Verificar que lleguen emails reales
```

#### 3️⃣ **Preparar para deploy**
```bash
# Crear repositorio GitHub
git init
git add .
git commit -m "Conversor Universal v3.0"
git remote add origin https://github.com/TU_USUARIO/conversor-universal.git
git push -u origin main
```

### 🚀 **FASE 4: Deploy en Streamlit Cloud**

#### 1️⃣ **Configurar en Streamlit Cloud**
```bash
# 1. Ir a: https://share.streamlit.io
# 2. Sign in with GitHub
# 3. New app → From existing repo
# 4. Seleccionar tu repositorio
# 5. Main file path: app.py
# 6. Click "Deploy"
```

#### 2️⃣ **Configurar secretos**
```toml
# En Streamlit Cloud → Settings → Secrets:
ADMIN_EMAIL = "tu_email@gmail.com"
ADMIN_PASSWORD = "abcdefghijklmnop"
AUTHORIZED_EMAILS = "cliente1@empresa.com,cliente2@hotmail.com,cliente3@gmail.com"
```

#### 3️⃣ **Verificar deploy**
```bash
# URL será algo como:
# https://tu-usuario-conversor-universal-main-app-xyz123.streamlit.app

# Probar:
# 1. Acceso con autenticación
# 2. Envío de códigos por email
# 3. Todos los convertidores
# 4. Descarga de archivos
```

---

## 👥 PARA EL USUARIO FINAL

### 🌐 **ACCESO A LA APLICACIÓN**

#### 1️⃣ **Obtener acceso**
```
1. Contactar al desarrollador:
   📱 WhatsApp: +593995959047
   📧 Email: patricio@ejemplo.com

2. Proporcionar email corporativo/personal para autorización

3. Recibir URL de la aplicación:
   🔗 https://conversor-universal.streamlit.app
```

#### 2️⃣ **Primera autenticación**
```
1. Abrir URL en navegador
2. Pantalla de login aparecerá
3. Introducir email autorizado
4. Clic en "Enviar código"
5. Revisar bandeja de entrada (y spam)
6. Introducir código de 6 caracteres
7. Clic en "Acceder"
```

### 📊 **USO DE LOS CONVERTIDORES**

#### 🏗️ **CONVERSOR DXF** (Archivos de CAD)

**Paso 1: Preparar archivo**
```
- Tener archivo DXF de AutoCAD, QGIS, etc.
- Verificar que contenga: puntos, líneas, polígonos, textos
- Conocer zona UTM del proyecto (ej: 17S para Ecuador)
```

**Paso 2: Configurar parámetros**
```
Panel lateral → Configuración:
1. Zona UTM WGS84: Seleccionar según país
   - Ecuador: 17S
   - Perú: 18S  
   - Colombia: 18N
   
2. Agrupación de capas: "Type" (recomendado)
3. Tipo de mapa HTML: "Normal"
```

**Paso 3: Convertir**
```
1. Pestaña "🏗️ DXF"
2. Subir archivo DXF
3. Clic en "Convertir DXF"
4. Revisar mapa de vista previa
5. Clic en "💾 Descargar todos los resultados"
```

**Resultado obtenido:**
```
📁 Carpeta descargada contiene:
├── archivo.json (datos estructurados)
├── archivo.geojson (para QGIS/ArcGIS)
├── archivo.kmz (para Google Earth)
├── archivo.dxf (DXF limpio)
├── index.html (visor web interactivo)
└── Shapes/ (shapefiles por categoría)
    ├── points.shp
    ├── lines.shp
    ├── polygons.shp
    └── texts.shp
```

#### 🚶 **CONVERSOR GPX** (Archivos de GPS)

**Paso 1: Obtener archivo GPX**
```
- Exportar desde GPS Garmin, Suunto, etc.
- Descargar de apps: Strava, Komoot, AllTrails
- Archivo contiene: rutas, tracks, waypoints
```

**Paso 2: Convertir**
```
1. Pestaña "🚶 GPX"
2. Subir archivo .gpx
3. Conversión automática (no requiere configuración)
4. Revisar mapa con tracks (rojo) y rutas (azul)
5. Descargar resultados
```

**Usos típicos:**
```
✅ Análisis de rutas de senderismo
✅ Mapeo de recorridos ciclistas
✅ Documentación de expediciones
✅ Planificación turística
```

#### 🌍 **CONVERSOR KML/KMZ** (Google Earth)

**Paso 1: Preparar archivo**
```
- Exportar desde Google Earth Pro
- Descargar de Google My Maps
- Verificar que contenga geometrías (no solo imágenes)
```

**Paso 2: Convertir**
```
1. Pestaña "🌍 KML/KMZ"
2. Subir archivo
3. Procesamiento automático inteligente
4. Revisar elementos en mapa
5. Descargar en múltiples formatos
```

**Casos de uso:**
```
✅ Levantamientos topográficos
✅ Planificación urbana
✅ Gestión de recursos naturales
✅ Análisis territorial
```

#### 📊 **CONVERSOR TOPOGRÁFICO** (Datos de campo)

**Paso 1: Preparar datos**
```
Formato de tabla:
No.    | X(UTM)    | Y(UTM)     | Cota  | Descripción
P001   | 500000.00 | 9800000.00 | 2450  | Esquina NE
P002   | 500100.00 | 9800000.00 | 2445  | Lindero

Para polígonos, separar con líneas: ---
```

**Paso 2: Configurar proyecto**
```
1. Pestaña "📊 Topográfico"
2. Nombre del proyecto
3. Seleccionar modo:
   - Solo puntos
   - Puntos + polígonos
4. Copiar/pegar datos en tabla
5. Clic en "Generar archivos"
```

**Salida especializada:**
```
✅ DXF con puntos y textos de cota
✅ KML organizado por carpetas
✅ Shapefiles separados por geometría
✅ Cálculos automáticos de áreas/perímetros
```

### 📖 **MANUAL INTEGRADO**

#### Acceso a ayuda
```
1. Pestaña "📚 Manual de Usuario"
2. 7 secciones disponibles:
   - 🎯 Introducción
   - ⚙️ Configuración
   - 🏗️ DXF
   - 🚶 GPX
   - 🌍 KML/KMZ
   - 📊 Topográfico
   - 🛠️ Resolución de problemas
```

### 🛠️ **SOLUCIÓN DE PROBLEMAS COMUNES**

#### ❌ **"No puedo descargar archivos"**
```
✅ Verificar que la conversión haya terminado
✅ Usar navegador actualizado (Chrome/Firefox)
✅ Desactivar bloqueador de pop-ups
✅ Intentar en ventana de incógnito
```

#### ❌ **"El mapa está desplazado"**
```
✅ Verificar zona UTM correcta:
   - Ecuador: 17S
   - Perú: 18S
   - Colombia: 18N
✅ Revisar EPSG de entrada en configuración
```

#### ❌ **"No recibo códigos de acceso"**
```
✅ Revisar carpeta de spam/promociones
✅ Verificar email exacto proporcionado
✅ Contactar soporte para reautorización
```

#### ❌ **"El HTML no se ve bien"**
```
✅ Abrir index.html con servidor local:
   python -m http.server
✅ Evitar abrir directamente desde carpeta
✅ Usar navegador moderno
```

### 📞 **SOPORTE TÉCNICO**

#### Contacto directo
```
👨‍💻 Desarrollador: Patricio Sarmiento Reinoso
📱 WhatsApp: +593995959047
📧 Email: [tu_email_de_soporte]
🕐 Horario: L-V 8AM-6PM, S 9AM-2PM (GMT-5)
```

#### Información para soporte
```
Siempre incluir:
✅ Tipo de archivo que intentas convertir
✅ Tamaño aproximado del archivo
✅ Zona UTM configurada
✅ Mensaje de error exacto (si hay)
✅ Navegador utilizado
```

### 🎯 **MEJORES PRÁCTICAS**

#### Para archivos grandes
```
✅ Subir archivos menores a 200MB
✅ Simplificar geometrías complejas antes
✅ Dividir proyectos grandes en secciones
✅ Usar configuración "Type" para mejor organización
```

#### Para resultados profesionales
```
✅ Verificar zona UTM antes de convertir
✅ Usar nombres descriptivos para proyectos
✅ Revisar vista previa antes de descargar
✅ Mantener archivos originales como respaldo
```

---

## 🚀 **RESUMEN EJECUTIVO**

### Para el desarrollador:
1. **Setup**: `python setup_local.py` → `python switch_auth.py simple` → `streamlit run app.py`
2. **Testing**: Probar con códigos TEST01, DEMO02, ADMIN3
3. **Deploy**: GitHub → Streamlit Cloud → Configurar secretos Gmail
4. **Producción**: `python switch_auth.py complete` → Autorizar usuarios

### Para el usuario:
1. **Acceso**: Solicitar autorización → Recibir URL → Autenticarse con código
2. **Uso**: Subir archivo → Configurar UTM → Convertir → Descargar
3. **Soporte**: WhatsApp +593995959047 para cualquier problema

---

**Conversor Universal Profesional v3.0**  
*Solución completa para conversión de datos geoespaciales*
