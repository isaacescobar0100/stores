#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, '/app')
os.chdir('/app')

from werkzeug.security import generate_password_hash
from models import get_connection

# Generar hash para admin123
password_hash = generate_password_hash('admin123')
print(f"Hash generado: {password_hash}")

db = get_connection()

# Verificar si existe
existing = db.execute("SELECT id, email, rol FROM usuarios WHERE email = %s", ('superadmin@restaurantes.com',)).fetchone()
if existing:
    print(f"Usuario existente: {dict(existing)}")
    # Actualizar password y rol
    db.execute("UPDATE usuarios SET password = %s, rol = 'superadmin', activo = 1 WHERE email = %s",
               (password_hash, 'superadmin@restaurantes.com'))
    db.commit()
    print("Password y rol actualizados")
else:
    # Crear nuevo
    db.execute("""
        INSERT INTO usuarios (nombre, email, password, rol, activo, tienda_id)
        VALUES ('Super Admin', 'superadmin@restaurantes.com', %s, 'superadmin', 1, NULL)
    """, (password_hash,))
    db.commit()
    print("Usuario superadmin creado")

# Verificar
user = db.execute("SELECT id, email, rol, activo FROM usuarios WHERE email = %s", ('superadmin@restaurantes.com',)).fetchone()
print(f"Usuario final: {dict(user)}")
