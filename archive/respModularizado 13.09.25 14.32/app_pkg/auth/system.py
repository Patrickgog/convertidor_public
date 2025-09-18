"""
Sistema de autenticación completo (con email) - Modular
Lee y escribe en data/ y config/ cuando estén disponibles.
"""

import json
import os
import random
import string
import time
import hashlib
import uuid
from pathlib import Path
from typing import Optional

import streamlit as st
import smtplib

try:
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
except ImportError:
    from email.message import EmailMessage
    MimeText = None
    MimeMultipart = None

try:
    from streamlit_cookies_manager import EncryptedCookieManager  # type: ignore
except Exception:
    EncryptedCookieManager = None  # type: ignore

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class AuthSystem:
    def __init__(self):
        self.codes_file = str(DATA_DIR / "auth_codes.json")
        self.users_file = str(DATA_DIR / "authorized_users.json")
        self.devices_file = str(DATA_DIR / "remembered_devices.json")
        self.session_timeout = 3600
        self._cookies = None

        # Email config: try Streamlit secrets, fallback to config/secrets_local.toml
        try:
            self.admin_email = st.secrets.get("ADMIN_EMAIL", "")
            self.admin_password = st.secrets.get("ADMIN_PASSWORD", "")
            self.authorized_emails = st.secrets.get("AUTHORIZED_EMAILS", "").split(",")
        except Exception:
            try:
                import toml  # type: ignore
                local_path = CONFIG_DIR / "secrets_local.toml"
                if local_path.exists():
                    local_secrets = toml.load(str(local_path))
                    self.admin_email = local_secrets.get("ADMIN_EMAIL", "test@example.com")
                    self.admin_password = local_secrets.get("ADMIN_PASSWORD", "test_password")
                    self.authorized_emails = local_secrets.get("AUTHORIZED_EMAILS", "test@gmail.com").split(",")
                else:
                    self.admin_email = "test@example.com"
                    self.admin_password = "test_password"
                    self.authorized_emails = ["test@gmail.com", "patricio@example.com"]
            except Exception:
                self.admin_email = "test@example.com"
                self.admin_password = "test_password"
                self.authorized_emails = ["test@gmail.com", "patricio@example.com"]

        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

    def _get_cookies(self):
        try:
            if self._cookies is not None:
                return self._cookies
            if EncryptedCookieManager is None:
                return None
            password = None
            try:
                password = st.secrets.get("COOKIE_PASSWORD", None)
            except Exception:
                password = None
            self._cookies = EncryptedCookieManager(prefix="auth_topografia", password=password or "dev-cookie-password")
            if not self._cookies.ready():
                return None
            return self._cookies
        except Exception:
            return None

    def _load_devices(self):
        try:
            if os.path.exists(self.devices_file):
                with open(self.devices_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_devices(self, data):
        try:
            with open(self.devices_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def create_device_token(self, email, days_valid=30):
        raw = f"{email}-{time.time()}-{uuid.uuid4()}"
        token = hashlib.sha256(raw.encode('utf-8')).hexdigest()
        devices = self._load_devices()
        devices[token] = {
            'email': email,
            'created_at': time.time(),
            'expires_at': time.time() + days_valid * 86400,
        }
        self._save_devices(devices)
        return token

    def validate_device_token(self, token: Optional[str]):
        if not token:
            return None
        devices = self._load_devices()
        info = devices.get(token)
        if not info:
            return None
        if time.time() > info.get('expires_at', 0):
            try:
                del devices[token]
                self._save_devices(devices)
            except Exception:
                pass
            return None
        return info.get('email')

    def remove_device_token(self, token: Optional[str]):
        if not token:
            return
        devices = self._load_devices()
        if token in devices:
            try:
                del devices[token]
                self._save_devices(devices)
            except Exception:
                pass

    def set_persistent_token(self, token):
        cookies = self._get_cookies()
        if cookies is not None:
            try:
                cookies["auth_token"] = token
                cookies.save()
                return True
            except Exception:
                return False
        try:
            st.query_params["token"] = token
        except Exception:
            pass
        return False

    def get_persistent_token(self):
        cookies = self._get_cookies()
        if cookies is not None:
            try:
                return cookies.get("auth_token")
            except Exception:
                return None
        try:
            params = st.query_params or {}
            token = params.get('token')
            token = token[0] if isinstance(token, list) else token
            return token
        except Exception:
            return None

    def clear_persistent_token(self):
        cookies = self._get_cookies()
        if cookies is not None:
            try:
                if "auth_token" in cookies:
                    del cookies["auth_token"]
                    cookies.save()
            except Exception:
                pass
        try:
            st.query_params.clear()
        except Exception:
            pass

    def generate_access_code(self, length=6):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

    def send_access_code(self, user_email: str, access_code: str) -> bool:
        try:
            if MimeText and MimeMultipart:
                msg = MimeMultipart()
                msg['From'] = self.admin_email
                msg['To'] = user_email
                msg['Subject'] = "🔑 Código de acceso - Conversor Universal Profesional"
                body = f"""
                <html><body style=\"font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;\">
                    <div style=\"background-color: #1E88E5; color: white; padding: 20px; text-align: center;\"> <h1>🚀 Conversor Universal Profesional</h1> </div>
                    <div style=\"padding: 30px; background-color: #f8f9fa;\">
                        <h2 style=\"color: #1E88E5;\">¡Bienvenido!</h2>
                        <p style=\"font-size: 16px; line-height: 1.6;\">Has solicitado acceso al <strong>Conversor Universal Profesional</strong>.</p>
                        <div style=\"background-color: white; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0;\">
                            <h3 style=\"color: #333; margin-bottom: 10px;\">Tu código de acceso es:</h3>
                            <div style=\"font-size: 32px; font-weight: bold; color: #1E88E5; letter-spacing: 5px; font-family: monospace;\">{access_code}</div>
                            <p style=\"color: #666; margin-top: 15px; font-size: 14px;\">⏰ Este código expira en 10 minutos</p>
                        </div>
                        <div style=\"border-top: 1px solid #ddd; padding-top: 20px; margin-top: 30px;\">
                            <p style=\"color: #666; font-size: 14px;\"><strong>Desarrollador:</strong> Patricio Sarmiento Reinoso</p>
                        </div>
                    </div>
                </body></html>
                """
                msg.attach(MimeText(body, 'html'))
            else:
                msg = EmailMessage()
                msg['From'] = self.admin_email
                msg['To'] = user_email
                msg['Subject'] = "🔑 Código de acceso - Conversor Universal Profesional"
                body = f"""
🚀 CONVERSOR UNIVERSAL PROFESIONAL

Tu código de acceso es: {access_code}
⏰ Este código expira en 10 minutos
"""
                msg.set_content(body)
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.admin_email, self.admin_password)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            st.error(f"Error al enviar email: {str(e)}")
            return False

    def save_access_code(self, email, code) -> bool:
        try:
            if os.path.exists(self.codes_file):
                with open(self.codes_file, 'r', encoding='utf-8') as f:
                    codes = json.load(f)
            else:
                codes = {}
            codes[email] = {'code': code, 'timestamp': time.time(), 'used': False}
            with open(self.codes_file, 'w', encoding='utf-8') as f:
                json.dump(codes, f, indent=2)
            return True
        except Exception as e:
            st.error(f"Error al guardar código: {str(e)}")
            return False

    def verify_access_code(self, email, entered_code) -> bool:
        try:
            if not os.path.exists(self.codes_file):
                return False
            with open(self.codes_file, 'r', encoding='utf-8') as f:
                codes = json.load(f)
            if email not in codes:
                return False
            code_data = codes[email]
            if code_data['used']:
                return False
            if time.time() - code_data['timestamp'] > 600:
                return False
            if code_data['code'] == entered_code.upper():
                codes[email]['used'] = True
                with open(self.codes_file, 'w', encoding='utf-8') as f:
                    json.dump(codes, f, indent=2)
                self.authorize_user(email)
                return True
            return False
        except Exception as e:
            st.error(f"Error al verificar código: {str(e)}")
            return False

    def authorize_user(self, email) -> bool:
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    users = json.load(f)
            else:
                users = {}
            users[email] = {
                'authorized_at': time.time(),
                'last_access': time.time(),
                'session_count': users.get(email, {}).get('session_count', 0) + 1,
            }
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users, f, indent=2)
            return True
        except Exception as e:
            st.error(f"Error al autorizar usuario: {str(e)}")
            return False

    def is_user_authorized(self, email) -> bool:
        try:
            if not os.path.exists(self.users_file):
                return False
            with open(self.users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
            if email in users:
                users[email]['last_access'] = time.time()
                with open(self.users_file, 'w', encoding='utf-8') as f:
                    json.dump(users, f, indent=2)
                return True
            return False
        except Exception:
            return False

    def check_session_timeout(self, email):
        if 'auth_timestamp' not in st.session_state:
            return True
        return time.time() - st.session_state.auth_timestamp > self.session_timeout


def show_login_page():
    auth = AuthSystem()
    st.markdown(
        """
    <div style="text-align: center; padding: 40px;">
        <h1 style="color: #1E88E5; margin-bottom: 10px;">🔐 Acceso Restringido</h1>
        <h2 style="color: #333; margin-bottom: 30px;">Conversor Universal Profesional</h2>
        <p style="font-size: 18px; color: #666; margin-bottom: 40px;">Esta aplicación requiere autorización para su uso</p>
    </div>
    """,
        unsafe_allow_html=True,
    )
    tab1, tab2 = st.tabs(["📧 Solicitar Acceso", "🔑 Ingresar Código"])
    with tab1:
        st.markdown("### 📨 Solicitar código de acceso")
        st.info("💡 Introduce tu email para recibir un código de acceso temporal")
        email = st.text_input("📧 Email autorizado:", placeholder="usuario@gmail.com", help="Solo emails autorizados pueden solicitar acceso")
        if st.button("📤 Enviar código", type="primary", use_container_width=True):
            if email and "@" in email:
                if email.lower() in [e.lower().strip() for e in auth.authorized_emails]:
                    code = auth.generate_access_code()
                    with st.spinner("📤 Enviando código..."):
                        if auth.send_access_code(email, code) and auth.save_access_code(email, code):
                            st.success(f"✅ Código enviado a {email}")
                            st.info("📱 Revisa tu bandeja de entrada y spam. El código expira en 10 minutos.")
                        else:
                            st.error("❌ Error al enviar código. Contacta al administrador.")
                else:
                    st.error("❌ Email no autorizado. Contacta al administrador.")
            else:
                st.error("❌ Introduce un email válido")
    with tab2:
        st.markdown("### 🔐 Verificar código de acceso")
        st.info("💡 Introduce el código que recibiste por email")
        email_verify = st.text_input("📧 Email:", placeholder="usuario@gmail.com")
        access_code = st.text_input("🔑 Código de acceso:", placeholder="ABC123", max_chars=6, help="Código de 6 caracteres recibido por email")
        remember_device = st.checkbox("Recordar este dispositivo")
        if st.button("🚀 Acceder", type="primary", use_container_width=True):
            if email_verify and access_code:
                if auth.verify_access_code(email_verify, access_code):
                    st.session_state.authenticated = True
                    st.session_state.user_email = email_verify
                    st.session_state.auth_timestamp = time.time()
                    st.session_state.remember_device = remember_device
                    if remember_device:
                        try:
                            token = auth.create_device_token(email_verify)
                            st.session_state.device_token = token
                            if not auth.set_persistent_token(token):
                                st.query_params["token"] = token
                        except Exception:
                            pass
                    st.success("✅ ¡Acceso autorizado!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Código inválido o expirado")
            else:
                st.error("❌ Completa todos los campos")


def check_authentication():
    auth = AuthSystem()
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        try:
            token = auth.get_persistent_token()
            email_from_token = auth.validate_device_token(token)
            if email_from_token and auth.is_user_authorized(email_from_token):
                st.session_state.authenticated = True
                st.session_state.user_email = email_from_token
                st.session_state.auth_timestamp = time.time()
                st.session_state.remember_device = True
                st.session_state.device_token = token
                return True
        except Exception:
            pass
    if not st.session_state.authenticated:
        show_login_page()
        return False
    if 'user_email' in st.session_state:
        if auth.check_session_timeout(st.session_state.user_email):
            st.session_state.authenticated = False
            st.warning("⏰ Sesión expirada. Vuelve a autenticarte.")
            st.rerun()
            return False
    return True


def show_user_info():
    if 'user_email' in st.session_state:
        with st.sidebar:
            st.success(f"✅ Sesión activa: {st.session_state.user_email}")
            if st.button("🚪 Cerrar sesión"):
                try:
                    token = st.session_state.get('device_token')
                    AuthSystem().remove_device_token(token)
                    AuthSystem().clear_persistent_token()
                except Exception:
                    pass
                for key in ['authenticated', 'user_email', 'auth_timestamp', 'remember_device', 'device_token']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()


__all__ = [
    "AuthSystem",
    "show_login_page",
    "check_authentication",
    "show_user_info",
]
