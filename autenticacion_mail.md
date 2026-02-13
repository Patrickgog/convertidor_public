# 📧 Sistema de Autenticación por Email - Conversor Universal Profesional

## 📋 Descripción General

El sistema de autenticación por email permite controlar el acceso a la aplicación mediante códigos temporales enviados por correo electrónico. Este sistema es ideal para aplicaciones profesionales que requieren un control de acceso seguro y fácil de gestionar.

## 🔧 Configuración del Sistema

### 1. Archivo `secrets_local.toml` (Desarrollo Local)

```toml
# Configuración local para desarrollo
# NO SUBIR A GITHUB

ADMIN_EMAIL = "tu_email@gmail.com"
ADMIN_PASSWORD = "tu_app_password_de_16_caracteres"
AUTHORIZED_EMAILS = "email1@gmail.com,email2@hotmail.com,email3@outlook.com"
SESSION_TIMEOUT = 86400
MAX_DAILY_CODES = 5
COOKIE_PASSWORD = "clave_secreta_para_cookies_de_64_caracteres_minimo"
DEV_AUTOLOGIN_EMAIL = "tu_email@gmail.com"
```

### 2. Configuración en Streamlit Cloud

Para el despliegue en Streamlit Cloud, configura estos secretos en la interfaz web:

```toml
# Archivo de secretos para Streamlit Cloud
# Configurar en la interfaz web de Streamlit Cloud

# Email de administrador para envío de códigos
ADMIN_EMAIL = "tu_email@gmail.com"

# Contraseña de aplicación de Gmail (no la contraseña normal)
# Generar en: https://myaccount.google.com/apppasswords
ADMIN_PASSWORD = "tu_app_password_de_16_caracteres"

# Lista de emails autorizados (separados por comas)
AUTHORIZED_EMAILS = "patricio@example.com,cliente1@gmail.com,cliente2@hotmail.com"

# Configuración adicional
SESSION_TIMEOUT = 3600  # 1 hora en segundos
MAX_DAILY_CODES = 5     # Máximo códigos por email por día
```

## 🔑 Descripción de Cada Elemento

### **ADMIN_EMAIL**
- **Descripción**: Email del administrador que enviará los códigos de acceso
- **Formato**: Debe ser un email válido de Gmail
- **Ejemplo**: `"patricio.sar@gmail.com"`
- **Importante**: Este email debe tener habilitada la autenticación de dos factores

### **ADMIN_PASSWORD**
- **Descripción**: Contraseña de aplicación de Gmail (NO la contraseña normal)
- **Formato**: 16 caracteres sin espacios
- **Ejemplo**: `"vuewvixjlcrsftho"`
- **Importante**: Se genera específicamente para aplicaciones externas

### **AUTHORIZED_EMAILS**
- **Descripción**: Lista de emails que pueden solicitar códigos de acceso
- **Formato**: Emails separados por comas, sin espacios
- **Ejemplo**: `"patricio.sar@gmail.com,patrickgog@outlook.com"`
- **Importante**: Solo estos emails podrán recibir códigos

### **SESSION_TIMEOUT**
- **Descripción**: Tiempo de vida de la sesión en segundos
- **Valor por defecto**: `86400` (24 horas)
- **Ejemplo**: `3600` para 1 hora, `86400` para 24 horas

### **MAX_DAILY_CODES**
- **Descripción**: Máximo número de códigos que puede solicitar un email por día
- **Valor por defecto**: `5`
- **Propósito**: Prevenir spam y uso excesivo

### **COOKIE_PASSWORD**
- **Descripción**: Clave secreta para cifrar las cookies de "recordar dispositivo"
- **Formato**: Cadena de al menos 64 caracteres
- **Ejemplo**: `"pLQYFTbuOfHcNT1a_cyKvz7Le76lq17aeoZiClsxLHXoTXD2yF5lDU4lDe4cNrYj"`
- **Importante**: Debe ser única y segura

### **DEV_AUTOLOGIN_EMAIL**
- **Descripción**: Email para auto-login en desarrollo local
- **Uso**: Solo para desarrollo, se ignora en producción
- **Ejemplo**: `"patricio.sar@gmail.com"`

