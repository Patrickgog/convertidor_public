
# Nueva versión con layout más grande, emails listados con botón de borrado, y botón de recarga

# Nueva versión: muestra emails y fecha de autorización desde authorized_users.json, título personalizado
import tkinter as tk
from tkinter import messagebox, simpledialog
import re
import os
import json
from datetime import datetime

TOML_PATH = "secrets_local.toml"
USERS_PATH = "authorized_users.json"


# Lee emails y fechas desde authorized_users.json
def read_authorized_emails():
    if not os.path.exists(USERS_PATH):
        return []
    with open(USERS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    result = []
    for email, info in data.items():
        ts = info.get("authorized_at", 0)
        fecha = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "-"
        result.append((email, fecha))
    return result

# Lee nombres desde archivo adicional
def read_names():
    path = "authorized_names.json"
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# Guarda nombres en archivo adicional
def write_names(names_dict):
    path = "authorized_names.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(names_dict, f, indent=2)

def write_authorized_emails(emails):
    # Actualiza authorized_users.json y secrets_local.toml
    # Mantiene la fecha original si existe, si no, pone la actual
    orig = {}
    if os.path.exists(USERS_PATH):
        with open(USERS_PATH, "r", encoding="utf-8") as f:
            orig = json.load(f)
    new_data = {}
    now = datetime.now().timestamp()
    for email in emails:
        if email in orig:
            new_data[email] = orig[email]
        else:
            new_data[email] = {"authorized_at": now, "last_access": 0, "session_count": 0, "manually_added": True}
    with open(USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(new_data, f, indent=2)
    # Actualiza secrets_local.toml
    if os.path.exists(TOML_PATH):
        with open(TOML_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        new_emails = ",".join(emails)
        new_content = re.sub(r'AUTHORIZED_EMAILS\s*=\s*"([^"]*)"', f'AUTHORIZED_EMAILS = "{new_emails}"', content)
        with open(TOML_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)



class EmailManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestión de Emails Autorizados - Conversor Profesional")
        self.root.geometry("900x540")
        self.root.configure(bg="#f8f9fa")
        self.emails = read_authorized_emails()
        self.names_dict = read_names()
        self.create_widgets()
        self.refresh_list()

    def create_widgets(self):
        title = tk.Label(self.root, text="Emails autorizados para Conversor Profesional", font=("Arial", 20, "bold"), bg="#f8f9fa", fg="#1976d2")
        title.pack(pady=10)

        self.frame_table = tk.Frame(self.root, bg="#f8f9fa")
        self.frame_table.pack(fill=tk.BOTH, expand=True, padx=20)

        # Encabezados tipo tabla con columnas centradas
        header = tk.Frame(self.frame_table, bg="#e3f2fd")
        header.pack(fill=tk.X)
        for col, text, width in zip(range(4), ["Email", "Fecha Autorización", "Nombre del Dueño", "Eliminar"], [25, 18, 20, 8]):
            lbl = tk.Label(header, text=text, font=("Arial", 13, "bold"), width=width, anchor="center", bg="#e3f2fd")
            lbl.grid(row=0, column=col, padx=2, pady=2, sticky="nsew")
            header.grid_columnconfigure(col, weight=1)

        self.frame_list = tk.Frame(self.frame_table, bg="#f8f9fa")
        self.frame_list.pack(fill=tk.BOTH, expand=True)

        btn_frame = tk.Frame(self.root, bg="#f8f9fa")
        btn_frame.pack(pady=10)

        btn_add = tk.Button(btn_frame, text="Agregar Email", font=("Arial", 13), bg="#e3f2fd", command=self.add_email)
        btn_add.grid(row=0, column=0, padx=5)

        btn_reload = tk.Button(btn_frame, text="Recargar Emails", font=("Arial", 13), bg="#fffde7", command=self.reload_emails)
        btn_reload.grid(row=0, column=1, padx=5)

        btn_save = tk.Button(btn_frame, text="Guardar Cambios", font=("Arial", 13), bg="#c8e6c9", command=self.save_emails)
        btn_save.grid(row=0, column=2, padx=5)

    def refresh_list(self):
        for widget in self.frame_list.winfo_children():
            widget.destroy()
        self.entry_names = []
        for idx, (email, fecha) in enumerate(self.emails):
            row = tk.Frame(self.frame_list, bg="#f8f9fa")
            for col in range(4):
                row.grid_columnconfigure(col, weight=1)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=email, font=("Arial", 12), width=25, anchor="center", bg="#f8f9fa").grid(row=0, column=0, padx=2, sticky="nsew")
            tk.Label(row, text=fecha, font=("Arial", 11), width=18, anchor="center", bg="#f8f9fa", fg="#388e3c").grid(row=0, column=1, padx=2, sticky="nsew")
            entry_name = tk.Entry(row, font=("Arial", 12), width=20, justify="center")
            entry_name.grid(row=0, column=2, padx=2, sticky="nsew")
            entry_name.insert(0, self.names_dict.get(email, ""))
            self.entry_names.append((email, entry_name))
            btn_del = tk.Button(row, text="🗑️", font=("Arial", 8), bg="#e3f2fd", fg="#1976d2", width=2,
                               command=lambda i=idx: self.delete_email(i))
            btn_del.grid(row=0, column=3, padx=2, sticky="nsew")

    def add_email(self):
        new_email = simpledialog.askstring("Agregar Email", "Introduce el nuevo email autorizado:")
        if new_email and "@" in new_email:
            self.emails.append((new_email.strip(), datetime.now().strftime("%Y-%m-%d %H:%M")))
            self.names_dict[new_email.strip()] = ""
            self.refresh_list()
            self.save_emails()  # Actualiza secrets_local.toml inmediatamente
        elif new_email:
            messagebox.showerror("Error", "Email inválido.")

    def delete_email(self, idx):
        email = self.emails[idx][0]
        if messagebox.askyesno("Confirmar", f"¿Eliminar el email '{email}'?"):
            self.emails.pop(idx)
            if email in self.names_dict:
                del self.names_dict[email]
            self.refresh_list()
            self.save_emails()  # Actualiza secrets_local.toml inmediatamente

    def reload_emails(self):
        self.emails = read_authorized_emails()
        self.names_dict = read_names()
        self.refresh_list()
        messagebox.showinfo("Recargado", "Emails recargados desde authorized_users.json.")

    def save_emails(self):
        emails_only = [email for email, _ in self.emails]
        write_authorized_emails(emails_only)
        # Actualiza secrets_local.toml
        if os.path.exists(TOML_PATH):
            with open(TOML_PATH, "r", encoding="utf-8") as f:
                content = f.read()
            new_emails = ",".join(emails_only)
            new_content = re.sub(r'AUTHORIZED_EMAILS\s*=\s*"([^"]*)"', f'AUTHORIZED_EMAILS = "{new_emails}"', content)
            with open(TOML_PATH, "w", encoding="utf-8") as f:
                f.write(new_content)
        # Guarda los nombres
        for email, entry in self.entry_names:
            self.names_dict[email] = entry.get()
        write_names(self.names_dict)
        messagebox.showinfo("Guardado", "Emails y nombres actualizados correctamente.")

if __name__ == "__main__":
    root = tk.Tk()
    app = EmailManagerApp(root)
    root.mainloop()
