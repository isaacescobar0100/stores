"""
Script para agregar columnas faltantes a la base de datos
"""
import pymysql
from dotenv import load_dotenv
import os

load_dotenv('.env.local')

conn = pymysql.connect(
    host=os.getenv('DB_HOST', '127.0.0.1'),
    port=int(os.getenv('DB_PORT', 3306)),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME'),
    cursorclass=pymysql.cursors.DictCursor
)

cursor = conn.cursor()

# Agregar columna metodo_pago si no existe
try:
    cursor.execute('''
        ALTER TABLE pedidos
        ADD COLUMN metodo_pago VARCHAR(50) DEFAULT 'efectivo'
    ''')
    conn.commit()
    print('Columna metodo_pago agregada exitosamente')
except Exception as e:
    if 'Duplicate column' in str(e):
        print('La columna metodo_pago ya existe')
    else:
        print(f'Error: {e}')

# Agregar columna mesero_id si no existe
try:
    cursor.execute('''
        ALTER TABLE pedidos
        ADD COLUMN mesero_id INT
    ''')
    conn.commit()
    print('Columna mesero_id agregada exitosamente')
except Exception as e:
    if 'Duplicate column' in str(e):
        print('La columna mesero_id ya existe')
    else:
        print(f'Error: {e}')

# Verificar las columnas
cursor.execute('DESCRIBE pedidos')
print('\nColumnas de la tabla pedidos:')
for row in cursor.fetchall():
    print(f"  - {row['Field']}: {row['Type']}")

conn.close()
print('\nMigracion completada!')