## 📧 Configuración de Gmail para Obtener Token

### Paso 1: Habilitar Autenticación de Dos Factores

1. Ve a [myaccount.google.com](https://myaccount.google.com)
2. Selecciona **Seguridad**
3. En **Iniciar sesión en Google**, activa **Verificación en 2 pasos**
4. Sigue las instrucciones para configurar 2FA

### Paso 2: Generar Contraseña de Aplicación

1. En la misma sección de **Seguridad**
2. Busca **Contraseñas de aplicaciones**
3. Selecciona **Aplicación** → **Otro (nombre personalizado)**
4. Escribe: `"Conversor Universal Profesional"`
5. Haz clic en **Generar**
6. **Copia la contraseña de 16 caracteres** (ej: `vuewvixjlcrsftho`)

### Paso 3: Configurar en la Aplicación

```toml
ADMIN_EMAIL = "tu_email@gmail.com"
ADMIN_PASSWORD = "vuewvixjlcrsftho"  # La contraseña de 16 caracteres
```

## 🚀 Flujo de Autenticación

### 1. Solicitud de Código
- Usuario ingresa su email
- Sistema verifica si está en `AUTHORIZED_EMAILS`
- Si está autorizado, genera código de 6 dígitos
- Envía email con el código

### 2. Verificación de Código
- Usuario ingresa el código recibido
- Sistema verifica:
  - Código correcto
  - No usado anteriormente
  - No expirado (10 minutos)
- Si es válido, establece sesión

### 3. Gestión de Sesión
- Sesión activa por `SESSION_TIMEOUT` segundos
- Opción de "Recordar dispositivo" con token persistente
- Token válido por 30 días

## 🔒 Características de Seguridad

### **Códigos Temporales**
- Duración: 10 minutos
- Uso único: Cada código solo se puede usar una vez
- Generación aleatoria: 6 dígitos (100000-999999)

### **Tokens Persistentes**
- Cifrado HMAC con SHA-256
- Incluye timestamp para expiración
- Almacenamiento seguro en cookies/localStorage

### **Protección Anti-Spam**
- Límite de códigos por día (`MAX_DAILY_CODES`)
- Lista blanca de emails autorizados
- Timeout de sesión automático

## 🔄 Mantener Sesión Activa al Recargar

### **¿Cómo Funciona?**

El sistema implementa **tres niveles de persistencia** para mantener la sesión activa:

1. **Query Parameters** (Streamlit Cloud)
2. **Cookies Cifradas** (Ambos entornos)
3. **localStorage** (Desarrollo local)

### **Configuración para Mantener Sesión**

#### **Paso 1: Activar "Recordar Dispositivo"**
```python
# Al hacer login, marcar la casilla "Recordar este dispositivo"
remember_device = st.checkbox("Recordar este dispositivo")
```

#### **Paso 2: Configurar COOKIE_PASSWORD**
```toml
# En secrets_local.toml o Streamlit Cloud
COOKIE_PASSWORD = "clave_secreta_para_cookies_de_64_caracteres_minimo"
```

**Importante**: Esta clave debe ser:
- Mínimo 64 caracteres
- Única para tu aplicación
- No compartida entre entornos

#### **Paso 3: Verificar Configuración de Cookies**

**Para Desarrollo Local:**
```python
# El sistema automáticamente usa localStorage
# No requiere configuración adicional
```

**Para Streamlit Cloud:**
```python
# Instalar dependencia de cookies
pip install streamlit-cookies-manager
```

### **Flujo de Persistencia**

#### **Al Iniciar Sesión:**
1. Usuario marca "Recordar este dispositivo"
2. Sistema genera token HMAC con timestamp
3. Token se guarda en:
   - **Cloud**: Query params + Cookies
   - **Local**: localStorage + Cookies

#### **Al Recargar Página:**
1. Sistema busca token en este orden:
   - Query parameters (Cloud)
   - Cookies cifradas
   - localStorage (Local)
2. Valida token y timestamp
3. Si es válido (< 30 días), restaura sesión

### **Configuración Avanzada**

#### **Extender Duración del Token**
```python
# En auth_system.py, línea ~196
if int(time.time()) - int(timestamp) < 30 * 24 * 3600:  # 30 días
    return email
```

**Cambiar a 60 días:**
```python
if int(time.time()) - int(timestamp) < 60 * 24 * 3600:  # 60 días
    return email
```

#### **Auto-Login para Desarrollo**
```toml
# En secrets_local.toml
DEV_AUTOLOGIN_EMAIL = "tu_email@gmail.com"
```

**Beneficios:**
- No requiere códigos en desarrollo
- Sesión automática al iniciar
- Ideal para testing

### **Verificar que Funciona**

#### **Test de Persistencia:**
1. Inicia sesión marcando "Recordar dispositivo"
2. Recarga la página (F5)
3. Verifica que sigues logueado
4. Cierra y abre el navegador
5. Verifica que sigues logueado

#### **Indicadores Visuales:**
```python
# En la sidebar aparece:
✅ Sesión activa: tu_email@gmail.com
```

### **Solución de Problemas**

#### **Problema: "Se cierra sesión al recargar"**

**Causas posibles:**
1. No marcaste "Recordar dispositivo"
2. `COOKIE_PASSWORD` muy corta
3. Cookies bloqueadas por el navegador

**Soluciones:**
```toml
# 1. Verificar COOKIE_PASSWORD (mínimo 64 caracteres)
COOKIE_PASSWORD = "pLQYFTbuOfHcNT1a_cyKvz7Le76lq17aeoZiClsxLHXoTXD2yF5lDU4lDe4cNrYj"

# 2. Generar nueva clave segura
import secrets
cookie_password = secrets.token_urlsafe(64)
print(cookie_password)
```

#### **Problema: "Token expirado"**

**Solución:**
```python
# Extender duración en auth_system.py
# Cambiar 30 días por el tiempo deseado
if int(time.time()) - int(timestamp) < 90 * 24 * 3600:  # 90 días
    return email
```

#### **Problema: "No funciona en Cloud"**

**Verificar:**
1. Instalar `streamlit-cookies-manager`
2. Configurar secretos en Streamlit Cloud
3. Verificar que `COOKIE_PASSWORD` esté configurado

### **Mejores Prácticas**

#### **Seguridad:**
- Cambiar `COOKIE_PASSWORD` regularmente
- Usar claves únicas por entorno
- No compartir tokens entre usuarios

#### **Usabilidad:**
- Ofrecer opción "Recordar dispositivo"
- Mostrar tiempo restante de sesión
- Permitir cerrar sesión manualmente

#### **Mantenimiento:**
- Monitorear tokens expirados
- Limpiar tokens antiguos periódicamente
- Log de accesos para auditoría

## 📱 Soporte Multi-Plataforma

### **Desarrollo Local**
- Auto-login con `DEV_AUTOLOGIN_EMAIL`
- Almacenamiento en localStorage
- Configuración desde `secrets_local.toml`

### **Streamlit Cloud**
- Configuración desde interfaz web
- Almacenamiento en cookies cifradas
- Query parameters para tokens

## 🛠️ Troubleshooting

### **Error: "Email no autorizado"**
- Verificar que el email esté en `AUTHORIZED_EMAILS`
- Comprobar formato (sin espacios, separados por comas)

### **Error: "Error al enviar email"**
- Verificar `ADMIN_EMAIL` y `ADMIN_PASSWORD`
- Confirmar que 2FA esté habilitado
- Regenerar contraseña de aplicación si es necesario

### **Error: "Código inválido o expirado"**
- Códigos expiran en 10 minutos
- Cada código solo se puede usar una vez
- Verificar que el código sea exacto (6 dígitos)

### **Problemas con "Recordar dispositivo"**
- Verificar `COOKIE_PASSWORD` (mínimo 64 caracteres)
- En Cloud, verificar configuración de cookies
- En local, verificar permisos de localStorage

## 📞 Soporte

**Desarrollador**: Patricio Sarmiento Reinoso  
**WhatsApp**: +593995959047  
**Horario**: L-V 8AM-6PM, S 9AM-2PM (GMT-5)

---

*Documentación actualizada para Conversor Universal Profesional v2.0*
