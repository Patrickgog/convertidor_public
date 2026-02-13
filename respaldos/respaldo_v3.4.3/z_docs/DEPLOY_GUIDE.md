# Guía de Deploy - Conversor Universal Profesional
# Autor: Patricio Sarmiento Reinoso

## 🚀 Opciones de Deploy Recomendadas

### 1. **Streamlit Cloud (Más Fácil - Recomendado)**

#### ✅ Ventajas:
- Gratuito hasta 3 apps públicas
- Deploy automático desde GitHub
- SSL incluido automáticamente
- Integración nativa con Streamlit

#### 📋 Pasos:
1. **Crear repositorio GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/tu_usuario/conversor-universal.git
   git push -u origin main
   ```

2. **Configurar en Streamlit Cloud:**
   - Ir a [share.streamlit.io](https://share.streamlit.io)
   - Conectar con GitHub
   - Seleccionar repositorio
   - Configurar secretos (ver sección Configuración)

3. **Configurar secretos en Streamlit Cloud:**
   ```toml
   ADMIN_EMAIL = "tu_email@gmail.com"
   ADMIN_PASSWORD = "app_password_gmail"
   AUTHORIZED_EMAILS = "cliente1@gmail.com,cliente2@hotmail.com"
   ```

#### 🔐 Configurar Gmail para envío de códigos:
1. Ir a [myaccount.google.com](https://myaccount.google.com)
2. Seguridad → Verificación en 2 pasos (activar)
3. Contraseñas de aplicaciones → Generar nueva
4. Usar la contraseña generada (16 caracteres)

---

### 2. **Heroku (Escalable)**

#### ✅ Ventajas:
- Escalamiento automático
- Base de datos PostgreSQL gratuita
- Add-ons disponibles
- Control total sobre configuración

#### 💰 Costos:
- Plan gratuito: 550 horas/mes
- Plan básico: $7/mes por dyno

#### 📋 Pasos:
1. **Instalar Heroku CLI:**
   ```bash
   # Windows
   winget install Heroku.HerokuCLI
   ```

2. **Crear archivos de configuración:**
   ```bash
   # Procfile
   echo "web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0" > Procfile
   
   # runtime.txt
   echo "python-3.11.5" > runtime.txt
   ```

3. **Deploy a Heroku:**
   ```bash
   heroku login
   heroku create tu-conversor-universal
   git push heroku main
   heroku config:set ADMIN_EMAIL="tu_email@gmail.com"
   heroku config:set ADMIN_PASSWORD="app_password"
   heroku config:set AUTHORIZED_EMAILS="cliente1@gmail.com,cliente2@hotmail.com"
   ```

---

### 3. **Railway (Moderno y Rápido)**

#### ✅ Ventajas:
- Deploy extremadamente fácil
- Pricing por uso real
- Performance excelente
- Soporte nativo para Python

#### 📋 Pasos:
1. **Conectar GitHub a Railway:**
   - Ir a [railway.app](https://railway.app)
   - Conectar repositorio GitHub
   - Deploy automático

2. **Configurar variables de entorno:**
   ```
   ADMIN_EMAIL=tu_email@gmail.com
   ADMIN_PASSWORD=app_password_gmail
   AUTHORIZED_EMAILS=cliente1@gmail.com,cliente2@hotmail.com
   ```

---

### 4. **Render (Alternativa Robusta)**

#### ✅ Ventajas:
- Plan gratuito generoso
- SSL automático
- Deploy desde GitHub
- Base de datos PostgreSQL gratuita

#### 📋 Pasos:
1. **Crear servicio en Render:**
   - Ir a [render.com](https://render.com)
   - New → Web Service
   - Conectar repositorio GitHub

2. **Configuración del servicio:**
   ```
   Build Command: pip install -r requirements_auth.txt
   Start Command: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
   ```

---

## 🔧 Configuración del Sistema de Autenticación

### 📧 Emails Autorizados
Editar en `auth_system.py` línea ~95:
```python
authorized_emails = [
    "patricio@example.com",
    "cliente1@gmail.com", 
    "cliente2@hotmail.com",
    "nuevo_cliente@empresa.com"
]
```

### 🔐 Configurar Gmail App Password
1. **Activar 2FA en Gmail:**
   - Google Account → Security → 2-Step Verification

2. **Generar App Password:**
   - Google Account → Security → App passwords
   - Select app: Mail
   - Select device: Other (custom name)
   - Copiar contraseña de 16 caracteres

3. **Configurar en secrets:**
   ```toml
   ADMIN_EMAIL = "tu_email@gmail.com"
   ADMIN_PASSWORD = "xxxx xxxx xxxx xxxx"  # Sin espacios en producción
   ```

### ⚙️ Personalización Avanzada

#### Modificar tiempo de expiración de códigos:
```python
# En auth_system.py línea ~12
self.session_timeout = 3600  # 1 hora
```

#### Cambiar longitud de códigos:
```python
# En auth_system.py línea ~23
def generate_access_code(self, length=8):  # 8 caracteres
```

#### Personalizar template de email:
Editar el HTML en `send_access_code()` función

---

## 🛡️ Seguridad Adicional

### 🔒 Restricciones recomendadas:
1. **Rate limiting por IP:**
   ```python
   # Implementar contador de intentos por IP
   # Bloquear después de 5 intentos fallidos
   ```

2. **Logs de acceso:**
   ```python
   # Registrar todos los intentos de acceso
   # Incluir IP, timestamp, resultado
   ```

3. **Blacklist de dominios:**
   ```python
   # Bloquear dominios temporales
   blocked_domains = ["tempmail.com", "10minutemail.com"]
   ```

### 📊 Monitoreo:
- Revisar `auth_codes.json` y `authorized_users.json`
- Implementar alertas por email para accesos
- Dashboard de usuarios activos

---

## 🚀 Recomendación Final

**Para empezar:** Streamlit Cloud (gratuito y fácil)
**Para producción:** Railway o Render (mejor performance)
**Para empresas:** Heroku (más control y opciones)

### 📞 Soporte
- **Desarrollador:** Patricio Sarmiento Reinoso
- **WhatsApp:** +593995959047
- **Email:** patricio@example.com
