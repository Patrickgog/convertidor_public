# Pasos para desarrollador: Autenticación por email

## ¿Para qué sirve cada script?

| Script                | Función principal                                                                 |
|-----------------------|---------------------------------------------------------------------------------|
| `setup_local.py`      | Crea archivos de configuración y usuarios de prueba para desarrollo local         |
| `switch_auth.py`      | Cambia entre modo simplificado (sin email) y completo (con email)                |
| `admin_panel.py`      | Panel web para gestionar usuarios autorizados y ver estadísticas                 |
| `gestor_emails.py`    | Interfaz gráfica para agregar, modificar o eliminar emails en `secrets_local.toml`|
| `app.py`              | Aplicación principal con autenticación y conversión de archivos geoespaciales    |
| `auth_simple.py`      | Sistema de autenticación simplificado (sin email, solo para desarrollo)          |
| `auth_system.py`      | Sistema de autenticación completo (envío de códigos por email)                   |

---

## Paso a paso para usar la autenticación

1. **Configura dependencias**
   ```powershell
   py -3.11 -m pip install -r requirements.txt
   py -3.11 -m pip install streamlit-folium
   ```

2. **Configura autenticación local (desarrollo)**
   ```powershell
   py -3.11 setup_local.py
   py -3.11 switch_auth.py simple
   py -3.11 -m streamlit run app.py
   ```
   - Usa los códigos de prueba para acceder.

3. **Configura autenticación por email (producción)**
   - Edita `secrets_local.toml` con tu email, app password y lista de emails autorizados.
   - Usa `gestor_emails.py` para gestionar emails fácilmente.
   ```powershell
   py -3.11 switch_auth.py complete
   py -3.11 -m streamlit run app.py
   ```
   - El usuario solicita código y lo ingresa para acceder.

4. **Gestiona usuarios**
   - Usa `admin_panel.py` para gestión avanzada y estadísticas.
   - Usa `gestor_emails.py` para editar emails autorizados.

---

## Recomendaciones
- Mantén `secrets_local.toml` actualizado.
- Usa el gestor gráfico para evitar errores manuales.
- Aplica estos pasos en cualquier app que requiera autenticación por email.
