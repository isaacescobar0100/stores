"""
Sistema de Auto-Actualizacion para VxPlay Launcher
Soporta actualizacion de archivos .exe compilados
"""
import os
import sys
import json
import requests
import shutil
import subprocess
from datetime import datetime

# Configuracion - Apunta al servidor principal
SERVER_URL = "http://72.61.72.32:5000"
VERSION_URL = f"{SERVER_URL}/static/launcher/version.json"
DOWNLOAD_URL = f"{SERVER_URL}/static/launcher"
EXE_VERSION_URL = f"{SERVER_URL}/static/apps/version.json"
EXE_DOWNLOAD_URL = f"{SERVER_URL}/static/apps/VxPlay.exe"
LOCAL_VERSION_FILE = "version.txt"
CURRENT_VERSION = "1.0.4"  # Version embebida en el exe

def get_app_data_dir():
    """Obtener directorio persistente en AppData para guardar la version"""
    app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
    vxplay_dir = os.path.join(app_data, 'VxPlay')
    if not os.path.exists(vxplay_dir):
        os.makedirs(vxplay_dir)
    return vxplay_dir

def get_script_dir():
    """Obtener directorio del script"""
    return os.path.dirname(os.path.abspath(__file__))

def is_running_as_exe():
    """Verificar si estamos corriendo como .exe compilado"""
    return getattr(sys, 'frozen', False)

def get_local_version():
    """Obtener version local instalada desde AppData o usar la embebida"""
    # Primero intentar leer de AppData (persistente)
    version_file = os.path.join(get_app_data_dir(), LOCAL_VERSION_FILE)
    if os.path.exists(version_file):
        with open(version_file, 'r') as f:
            saved_version = f.read().strip()
            # Si la version guardada es menor que la embebida, usar la embebida
            if compare_versions(CURRENT_VERSION, saved_version) > 0:
                save_local_version(CURRENT_VERSION)
                return CURRENT_VERSION
            return saved_version
    # Si no existe, guardar la version actual y retornarla
    save_local_version(CURRENT_VERSION)
    return CURRENT_VERSION

def save_local_version(version):
    """Guardar version local en AppData (persistente)"""
    version_file = os.path.join(get_app_data_dir(), LOCAL_VERSION_FILE)
    with open(version_file, 'w') as f:
        f.write(version)
    print(f"[UPDATE] Version guardada en: {version_file}")

def check_for_updates():
    """Verificar si hay actualizaciones disponibles"""
    try:
        # Si estamos corriendo como exe, verificar version del exe
        if is_running_as_exe():
            url = EXE_VERSION_URL
        else:
            url = VERSION_URL

        print(f"[UPDATE] Consultando: {url}")
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            server_info = response.json()
            server_version = server_info.get('version', '0.0.0')
            local_version = get_local_version()

            print(f"[UPDATE] Version local: {local_version}")
            print(f"[UPDATE] Version servidor: {server_version}")
            print(f"[UPDATE] Corriendo como exe: {is_running_as_exe()}")

            if compare_versions(server_version, local_version) > 0:
                return {
                    'update_available': True,
                    'server_version': server_version,
                    'local_version': local_version,
                    'files': server_info.get('files', []),
                    'changelog': server_info.get('changelog', ''),
                    'exe_url': server_info.get('exe_url', EXE_DOWNLOAD_URL),
                    'is_exe': is_running_as_exe()
                }
        return {'update_available': False}
    except Exception as e:
        print(f"[UPDATE] Error verificando actualizaciones: {e}")
        return {'update_available': False, 'error': str(e)}

def compare_versions(v1, v2):
    """Comparar dos versiones (ej: 1.2.0 vs 1.1.0)"""
    try:
        v1_parts = [int(x) for x in v1.split('.')]
        v2_parts = [int(x) for x in v2.split('.')]

        # Rellenar con ceros si es necesario
        while len(v1_parts) < 3:
            v1_parts.append(0)
        while len(v2_parts) < 3:
            v2_parts.append(0)

        for i in range(3):
            if v1_parts[i] > v2_parts[i]:
                return 1
            elif v1_parts[i] < v2_parts[i]:
                return -1
        return 0
    except:
        return 0

