"""
Script de cambio de modo de autenticación
Uso:
  python switch_auth.py simple
  python switch_auth.py complete

Este script escribe config/auth_mode.txt con el modo deseado y no modifica app.py.
app.py leerá este archivo para preferir el sistema de autenticación indicado.
"""

import sys
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent / "config"
MODE_FILE = CONFIG_DIR / "auth_mode.txt"


def show_current_mode() -> None:
    if MODE_FILE.exists():
        mode = MODE_FILE.read_text(encoding="utf-8").strip().lower()
        if mode in ("simple", "complete"):
            print(f"🔧 Modo actual: {mode.upper()}")
            return
    print("❓ Modo no establecido (se usará autodetección por imports)")


def switch_mode(mode: str) -> bool:
    mode = mode.strip().lower()
    if mode not in ("simple", "complete"):
        print("❌ Modo inválido. Usar: simple | complete")
        return False
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    MODE_FILE.write_text(mode, encoding="utf-8")
    print(f"✅ Modo de autenticación establecido a: {mode.upper()}")
    print("ℹ️ Reinicia la app si está ejecutándose: streamlit run app.py")
    return True


def main() -> None:
    print("🔄 Gestión de sistemas de autenticación")
    print("=" * 40)

    if len(sys.argv) == 1:
        show_current_mode()
        print("\n📋 Uso:")
        print("  python switch_auth.py simple")
        print("  python switch_auth.py complete")
        return

    if switch_mode(sys.argv[1]):
        print("\n🚀 Para aplicar cambios, ejecuta: streamlit run app.py")
    else:
        print("❌ Error al cambiar modo de autenticación")


if __name__ == "__main__":
    main()
