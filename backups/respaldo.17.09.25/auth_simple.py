"""
Sistema de autenticación simplificado - Solo para desarrollo local
Sin dependencias de email - códigos predeterminados
Autor: Patricio Sarmiento Reinoso
"""

import streamlit as st
import json
import os
import time
from datetime import datetime
import uuid
import hashlib

try:
    from streamlit_cookies_manager import EncryptedCookieManager  # type: ignore
except Exception:
    EncryptedCookieManager = None  # type: ignore

class SimpleAuthSystem:
    def __init__(self):
        self.users_file = "authorized_users.json"
        self.session_timeout = 3600  # 1 hora
        self.devices_file = "remembered_devices.json"
        self._cookies = None
        
        # Códigos predeterminados para testing
        self.test_codes = {
            "test@gmail.com": "TEST01",
            "patricio@example.com": "DEMO02", 
            "admin@conversor.com": "ADMIN3"
        }
        
        # Lista de emails autorizados
        self.authorized_emails = [
            "test@gmail.com",
            "patricio@example.com", 
            "admin@conversor.com",
            "demo@empresa.com"
        ]

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

    def validate_device_token(self, token):
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

    def remove_device_token(self, token):
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
    
    def verify_access_code(self, email, entered_code):
        """Verifica código de acceso (códigos predeterminados para testing)"""
        try:
            # Verificar código predeterminado
            if email in self.test_codes:
                if self.test_codes[email] == entered_code.upper():
                    self.authorize_user(email)
                    return True
            
            return False
            
        except Exception as e:
            st.error(f"Error al verificar código: {str(e)}")
            return False
    
    def authorize_user(self, email):
        """Agrega usuario a lista de autorizados"""
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    users = json.load(f)
            else:
                users = {}
            
            users[email] = {
                'authorized_at': time.time(),
                'last_access': time.time(),
                'session_count': users.get(email, {}).get('session_count', 0) + 1
            }
            
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users, f, indent=2)
                
            return True
            
        except Exception as e:
            st.error(f"Error al autorizar usuario: {str(e)}")
            return False
    
    def check_session_timeout(self, email):
        """Verifica timeout de sesión"""
        if 'auth_timestamp' not in st.session_state:
            return True
            
        return time.time() - st.session_state.auth_timestamp > self.session_timeout

def show_simple_login():
    """Muestra página de autenticación simplificada"""
    auth = SimpleAuthSystem()
    
    st.markdown("""
    <div style="text-align: center; padding: 40px;">
        <h1 style="color: #1E88E5; margin-bottom: 10px;">🔐 Acceso Restringido</h1>
        <h2 style="color: #333; margin-bottom: 30px;">Conversor Universal Profesional</h2>
        <p style="font-size: 18px; color: #666; margin-bottom: 40px;">
            Versión de desarrollo - Códigos predeterminados
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Mostrar códigos de testing
    with st.expander("📋 Códigos de testing disponibles", expanded=True):
        st.markdown("""
        **Usuarios de prueba:**
        - **test@gmail.com** → Código: `TEST01`
        - **patricio@example.com** → Código: `DEMO02`
        - **admin@conversor.com** → Código: `ADMIN3`
        
        💡 *Para producción, reemplazar con sistema de email completo*
        """)
    
    st.markdown("### 🔐 Acceso al sistema")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        email = st.text_input(
            "📧 Email autorizado:",
            placeholder="test@gmail.com",
            help="Usar uno de los emails de prueba mostrados arriba"
        )
    
    with col2:
        access_code = st.text_input(
            "🔑 Código de acceso:",
            placeholder="TEST01",
            max_chars=6,
            help="Código correspondiente al email"
        )
    
    if st.button("🚀 Acceder", type="primary", use_container_width=True):
        if email and access_code:
            if email.lower() in [e.lower() for e in auth.authorized_emails]:
                if auth.verify_access_code(email, access_code):
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.auth_timestamp = time.time()
                    # Recordar dispositivo (modo simple): crear token en URL
                    try:
                        token = auth.create_device_token(email)
                        st.session_state.device_token = token
                        if not auth.set_persistent_token(token):
                            st.query_params["token"] = token
                    except Exception:
                        pass
                    st.success("✅ ¡Acceso autorizado!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Código inválido")
            else:
                st.error("❌ Email no autorizado")
        else:
            st.error("❌ Completa todos los campos")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 20px; color: #666;">
        <p><strong>Desarrollador:</strong> Patricio Sarmiento Reinoso</p>
        <p><strong>WhatsApp:</strong> +593995959047</p>
        <p><strong>Versión:</strong> Desarrollo/Testing</p>
    </div>
    """, unsafe_allow_html=True)

def check_simple_authentication():
    """Verifica autenticación simplificada"""
    # Verificar si está autenticado
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    # Auto-login con token de query params si existe
    if not st.session_state.authenticated:
        try:
            token = SimpleAuthSystem().get_persistent_token()
            email_from_token = SimpleAuthSystem().validate_device_token(token)
            if email_from_token:
                st.session_state.authenticated = True
                st.session_state.user_email = email_from_token
                st.session_state.auth_timestamp = time.time()
                return True
        except Exception:
            pass

    if not st.session_state.authenticated:
        show_simple_login()
        return False
    
    # Verificar timeout de sesión
    auth = SimpleAuthSystem()
    if 'user_email' in st.session_state:
        if auth.check_session_timeout(st.session_state.user_email):
            st.session_state.authenticated = False
            st.warning("⏰ Sesión expirada. Vuelve a autenticarte.")
            st.rerun()
            return False
    
    return True

def show_simple_user_info():
    """Muestra información del usuario autenticado"""
    if 'user_email' in st.session_state:
        with st.sidebar:
            st.success(f"✅ Sesión activa: {st.session_state.user_email}")
            st.caption("🧪 Modo desarrollo")
            if st.button("🚪 Cerrar sesión"):
                try:
                    token = st.session_state.get('device_token')
                    SimpleAuthSystem().remove_device_token(token)
                    SimpleAuthSystem().clear_persistent_token()
                except Exception:
                    pass
                for key in ['authenticated', 'user_email', 'auth_timestamp', 'device_token']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
