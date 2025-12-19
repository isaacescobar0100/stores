"""
Launcher Unificado - Sistema Restaurante
Diseño Moderno con CustomTkinter
Con Sistema de Auto-Actualización
"""
import customtkinter as ctk
from tkinter import messagebox
import urllib.request
import urllib.error
import json
import os
import sys
import threading
import tempfile
import shutil
from api_client import APIClient

# Configuración de CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Versión actual de la aplicación
APP_VERSION = "1.0.8"
APP_NAME = "VxPlay"

# URL del servidor principal para actualizaciones
UPDATE_SERVER = "https://vxplay.online"


class AutoUpdater:
    """Sistema de auto-actualización para .exe compilados"""

    def __init__(self, servidor_url=None):
        self.servidor_url = UPDATE_SERVER
        self.update_available = False
        self.new_version = None
        self.changelog = ""
        self.exe_url = None

    def check_for_updates(self):
        """Verificar si hay actualizaciones disponibles"""
        try:
            url = f"{self.servidor_url}/static/apps/version.json"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))

            server_version = data.get('version', '0.0.0')

            if self._compare_versions(server_version, APP_VERSION) > 0:
                self.update_available = True
                self.new_version = server_version
                self.changelog = data.get('changelog', '')
                self.exe_url = data.get('exe_url', f"{self.servidor_url}/static/apps/RestaurantOS.exe")
                return True
            return False
        except Exception as e:
            print(f"Error al verificar actualizaciones: {e}")
            return False

    def _compare_versions(self, v1, v2):
        """Comparar versiones"""
        try:
            parts1 = [int(x) for x in v1.split('.')]
            parts2 = [int(x) for x in v2.split('.')]
            for i in range(max(len(parts1), len(parts2))):
                p1 = parts1[i] if i < len(parts1) else 0
                p2 = parts2[i] if i < len(parts2) else 0
                if p1 > p2:
                    return 1
                elif p1 < p2:
                    return -1
            return 0
        except:
            return 0

    def download_update(self, progress_callback=None):
        """Descargar el nuevo .exe"""
        try:
            if not self.exe_url:
                self.exe_url = f"{self.servidor_url}/static/apps/VxPlay.exe"

            # Descargar a carpeta Descargas del usuario
            downloads_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
            if not os.path.exists(downloads_dir):
                downloads_dir = os.path.join(os.path.expanduser('~'), 'Descargas')
            if not os.path.exists(downloads_dir):
                downloads_dir = tempfile.gettempdir()
            temp_exe = os.path.join(downloads_dir, f"VxPlay_v{self.new_version}.exe")

            print(f"[UPDATE] Descargando desde: {self.exe_url}")
            print(f"[UPDATE] Guardando en: {temp_exe}")

            req = urllib.request.Request(self.exe_url)
            with urllib.request.urlopen(req, timeout=120) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                chunk_size = 8192

                with open(temp_exe, 'wb') as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress = downloaded / total_size
                            progress_callback(progress)

            print(f"[UPDATE] Descarga completada: {os.path.getsize(temp_exe)} bytes")
            return temp_exe
        except Exception as e:
            print(f"Error al descargar actualización: {e}")
            return None

    def apply_update(self, temp_exe_path):
        """Aplicar la actualización - reemplazar exe y reiniciar"""
        try:
            if not temp_exe_path or not os.path.exists(temp_exe_path):
                return False

            if getattr(sys, 'frozen', False):
                # Es un .exe compilado
                current_exe = sys.executable
                exe_dir = os.path.dirname(current_exe)
                exe_name = os.path.basename(current_exe)
                new_exe = os.path.join(exe_dir, "VxPlay_new.exe")

                # Crear batch en AppData (no en el mismo dir del exe)
                app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
                updater_bat = os.path.join(app_data, "VxPlay_update.bat")

                # Copiar el nuevo exe descargado
                shutil.copy2(temp_exe_path, new_exe)
                print(f"[UPDATE] Nuevo exe copiado a: {new_exe}")

                # Script batch que espera, reemplaza con COPY (no delete+move) y reinicia
                batch_content = f'''@echo off
echo Esperando a que VxPlay se cierre...
:waitloop
timeout /t 1 /nobreak >nul
tasklist /FI "IMAGENAME eq {exe_name}" 2>nul | find /I "{exe_name}" >nul
if not errorlevel 1 goto waitloop

echo Aplicando actualizacion...
copy /Y "{new_exe}" "{current_exe}"
if errorlevel 1 (
    echo Reintentando...
    timeout /t 2 /nobreak >nul
    copy /Y "{new_exe}" "{current_exe}"
)

echo Limpiando...
del /F /Q "{new_exe}" 2>nul
del /F /Q "{temp_exe_path}" 2>nul

echo Iniciando VxPlay actualizado...
start "" "{current_exe}"

timeout /t 2 /nobreak >nul
del /F /Q "%~f0" 2>nul
'''
                with open(updater_bat, 'w') as f:
                    f.write(batch_content)
                print(f"[UPDATE] Script creado: {updater_bat}")

                # Ejecutar el batch (en segundo plano)
                import subprocess
                subprocess.Popen(['cmd', '/c', updater_bat],
                               creationflags=subprocess.CREATE_NO_WINDOW,
                               cwd=app_data)
                return True
            else:
                # Modo desarrollo - solo informar
                messagebox.showinfo(
                    "Actualización",
                    f"Nuevo exe descargado en:\n{temp_exe_path}\n\n"
                    "En modo desarrollo, copia manualmente."
                )
                return False
        except Exception as e:
            print(f"Error al aplicar actualización: {e}")
            return False