def download_file(filename, dest_path):
    """Descargar un archivo del servidor"""
    try:
        url = f"{DOWNLOAD_URL}/{filename}"
        print(f"[UPDATE] Descargando {filename} desde {url}...")

        response = requests.get(url, timeout=60, stream=True)
        if response.status_code == 200:
            # Crear backup del archivo actual
            if os.path.exists(dest_path):
                backup_path = f"{dest_path}.backup"
                shutil.copy2(dest_path, backup_path)
                print(f"[UPDATE] Backup creado: {backup_path}")

            # Guardar nuevo archivo
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"[UPDATE] {filename} descargado correctamente")
            return True
        else:
            print(f"[UPDATE] Error descargando {filename}: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"[UPDATE] Error descargando {filename}: {e}")
        return False

def download_exe_update(update_info):
    """Descargar nuevo exe y preparar actualizacion"""
    try:
        exe_url = update_info.get('exe_url', EXE_DOWNLOAD_URL)
        app_data_dir = get_app_data_dir()
        new_exe_path = os.path.join(app_data_dir, 'VxPlay_new.exe')

        print(f"[UPDATE] Descargando nuevo exe desde: {exe_url}")

        response = requests.get(exe_url, timeout=120, stream=True)
        if response.status_code == 200:
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(new_exe_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r[UPDATE] Descargando: {percent:.1f}%", end='')
            print()

            # Guardar la nueva version
            save_local_version(update_info['server_version'])
            print(f"[UPDATE] Exe descargado en: {new_exe_path}")

            # Crear script de actualizacion que reemplaza el exe
            create_update_script(new_exe_path)
            return True
        else:
            print(f"[UPDATE] Error descargando exe: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"[UPDATE] Error descargando exe: {e}")
        return False

def create_update_script(new_exe_path):
    """Crear script batch para reemplazar el exe despues de cerrar"""
    try:
        current_exe = sys.executable
        app_data_dir = get_app_data_dir()
        script_path = os.path.join(app_data_dir, 'update.bat')

        script_content = f'''@echo off
echo Esperando a que VxPlay se cierre...
timeout /t 2 /nobreak > nul
echo Aplicando actualizacion...
copy /Y "{new_exe_path}" "{current_exe}"
if errorlevel 1 (
    echo Error copiando archivo. Intentando de nuevo...
    timeout /t 3 /nobreak > nul
    copy /Y "{new_exe_path}" "{current_exe}"
)
echo Iniciando VxPlay actualizado...
start "" "{current_exe}"
del "{new_exe_path}"
del "%~f0"
'''
        with open(script_path, 'w') as f:
            f.write(script_content)

        print(f"[UPDATE] Script de actualizacion creado: {script_path}")
        return script_path
    except Exception as e:
        print(f"[UPDATE] Error creando script: {e}")
        return None

def apply_update(update_info):
    """Aplicar actualizacion - descarga exe o archivos segun corresponda"""

    # Si estamos corriendo como exe, descargar el nuevo exe
    if update_info.get('is_exe', False):
        return download_exe_update(update_info)

    # Si estamos corriendo como Python, descargar archivos
    files = update_info.get('files', [])
    success_count = 0
    script_dir = get_script_dir()

    for file_info in files:
        filename = file_info.get('name')
        if filename:
            dest_path = os.path.join(script_dir, filename)
            if download_file(filename, dest_path):
                success_count += 1

    if success_count == len(files):
        # Guardar nueva version
        save_local_version(update_info['server_version'])
        print(f"[UPDATE] Actualizacion completada a version {update_info['server_version']}")
        return True
    else:
        print(f"[UPDATE] Actualizacion parcial: {success_count}/{len(files)} archivos")
        return False

def show_update_dialog(update_info):
    """Mostrar dialogo de actualizacion usando Tkinter"""
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()  # Ocultar ventana principal

        message = f"""Nueva version disponible!

Version actual: {update_info['local_version']}
Nueva version: {update_info['server_version']}

Cambios:
{update_info.get('changelog', 'Mejoras y correcciones')}

Desea actualizar ahora?"""

        result = messagebox.askyesno("Actualizacion Disponible", message)
        root.destroy()

        return result
    except Exception as e:
        print(f"[UPDATE] Error mostrando dialogo: {e}")
        return False

def check_and_update():
    """Verificar y aplicar actualizaciones si el usuario acepta"""
    print("[UPDATE] Verificando actualizaciones...")

    update_info = check_for_updates()

    if update_info.get('update_available'):
        print(f"[UPDATE] Nueva version disponible: {update_info['server_version']}")

        # Mostrar dialogo al usuario
        if show_update_dialog(update_info):
            print("[UPDATE] Usuario acepto la actualizacion")
            if apply_update(update_info):
                # Reiniciar aplicacion
                print("[UPDATE] Reiniciando aplicacion...")
                restart_application()
            else:
                print("[UPDATE] Error aplicando actualizacion")
        else:
            print("[UPDATE] Usuario rechazo la actualizacion")
    else:
        print("[UPDATE] No hay actualizaciones disponibles")

    return update_info

def restart_application():
    """Reiniciar la aplicacion - ejecuta script de actualizacion si es exe"""
    try:
        if is_running_as_exe():
            # Ejecutar script de actualizacion
            app_data_dir = get_app_data_dir()
            script_path = os.path.join(app_data_dir, 'update.bat')
            if os.path.exists(script_path):
                print(f"[UPDATE] Ejecutando script de actualizacion: {script_path}")
                subprocess.Popen(['cmd', '/c', script_path],
                               creationflags=subprocess.CREATE_NO_WINDOW)
                sys.exit(0)
            else:
                # Si no hay script, solo reiniciar
                print(f"[UPDATE] Reiniciando exe...")
                subprocess.Popen([sys.executable])
                sys.exit(0)
        else:
            # Reiniciar script Python
            python = sys.executable
            script = os.path.join(get_script_dir(), 'launcher.py')
            print(f"[UPDATE] Ejecutando: {python} {script}")
            subprocess.Popen([python, script])
            sys.exit(0)
    except Exception as e:
        print(f"[UPDATE] Error reiniciando: {e}")

if __name__ == "__main__":
    # Prueba del sistema de actualizacion
    check_and_update()
