# 🎯 Tarjeta de Referencia Rápida

## 👤 PARA USUARIOS FINALES

### 🔐 **ACCESO**
1. **Solicitar autorización** → WhatsApp +593995959047
2. **Recibir URL** de la aplicación  
3. **Email + Código** → Revisar bandeja (y spam)
4. **¡Listo para convertir!**

### 📂 **TIPOS DE ARCHIVO SOPORTADOS**

| Tipo | Extensión | Fuente típica | Resultado |
|------|-----------|---------------|-----------|
| **CAD** | `.dxf` | AutoCAD, QGIS | 7 formatos + visor |
| **GPS** | `.gpx` | Garmin, Strava | Rutas + waypoints |
| **Google Earth** | `.kml/.kmz` | Google Earth Pro | Datos geográficos |
| **Topográfico** | Tabla manual | Levantamiento campo | Planos + cálculos |

### ⚙️ **CONFIGURACIÓN BÁSICA**

#### 🌍 Zona UTM por país:
- **🇪🇨 Ecuador**: 17S
- **🇵🇪 Perú**: 18S  
- **🇨🇴 Colombia**: 18N
- **🇧🇷 Brasil**: 21S-25S
- **🇦🇷 Argentina**: 19S-21S

#### 🗂️ Agrupación:
- **"Type"**: Por geometría (recomendado)
- **"Capa"**: Estructura original

#### 🗺️ Mapa HTML:
- **"Normal"**: Compatible universal
- **"Mapbox"**: 3D con terreno

### 🔄 **FLUJO DE TRABAJO**

```
📤 Subir archivo
    ↓
⚙️ Configurar UTM
    ↓  
🔄 Convertir
    ↓
🗺️ Revisar mapa
    ↓
💾 Descargar ZIP
```

### 📁 **QUÉ RECIBES**

```
📁 MiProyecto_convertido.zip
├── 📄 archivo.json (datos estructurados)
├── 🌍 archivo.geojson (QGIS/ArcGIS)
├── 🌐 archivo.kmz (Google Earth)
├── 📐 archivo.dxf (CAD limpio)
├── 🖥️ index.html (visor web)
└── 📂 Shapes/ (archivos SHP)
    ├── points.shp
    ├── lines.shp
    ├── polygons.shp
    └── texts.shp
```

### 🛠️ **PROBLEMAS COMUNES**

| Problema | Solución |
|----------|----------|
| 🗺️ **Mapa desplazado** | Verificar zona UTM correcta |
| 📧 **No llega código** | Revisar spam/promociones |
| 💾 **No puedo descargar** | Usar Chrome/Firefox actualizado |
| 🌐 **HTML en blanco** | Usar servidor local: `python -m http.server` |
| ❌ **Error de subida** | Archivo máximo 200MB |

### 📞 **SOPORTE**

```
👨‍💻 Patricio Sarmiento Reinoso
📱 WhatsApp: +593995959047
🕐 L-V 8AM-6PM, S 9AM-2PM (GMT-5)

📧 Incluir siempre:
✅ Tipo de archivo
✅ Zona UTM usada  
✅ Mensaje de error exacto
✅ Navegador utilizado
```

---

## 👨‍💻 PARA DESARROLLADORES

### 🚀 **SETUP INICIAL**

```bash
# Verificar configuración
python check_setup.py

# Configuración automática
python setup_local.py

# Modo desarrollo
python switch_auth.py simple

# Probar aplicación
streamlit run app.py
```

### 🔑 **CÓDIGOS DE TESTING**

| Email | Código | Uso |
|-------|--------|-----|
| `test@gmail.com` | `TEST01` | Pruebas generales |
| `patricio@example.com` | `DEMO02` | Desarrollador |
| `admin@conversor.com` | `ADMIN3` | Administrador |

### 🌐 **DEPLOY PRODUCCIÓN**

```bash
# 1. Configurar Gmail
# Google Account → Security → App passwords

# 2. Cambiar a modo completo
python switch_auth.py complete

# 3. GitHub + Streamlit Cloud
git init && git add . && git commit -m "Deploy"
git remote add origin https://github.com/USER/repo.git
git push -u origin main

# 4. Configurar secretos en Streamlit Cloud:
ADMIN_EMAIL = "email@gmail.com"
ADMIN_PASSWORD = "app_password_16_chars"
AUTHORIZED_EMAILS = "client1@empresa.com,client2@gmail.com"
```

### 📊 **GESTIÓN USUARIOS**

```bash
# Panel administración
streamlit run admin_panel.py
# Password: Admin2025!

# Autorizar usuarios manualmente
# Editar authorized_users.json

# Ver logs y estadísticas
# Revisar archivos JSON generados
```

### 🔧 **SCRIPTS ÚTILES**

| Script | Función |
|--------|---------|
| `check_setup.py` | Verificar configuración |
| `switch_auth.py` | Cambiar modo autenticación |
| `setup_local.py` | Configuración inicial |
| `admin_panel.py` | Gestión usuarios |

### 📁 **ESTRUCTURA PROYECTO**

```
📁 Proyecto/
├── 🎯 app.py (aplicación principal)
├── 🔐 auth_simple.py (auth desarrollo)
├── 🔐 auth_system.py (auth producción)
├── 🛠️ admin_panel.py (gestión usuarios)
├── 📋 requirements.txt (dependencias)
├── 📖 README.md (documentación)
├── 📋 GUIA_PASO_A_PASO.md (tutorial completo)
└── 🔧 Scripts de utilidad
```

### 🚨 **TROUBLESHOOTING**

| Error | Causa | Solución |
|-------|-------|----------|
| `ImportError: MimeText` | Python 3.13 | Usar `auth_simple.py` |
| `ModuleNotFoundError` | Dependencias | `pip install -r requirements.txt` |
| `FileNotFoundError` | Archivos auth | `python setup_local.py` |
| Email no funciona | Gmail config | Verificar App Password |

---

## 🎓 **REFERENCIA TÉCNICA**

### 📐 **CÓDIGOS EPSG COMUNES**

| Región | EPSG | Descripción |
|--------|------|-------------|
| **Global** | 4326 | WGS84 (lat/lon) |
| **Ecuador** | 32717 | UTM 17S WGS84 |
| **Perú** | 32718 | UTM 18S WGS84 |
| **Colombia** | 32618 | UTM 18N WGS84 |

### 🗂️ **ORGANIZACIÓN KML**

#### DXF → 7 carpetas:
📍 Puntos • 📏 Líneas • 🔗 Polilíneas • 🔷 Formas • ⭕ Círculos • 📝 Textos • 🧩 Bloques

#### GPX → 3 carpetas:
📍 Puntos GPX • 🛤️ Pistas • 🗺️ Rutas

#### KML → 2 carpetas:
📍 Puntos Topográficos • 🔗 Polígonos/Líneas

### 🎨 **ICONOS EMOJI POR TIPO**

| Geometría | Icono | Uso |
|-----------|-------|-----|
| Punto | 📍 | Ubicaciones, referencias |
| Línea | 📏 | Límites, ejes |
| Polilínea | 🔗 | Rutas, contornos |
| Círculo | ⭕ | Áreas circulares |
| Texto | 📝 | Etiquetas, cotas |
| Bloque | 🧩 | Símbolos, referencias |
| Forma | 🔷 | Polígonos complejos |

---

**Conversor Universal Profesional v3.0**  
*Referencia rápida actualizada - Septiembre 2025*
