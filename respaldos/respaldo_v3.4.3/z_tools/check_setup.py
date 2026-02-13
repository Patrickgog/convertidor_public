"""
Script de verificación rápida para el desarrollador
Ejecutar con: python check_setup.py
"""

import os
import sys
import subprocess
import json

def print_status(message, status="info"):
    """Imprime mensaje con estado coloreado"""
    colors = {
        "success": "✅",
        "error": "❌", 
        "warning": "⚠️",
        "info": "ℹ️"
    }
    print(f"{colors.get(status, 'ℹ️')} {message}")

def check_python_version():
    """Verifica versión de Python"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print_status(f"Python {version.major}.{version.minor}.{version.micro} ✓", "success")
        return True
    else:
        print_status(f"Python {version.major}.{version.minor} - Se recomienda 3.8+", "warning")
        return False

def check_required_files():
    """Verifica archivos esenciales"""
    required_files = [
        "app.py",
        "auth_simple.py", 
        "auth_system.py",
        "requirements.txt",
        "switch_auth.py",
        "setup_local.py"
    ]
    
    missing = []
    for file in required_files:
        if os.path.exists(file):
            print_status(f"{file} encontrado", "success")
        else:
            print_status(f"{file} FALTANTE", "error")
            missing.append(file)
    
    return len(missing) == 0

def check_dependencies():
    """Verifica dependencias instaladas"""
    try:
        import streamlit
        print_status(f"Streamlit {streamlit.__version__} instalado", "success")
    except ImportError:
        print_status("Streamlit NO instalado", "error")
        return False
    
    required_modules = [
        "folium", "ezdxf", "shapely", "pyproj", 
        "gpxpy", "fastkml", "simplekml", "pandas"
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
            print_status(f"{module} ✓", "success")
        except ImportError:
            print_status(f"{module} FALTANTE", "error")
            missing.append(module)
    
    return len(missing) == 0

def check_auth_setup():
    """Verifica configuración de autenticación"""
    if os.path.exists("authorized_users.json"):
        print_status("authorized_users.json encontrado", "success")
        try:
            with open("authorized_users.json", 'r') as f:
                users = json.load(f)
                print_status(f"{len(users)} usuarios autorizados", "info")
        except:
            print_status("Error leyendo authorized_users.json", "error")
    else:
        print_status("authorized_users.json NO encontrado", "warning")
        print_status("Ejecutar: python setup_local.py", "info")
    
    if os.path.exists("secrets_local.toml"):
        print_status("secrets_local.toml encontrado", "success")
    else:
        print_status("secrets_local.toml NO encontrado", "warning")

def check_auth_mode():
    """Verifica modo de autenticación actual"""
    try:
        with open("app.py", 'r', encoding='utf-8') as f:
            content = f.read()
            
        if "auth_simple" in content and "check_simple_authentication" in content:
            print_status("Modo: SIMPLIFICADO (sin email) - Recomendado para desarrollo", "success")
            return "simple"
        elif "auth_system" in content and "from auth_system import" in content:
            print_status("Modo: COMPLETO (con email) - Para producción", "info")
            return "complete"
        else:
            print_status("Modo de autenticación no determinado", "warning")
            return "unknown"
    except FileNotFoundError:
        print_status("app.py no encontrado", "error")
        return "error"

def test_compilation():
    """Prueba compilación de archivos principales"""
    files_to_test = ["app.py", "auth_simple.py", "auth_system.py"]
    
    for file in files_to_test:
        if os.path.exists(file):
            try:
                result = subprocess.run([
                    sys.executable, "-m", "py_compile", file
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    print_status(f"{file} compila correctamente", "success")
                else:
                    print_status(f"{file} ERROR de compilación", "error")
                    print(f"   Error: {result.stderr}")
            except Exception as e:
                print_status(f"{file} Error al compilar: {e}", "error")

def show_next_steps(auth_mode):
    """Muestra próximos pasos según configuración"""
    print("\n" + "="*50)
    print("🚀 PRÓXIMOS PASOS:")
    print("="*50)
    
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
        print("   1. secrets_local.toml con Gmail App Password")
        print("   2. Lista de emails autorizados")
        print("   3. Probar envío de códigos")
        
    print("\n🌐 Para deploy en Streamlit Cloud:")
    print("   1. Subir a GitHub")
    print("   2. Conectar en share.streamlit.io")
    print("   3. Configurar secretos")
    
    print("\n📞 Soporte: WhatsApp +593995959047")

def main():
    print("🔍 VERIFICACIÓN DE CONFIGURACIÓN")
    try:
        from src.core.config.settings import APP_VERSION
        print(f"Conversor Universal Profesional {APP_VERSION}")
    except ImportError:
        print("Conversor Universal Profesional v3.0")
    print("="*50)
    
    # Verificaciones
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
    
    # Resumen
    print("\n" + "="*50)
    print("📊 RESUMEN:")
    print("="*50)
    
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
