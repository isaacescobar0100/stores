#!/usr/bin/env python3
"""
Script para subir actualizaciones del launcher al servidor.
Sube el .exe compilado y el version.json para auto-actualizacion.

Uso: python upload_and_restart.py
"""

import paramiko
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Configuracion del servidor (desde .env)
HOST = os.getenv('DEPLOY_HOST', '72.61.72.32')
USER = os.getenv('DEPLOY_USER', 'root')
PASSWORD = os.getenv('DEPLOY_PASSWORD')

if not PASSWORD:
    print("ERROR: Falta DEPLOY_PASSWORD en el archivo .env")
    print("Crea un archivo .env con: DEPLOY_PASSWORD=tu_password")
    exit(1)

# Rutas locales
LOCAL_APPS_PATH = r"c:\Users\issac\OneDrive\Desktop\rest\static\apps"
LOCAL_LAUNCHER_PATH = r"c:\Users\issac\OneDrive\Desktop\rest\static\launcher"

# Rutas remotas
REMOTE_APPS_PATH = "/var/www/restaurante/static/apps"
REMOTE_LAUNCHER_PATH = "/var/www/restaurante/static/launcher"


def get_next_version(current_version):
    """Incrementar version automaticamente"""
    parts = current_version.split('.')
    parts[-1] = str(int(parts[-1]) + 1)
    return '.'.join(parts)


def main():
    print("=" * 50)
    print("SUBIENDO ACTUALIZACION DEL LAUNCHER (.exe)")
    print("=" * 50)

    # Verificar que existe el exe - usar temp, dist o apps
    exe_local_temp = r"c:\temp\vxplay\VxPlay.exe"
    exe_local_dist = os.path.join(LOCAL_LAUNCHER_PATH, "dist", "VxPlay.exe")
    exe_local_apps = os.path.join(LOCAL_APPS_PATH, "VxPlay.exe")

    # Preferir el de temp (recién compilado) si existe
    if os.path.exists(exe_local_temp):
        exe_local = exe_local_temp
    elif os.path.exists(exe_local_dist):
        exe_local = exe_local_dist
    else:
        exe_local = exe_local_apps
    if not os.path.exists(exe_local):
        print(f"\nERROR: No existe {exe_local}")
        print("Primero compila el .exe con: pyinstaller --onefile --windowed --name VxPlay launcher.py")
        return

    exe_size = os.path.getsize(exe_local) / (1024 * 1024)
    print(f"\nArchivo: VxPlay.exe ({exe_size:.1f} MB)")

    # Conectar al servidor
    print("\nConectando al servidor...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASSWORD)
    sftp = client.open_sftp()

    # Leer version actual del servidor
    try:
        with sftp.file(f"{REMOTE_APPS_PATH}/version.json", 'r') as f:
            version_data = json.load(f)
            current_version = version_data.get('version', '1.0.0')
    except:
        current_version = '2.9.4'

    # Calcular nueva version
    new_version = get_next_version(current_version)

    print(f"\nVersion actual: {current_version}")
    print(f"Nueva version:  {new_version}")

    # Changelog
    changelog = "Seccion reportes basica"

    # Subir el .exe
    print(f"\nSubiendo VxPlay.exe ({exe_size:.1f} MB)...")
    sftp.put(exe_local, f"{REMOTE_APPS_PATH}/VxPlay.exe")
    print("  + VxPlay.exe subido")

    # Obtener dominio desde .env o usar IP
    dominio = os.getenv('DOMINIO_BASE', f"{HOST}:5000")

    # Actualizar version.json en /static/apps/
    version_data = {
        "version": new_version,
        "release_date": datetime.now().strftime("%Y-%m-%d"),
        "changelog": changelog,
        "exe_url": f"https://{dominio}/static/apps/VxPlay.exe"
    }

    with sftp.file(f"{REMOTE_APPS_PATH}/version.json", 'w') as f:
        json.dump(version_data, f, indent=4)
    print("  + version.json actualizado")

    # Actualizar version.json local
    with open(os.path.join(LOCAL_APPS_PATH, "version.json"), 'w') as f:
        json.dump(version_data, f, indent=4)

    sftp.close()

    # Reiniciar contenedor
    print("\nReiniciando servidor...")
    stdin, stdout, stderr = client.exec_command('docker restart restaurante-web-1')
    stdout.read()
    print("  + Servidor reiniciado")

    client.close()

    print("\n" + "=" * 50)
    print(f"ACTUALIZACION v{new_version} SUBIDA EXITOSAMENTE")
    print("=" * 50)
    print("\nTodas las maquinas descargaran el nuevo .exe automaticamente.")


if __name__ == '__main__':
    main()
