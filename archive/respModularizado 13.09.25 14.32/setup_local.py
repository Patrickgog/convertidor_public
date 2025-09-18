# Script de setup para desarrollo local (modular)
# Ejecutar con: python setup_local.py

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
CONFIG = ROOT / "config"


def setup_local_auth():
    print("🚀 Configurando autenticación local...")
    DATA.mkdir(parents=True, exist_ok=True)
    CONFIG.mkdir(parents=True, exist_ok=True)

    test_users = {
        "test@gmail.com": {
            "authorized_at": 1694257200,
            "last_access": 1694257200,
            "session_count": 1,
            "manually_added": True,
        },
        "patricio@example.com": {
            "authorized_at": 1694257200,
            "last_access": 1694257200,
            "session_count": 5,
            "manually_added": True,
        },
    }

    (DATA / "authorized_users.json").write_text(json.dumps(test_users, indent=2), encoding="utf-8")
    print("✅ data/authorized_users.json creado")

    (DATA / "auth_codes.json").write_text(json.dumps({}, indent=2), encoding="utf-8")
    print("✅ data/auth_codes.json creado")

    secrets_content = """# Configuración local para desarrollo
# NO SUBIR A GITHUB

ADMIN_EMAIL = "tu_email@gmail.com"
ADMIN_PASSWORD = "tu_app_password_gmail"
AUTHORIZED_EMAILS = "test@gmail.com,patricio@example.com"
SESSION_TIMEOUT = 3600
MAX_DAILY_CODES = 5
"""
    (CONFIG / "secrets_local.toml").write_text(secrets_content, encoding="utf-8")
    print("✅ config/secrets_local.toml creado")

    print("\n📋 Para configurar correctamente:")
    print("1. Edita config/secrets_local.toml con tu email y app password de Gmail")
    print("2. Agrega emails autorizados en data/authorized_users.json")
    print("3. Ejecuta: streamlit run app.py")
    print("\n🔐 Para testing rápido, usa: test@gmail.com")


if __name__ == "__main__":
    setup_local_auth()
