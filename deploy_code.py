#!/usr/bin/env python3
"""
Script para subir actualizaciones del codigo al servidor.
Sube los archivos Python y templates modificados.

Uso: python deploy_code.py
"""

import paramiko
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Configuracion del servidor (desde .env)
HOST = os.getenv('DEPLOY_HOST', '72.61.72.32')
USER = os.getenv('DEPLOY_USER', 'root')
PASSWORD = os.getenv('DEPLOY_PASSWORD')

if not PASSWORD:
    print("ERROR: Falta DEPLOY_PASSWORD en el archivo .env")
    exit(1)

# Rutas
LOCAL_PATH = r"c:\Users\issac\OneDrive\Desktop\rest"
REMOTE_PATH = "/var/www/restaurante"

# Archivos a subir
FILES_TO_UPLOAD = [
    "superadmin_routes.py",
    "templates/superadmin/base.html",
    "templates/superadmin/importar_productos.html",
    "templates/superadmin/galeria_productos.html",
]


def main():
    print("=" * 50)
    print("SUBIENDO ACTUALIZACION DE CODIGO")
    print("=" * 50)

    # Conectar al servidor
    print("\nConectando al servidor...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASSWORD)
    sftp = client.open_sftp()

    print("\nSubiendo archivos...")
    for file_path in FILES_TO_UPLOAD:
        local_file = os.path.join(LOCAL_PATH, file_path)
        remote_file = f"{REMOTE_PATH}/{file_path}"

        if os.path.exists(local_file):
            # Crear directorio remoto si no existe
            remote_dir = os.path.dirname(remote_file)
            try:
                sftp.stat(remote_dir)
            except FileNotFoundError:
                # Crear directorios recursivamente
                parts = remote_dir.split('/')
                current = ""
                for part in parts:
                    if part:
                        current += f"/{part}"
                        try:
                            sftp.stat(current)
                        except FileNotFoundError:
                            sftp.mkdir(current)

            sftp.put(local_file, remote_file)
            print(f"  + {file_path}")
        else:
            print(f"  ! {file_path} no encontrado")

    sftp.close()

    # Reiniciar contenedor
    print("\nReiniciando servidor...")
    stdin, stdout, stderr = client.exec_command('docker restart restaurante-web-1')
    stdout.read()
    print("  + Servidor reiniciado")

    client.close()

    print("\n" + "=" * 50)
    print("CODIGO ACTUALIZADO EXITOSAMENTE")
    print("=" * 50)


if __name__ == '__main__':
    main()
