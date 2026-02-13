"""
Panel de Administración - Conversor Universal Profesional
Autor: Patricio Sarmiento Reinoso
Uso: streamlit run admin_panel.py
"""

import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
import time

def load_users():
    """Carga usuarios autorizados"""
    if os.path.exists("authorized_users.json"):
        with open("authorized_users.json", 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def load_codes():
    """Carga códigos de acceso"""
    if os.path.exists("auth_codes.json"):
        with open("auth_codes.json", 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    """Guarda usuarios autorizados"""
    with open("authorized_users.json", 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2)

def format_timestamp(timestamp):
    """Formatea timestamp a fecha legible"""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

def main():
    st.set_page_config(
        page_title="Admin Panel - Conversor Universal", 
        layout="wide",
        page_icon="🛠️"
    )
    
    st.title("🛠️ Panel de Administración")
    st.markdown("**Conversor Universal Profesional**")
    
    # Contraseña de administrador
    admin_password = st.text_input("🔐 Contraseña de administrador:", type="password")
    
    if admin_password != "Admin2025!":  # Cambiar por tu contraseña segura
        st.error("❌ Contraseña incorrecta")
        return
    
    st.success("✅ Acceso autorizado")
    
    # Pestañas del panel
    tab1, tab2, tab3, tab4 = st.tabs([
        "👥 Usuarios Autorizados", 
        "🔑 Códigos de Acceso", 
        "➕ Gestión de Usuarios",
        "📊 Estadísticas"
    ])
    
    # ===== USUARIOS AUTORIZADOS =====
    with tab1:
        st.header("👥 Usuarios Autorizados")
        
        users = load_users()
        
        if users:
            # Convertir a DataFrame para mejor visualización
            user_data = []
            for email, data in users.items():
                user_data.append({
                    "Email": email,
                    "Autorizado": format_timestamp(data.get('authorized_at', 0)),
                    "Último Acceso": format_timestamp(data.get('last_access', 0)),
                    "Sesiones": data.get('session_count', 0)
                })
            
            df_users = pd.DataFrame(user_data)
            st.dataframe(df_users, use_container_width=True)
            
            # Opciones de gestión
            st.subheader("🛠️ Acciones")
            col1, col2 = st.columns(2)
            
            with col1:
                # Revocar acceso
                email_to_revoke = st.selectbox(
                    "Revocar acceso a:",
                    ["Seleccionar..."] + list(users.keys())
                )
                
                if st.button("🚫 Revocar Acceso") and email_to_revoke != "Seleccionar...":
                    del users[email_to_revoke]
                    save_users(users)
                    st.success(f"✅ Acceso revocado a {email_to_revoke}")
                    st.rerun()
            
            with col2:
                # Exportar lista
                if st.button("📥 Exportar Lista"):
                    csv = df_users.to_csv(index=False)
                    st.download_button(
                        "💾 Descargar CSV",
                        csv,
                        "usuarios_autorizados.csv",
                        "text/csv"
                    )
        else:
            st.info("📭 No hay usuarios autorizados registrados")
    
    # ===== CÓDIGOS DE ACCESO =====
    with tab2:
        st.header("🔑 Códigos de Acceso")
        
        codes = load_codes()
        
        if codes:
            code_data = []
            for email, data in codes.items():
                status = "✅ Usado" if data.get('used', False) else "⏳ Pendiente"
                time_left = 600 - (time.time() - data.get('timestamp', 0))
                
                if time_left <= 0:
                    status = "⏰ Expirado"
                    time_left_str = "Expirado"
                else:
                    time_left_str = f"{int(time_left/60)}:{int(time_left%60):02d}"
                
                code_data.append({
                    "Email": email,
                    "Código": data.get('code', ''),
                    "Creado": format_timestamp(data.get('timestamp', 0)),
                    "Estado": status,
                    "Tiempo Restante": time_left_str
                })
            
            df_codes = pd.DataFrame(code_data)
            st.dataframe(df_codes, use_container_width=True)
            
            # Limpiar códigos expirados
            if st.button("🧹 Limpiar Códigos Expirados"):
                current_time = time.time()
                clean_codes = {}
                
                for email, data in codes.items():
                    if not data.get('used', False) and (current_time - data.get('timestamp', 0)) < 600:
                        clean_codes[email] = data
                
                with open("auth_codes.json", 'w', encoding='utf-8') as f:
                    json.dump(clean_codes, f, indent=2)
                
                st.success("✅ Códigos expirados eliminados")
                st.rerun()
        else:
            st.info("📭 No hay códigos de acceso registrados")
    
    # ===== GESTIÓN DE USUARIOS =====
    with tab3:
        st.header("➕ Gestión de Usuarios")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("➕ Autorizar Nuevo Usuario")
            
            new_email = st.text_input("📧 Email del nuevo usuario:")
            
            if st.button("✅ Autorizar Usuario"):
                if new_email and "@" in new_email:
                    users = load_users()
                    
                    if new_email not in users:
                        users[new_email] = {
                            'authorized_at': time.time(),
                            'last_access': 0,
                            'session_count': 0,
                            'manually_added': True
                        }
                        save_users(users)
                        st.success(f"✅ Usuario {new_email} autorizado")
                    else:
                        st.warning("⚠️ Usuario ya autorizado")
                else:
                    st.error("❌ Email inválido")
        
        with col2:
            st.subheader("📋 Autorización Masiva")
            
            bulk_emails = st.text_area(
                "📧 Emails (uno por línea):",
                placeholder="usuario1@gmail.com\nusuario2@hotmail.com\nusuario3@empresa.com"
            )
            
            if st.button("✅ Autorizar Todos"):
                if bulk_emails:
                    users = load_users()
                    emails_list = [email.strip() for email in bulk_emails.split('\n') if email.strip()]
                    added = 0
                    
                    for email in emails_list:
                        if "@" in email and email not in users:
                            users[email] = {
                                'authorized_at': time.time(),
                                'last_access': 0,
                                'session_count': 0,
                                'manually_added': True
                            }
                            added += 1
                    
                    save_users(users)
                    st.success(f"✅ {added} usuarios autorizados")
    
    # ===== ESTADÍSTICAS =====
    with tab4:
        st.header("📊 Estadísticas de Uso")
        
        users = load_users()
        codes = load_codes()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("👥 Usuarios Totales", len(users))
        
        with col2:
            active_users = len([u for u in users.values() if u.get('last_access', 0) > time.time() - 86400])
            st.metric("🟢 Activos (24h)", active_users)
        
        with col3:
            pending_codes = len([c for c in codes.values() if not c.get('used', False)])
            st.metric("🔑 Códigos Pendientes", pending_codes)
        
        with col4:
            total_sessions = sum([u.get('session_count', 0) for u in users.values()])
            st.metric("📈 Sesiones Totales", total_sessions)
        
        # Gráfico de actividad
        if users:
            st.subheader("📅 Actividad Reciente")
            
            # Últimos accesos
            recent_activity = []
            for email, data in users.items():
                if data.get('last_access', 0) > 0:
                    recent_activity.append({
                        'Usuario': email,
                        'Último Acceso': format_timestamp(data.get('last_access', 0)),
                        'Sesiones': data.get('session_count', 0)
                    })
            
            if recent_activity:
                df_activity = pd.DataFrame(recent_activity)
                st.dataframe(df_activity, use_container_width=True)
            else:
                st.info("📭 No hay actividad reciente registrada")

if __name__ == "__main__":
    main()
