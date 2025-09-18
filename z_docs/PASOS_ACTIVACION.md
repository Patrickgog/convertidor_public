# Paso a paso para activar y usar la app

## 1. Instalar dependencias en Python 3.11

Si necesitas instalar dependencias extra:
```powershell
py -3.11 -m pip install -r requirements.txt
py -3.11 -m pip install streamlit-folium
```

---

## 2. Configurar autenticación para desarrollo (códigos predeterminados)

1. Ejecuta la configuración local:
   ```powershell
   py -3.11 setup_local.py
   py -3.11 switch_auth.py simple
   ```
2. Inicia la app:
   ```powershell
   py -3.11 -m streamlit run app.py
   ```
3. Accede en el navegador a `http://localhost:8501`.
4. Usa estos datos de prueba para ingresar:
   - Email: `test@gmail.com` → Código: `TEST01`
   - Email: `patricio@example.com` → Código: `DEMO02`
   - Email: `admin@conversor.com` → Código: `ADMIN3`

---

## 3. Activar autenticación por email (modo producción)

1. Configura Gmail App Password:
   - Activa verificación en 2 pasos en tu cuenta de Gmail.
   - Genera una contraseña de aplicación (16 caracteres).
2. Edita el archivo `secrets_local.toml` con tu email, app password y lista de emails autorizados.
3. Cambia a modo completo:
   ```powershell
   py -3.11 switch_auth.py complete
   ```
4. Inicia la app:
   ```powershell
   py -3.11 -m streamlit run app.py
   ```
5. Flujo de acceso:
   - El usuario autorizado solicita un código ingresando su email.
   - El sistema envía el código por email.
   - El usuario ingresa el código recibido para acceder.

---

## 4. Gestión de usuarios

- Para agregar o revocar usuarios, usa el panel de administración:
  ```powershell
  py -3.11 -m streamlit run admin_panel.py
  ```
  - Password: `Admin2025!`

---

¿Quieres el paso a paso para deploy en la nube (Streamlit Cloud, Heroku, etc.)? ¿O necesitas ayuda con la gestión de usuarios?
