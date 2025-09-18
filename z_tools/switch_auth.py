"""
Script para cambiar entre sistemas de autenticación
Uso: python switch_auth.py [simple|complete]
"""

import sys
import os

def switch_auth_system(mode):
    """Cambia entre sistema de autenticación simple y completo"""
    
    app_file = "app.py"
    
    if not os.path.exists(app_file):
        print("❌ Error: app.py no encontrado")
        return False
    
    # Leer contenido actual
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if mode == "simple":
        # Cambiar a sistema simplificado
        old_import = """# Sistema de autenticación (cambiar entre simple/completo según necesidad)
try:
    # Intentar sistema completo primero
    from auth_system import check_authentication, show_user_info
    AUTH_MODE = "complete"
except ImportError:
    # Fallback a sistema simplificado si hay problemas con email
    from auth_simple import check_simple_authentication as check_authentication, show_simple_user_info as show_user_info
    AUTH_MODE = "simple"
    print("🔧 Usando sistema de autenticación simplificado (sin email)")"""
        
        new_import = """# Sistema de autenticación simplificado (sin email)
from auth_simple import check_simple_authentication as check_authentication, show_simple_user_info as show_user_info
AUTH_MODE = "simple"
print("🔧 Modo desarrollo: Autenticación simplificada activa")"""
        
        content = content.replace(old_import, new_import)
        print("✅ Cambiado a sistema de autenticación SIMPLIFICADO")
        print("📝 Códigos de prueba:")
        print("   - test@gmail.com → TEST01")
        print("   - patricio@example.com → DEMO02")
        print("   - admin@conversor.com → ADMIN3")
        
    elif mode == "complete":
        # Cambiar a sistema completo
        old_import = """# Sistema de autenticación simplificado (sin email)
from auth_simple import check_simple_authentication as check_authentication, show_simple_user_info as show_user_info
AUTH_MODE = "simple"
print("🔧 Modo desarrollo: Autenticación simplificada activa")"""
        
        new_import = """# Sistema de autenticación completo (con email)
from auth_system import check_authentication, show_user_info
AUTH_MODE = "complete"
print("🔧 Sistema de autenticación completo activo")"""
        
        content = content.replace(old_import, new_import)
        print("✅ Cambiado a sistema de autenticación COMPLETO")
        print("📧 Requiere configuración de Gmail:")
        print("   1. Editar secrets_local.toml")
        print("   2. Configurar App Password de Gmail")
        print("   3. Definir emails autorizados")
        
    else:
        print("❌ Modo inválido. Usar: simple | complete")
        return False
    
    # Guardar cambios
    with open(app_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def show_current_mode():
    """Muestra el modo actual de autenticación"""
    try:
        with open("app.py", 'r', encoding='utf-8') as f:
            content = f.read()
            
        if "auth_simple" in content:
            print("🔧 Modo actual: SIMPLIFICADO (sin email)")
            print("📝 Códigos de prueba disponibles")
        elif "auth_system" in content:
            print("🔧 Modo actual: COMPLETO (con email)")
            print("📧 Requiere configuración de Gmail")
        else:
            print("❓ Modo no determinado")
            
    except FileNotFoundError:
        print("❌ app.py no encontrado")

def main():
    print("🔄 Gestión de sistemas de autenticación")
    print("=" * 40)
    
    if len(sys.argv) == 1:
        show_current_mode()
        print("\n📋 Uso:")
        print("  python switch_auth.py simple    # Usar códigos predeterminados")
        print("  python switch_auth.py complete  # Usar envío por email")
        return
    
    mode = sys.argv[1].lower()
    
    if switch_auth_system(mode):
        print(f"\n🚀 Para aplicar cambios, ejecuta: streamlit run app.py")
    else:
        print("❌ Error al cambiar modo de autenticación")

if __name__ == "__main__":
    main()
