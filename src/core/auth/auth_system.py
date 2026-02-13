import os
import json
import time
import hashlib
import hmac
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# Intentar importar cookies manager
try:
    from streamlit_cookies_manager import EncryptedCookieManager
    COOKIES_AVAILABLE = True
except ImportError:
    COOKIES_AVAILABLE = False
    EncryptedCookieManager = None

class AuthSystem:
    def __init__(self):
        # Detectar si estamos en Cloud
        self.is_cloud = os.path.exists("/mount") or bool(st.secrets.get("IS_CLOUD", False))
        
        # Rutas de datos (Base es la raíz del proyecto, asumimos app.py está ahí)
        # AuthSystem está en src/core/auth/auth_system.py
        self.base_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.data_dir = self.base_dir / "z_data" / "auth"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuración de email con fallback para desarrollo local
        try:
            # 1. Intentar cargar desde secrets de Streamlit (Cloud o .streamlit/secrets.toml)
            self.admin_email = st.secrets.get("ADMIN_EMAIL", "")
            self.admin_password = st.secrets.get("ADMIN_PASSWORD", "")
            self.authorized_emails = st.secrets.get("AUTHORIZED_EMAILS", "").split(",")
            self.cookie_password = st.secrets.get("COOKIE_PASSWORD", "default_password")
        except:
            # 2. Fallback para desarrollo local (secrets_local.toml en la raíz)
            try:
                import toml
                secrets_path = self.base_dir / "secrets_local.toml"
                
                if secrets_path.exists():
                    with open(secrets_path, "r") as f:
                        local_secrets = toml.load(f)
                    self.admin_email = local_secrets.get("ADMIN_EMAIL", "")
                    self.admin_password = local_secrets.get("ADMIN_PASSWORD", "")
                    self.authorized_emails = local_secrets.get("AUTHORIZED_EMAILS", "").split(",")
                    self.cookie_password = local_secrets.get("COOKIE_PASSWORD", "default_password")
                else:
                    raise FileNotFoundError
            except:
                # 3. Configuración mínima de emergencia
                self.admin_email = ""
                self.admin_password = ""
                self.authorized_emails = ["test@gmail.com"]
                self.cookie_password = "default_password"
        
        # Configuración SMTP
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        
        # Archivos de datos
        self.auth_codes_file = self.data_dir / "auth_codes.json"
        self.authorized_users_file = self.data_dir / "authorized_users.json"
        self.remembered_devices_file = self.data_dir / "remembered_devices.json"
        
        # Cargar datos
        self.load_data()
        
        # Inicializar cookies
        self.cookies = self._get_cookies()

    def _get_cookies(self):
        """Obtiene el gestor de cookies"""
        if not COOKIES_AVAILABLE:
            return None
        try:
            cookies = EncryptedCookieManager(
                prefix="streamlit_",
                password=self.cookie_password
            )
            if not cookies.ready():
                return None
            return cookies
        except Exception:
            return None

    def load_data(self):
        """Carga datos de archivos JSON"""
        try:
            with open(self.auth_codes_file, 'r') as f:
                self.auth_codes = json.load(f)
        except Exception:
            self.auth_codes = {}
        
        try:
            with open(self.authorized_users_file, 'r') as f:
                self.authorized_users = json.load(f)
        except Exception:
            self.authorized_users = {}
        
        try:
            with open(self.remembered_devices_file, 'r') as f:
                self.remembered_devices = json.load(f)
        except Exception:
            self.remembered_devices = {}

    def save_data(self):
        """Guarda datos en archivos JSON"""
        try:
            with open(self.auth_codes_file, 'w') as f:
                json.dump(self.auth_codes, f)
            with open(self.authorized_users_file, 'w') as f:
                json.dump(self.authorized_users, f)
            with open(self.remembered_devices_file, 'w') as f:
                json.dump(self.remembered_devices, f)
        except Exception as e:
            st.error(f"Error guardando datos de auth: {e}")

    def generate_code(self):
        """Genera código de 6 dígitos"""
        import random
        return str(random.randint(100000, 999999))

    def send_code_email(self, email, code):
        """Envía código por email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.admin_email
            msg['To'] = email
            msg['Subject'] = "🚀 Conversor Universal Profesional - Código de Acceso"
            
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
                <div style="background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <h1 style="color: #2c3e50; text-align: center; margin-bottom: 30px;">🚀 CONVERSOR UNIVERSAL PROFESIONAL</h1>
                    
                    <h2 style="color: #27ae60;">¡Bienvenido!</h2>
                    <p>Has solicitado acceso al <strong>Conversor Universal Profesional</strong>.</p>
                    
                    <div style="background-color: #ecf0f1; padding: 20px; border-radius: 5px; text-align: center; margin: 20px 0;">
                        <h3 style="color: #2c3e50; margin: 0;">🔑 Tu código de acceso es:</h3>
                        <h1 style="color: #e74c3c; font-size: 32px; margin: 10px 0;">{code}</h1>
                    </div>
                    
                    <p style="color: #7f8c8d;">⏰ Este código expira en 10 minutos</p>
                    
                    <h3 style="color: #2c3e50;">📋 Instrucciones:</h3>
                    <ol style="color: #34495e;">
                        <li>Regresa a la aplicación web</li>
                        <li>Introduce este código en el campo correspondiente</li>
                        <li>¡Comienza a convertir tus archivos geoespaciales!</li>
                    </ol>
                    
                    <hr style="border: none; border-top: 2px solid #ecf0f1; margin: 30px 0;">
                    
                    <div style="text-align: center; color: #7f8c8d; font-size: 14px;">
                        <p><strong>Desarrollador:</strong> Patricio Sarmiento Reinoso</p>
                        <p><strong>WhatsApp:</strong> +593995959047</p>
                        <p><strong>Soporte:</strong> L-V 8AM-6PM, S 9AM-2PM (GMT-5)</p>
                    </div>
                </div>
            </body>
            </html>
            """
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.admin_email, self.admin_password)
            text = msg.as_string()
            server.sendmail(self.admin_email, email, text)
            server.quit()
            return True
        except Exception as e:
            st.error(f"Error al enviar email: {e}")
            return False

    def create_device_token(self, email):
        """Crea token para recordar dispositivo"""
        timestamp = int(time.time())
        data = f"{email}:{timestamp}"
        token = hmac.new(
            self.cookie_password.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{data}:{token}"

    def validate_device_token(self, token):
        """Valida token de dispositivo"""
        try:
            parts = token.split(':')
            if len(parts) != 3:
                return None
            email, timestamp, signature = parts
            data = f"{email}:{timestamp}"
            expected_signature = hmac.new(
                self.cookie_password.encode(),
                data.encode(),
                hashlib.sha256
            ).hexdigest()
            if signature == expected_signature:
                # Verificar que no haya expirado (30 días)
                if int(time.time()) - int(timestamp) < 30 * 24 * 3600:
                    return email
            return None
        except Exception:
            return None

    def set_persistent_token(self, email):
        """Establece token persistente"""
        token = self.create_device_token(email)
        
        # Guardar en query parameter (para Cloud)
        if self.is_cloud:
            st.query_params.token = token
        
        # Guardar en cookie
        if self.cookies:
            try:
                self.cookies['auth_token'] = token
                self.cookies.save()
            except Exception:
                pass
        
        # Guardar en localStorage (solo local)
        if not self.is_cloud:
            try:
                components.html(f"""
                <script>
                localStorage.setItem('auth_token', '{token}');
                </script>
                """, height=0)
            except Exception:
                pass

    def clear_persistent_token(self):
        """Limpia token persistente"""
        # Limpiar query parameter
        if 'token' in st.query_params:
            del st.query_params.token
        
        # Limpiar cookie
        if self.cookies:
            try:
                self.cookies.delete('auth_token')
                self.cookies.save()
            except Exception:
                pass
        
        # Limpiar localStorage (solo local)
        if not self.is_cloud:
            try:
                components.html("""
                <script>
                localStorage.removeItem('auth_token');
                </script>
                """, height=0)
            except Exception:
                pass

    def show_login_page(self):
        """Muestra página de login"""
        st.title("🚀 Conversor Universal Profesional")
        st.markdown("Esta aplicación requiere autenticación para su uso.")
        
        email = st.text_input("Email")
        
        if st.button("Solicitar código"):
            if email in self.authorized_emails:
                code = self.generate_code()
                self.auth_codes[email] = {
                    'code': code,
                    'timestamp': time.time(),
                    'used': False
                }
                self.save_data()
                
                if self.send_code_email(email, code):
                    st.success("Código enviado por email")
                else:
                    st.error("Error al enviar código")
            else:
                st.error("Email no autorizado")
        
        code = st.text_input("Código de acceso")
        remember_device = st.checkbox("Recordar este dispositivo")
        
        if st.button("Verificar código"):
            if email in self.auth_codes:
                auth_data = self.auth_codes[email]
                if (auth_data['code'] == code and 
                    not auth_data['used'] and 
                    time.time() - auth_data['timestamp'] < 600):  # 10 minutos
                    
                    # Marcar código como usado
                    auth_data['used'] = True
                    self.save_data()
                    
                    # Establecer sesión
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.auth_timestamp = time.time()
                    
                    if remember_device:
                        st.session_state.remember_device = True
                        self.set_persistent_token(email)
                    
                    st.success("Acceso autorizado")
                    st.rerun()
                else:
                    st.error("Código inválido o expirado")
            else:
                st.error("Código no encontrado")

    def show_user_info(self):
        """Muestra información del usuario autenticado"""
        if 'user_email' in st.session_state:
            with st.sidebar:
                st.success(f"✅ Sesión activa: {st.session_state.user_email}")
                if st.button("🚪 Cerrar sesión", key=f"logout_btn_{st.session_state.user_email}"):
                    # Limpiar sesión
                    st.session_state.authenticated = False
                    st.session_state.user_email = None
                    st.session_state.auth_timestamp = None
                    st.session_state.remember_device = False
                    st.session_state.session_closed = True
                    
                    # Limpiar token persistente
                    self.clear_persistent_token()
                    
                    st.rerun()

def check_authentication():
    """Verifica autenticación"""
    auth = AuthSystem()
    
    # Verificar si ya está autenticado
    if st.session_state.get('authenticated', False):
        # Verificar timeout (24 horas)
        if time.time() - st.session_state.get('auth_timestamp', 0) < 86400:
            auth.show_user_info()
            return True
        else:
            # Sesión expirada
            st.session_state.authenticated = False
            st.session_state.user_email = None
            st.session_state.auth_timestamp = None
    
    # Verificar token persistente
    token = None
    
    # 1. Query parameter (prioridad para Cloud)
    if 'token' in st.query_params:
        token = st.query_params.token
    
    # 2. Cookie
    elif auth.cookies and 'auth_token' in auth.cookies:
        token = auth.cookies.get('auth_token')
    
    # 3. localStorage (solo local)
    elif not auth.is_cloud:
        try:
            token = components.html("""
            <script>
            const token = localStorage.getItem('auth_token');
            if (token) {
                window.parent.postMessage({type: 'auth_token', token: token}, '*');
            }
            </script>
            """, height=0)
        except Exception:
            pass
    
    if token:
        email = auth.validate_device_token(token)
        if email:
            st.session_state.authenticated = True
            st.session_state.user_email = email
            st.session_state.auth_timestamp = time.time()
            auth.show_user_info()
            return True
    
    # Auto-login para desarrollo local
    if not auth.is_cloud and not st.session_state.get('session_closed', False):
        try:
            dev_email = st.secrets.get("DEV_AUTOLOGIN_EMAIL", "")
            if dev_email and dev_email in auth.authorized_emails:
                st.session_state.authenticated = True
                st.session_state.user_email = dev_email
                st.session_state.auth_timestamp = time.time()
                auth.show_user_info()
                return True
        except Exception:
            pass
    
    # Mostrar página de login
    auth.show_login_page()
    return False

def show_user_info():
    """Muestra información del usuario"""
    auth = AuthSystem()
    auth.show_user_info()
