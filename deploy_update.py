#!/usr/bin/env python3
"""
Script para desplegar actualizaciones del backend al servidor.
Sube archivos de configuracion y reinicia los contenedores Docker.
"""

import paramiko
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

HOST = os.getenv('DEPLOY_HOST', '72.61.72.32')
USER = os.getenv('DEPLOY_USER', 'root')
PASSWORD = os.getenv('DEPLOY_PASSWORD')

if not PASSWORD:
    print("ERROR: Falta DEPLOY_PASSWORD en .env")
    exit(1)

REMOTE_PATH = "/var/www/restaurante"

# Archivos a subir
FILES_TO_UPLOAD = [
    'app.py',
    'models.py',
    'superadmin_routes.py',
    'docker-compose.yml',
    'Dockerfile',
    'requirements.txt',
    'nginx.conf',
    'init-ssl.sh',
]

def main():
    print("=" * 50)
    print("DESPLEGANDO ACTUALIZACION AL SERVIDOR")
    print("=" * 50)

    # Conectar
    print(f"\nConectando a {HOST}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, username=USER, password=PASSWORD)
    sftp = client.open_sftp()

    # Subir archivos
    print("\nSubiendo archivos...")
    local_path = r"c:\Users\issac\OneDrive\Desktop\rest"

    for filename in FILES_TO_UPLOAD:
        local_file = os.path.join(local_path, filename)
        if os.path.exists(local_file):
            remote_file = f"{REMOTE_PATH}/{filename}"
            sftp.put(local_file, remote_file)
            print(f"  + {filename}")
        else:
            print(f"  - {filename} (no existe)")

    sftp.close()

    # Rebuild y restart (usar "docker compose" sin guion para versiones nuevas)
    print("\nReconstruyendo contenedores...")
    commands = [
        f"cd {REMOTE_PATH} && docker compose down",
        f"cd {REMOTE_PATH} && docker compose build --no-cache web",
        f"cd {REMOTE_PATH} && docker compose up -d",
    ]

    for cmd in commands:
        print(f"\n> {cmd}")
        stdin, stdout, stderr = client.exec_command(cmd, timeout=300)
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')
        if output:
            print(output[:2000])  # Limitar output
        if error and 'WARNING' not in error and 'warn' not in error.lower():
            print(f"Info: {error[:1000]}")

    # Verificar estado
    print("\nVerificando estado...")
    stdin, stdout, stderr = client.exec_command(f"cd {REMOTE_PATH} && docker compose ps")
    print(stdout.read().decode('utf-8', errors='replace'))

    # Esperar y probar health
    print("Esperando que el servidor inicie...")
    import time
    time.sleep(15)

    stdin, stdout, stderr = client.exec_command("curl -s http://localhost:5000/health 2>/dev/null || echo 'Servidor aun iniciando...'")
    health = stdout.read().decode('utf-8', errors='replace')
    print(f"\nHealth check: {health[:500]}")

    client.close()

    print("\n" + "=" * 50)
    print("DEPLOY COMPLETADO")
    print("=" * 50)

if __name__ == '__main__':
    main()
