"""
Script de verificación rápida para el desarrollador (modular)
Ejecutar con: python check_setup.py
"""

import os
import sys
import subprocess
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
CONFIG = ROOT / "config"


def print_status(message, status="info"):
    icons = {"success": "✅", "error": "❌", "warning": "⚠️", "info": "ℹ️"}
    print(f"{icons.get(status, 'ℹ️')} {message}")


def check_python_version():
    v = sys.version_info
    if v.major == 3 and v.minor >= 8:
        print_status(f"Python {v.major}.{v.minor}.{v.micro} ✓", "success")
        return True
    print_status(f"Python {v.major}.{v.minor} - Se recomienda 3.8+", "warning")
    return False


def check_required_files():
    required = [
        "app.py",
        str(ROOT / "app_pkg" / "ui" / "layout.py"),
        str(ROOT / "app_pkg" / "core" / "geojson_utils.py"),
        str(ROOT / "app_pkg" / "export" / "html_templates.py"),
        "requirements.txt",
        "switch_auth.py",
        "setup_local.py",
    ]
    missing = []
    for f in required:
        if os.path.exists(f):
            print_status(f"{f} encontrado", "success")
        else:
            print_status(f"{f} FALTANTE", "error")
            missing.append(f)
    return len(missing) == 0


def check_dependencies():
    try:
        import streamlit  # noqa: F401
        print_status("Streamlit instalado", "success")
    except ImportError:
        print_status("Streamlit NO instalado", "error")
        return False
    for module in ["folium", "ezdxf", "shapely", "pyproj", "gpxpy", "fastkml", "simplekml", "pandas"]:
        try:
            __import__(module)
            print_status(f"{module} ✓", "success")
        except ImportError:
            print_status(f"{module} FALTANTE", "warning")
    return True


def check_auth_setup():
    if (DATA / "authorized_users.json").exists():
        print_status("data/authorized_users.json encontrado", "success")
        try:
            users = json.loads((DATA / "authorized_users.json").read_text(encoding="utf-8"))
            print_status(f"{len(users)} usuarios autorizados", "info")
        except Exception:
            print_status("Error leyendo authorized_users.json", "error")
    else:
        print_status("data/authorized_users.json NO encontrado", "warning")
        print_status("Ejecutar: python setup_local.py", "info")

    if (CONFIG / "secrets_local.toml").exists():
        print_status("config/secrets_local.toml encontrado", "success")
    else:
        print_status("config/secrets_local.toml NO encontrado", "warning")


def check_auth_mode():
    try:
        mode_file = CONFIG / "auth_mode.txt"
        if mode_file.exists():
            mode = mode_file.read_text(encoding="utf-8").strip().lower()
            if mode == "simple":
                print_status("Modo: SIMPLIFICADO (preferencia configurada)", "success")
                return "simple"
            if mode == "complete":
                print_status("Modo: COMPLETO (preferencia configurada)", "info")
                return "complete"
        # fallback por contenido de app.py
        content = (ROOT / "app.py").read_text(encoding="utf-8")
        if "app_pkg.auth.simple" in content:
            print_status("Modo: SIMPLIFICADO (por fallback de import)", "success")
            return "simple"
        print_status("Modo: COMPLETO (por fallback de import)", "info")
        return "complete"
    except Exception:
        print_status("Modo de autenticación no determinado", "warning")
        return "unknown"


def test_compilation():
    for file in ["app.py", str(ROOT / "app_pkg" / "auth" / "simple.py"), str(ROOT / "app_pkg" / "auth" / "system.py")]:
        if os.path.exists(file):
            try:
                result = subprocess.run([sys.executable, "-m", "py_compile", file], capture_output=True, text=True)
                if result.returncode == 0:
                    print_status(f"{file} compila correctamente", "success")
                else:
                    print_status(f"{file} ERROR de compilación", "error")
                    print(f"   Error: {result.stderr}")
            except Exception as e:
                print_status(f"{file} Error al compilar: {e}", "error")


def show_next_steps(auth_mode):
    print("\n" + "=" * 50)
    print("🚀 PRÓXIMOS PASOS:")
    print("=" * 50)
    if auth_mode == "simple":
        print("✅ Configuración para DESARROLLO lista")
        print("\n📋 Para probar la aplicación:")
        print("   streamlit run app.py")
        print("\n🔑 Códigos de prueba:")
        print("   test@gmail.com → TEST01")
        print("   patricio@example.com → DEMO02")
        print("   admin@conversor.com → ADMIN3")
    elif auth_mode == "complete":
        print("⚙️ Configuración para PRODUCCIÓN")
        print("\n📧 Asegúrate de configurar:")
        print("   1. config/secrets_local.toml con Gmail App Password")
        print("   2. Lista de emails autorizados en data/authorized_users.json")
        print("   3. Probar envío de códigos")
    print("\n🌐 Para deploy en Streamlit Cloud:")
    print("   1. Subir a GitHub")
    print("   2. Conectar en share.streamlit.io")
    print("   3. Configurar secretos")
    print("\n📞 Soporte: WhatsApp +593995959047")


def main():
    print("🔍 VERIFICACIÓN DE CONFIGURACIÓN (modular)")
    print("Conversor Universal Profesional v3.0")
    print("=" * 50)
    print("\n📋 Verificando entorno...")
    python_ok = check_python_version()
    print("\n📁 Verificando archivos...")
    files_ok = check_required_files()
    print("\n📦 Verificando dependencias...")
    deps_ok = check_dependencies()
    print("\n🔐 Verificando autenticación...")
    check_auth_setup()
    auth_mode = check_auth_mode()
    print("\n🔧 Probando compilación...")
    test_compilation()
    print("\n" + "=" * 50)
    print("📊 RESUMEN:")
    print("=" * 50)
    if python_ok and files_ok and deps_ok:
        print_status("Configuración básica: COMPLETA", "success")
    else:
        print_status("Configuración básica: INCOMPLETA", "error")
        if not deps_ok:
            print_status("Ejecutar: pip install -r requirements.txt", "info")
        if not files_ok:
            print_status("Verificar archivos faltantes", "info")
    show_next_steps(auth_mode)


if __name__ == "__main__":
    main()
