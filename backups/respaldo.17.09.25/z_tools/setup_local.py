# Script de setup para desarrollo local
# Ejecutar con: python setup_local.py

import json
import os

def setup_local_auth():
    """Configura autenticación para desarrollo local"""
    
    print("🚀 Configurando autenticación local...")
    
    # Crear archivo de usuarios autorizados de prueba
    test_users = {
        "test@gmail.com": {
            "authorized_at": 1694257200,  # Timestamp de prueba
            "last_access": 1694257200,
            "session_count": 1,
            "manually_added": True
        },
        "patricio@example.com": {
            "authorized_at": 1694257200,
            "last_access": 1694257200, 
            "session_count": 5,
            "manually_added": True
        }
    }
    
    with open("authorized_users.json", "w", encoding="utf-8") as f:
        json.dump(test_users, f, indent=2)
    
    print("✅ Archivo authorized_users.json creado")
    
    # Crear archivo de códigos vacío
    with open("auth_codes.json", "w", encoding="utf-8") as f:
        json.dump({}, f, indent=2)
    
    print("✅ Archivo auth_codes.json creado")
    
    # Crear archivo de secrets local
    secrets_content = """# Configuración local para desarrollo
# NO SUBIR A GITHUB

ADMIN_EMAIL = "tu_email@gmail.com"
ADMIN_PASSWORD = "tu_app_password_gmail"
AUTHORIZED_EMAILS = "test@gmail.com,patricio@example.com"
SESSION_TIMEOUT = 3600
MAX_DAILY_CODES = 5
"""
    
    with open("secrets_local.toml", "w", encoding="utf-8") as f:
        f.write(secrets_content)
    
    print("✅ Archivo secrets_local.toml creado")
    
    print("\n📋 Para configurar correctamente:")
    print("1. Edita secrets_local.toml con tu email y app password de Gmail")
    print("2. Agrega emails autorizados en authorized_users.json")
    print("3. Ejecuta: streamlit run app.py")
    print("\n🔐 Para testing rápido, usa: test@gmail.com")

if __name__ == "__main__":
    setup_local_auth()
