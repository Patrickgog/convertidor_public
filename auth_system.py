import streamlit as st
import streamlit.components.v1 as components
import smtplib
import json
import time
import hashlib
import hmac
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import toml

try:
    from streamlit_cookies_manager import EncryptedCookieManager
    COOKIES_AVAILABLE = True
except ImportError:
    COOKIES_AVAILABLE = False

class AuthSystem:
    def __init__(self):
        # Detectar si estamos en Cloud
        self.is_cloud = os.path.exists("/mount") or bool(st.secrets.get("IS_CLOUD", False))
        
        # Configuración de email
        self.admin_email = st.secrets.get("ADMIN_EMAIL", "patricio.sar@gmail.com")
        self.admin_password = st.secrets.get("ADMIN_PASSWORD", "vuewvixjlcrsftho")
        self.authorized_emails = st.secrets.get("AUTHORIZED_EMAILS", "patricio.sar@gmail.com,patrickgog@outlook.com").split(",")
        self.cookie_password = st.secrets.get("COOKIE_PASSWORD", "una_clave_larga_y_unica")
        
        # Configuración SMTP
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        
        # Archivos de datos
        self.auth_codes_file = "auth_codes.json"
        self.authorized_users_file = "authorized_users.json"
        self.remembered_devices_file = "remembered_devices.json"
        
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
        except FileNotFoundError:
            self.auth_codes = {}
        
        try:
            with open(self.authorized_users_file, 'r') as f:
                self.authorized_users = json.load(f)
        except FileNotFoundError:
            self.authorized_users = {}
        
        try:
            with open(self.remembered_devices_file, 'r') as f:
                self.remembered_devices = json.load(f)
        except FileNotFoundError:
            self.remembered_devices = {}

    def save_data(self):
        """Guarda datos en archivos JSON"""
        with open(self.auth_codes_file, 'w') as f:
            json.dump(self.auth_codes, f, indent=2)
        with open(self.authorized_users_file, 'w') as f:
            json.dump(self.authorized_users, f, indent=2)
        with open(self.remembered_devices_file, 'w') as f:
            json.dump(self.remembered_devices, f, indent=2)

    def is_user_authorized(self, email):
        """Verifica si el usuario está autorizado"""
        return email in self.authorized_emails or email in self.authorized_users

    def generate_code(self):
        """Genera código de acceso"""
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
        """Crea token HMAC para dispositivo"""
        timestamp = str(int(time.time()))
        data = f"{email}:{timestamp}"
        token = hmac.new(
            self.cookie_password.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{email}:{timestamp}:{token}"

    def validate_device_token(self, token):
        """Valida token HMAC"""
        if not token or token == "dev_override":
            return None
        
        try:
            parts = token.split(":")
            if len(parts) != 3:
                return None
            
            email, timestamp, signature = parts
            data = f"{email}:{timestamp}"
            expected_signature = hmac.new(
                self.cookie_password.encode(),
                data.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if hmac.compare_digest(signature, expected_signature):
                # Verificar que no sea muy antiguo (30 días)
                token_time = int(timestamp)
                current_time = int(time.time())
                if current_time - token_time < 30 * 24 * 3600:
                    return email
        except Exception:
            pass
        return None

    def set_persistent_token(self, token):
        """Guarda token persistente con múltiples métodos"""
        success = False
        
        # 1) Query parameter (más confiable para Cloud)
        try:
            st.query_params.token = token
            success = True
        except Exception:
            pass
        
        # 2) Cookie (método secundario)
        if self.cookies:
            try:
                self.cookies["auth_token"] = token
                self.cookies.set("auth_token", token, max_age_days=30)
                self.cookies.save()
                success = True
            except Exception:
                pass
        
        # 3) localStorage (solo local)
        if not self.is_cloud:
            try:
                components.html(f"""
                <script>
                localStorage.setItem('auth_token', '{token}');
                </script>
                """, height=0)
                success = True
            except Exception:
                pass
        
        return success

    def get_persistent_token(self):
        """Obtiene token persistente de múltiples fuentes"""
        # 1) Query parameter (más confiable)
        try:
            token = st.query_params.get("token")
            if token:
                return token
        except Exception:
            pass
        
        # 2) Cookie
        if self.cookies:
            try:
                token = self.cookies.get("auth_token")
                if token:
                    return token
            except Exception:
                pass
        
        # 3) localStorage (solo local)
        if not self.is_cloud:
            try:
                components.html("""
                <script>
                const token = localStorage.getItem('auth_token') || '';
                if (token) {
                    const url = new URL(window.location.href);
                    if (!url.searchParams.get('token')) {
                        url.searchParams.set('token', token);
                        window.location.replace(url.toString());
                    }
                }
                </script>
                """, height=0)
            except Exception:
                pass
        
        return None

    def check_session_timeout(self, email):
        """Verifica timeout de sesión"""
        if email in self.authorized_users:
            last_access = self.authorized_users[email].get('last_access', 0)
            timeout = st.secrets.get("SESSION_TIMEOUT", 86400)  # 24 horas por defecto
            return time.time() - last_access > timeout
        return True

    def update_last_access(self, email):
        """Actualiza último acceso"""
        if email not in self.authorized_users:
            self.authorized_users[email] = {}
        self.authorized_users[email]['last_access'] = time.time()
        self.save_data()

def show_login_page():
    """Muestra página de login"""
    st.title("🚀 Conversor Universal Profesional")
    st.markdown("Esta aplicación requiere autenticación para su uso.")
    
    auth = AuthSystem()
    
    # Formulario de login
    with st.form("login_form"):
        email = st.text_input("📧 Email", placeholder="tu@email.com")
        col1, col2 = st.columns(2)
        
        with col1:
            request_code = st.form_submit_button("📨 Solicitar Código", use_container_width=True)
        
        with col2:
            verify_code = st.form_submit_button("✅ Verificar Código", use_container_width=True)
        
        if request_code:
            if email and "@" in email:
                if auth.is_user_authorized(email):
                    code = auth.generate_code()
                    auth.auth_codes[email] = {
                        'code': code,
                        'timestamp': time.time(),
                        'attempts': 0
                    }
                    auth.save_data()
                    
                    if auth.send_code_email(email, code):
                        st.success(f"✅ Código enviado a {email}")
                    else:
                        st.error("❌ Error al enviar código")
                else:
                    st.error("❌ Email no autorizado")
            else:
                st.error("❌ Email inválido")
        
        if verify_code:
            code = st.text_input("🔢 Código de Acceso", placeholder="123456")
            remember_device = st.checkbox("💾 Recordar este dispositivo", value=True)
            
            if code and email:
                if email in auth.auth_codes:
                    stored_code = auth.auth_codes[email]
                    if (time.time() - stored_code['timestamp'] < 600 and  # 10 minutos
                        stored_code['code'] == code and
                        stored_code['attempts'] < 3):
                        
                        # Autenticación exitosa
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        st.session_state.auth_timestamp = time.time()
                        st.session_state.remember_device = remember_device
                        
                        # Guardar token persistente si se seleccionó recordar
                        if remember_device:
                            token = auth.create_device_token(email)
                            if auth.set_persistent_token(token):
                                st.session_state.device_token = token
                                st.success("✅ Dispositivo recordado")
                            else:
                                st.warning("⚠️ No se pudo recordar el dispositivo")
                        
                        # Limpiar código usado
                        del auth.auth_codes[email]
                        auth.save_data()
                        
                        # Actualizar último acceso
                        auth.update_last_access(email)
                        
                        st.success("✅ Autenticación exitosa")
                        st.rerun()
                    else:
                        st.error("❌ Código inválido o expirado")
                        auth.auth_codes[email]['attempts'] += 1
                        auth.save_data()
                else:
                    st.error("❌ No hay código pendiente para este email")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 20px; color: #666;">
        <p><strong>Desarrollador:</strong> Patricio Sarmiento Reinoso</p>
        <p><strong>WhatsApp:</strong> +593995959047</p>
        <p><strong>Soporte:</strong> L-V 8AM-6PM, S 9AM-2PM (GMT-5)</p>
    </div>
    """, unsafe_allow_html=True)

def check_authentication():
    """Verifica autenticación del usuario"""
    auth = AuthSystem()

    # Verificar si está autenticado
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    # Auto-login por token recordado
    if not st.session_state.authenticated:
        # 1) DEV OVERRIDE: autologin por secrets en local (solo si no se cerró sesión manualmente)
        if not auth.is_cloud and not st.session_state.get('session_closed', False):
            try:
                dev_email = None
                try:
                    dev_email = st.secrets.get("DEV_AUTOLOGIN_EMAIL", None)
                except Exception:
                    dev_email = None
                if not dev_email:
                    try:
                        with open("secrets_local.toml", "r") as f:
                            dev_email = toml.load(f).get("DEV_AUTOLOGIN_EMAIL", None)
                    except Exception:
                        pass
                if dev_email and auth.is_user_authorized(dev_email):
                    st.session_state.authenticated = True
                    st.session_state.user_email = dev_email
                    st.session_state.auth_timestamp = time.time()
                    st.session_state.remember_device = True
                    st.session_state.device_token = "dev_override"
                    return True
            except Exception:
                pass
        
        # 2) Token persistente - múltiples métodos
        token = None
        
        # 2a) Query parameter (más confiable)
        try:
            token = st.query_params.get("token")
        except Exception:
            pass
        
        # 2b) Cookie
        if not token and auth.cookies:
            try:
                token = auth.cookies.get("auth_token")
            except Exception:
                pass
        
        # 2c) localStorage (solo local)
        if not token and not auth.is_cloud:
            try:
                components.html("""
                <script>
                const token = localStorage.getItem('auth_token') || '';
                if (token && !window.location.search.includes('token=')) {
                    const url = new URL(window.location.href);
                    url.searchParams.set('token', token);
                    window.location.replace(url.toString());
                }
                </script>
                """, height=0)
            except Exception:
                pass
        
        # Validar token encontrado
        if token:
            email_from_token = auth.validate_device_token(token)
            if email_from_token and auth.is_user_authorized(email_from_token):
                st.session_state.authenticated = True
                st.session_state.user_email = email_from_token
                st.session_state.auth_timestamp = time.time()
                st.session_state.remember_device = True
                st.session_state.device_token = token
                return True

    if not st.session_state.authenticated:
        show_login_page()
        return False

    # Verificar timeout de sesión
    if 'user_email' in st.session_state:
        if auth.check_session_timeout(st.session_state.user_email):
            st.session_state.authenticated = False
            st.warning("⏰ Sesión expirada. Vuelve a autenticarte.")
            st.rerun()
            return False

    return True

def show_user_info():
    """Muestra información del usuario autenticado"""
    if 'user_email' in st.session_state:
        with st.sidebar:
            st.success(f"✅ Sesión activa: {st.session_state.user_email}")
            if st.button("🚪 Cerrar Sesión"):
                # Limpiar sesión
                st.session_state.authenticated = False
                st.session_state.user_email = None
                st.session_state.auth_timestamp = None
                st.session_state.remember_device = False
                st.session_state.device_token = None
                st.session_state.session_closed = True  # Marcar que se cerró manualmente
                
                # Limpiar token persistente
                auth = AuthSystem()
                try:
                    # Limpiar query parameter
                    if "token" in st.query_params:
                        del st.query_params.token
                except Exception:
                    pass
                
                # Limpiar cookie
                if auth.cookies:
                    try:
                        auth.cookies.delete("auth_token")
                        auth.cookies.save()
                    except Exception:
                        pass
                
                # Limpiar localStorage (solo local)
                if not auth.is_cloud:
                    try:
                        components.html("""
                        <script>
                        localStorage.removeItem('auth_token');
                        </script>
                        """, height=0)
                    except Exception:
                        pass
                
                st.rerun()