class LauncherApp(ctk.CTk):
    """Pantalla principal - Diseño Moderno con CustomTkinter"""

    def __init__(self):
        super().__init__()

        self.api = APIClient()
        self.updater = AutoUpdater()  # Usa servidor principal automáticamente

        # Configuración ventana
        self.title("VxPlay")
        self.geometry("900x450")
        self.resizable(False, False)

        # Centrar ventana
        self._center_window(900, 450)

        # Crear widgets
        self._create_widgets()

        # Verificar actualizaciones
        threading.Thread(target=self._check_updates_background, daemon=True).start()

    def _center_window(self, w, h):
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _create_widgets(self):
        # Container principal
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(expand=True, fill='both', padx=30, pady=25)

        # Header
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.pack(fill='x', pady=(0, 20))

        # Logo + Titulo
        logo_frame = ctk.CTkFrame(header, fg_color="transparent")
        logo_frame.pack(side='left')

        # Logo circular
        logo_label = ctk.CTkLabel(
            logo_frame,
            text="V",
            font=ctk.CTkFont(size=24, weight="bold"),
            fg_color="#3b82f6",
            corner_radius=25,
            width=50,
            height=50
        )
        logo_label.pack(side='left')

        # Titulo y subtitulo
        title_frame = ctk.CTkFrame(logo_frame, fg_color="transparent")
        title_frame.pack(side='left', padx=(15, 0))

        ctk.CTkLabel(
            title_frame,
            text="VxPlay",
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack(anchor='w')

        # Mostrar nombre de tienda si está configurado
        tienda_nombre = self.api.tienda.get('nombre', '')
        if tienda_nombre:
            ctk.CTkLabel(
                title_frame,
                text=tienda_nombre,
                font=ctk.CTkFont(size=13),
                text_color="gray"
            ).pack(anchor='w')

        # Versión
        self.version_label = ctk.CTkLabel(
            header,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.version_label.pack(side='right')

        # Separador
        separator = ctk.CTkFrame(self.main_frame, height=2, fg_color=("gray80", "gray30"))
        separator.pack(fill='x', pady=(0, 25))

        # Cards container
        cards_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        cards_frame.pack(fill='both', expand=True)
        cards_frame.grid_columnconfigure((0, 1, 2), weight=1)
        cards_frame.grid_rowconfigure(0, weight=1)

        # Card Admin
        self._create_card(
            cards_frame,
            column=0,
            title="Panel Admin",
            description="Gestiona productos,\npedidos y reportes",
            icon="👨‍💼",
            color="#10b981",
            hover_color="#059669",
            command=self._open_admin
        )

        # Card Caja
        self._create_card(
            cards_frame,
            column=1,
            title="Panel Caja",
            description="Cobra pedidos y\ngenera links de pago",
            icon="💰",
            color="#f59e0b",
            hover_color="#d97706",
            command=self._open_caja
        )

        # Card Cocina
        self._create_card(
            cards_frame,
            column=2,
            title="Panel Cocina",
            description="Visualiza pedidos\nen tiempo real",
            icon="👨‍🍳",
            color="#ef4444",
            hover_color="#dc2626",
            command=self._open_cocina
        )

        # Footer
        footer = ctk.CTkLabel(
            self.main_frame,
            text="Selecciona un panel para comenzar",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        footer.pack(pady=(20, 0))

    def _create_card(self, parent, column, title, description, icon, color, hover_color, command):
        """Crear card moderna"""
        card = ctk.CTkFrame(parent, corner_radius=15)
        card.grid(row=0, column=column, padx=10, sticky="nsew")

        # Contenido
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(expand=True, pady=30, padx=20)

        # Icono
        icon_label = ctk.CTkLabel(
            content,
            text=icon,
            font=ctk.CTkFont(size=48)
        )
        icon_label.pack()

        # Titulo
        title_label = ctk.CTkLabel(
            content,
            text=title,
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=(15, 5))

        # Descripción
        desc_label = ctk.CTkLabel(
            content,
            text=description,
            font=ctk.CTkFont(size=13),
            text_color="gray",
            justify="center"
        )
        desc_label.pack()

        # Botón
        btn = ctk.CTkButton(
            content,
            text="Abrir",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=color,
            hover_color=hover_color,
            corner_radius=10,
            height=40,
            width=150,
            command=command
        )
        btn.pack(pady=(20, 0))

    def _open_admin(self):
        """Abrir login Admin"""
        self.withdraw()
        login = LoginWindow(self, 'admin', self._on_login_admin, self._back_to_launcher)

    def _open_caja(self):
        """Abrir login Caja"""
        self.withdraw()
        login = LoginWindow(self, 'caja', self._on_login_caja, self._back_to_launcher)

    def _open_cocina(self):
        """Abrir login Cocina"""
        self.withdraw()
        login = LoginWindow(self, 'cocina', self._on_login_cocina, self._back_to_launcher)

    def _back_to_launcher(self):
        """Volver al launcher"""
        self.deiconify()

    def _check_updates_background(self):
        """Verificar actualizaciones"""
        try:
            if self.updater.check_for_updates():
                self.after(0, self._show_update_notification)
        except Exception as e:
            print(f"Error verificando actualizaciones: {e}")

    def _show_update_notification(self):
        """Mostrar notificación de actualización - pregunta directamente"""
        self.version_label.configure(
            text=f"v{APP_VERSION} → v{self.updater.new_version} disponible",
            text_color="#3b82f6",
            cursor="hand2"
        )
        self.version_label.bind('<Button-1>', lambda e: self._prompt_update())
        # Preguntar automáticamente
        self._prompt_update()

    def _prompt_update(self):
        """Preguntar por actualización"""
        result = messagebox.askyesno(
            "Actualización Disponible",
            f"Nueva versión {self.updater.new_version} disponible.\n\n"
            f"Versión actual: {APP_VERSION}\n\n"
            "¿Deseas actualizar ahora?"
        )
        if result:
            self._start_update()

    def _start_update(self):
        """Iniciar actualización"""
        self.update_window = ctk.CTkToplevel(self)
        self.update_window.title("Actualizando...")
        self.update_window.geometry("400x200")
        self.update_window.resizable(False, False)
        self.update_window.transient(self)
        self.update_window.grab_set()

        # Centrar
        x = (self.update_window.winfo_screenwidth() - 400) // 2
        y = (self.update_window.winfo_screenheight() - 200) // 2
        self.update_window.geometry(f"400x200+{x}+{y}")

        container = ctk.CTkFrame(self.update_window, fg_color="transparent")
        container.pack(expand=True, fill='both', padx=30, pady=20)

        ctk.CTkLabel(
            container,
            text="Descargando actualización...",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(0, 20))

        self.progress_bar = ctk.CTkProgressBar(container, width=300)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            container,
            text="0%",
            font=ctk.CTkFont(size=14)
        )
        self.progress_label.pack()

        threading.Thread(target=self._download_update, daemon=True).start()

    def _download_update(self):
        """Descargar actualización"""
        def update_progress(progress):
            self.after(0, lambda: self.progress_bar.set(progress))
            self.after(0, lambda: self.progress_label.configure(text=f"{int(progress * 100)}%"))

        temp_file = self.updater.download_update(progress_callback=update_progress)

        if temp_file:
            self.after(0, lambda: self._apply_update(temp_file))
        else:
            self.after(0, self._update_failed)

    def _apply_update(self, temp_file):
        """Aplicar actualización"""
        self.update_window.destroy()
        if self.updater.apply_update(temp_file):
            self.quit()
        else:
            messagebox.showinfo(
                "Actualización",
                f"Versión {self.updater.new_version} descargada.\n"
                "En modo desarrollo, actualiza manualmente."
            )

    def _update_failed(self):
        """Fallo de actualización"""
        self.update_window.destroy()
        messagebox.showerror(
            "Error",
            "No se pudo descargar la actualización.\n"
            "Verifica tu conexión a internet."
        )

    def _on_login_admin(self, api, window):
        """Login admin exitoso"""
        window.destroy()
        admin_window = ctk.CTkToplevel(self)
        from admin_cloud import AdminApp
        app = AdminApp(admin_window, api)
        admin_window.protocol("WM_DELETE_WINDOW", lambda: self._close_panel(admin_window, app))

    def _on_login_caja(self, api, window):
        """Login caja exitoso"""
        window.destroy()
        caja_window = ctk.CTkToplevel(self)
        from caja_cloud import CajaApp
        app = CajaApp(caja_window, api)
        caja_window.protocol("WM_DELETE_WINDOW", lambda: self._close_panel(caja_window, app))

    def _on_login_cocina(self, api, window):
        """Login cocina exitoso"""
        window.destroy()
        cocina_window = ctk.CTkToplevel(self)
        from cocina_cloud import CocinaApp
        app = CocinaApp(cocina_window, api)
        cocina_window.protocol("WM_DELETE_WINDOW", lambda: self._close_panel(cocina_window, app))

    def _close_panel(self, window, app):
        """Cerrar panel"""
        if hasattr(app, 'running'):
            app.running = False
        window.destroy()
        self.deiconify()


class LoginWindow(ctk.CTkToplevel):
    """Ventana de Login - Diseño Moderno"""

    def __init__(self, parent, tipo, on_success, on_cancel):
        super().__init__(parent)

        self.tipo = tipo
        self.on_success = on_success
        self.on_cancel = on_cancel
        self.api = APIClient()

        # Configuración
        if tipo == 'admin':
            color = "#10b981"
        elif tipo == 'caja':
            color = "#f59e0b"
        else:
            color = "#ef4444"
        self.accent_color = color

        titulos = {'admin': 'Admin', 'caja': 'Caja', 'cocina': 'Cocina'}
        self.title(f"{titulos.get(tipo, 'Panel')} - Iniciar Sesión")
        self.geometry("420x580")
        self.resizable(False, False)

        # Centrar
        x = (self.winfo_screenwidth() - 420) // 2
        y = (self.winfo_screenheight() - 580) // 2
        self.geometry(f"420x580+{x}+{y}")

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.transient(parent)
        self.grab_set()

        self._create_widgets()

    def _create_widgets(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(expand=True, fill='both', padx=40, pady=30)

        # Header
        iconos = {'admin': '👨‍💼', 'caja': '💰', 'cocina': '👨‍🍳'}
        icon = iconos.get(self.tipo, '👤')
        ctk.CTkLabel(
            container,
            text=icon,
            font=ctk.CTkFont(size=50)
        ).pack(pady=(0, 10))

        titulos = {'admin': 'Panel Admin', 'caja': 'Panel Caja', 'cocina': 'Panel Cocina'}
        titulo = titulos.get(self.tipo, 'Panel')
        ctk.CTkLabel(
            container,
            text=titulo,
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack()

        ctk.CTkLabel(
            container,
            text="Ingresa tus credenciales",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        ).pack(pady=(5, 25))

        # Form
        form = ctk.CTkFrame(container, fg_color="transparent")
        form.pack(fill='x')

        # Campos
        self.servidor_var = ctk.StringVar(value=self.api.servidor_url)
        self.tienda_var = ctk.StringVar(value=self.api.tienda_slug)
        self.email_var = ctk.StringVar()
        self.password_var = ctk.StringVar()

        self._create_input(form, "Servidor", self.servidor_var)
        self._create_input(form, "Tienda", self.tienda_var)
        self._create_input(form, "Email", self.email_var)
        self._create_input(form, "Contraseña", self.password_var, show="*")

        # Botón login
        self.login_btn = ctk.CTkButton(
            form,
            text="Iniciar Sesión",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=self.accent_color,
            hover_color=self._darken_color(self.accent_color),
            corner_radius=10,
            height=45,
            command=self._login
        )
        self.login_btn.pack(fill='x', pady=(20, 10))

        # Botón volver
        ctk.CTkButton(
            form,
            text="← Volver",
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            text_color="gray",
            command=self._cancel
        ).pack()

        # Status
        self.status_label = ctk.CTkLabel(
            form,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#ef4444"
        )
        self.status_label.pack(pady=(15, 0))

    def _create_input(self, parent, label, variable, show=None):
        """Crear campo de input"""
        ctk.CTkLabel(
            parent,
            text=label,
            font=ctk.CTkFont(size=12),
            text_color="gray"
        ).pack(anchor='w', pady=(10, 2))

        entry = ctk.CTkEntry(
            parent,
            textvariable=variable,
            font=ctk.CTkFont(size=14),
            height=40,
            corner_radius=8
        )
        if show:
            entry.configure(show=show)
        entry.pack(fill='x')

    def _darken_color(self, hex_color):
        """Oscurecer color para hover"""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = max(0, r - 30)
        g = max(0, g - 30)
        b = max(0, b - 30)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _login(self):
        self.status_label.configure(text="Conectando...")
        self.login_btn.configure(state="disabled")

        self.api.servidor_url = self.servidor_var.get().strip()
        self.api.tienda_slug = self.tienda_var.get().strip()
        email = self.email_var.get().strip()
        password = self.password_var.get()

        def login_async():
            result = self.api.login(email, password)
            self.after(0, lambda: self._login_callback(result))

        threading.Thread(target=login_async, daemon=True).start()

    def _login_callback(self, result):
        """Callback del login en hilo principal"""
        if result and result.get('success'):
            self.on_success(self.api, self)
        else:
            self.login_btn.configure(state="normal")
            self.status_label.configure(text=result.get('error', 'Error de conexión') if result else 'Error de conexión')

    def _cancel(self):
        self.destroy()
        self.on_cancel()


def main():
    app = LauncherApp()
    app.mainloop()


if __name__ == '__main__':
    main()
