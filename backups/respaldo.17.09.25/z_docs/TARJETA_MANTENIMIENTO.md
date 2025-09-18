### Tarjeta de Mantenimiento – Autenticación y Acceso

- **Modo de autenticación**
  - Import conmutado en `app.py`: intenta `auth_system` (email/códigos) y si falla usa `auth_simple` (testing).
  - Forzado en tiempo de ejecución: `check_authentication()` al inicio y `show_user_info()` en el sidebar.

- **Secretos requeridos (producción)**
  - En `secrets` (Cloud) o `secrets_local.toml` (local):
    - `ADMIN_EMAIL`: Gmail del emisor.
    - `ADMIN_PASSWORD`: App Password de Gmail (no la clave normal).
    - `AUTHORIZED_EMAILS`: Lista separada por comas de correos autorizados.
    - `COOKIE_PASSWORD` (recomendado): clave larga para cifrar cookies.
    - Opcionales: `SESSION_TIMEOUT`, `MAX_DAILY_CODES` (si se usan).

- **Archivos de estado**
  - `authorized_users.json`: Usuarios autorizados y métricas básicas.
  - `auth_codes.json`: Códigos de acceso temporales (expiran a 10 min).
  - `remembered_devices.json`: Tokens de “Recordar este dispositivo”.

- **Recordar este dispositivo (persistencia)**
  - Preferencia: cookie cifrada (`auth_token`) vía `EncryptedCookieManager`.
  - Fallback: query param `?token=...` si cookies no están disponibles.
  - Vigencia por defecto: 30 días.
  - Logout limpia cookie y tokens; también elimina query params.

- **Dependencias clave**
  - App: `streamlit`, `folium`, `streamlit-folium`, `ezdxf`, `simplekml`, `shapely`, `pyproj`, `pyshp`, `gpxpy`, `fastkml`, `pandas`.
  - Cookies (opcional): `streamlit-cookies-manager`.

- **Flujos rápidos**
  - Desarrollo (sin email):
    - `python switch_auth.py simple`
    - `streamlit run app.py`
    - Usar códigos de prueba definidos en `auth_simple.py`.
  - Producción (con email):
    - Configurar `secrets` (ADMIN_EMAIL / ADMIN_PASSWORD / AUTHORIZED_EMAILS / COOKIE_PASSWORD).
    - `python switch_auth.py complete`
    - `streamlit run app.py`

- **Verificación y diagnóstico**
  - Chequeo general: `python check_setup.py`
  - Instalar dependencias: `pip install -r requirements.txt`
  - (Opcional cookies) `pip install streamlit-cookies-manager`
  - Cambiar modo auth: `python switch_auth.py simple` | `python switch_auth.py complete`

- **Administración**
  - Panel admin: `streamlit run admin_panel.py` (revocar/autorizar usuarios, ver códigos/estadísticas).
  - Gestión de emails/nombres (GUI): `gestor_emails.py` (actualiza `authorized_users.json`, `authorized_names.json` y `secrets_local.toml`).

- **Buenas prácticas de seguridad**
  - Usar App Password de Gmail con 2FA.
  - Definir `COOKIE_PASSWORD` en secretos para cifrar cookies.
  - Evitar compartir URLs con `?token=...` (fallback visible).
  - Limpiar usuarios/tokens obsoletos periódicamente (panel admin o borrado de `remembered_devices.json`).

- **Ubicaciones clave**
  - Autenticación completa: `auth_system.py`
  - Autenticación simple (dev): `auth_simple.py`
  - App principal: `app.py`
  - Panel administración: `admin_panel.py`
  - Utilidades: `switch_auth.py`, `check_setup.py`, `setup_local.py`
