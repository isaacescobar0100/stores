"""
Modelos de base de datos - Sistema Multi-Tenant para Restaurantes
Soporte para SQLite y MySQL con reintentos automaticos y logging
"""
import os
import logging
import time
from datetime import datetime, date, timedelta
from decimal import Decimal
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

# Configurar logging estructurado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('models')

# Configuracion de reintentos
MAX_RETRIES = 3
RETRY_DELAY = 0.5  # segundos

def with_retry(func):
    """Decorador para reintentar operaciones de base de datos"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Intento {attempt + 1}/{MAX_RETRIES} fallido en {func.__name__}: {e}")
                    time.sleep(RETRY_DELAY * (attempt + 1))  # Backoff exponencial
                else:
                    logger.error(f"Todos los intentos fallidos en {func.__name__}: {e}")
        raise last_error
    return wrapper

# Detectar tipo de base de datos
DB_TYPE = os.environ.get('DB_TYPE', 'sqlite')  # 'sqlite' o 'mysql'

if DB_TYPE == 'mysql':
    import pymysql
    pymysql.install_as_MySQLdb()
    from dbutils.pooled_db import PooledDB

    DB_CONFIG = {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': int(os.environ.get('DB_PORT', 3306)),
        'user': os.environ.get('DB_USER', 'restaurante'),
        'password': os.environ.get('DB_PASSWORD', 'restaurante_pass_2024'),
        'database': os.environ.get('DB_NAME', 'restaurantes'),
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }

    # Pool de conexiones - reutiliza conexiones en lugar de crear nuevas
    MYSQL_POOL = PooledDB(
        creator=pymysql,
        maxconnections=20,
        mincached=5,
        maxcached=10,
        blocking=True,
        **DB_CONFIG
    )
else:
    import sqlite3
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATABASE_PATH = os.path.join(BASE_DIR, 'data', 'restaurantes.db')


class MySQLRow:
    """Clase que permite acceso a resultados tanto por indice [0] como por nombre ['columna']"""
    def __init__(self, data):
        # Convertir tipos MySQL a tipos compatibles con SQLite
        self._data = {}
        if data:
            for k, v in data.items():
                if isinstance(v, datetime):
                    self._data[k] = v.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(v, date):
                    self._data[k] = v.strftime('%Y-%m-%d')
                elif isinstance(v, timedelta):
                    # Convertir timedelta a string HH:MM:SS
                    total_seconds = int(v.total_seconds())
                    hours, remainder = divmod(total_seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    self._data[k] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                elif isinstance(v, Decimal):
                    self._data[k] = float(v)
                else:
                    self._data[k] = v
        self._keys = list(self._data.keys()) if self._data else []
        self._values = list(self._data.values()) if self._data else []

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._data[key]

    def __contains__(self, key):
        return key in self._data

    def keys(self):
        return self._keys

    def values(self):
        return self._values

    def items(self):
        return self._data.items()

    def get(self, key, default=None):
        return self._data.get(key, default)


class MySQLCursorWrapper:
    """Wrapper del cursor que convierte resultados a MySQLRow"""
    def __init__(self, cursor):
        self._cursor = cursor

    def fetchone(self):
        row = self._cursor.fetchone()
        return MySQLRow(row) if row else None

    def fetchall(self):
        rows = self._cursor.fetchall()
        return [MySQLRow(row) for row in rows] if rows else []

    def fetchmany(self, size=None):
        rows = self._cursor.fetchmany(size) if size else self._cursor.fetchmany()
        return [MySQLRow(row) for row in rows] if rows else []

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount


class MySQLConnectionWrapper:
    """Wrapper para que MySQL funcione como SQLite (conn.execute())"""
    def __init__(self, conn):
        self._conn = conn
        self._cursor = None

    def execute(self, query, params=None):
        # Convertir placeholders ? a %s para MySQL
        query = query.replace('?', '%s')
        cursor = self._conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        self._cursor = MySQLCursorWrapper(cursor)
        return self._cursor

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def cursor(self):
        return self._conn.cursor()

    @property
    def lastrowid(self):
        if self._cursor:
            return self._cursor.lastrowid
        return None


@with_retry
def get_connection():
    """Obtener conexion a la base de datos con reintentos automaticos"""
    if DB_TYPE == 'mysql':
        try:
            conn = MYSQL_POOL.connection()
            # Desactivar only_full_group_by para compatibilidad con SQLite
            cursor = conn.cursor()
            cursor.execute("SET SESSION sql_mode=(SELECT REPLACE(@@sql_mode,'ONLY_FULL_GROUP_BY',''))")
            cursor.close()
            return MySQLConnectionWrapper(conn)
        except Exception as e:
            logger.error(f"Error conectando a MySQL: {e}")
            raise
    else:
        try:
            os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
            conn = sqlite3.connect(DATABASE_PATH, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA busy_timeout = 30000")
            return conn
        except Exception as e:
            logger.error(f"Error conectando a SQLite: {e}")
            raise


def dict_from_row(row):
    """Convierte una fila a diccionario (compatible SQLite y MySQL)"""
    if row is None:
        return None
    if DB_TYPE == 'mysql':
        d = dict(row) if row else None
    else:
        d = dict(row) if row else None

    # Formatear fechas a espanol (convertir UTC a Colombia -5 horas)
    if d:
        from datetime import datetime, timedelta
        MESES_ES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        DIAS_ES = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom']
        for key, val in d.items():
            if isinstance(val, datetime):
                # Convertir UTC a Colombia (UTC-5)
                val_colombia = val - timedelta(hours=5)
                dia_semana = DIAS_ES[val_colombia.weekday()]
                mes = MESES_ES[val_colombia.month - 1]
                d[key] = f"{dia_semana}, {val_colombia.day:02d} {mes} {val_colombia.year}"
    return d



def get_placeholder():
    """Retorna el placeholder correcto para cada DB"""
    return '%s' if DB_TYPE == 'mysql' else '?'


def get_autoincrement():
    """Retorna la sintaxis de autoincrement"""
    return 'AUTO_INCREMENT' if DB_TYPE == 'mysql' else 'AUTOINCREMENT'


def init_database():
    """Inicializar la base de datos con todas las tablas"""
    conn = get_connection()
    cursor = conn.cursor()
    p = get_placeholder()
    auto = get_autoincrement()

    if DB_TYPE == 'mysql':
        # MySQL syntax
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS tiendas (
                id INT PRIMARY KEY {auto},
                nombre VARCHAR(255) NOT NULL,
                slug VARCHAR(100) UNIQUE NOT NULL,
                subdominio VARCHAR(100) UNIQUE NOT NULL,
                logo TEXT,
                color_primario VARCHAR(20) DEFAULT '#ff441f',
                color_secundario VARCHAR(20) DEFAULT '#00b14f',
                color_terciario VARCHAR(20) DEFAULT '#f5f5f5',
                telefono VARCHAR(50),
                direccion TEXT,
                horario VARCHAR(255),
                pedido_minimo DECIMAL(10,2) DEFAULT 50.0,
                costo_domicilio DECIMAL(10,2) DEFAULT 20.0,
                activo TINYINT DEFAULT 1,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT PRIMARY KEY {auto},
                tienda_id INT NOT NULL,
                email VARCHAR(255) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                nombre VARCHAR(255) NOT NULL,
                rol ENUM('superadmin', 'admin', 'cocina', 'repartidor') NOT NULL,
                activo TINYINT DEFAULT 1,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tienda_id) REFERENCES tiendas(id),
                UNIQUE KEY unique_tienda_email (tienda_id, email)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS categorias_maestras (
                id INT PRIMARY KEY {auto},
                nombre VARCHAR(255) UNIQUE NOT NULL,
                icono_url TEXT NOT NULL,
                orden INT DEFAULT 0,
                activo TINYINT DEFAULT 1
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS categorias (
                id INT PRIMARY KEY {auto},
                tienda_id INT NOT NULL,
                categoria_maestra_id INT,
                nombre VARCHAR(255) NOT NULL,
                descripcion TEXT,
                icono TEXT,
                orden INT DEFAULT 0,
                activo TINYINT DEFAULT 1,
                FOREIGN KEY (tienda_id) REFERENCES tiendas(id),
                FOREIGN KEY (categoria_maestra_id) REFERENCES categorias_maestras(id),
                UNIQUE KEY unique_tienda_categoria (tienda_id, nombre)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS productos (
                id INT PRIMARY KEY {auto},
                tienda_id INT NOT NULL,
                categoria_id INT,
                nombre VARCHAR(255) NOT NULL,
                descripcion TEXT,
                precio DECIMAL(10,2) NOT NULL,
                imagen TEXT,
                disponible TINYINT DEFAULT 1,
                destacado TINYINT DEFAULT 0,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tienda_id) REFERENCES tiendas(id),
                FOREIGN KEY (categoria_id) REFERENCES categorias(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS ofertas (
                id INT PRIMARY KEY {auto},
                tienda_id INT NOT NULL,
                titulo VARCHAR(255) NOT NULL,
                descripcion TEXT,
                tipo ENUM('porcentaje', 'precio_fijo', 'combo') NOT NULL,
                valor_descuento DECIMAL(10,2),
                precio_oferta DECIMAL(10,2),
                producto_id INT,
                productos_ids TEXT,
                imagen TEXT,
                activo TINYINT DEFAULT 1,
                fecha_inicio DATE,
                fecha_fin DATE,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tienda_id) REFERENCES tiendas(id),
                FOREIGN KEY (producto_id) REFERENCES productos(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS clientes (
                id INT PRIMARY KEY {auto},
                tienda_id INT NOT NULL,
                nombre VARCHAR(255) NOT NULL,
                telefono VARCHAR(50) NOT NULL,
                email VARCHAR(255),
                direccion TEXT,
                referencias TEXT,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tienda_id) REFERENCES tiendas(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS pedidos (
                id INT PRIMARY KEY {auto},
                tienda_id INT NOT NULL,
                cliente_id INT,
                numero_orden VARCHAR(50),
                tipo ENUM('domicilio', 'local', 'para_llevar') NOT NULL,
                estado VARCHAR(50) DEFAULT 'pendiente',
                subtotal DECIMAL(10,2) NOT NULL,
                costo_domicilio DECIMAL(10,2) DEFAULT 0,
                total DECIMAL(10,2) NOT NULL,
                notas TEXT,
                direccion_entrega TEXT,
                fecha_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_confirmado TIMESTAMP NULL,
                fecha_preparando TIMESTAMP NULL,
                fecha_listo TIMESTAMP NULL,
                fecha_entrega TIMESTAMP NULL,
                FOREIGN KEY (tienda_id) REFERENCES tiendas(id),
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS detalle_pedidos (
                id INT PRIMARY KEY {auto},
                pedido_id INT NOT NULL,
                producto_id INT NOT NULL,
                cantidad INT NOT NULL,
                precio_unitario DECIMAL(10,2) NOT NULL,
                subtotal DECIMAL(10,2) NOT NULL,
                notas TEXT,
                FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
                FOREIGN KEY (producto_id) REFERENCES productos(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
    else:
        # SQLite syntax (original)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tiendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                subdominio TEXT UNIQUE NOT NULL,
                logo TEXT,
                color_primario TEXT DEFAULT '#ff441f',
                color_secundario TEXT DEFAULT '#00b14f',
                color_terciario TEXT DEFAULT '#f5f5f5',
                telefono TEXT,
                direccion TEXT,
                horario TEXT,
                pedido_minimo REAL DEFAULT 50.0,
                costo_domicilio REAL DEFAULT 20.0,
                activo INTEGER DEFAULT 1,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tienda_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                nombre TEXT NOT NULL,
                rol TEXT NOT NULL CHECK(rol IN ('superadmin', 'admin', 'cocina', 'repartidor')),
                activo INTEGER DEFAULT 1,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tienda_id) REFERENCES tiendas(id),
                UNIQUE(tienda_id, email)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categorias_maestras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL,
                icono_url TEXT NOT NULL,
                orden INTEGER DEFAULT 0,
                activo INTEGER DEFAULT 1
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tienda_id INTEGER NOT NULL,
                categoria_maestra_id INTEGER,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                icono TEXT,
                orden INTEGER DEFAULT 0,
                activo INTEGER DEFAULT 1,
                FOREIGN KEY (tienda_id) REFERENCES tiendas(id),
                FOREIGN KEY (categoria_maestra_id) REFERENCES categorias_maestras(id),
                UNIQUE(tienda_id, nombre)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tienda_id INTEGER NOT NULL,
                categoria_id INTEGER,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                precio REAL NOT NULL,
                imagen TEXT,
                disponible INTEGER DEFAULT 1,
                destacado INTEGER DEFAULT 0,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tienda_id) REFERENCES tiendas(id),
                FOREIGN KEY (categoria_id) REFERENCES categorias(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ofertas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tienda_id INTEGER NOT NULL,
                titulo TEXT NOT NULL,
                descripcion TEXT,
                tipo TEXT NOT NULL CHECK(tipo IN ('porcentaje', 'precio_fijo', 'combo')),
                valor_descuento REAL,
                precio_oferta REAL,
                producto_id INTEGER,
                productos_ids TEXT,
                imagen TEXT,
                activo INTEGER DEFAULT 1,
                fecha_inicio DATE,
                fecha_fin DATE,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tienda_id) REFERENCES tiendas(id),
                FOREIGN KEY (producto_id) REFERENCES productos(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tienda_id INTEGER NOT NULL,
                nombre TEXT NOT NULL,
                telefono TEXT NOT NULL,
                email TEXT,
                direccion TEXT,
                referencias TEXT,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tienda_id) REFERENCES tiendas(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tienda_id INTEGER NOT NULL,
                cliente_id INTEGER,
                numero_orden TEXT,
                tipo TEXT NOT NULL CHECK(tipo IN ('domicilio', 'local', 'para_llevar')),
                estado TEXT DEFAULT 'pendiente',
                subtotal REAL NOT NULL,
                costo_domicilio REAL DEFAULT 0,
                total REAL NOT NULL,
                notas TEXT,
                direccion_entrega TEXT,
                fecha_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_confirmado TIMESTAMP,
                fecha_preparando TIMESTAMP,
                fecha_listo TIMESTAMP,
                fecha_entrega TIMESTAMP,
                FOREIGN KEY (tienda_id) REFERENCES tiendas(id),
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detalle_pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER NOT NULL,
                producto_id INTEGER NOT NULL,
                cantidad INTEGER NOT NULL,
                precio_unitario REAL NOT NULL,
                subtotal REAL NOT NULL,
                notas TEXT,
                FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
                FOREIGN KEY (producto_id) REFERENCES productos(id)
            )
        ''')

    # Insertar categorias maestras
    categorias_maestras = [
        ('Hamburguesas', 'https://cdn-icons-png.flaticon.com/128/3075/3075977.png', 1),
        ('Pizza', 'https://cdn-icons-png.flaticon.com/128/3595/3595458.png', 2),
        ('Hot Dogs', 'https://cdn-icons-png.flaticon.com/128/1046/1046751.png', 3),
        ('Papas Fritas', 'https://cdn-icons-png.flaticon.com/128/3480/3480618.png', 4),
        ('Sandwiches', 'https://cdn-icons-png.flaticon.com/128/3480/3480557.png', 5),
        ('Tacos', 'https://cdn-icons-png.flaticon.com/128/5787/5787016.png', 6),
        ('Burritos', 'https://cdn-icons-png.flaticon.com/128/5140/5140360.png', 7),
        ('Nachos', 'https://cdn-icons-png.flaticon.com/128/2515/2515183.png', 8),
        ('Quesadillas', 'https://cdn-icons-png.flaticon.com/128/2718/2718224.png', 9),
        ('Empanadas', 'https://cdn-icons-png.flaticon.com/128/5787/5787069.png', 10),
        ('Alitas', 'https://cdn-icons-png.flaticon.com/128/1046/1046769.png', 11),
        ('Nuggets', 'https://cdn-icons-png.flaticon.com/128/2674/2674505.png', 12),
        ('Sushi', 'https://cdn-icons-png.flaticon.com/128/2252/2252075.png', 13),
        ('Ramen', 'https://cdn-icons-png.flaticon.com/128/2276/2276931.png', 14),
        ('Pasta', 'https://cdn-icons-png.flaticon.com/128/3480/3480507.png', 18),
        ('Pollo', 'https://cdn-icons-png.flaticon.com/128/1046/1046751.png', 22),
        ('Carnes', 'https://cdn-icons-png.flaticon.com/128/3143/3143643.png', 23),
        ('Pescados', 'https://cdn-icons-png.flaticon.com/128/1046/1046747.png', 24),
        ('Mariscos', 'https://cdn-icons-png.flaticon.com/128/2252/2252076.png', 25),
        ('Sopas', 'https://cdn-icons-png.flaticon.com/128/2276/2276900.png', 29),
        ('Ensaladas', 'https://cdn-icons-png.flaticon.com/128/2515/2515263.png', 30),
        ('Postres', 'https://cdn-icons-png.flaticon.com/128/3081/3081967.png', 37),
        ('Helados', 'https://cdn-icons-png.flaticon.com/128/938/938063.png', 38),
        ('Bebidas', 'https://cdn-icons-png.flaticon.com/128/2738/2738730.png', 46),
        ('Jugos', 'https://cdn-icons-png.flaticon.com/128/2738/2738754.png', 47),
        ('Cafe', 'https://cdn-icons-png.flaticon.com/128/924/924514.png', 49),
        ('Combos', 'https://cdn-icons-png.flaticon.com/128/3081/3081840.png', 62),
        ('Ofertas', 'https://cdn-icons-png.flaticon.com/128/3081/3081886.png', 63),
    ]

    for nombre, icono_url, orden in categorias_maestras:
        try:
            if DB_TYPE == 'mysql':
                cursor.execute(f'''
                    INSERT IGNORE INTO categorias_maestras (nombre, icono_url, orden)
                    VALUES ({p}, {p}, {p})
                ''', (nombre, icono_url, orden))
            else:
                cursor.execute(f'''
                    INSERT OR IGNORE INTO categorias_maestras (nombre, icono_url, orden)
                    VALUES ({p}, {p}, {p})
                ''', (nombre, icono_url, orden))
        except:
            pass

    # REMOVIDO:     # Crear tienda demo
    # REMOVIDO:     try:
    # REMOVIDO:         if DB_TYPE == 'mysql':
    # REMOVIDO:             cursor.execute(f'''
    # REMOVIDO:                 INSERT IGNORE INTO tiendas (nombre, slug, subdominio, telefono, direccion, horario)
    # REMOVIDO:                 VALUES ({p}, {p}, {p}, {p}, {p}, {p})
    # REMOVIDO:             ''', ('Demo Restaurant', 'demo', 'demo', '555-0100', 'Calle Demo 123', '9:00 AM - 10:00 PM'))
    # REMOVIDO:         else:
    # REMOVIDO:             cursor.execute(f'''
    # REMOVIDO:                 INSERT OR IGNORE INTO tiendas (nombre, slug, subdominio, telefono, direccion, horario)
    # REMOVIDO:                 VALUES ({p}, {p}, {p}, {p}, {p}, {p})
    # REMOVIDO:             ''', ('Demo Restaurant', 'demo', 'demo', '555-0100', 'Calle Demo 123', '9:00 AM - 10:00 PM'))
    # REMOVIDO:     except:
    # REMOVIDO:         pass
    # REMOVIDO: 
    # REMOVIDO:     # Obtener ID de la tienda demo y crear usuarios
    # REMOVIDO:     cursor.execute(f"SELECT id FROM tiendas WHERE slug = {p}", ('demo',))
    # REMOVIDO:     tienda = cursor.fetchone()
    # REMOVIDO:     if tienda:
    # REMOVIDO:         tienda_id = tienda['id'] if DB_TYPE == 'mysql' else tienda[0]
    # REMOVIDO: 
    # REMOVIDO:         try:
    # REMOVIDO:             if DB_TYPE == 'mysql':
    # REMOVIDO:                 cursor.execute(f'''
    # REMOVIDO:                     INSERT IGNORE INTO usuarios (tienda_id, email, password_hash, nombre, rol)
    # REMOVIDO:                     VALUES ({p}, {p}, {p}, {p}, {p})
    # REMOVIDO:                 ''', (tienda_id, 'super@admin.com', generate_password_hash('super123'), 'Super Admin', 'superadmin'))
    # REMOVIDO: 
    # REMOVIDO:                 cursor.execute(f'''
    # REMOVIDO:                     INSERT IGNORE INTO usuarios (tienda_id, email, password_hash, nombre, rol)
    # REMOVIDO:                     VALUES ({p}, {p}, {p}, {p}, {p})
    # REMOVIDO:                 ''', (tienda_id, 'admin@demo.com', generate_password_hash('admin123'), 'Admin Demo', 'admin'))
    # REMOVIDO:             else:
    # REMOVIDO:                 cursor.execute(f'''
    # REMOVIDO:                     INSERT OR IGNORE INTO usuarios (tienda_id, email, password_hash, nombre, rol)
    # REMOVIDO:                     VALUES ({p}, {p}, {p}, {p}, {p})
    # REMOVIDO:                 ''', (tienda_id, 'super@admin.com', generate_password_hash('super123'), 'Super Admin', 'superadmin'))
    # REMOVIDO: 
    # REMOVIDO:                 cursor.execute(f'''
    # REMOVIDO:                     INSERT OR IGNORE INTO usuarios (tienda_id, email, password_hash, nombre, rol)
    # REMOVIDO:                     VALUES ({p}, {p}, {p}, {p}, {p})
    # REMOVIDO:                 ''', (tienda_id, 'admin@demo.com', generate_password_hash('admin123'), 'Admin Demo', 'admin'))
    # REMOVIDO:         except:
    # REMOVIDO:             pass
    # REMOVIDO: 
    conn.commit()
    conn.close()
    print(f"Base de datos inicializada correctamente (usando {DB_TYPE})")
    # REMOVIDO: 
    # REMOVIDO: 
# ============ CLASE TIENDA ============
class Tienda:
    @staticmethod
    def obtener_por_subdominio(subdominio):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT * FROM tiendas WHERE LOWER(subdominio) = LOWER({p}) AND activo = 1', (subdominio,))
        tienda = cursor.fetchone()
        conn.close()
        return dict_from_row(tienda)

    @staticmethod
    def obtener_por_id(tienda_id):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT * FROM tiendas WHERE id = {p}', (tienda_id,))
        tienda = cursor.fetchone()
        conn.close()
        return dict_from_row(tienda)

    @staticmethod
    def obtener_todas():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tiendas ORDER BY nombre')
        tiendas = [dict_from_row(row) for row in cursor.fetchall()]
        conn.close()
        return tiendas

    @staticmethod
    def crear(nombre, slug, subdominio, **kwargs):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                INSERT INTO tiendas (nombre, slug, subdominio, telefono, direccion, horario,
                                    pedido_minimo, costo_domicilio, color_primario)
                VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
            ''', (nombre, slug, subdominio,
                  kwargs.get('telefono', ''),
                  kwargs.get('direccion', ''),
                  kwargs.get('horario', ''),
                  kwargs.get('pedido_minimo', 50.0),
                  kwargs.get('costo_domicilio', 20.0),
                  kwargs.get('color_primario', '#ff441f')))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error creando tienda: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def actualizar(tienda_id, **kwargs):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        campos = []
        valores = []
        for key, value in kwargs.items():
            if key in ['nombre', 'telefono', 'direccion', 'horario', 'pedido_minimo',
                       'costo_domicilio', 'color_primario', 'color_secundario', 'color_terciario', 'logo', 'activo',
                       'slogan', 'banner_url', 'domicilios_activo', 'zona_cobertura', 'modo_pedido']:
                campos.append(f"{key} = {p}")
                valores.append(value)
        if campos:
            valores.append(tienda_id)
            cursor.execute(f"UPDATE tiendas SET {', '.join(campos)} WHERE id = {p}", valores)
            conn.commit()
        conn.close()


# ============ CLASE USUARIO ============
class Usuario:
    @staticmethod
    def validar(email, password, tienda_id=None):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        if tienda_id:
            cursor.execute(f'''
                SELECT * FROM usuarios WHERE LOWER(email) = LOWER({p}) AND tienda_id = {p} AND activo = 1
            ''', (email, tienda_id))
        else:
            cursor.execute(f'''
                SELECT * FROM usuarios WHERE LOWER(email) = LOWER({p}) AND activo = 1
            ''', (email,))
        user = cursor.fetchone()
        conn.close()
        if user:
            user_dict = dict_from_row(user)
            if check_password_hash(user_dict['password_hash'], password):
                return user_dict
        return None

    @staticmethod
    def obtener_por_id(user_id):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT * FROM usuarios WHERE id = {p}', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return dict_from_row(user)

    @staticmethod
    def obtener_por_tienda(tienda_id):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT * FROM usuarios WHERE tienda_id = {p} ORDER BY nombre', (tienda_id,))
        usuarios = [dict_from_row(row) for row in cursor.fetchall()]
        conn.close()
        return usuarios

    @staticmethod
    def crear(tienda_id, email, password, nombre, rol):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                INSERT INTO usuarios (tienda_id, email, password_hash, nombre, rol)
                VALUES ({p}, {p}, {p}, {p}, {p})
            ''', (tienda_id, email, generate_password_hash(password), nombre, rol))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error creando usuario: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def actualizar(user_id, **kwargs):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        try:
            updates = []
            params = []
            for key, value in kwargs.items():
                if key == 'password' and value:
                    updates.append(f'password_hash = {p}')
                    params.append(generate_password_hash(value))
                elif key in ['nombre', 'email', 'rol', 'activo']:
                    updates.append(f'{key} = {p}')
                    params.append(value)
            if updates:
                params.append(user_id)
                cursor.execute(f'UPDATE usuarios SET {", ".join(updates)} WHERE id = {p}', params)
                conn.commit()
            return True
        except Exception as e:
            print(f"Error actualizando usuario: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def eliminar(user_id):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'DELETE FROM usuarios WHERE id = {p}', (user_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error eliminando usuario: {e}")
            return False
        finally:
            conn.close()


# ============ CLASE CATEGORIA MAESTRA ============
class CategoriaMaestra:
    @staticmethod
    def obtener_todas(solo_activas=True):
        conn = get_connection()
        cursor = conn.cursor()
        query = 'SELECT * FROM categorias_maestras'
        if solo_activas:
            query += ' WHERE activo = 1'
        query += ' ORDER BY orden'
        cursor.execute(query)
        categorias = [dict_from_row(row) for row in cursor.fetchall()]
        conn.close()
        return categorias

    @staticmethod
    def obtener_por_id(categoria_id):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT * FROM categorias_maestras WHERE id = {p}', (categoria_id,))
        cat = cursor.fetchone()
        conn.close()
        return dict_from_row(cat)

    @staticmethod
    def crear(nombre, icono_url, orden=0):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                INSERT INTO categorias_maestras (nombre, icono_url, orden)
                VALUES ({p}, {p}, {p})
            ''', (nombre, icono_url, orden))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error creando categoria maestra: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def actualizar(categoria_id, **kwargs):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        campos = []
        valores = []
        for key, value in kwargs.items():
            if key in ['nombre', 'icono_url', 'orden', 'activo']:
                campos.append(f"{key} = {p}")
                valores.append(value)
        if campos:
            valores.append(categoria_id)
            cursor.execute(f"UPDATE categorias_maestras SET {', '.join(campos)} WHERE id = {p}", valores)
            conn.commit()
        conn.close()

    @staticmethod
    def eliminar(categoria_id):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'UPDATE categorias_maestras SET activo = 0 WHERE id = {p}', (categoria_id,))
        conn.commit()
        conn.close()

    @staticmethod
    def asignar_a_tienda(tienda_id, categoria_maestra_id, orden=0):
        p = get_placeholder()
        maestra = CategoriaMaestra.obtener_por_id(categoria_maestra_id)
        if not maestra:
            return None
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Verificar si ya existe la categoria para esta tienda (por maestra_id)
            cursor.execute(f'''
                SELECT id, activo FROM categorias
                WHERE tienda_id = {p} AND categoria_maestra_id = {p}
            ''', (tienda_id, categoria_maestra_id))
            existente = cursor.fetchone()

            if existente:
                # Si existe pero está inactiva, activarla y actualizar icono
                cursor.execute(f'''
                    UPDATE categorias SET activo = 1, orden = {p}, icono = {p}
                    WHERE tienda_id = {p} AND categoria_maestra_id = {p}
                ''', (orden, maestra['icono_url'], tienda_id, categoria_maestra_id))
                conn.commit()
                return existente[0] if isinstance(existente, tuple) else existente['id']

            # Verificar si existe una categoria con el mismo nombre pero sin vincular
            cursor.execute(f'''
                SELECT id FROM categorias
                WHERE tienda_id = {p} AND nombre = {p} AND categoria_maestra_id IS NULL
            ''', (tienda_id, maestra['nombre']))
            sin_vincular = cursor.fetchone()

            if sin_vincular:
                # Vincular la categoria existente con la maestra y actualizar icono
                cat_id = sin_vincular[0] if isinstance(sin_vincular, tuple) else sin_vincular['id']
                cursor.execute(f'''
                    UPDATE categorias SET categoria_maestra_id = {p}, icono = {p}, activo = 1, orden = {p}
                    WHERE id = {p}
                ''', (categoria_maestra_id, maestra['icono_url'], orden, cat_id))
                conn.commit()
                return cat_id
            else:
                # Si no existe, crearla
                cursor.execute(f'''
                    INSERT INTO categorias (tienda_id, categoria_maestra_id, nombre, icono, orden, activo)
                    VALUES ({p}, {p}, {p}, {p}, {p}, 1)
                ''', (tienda_id, categoria_maestra_id, maestra['nombre'], maestra['icono_url'], orden))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Error asignando categoria: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def obtener_para_tienda(tienda_id):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT cm.*,
                   CASE WHEN c.id IS NOT NULL AND c.activo = 1 THEN 1 ELSE 0 END as asignada,
                   c.id as categoria_tienda_id
            FROM categorias_maestras cm
            LEFT JOIN categorias c ON cm.id = c.categoria_maestra_id AND c.tienda_id = {p}
            WHERE cm.activo = 1
            ORDER BY cm.orden
        ''', (tienda_id,))
        categorias = [dict_from_row(row) for row in cursor.fetchall()]
        conn.close()
        return categorias


# ============ CLASE CATEGORIA ============
class Categoria:
    @staticmethod
    def obtener_por_tienda(tienda_id, solo_activas=True):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        # JOIN con categorias_maestras para obtener el icono
        query = f'''
            SELECT c.*,
                   COALESCE(c.icono, cm.icono_url) as icono_url
            FROM categorias c
            LEFT JOIN categorias_maestras cm ON c.categoria_maestra_id = cm.id
            WHERE c.tienda_id = {p}
        '''
        if solo_activas:
            query += ' AND c.activo = 1'
        query += ' ORDER BY c.orden'
        cursor.execute(query, (tienda_id,))
        categorias = [dict_from_row(row) for row in cursor.fetchall()]
        conn.close()
        return categorias

    @staticmethod
    def crear(tienda_id, nombre, descripcion='', orden=0):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f'''
                INSERT INTO categorias (tienda_id, nombre, descripcion, orden)
                VALUES ({p}, {p}, {p}, {p})
            ''', (tienda_id, nombre, descripcion, orden))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error creando categoria: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def actualizar(categoria_id, **kwargs):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        campos = []
        valores = []
        for key, value in kwargs.items():
            if key in ['nombre', 'descripcion', 'orden', 'activo', 'icono']:
                campos.append(f"{key} = {p}")
                valores.append(value)
        if campos:
            valores.append(categoria_id)
            cursor.execute(f"UPDATE categorias SET {', '.join(campos)} WHERE id = {p}", valores)
            conn.commit()
        conn.close()

    @staticmethod
    def eliminar(categoria_id):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'UPDATE categorias SET activo = 0 WHERE id = {p}', (categoria_id,))
        conn.commit()
        conn.close()


# ============ CLASE PRODUCTO ============
class Producto:
    @staticmethod
    def obtener_por_tienda(tienda_id, categoria_id=None, solo_disponibles=False):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        query = f'''
            SELECT p.*, c.nombre as categoria_nombre
            FROM productos p
            LEFT JOIN categorias c ON p.categoria_id = c.id
            WHERE p.tienda_id = {p}
        '''
        params = [tienda_id]

        if categoria_id:
            query += f' AND p.categoria_id = {p}'
            params.append(categoria_id)

        if solo_disponibles:
            query += ' AND p.disponible = 1'

        query += ' ORDER BY c.orden, p.nombre'
        cursor.execute(query, params)
        productos = [dict_from_row(row) for row in cursor.fetchall()]

        # Cargar variantes para todos los productos en una sola query (optimizado)
        if productos:
            producto_ids = [prod['id'] for prod in productos]
            placeholders = ','.join(['%s'] * len(producto_ids))
            cursor.execute(f'''
                SELECT id, producto_id, nombre, precio, disponible, orden
                FROM producto_variantes
                WHERE producto_id IN ({placeholders}) AND disponible = 1
                ORDER BY producto_id, orden, nombre
            ''', producto_ids)

            # Agrupar variantes por producto_id
            variantes_map = {}
            for row in cursor.fetchall():
                var = dict_from_row(row)
                pid = var['producto_id']
                if pid not in variantes_map:
                    variantes_map[pid] = []
                variantes_map[pid].append(var)

            # Asignar variantes a cada producto
            for producto in productos:
                variantes = variantes_map.get(producto['id'], [])
                producto['variantes'] = variantes
                producto['tiene_variantes'] = len(variantes) > 0

        conn.close()
        return productos

    @staticmethod
    def obtener_por_id(producto_id):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT * FROM productos WHERE id = {p}', (producto_id,))
        producto = cursor.fetchone()
        conn.close()
        return dict_from_row(producto)

    @staticmethod
    def crear(tienda_id, nombre, precio, categoria_id=None, descripcion='', imagen=''):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            INSERT INTO productos (tienda_id, categoria_id, nombre, descripcion, precio, imagen)
            VALUES ({p}, {p}, {p}, {p}, {p}, {p})
        ''', (tienda_id, categoria_id, nombre, descripcion, precio, imagen))
        conn.commit()
        producto_id = cursor.lastrowid
        conn.close()
        return producto_id

    @staticmethod
    def actualizar(producto_id, **kwargs):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        campos = []
        valores = []
        for key, value in kwargs.items():
            if key in ['nombre', 'descripcion', 'precio', 'categoria_id', 'imagen', 'disponible', 'destacado']:
                campos.append(f"{key} = {p}")
                valores.append(value)
        if campos:
            valores.append(producto_id)
            cursor.execute(f"UPDATE productos SET {', '.join(campos)} WHERE id = {p}", valores)
            conn.commit()
        conn.close()

    @staticmethod
    def eliminar(producto_id):
        """Eliminar producto y sus referencias en pedidos."""
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Primero eliminar variantes
            cursor.execute(f'DELETE FROM producto_variantes WHERE producto_id = {p}', (producto_id,))
            # Eliminar referencias en detalle_pedidos
            cursor.execute(f'DELETE FROM detalle_pedidos WHERE producto_id = {p}', (producto_id,))
            # Luego eliminar el producto
            cursor.execute(f'DELETE FROM productos WHERE id = {p}', (producto_id,))
            conn.commit()
            return {'success': True, 'deleted': True}
        except Exception as e:
            conn.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()

    @staticmethod
    def crear_variante(producto_id, nombre, precio, disponible=1, orden=0):
        """Crear una variante para un producto"""
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            INSERT INTO producto_variantes (producto_id, nombre, precio, disponible, orden)
            VALUES ({p}, {p}, {p}, {p}, {p})
        ''', (producto_id, nombre, precio, disponible, orden))
        conn.commit()
        variante_id = cursor.lastrowid
        conn.close()
        return variante_id

    @staticmethod
    def obtener_variantes(producto_id):
        """Obtener variantes de un producto"""
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT id, nombre, precio, disponible, orden
            FROM producto_variantes
            WHERE producto_id = {p}
            ORDER BY orden, nombre
        ''', (producto_id,))
        variantes = [dict_from_row(row) for row in cursor.fetchall()]
        conn.close()
        return variantes

    @staticmethod
    def eliminar_variantes(producto_id):
        """Eliminar todas las variantes de un producto"""
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'DELETE FROM producto_variantes WHERE producto_id = {p}', (producto_id,))
        conn.commit()
        conn.close()


# ============ CLASE OFERTA ============
class Oferta:
    @staticmethod
    def obtener_por_tienda(tienda_id, solo_activas=False):
        import json
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()

        if DB_TYPE == 'mysql':
            date_func = "CURDATE()"
        else:
            date_func = "DATE('now', 'localtime')"

        query = f'''
            SELECT o.*, p.nombre as producto_nombre, p.precio as producto_precio
            FROM ofertas o
            LEFT JOIN productos p ON o.producto_id = p.id
            WHERE o.tienda_id = {p}
        '''
        if solo_activas:
            query += f''' AND o.activo = 1
                         AND (o.fecha_inicio IS NULL OR DATE(o.fecha_inicio) <= {date_func})
                         AND (o.fecha_fin IS NULL OR DATE(o.fecha_fin) >= {date_func})'''
        query += ' ORDER BY o.fecha_creacion DESC'
        cursor.execute(query, (tienda_id,))
        ofertas = []
        for row in cursor.fetchall():
            oferta = dict_from_row(row)
            # Si valor_descuento es None, extraer del titulo ("20% de descuento" -> 20)
            if not oferta.get('valor_descuento'):
                import re
                titulo = oferta.get('titulo', '')
                match = re.search(r'(\d+)%', titulo)
                if match:
                    oferta['valor_descuento'] = int(match.group(1))
                else:
                    oferta['valor_descuento'] = 0
            if oferta.get('productos_ids'):
                try:
                    prod_ids = json.loads(oferta['productos_ids'])
                    if prod_ids:
                        placeholders = ','.join([p] * len(prod_ids))
                        cursor.execute(f'SELECT nombre FROM productos WHERE id IN ({placeholders})', prod_ids)
                        nombres = [dict_from_row(r)['nombre'] for r in cursor.fetchall()]
                        oferta['productos_nombres'] = ', '.join(nombres)
                except:
                    oferta['productos_nombres'] = oferta.get('producto_nombre', '')
            else:
                oferta['productos_nombres'] = oferta.get('producto_nombre', '')
            ofertas.append(oferta)
        conn.close()
        return ofertas

    @staticmethod
    def crear(tienda_id, titulo, tipo, **kwargs):
        import json
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        productos = kwargs.get('productos')
        producto_id = kwargs.get('producto_id')
        productos_json = None
        if productos:
            productos_json = json.dumps(productos) if isinstance(productos, list) else productos
        elif producto_id:
            productos_json = json.dumps([producto_id])

        activo = kwargs.get('activo', 1)

        cursor.execute(f'''
            INSERT INTO ofertas (tienda_id, titulo, descripcion, tipo, valor_descuento,
                                precio_oferta, producto_id, productos_ids, fecha_inicio, fecha_fin, imagen, activo)
            VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
        ''', (tienda_id, titulo, kwargs.get('descripcion'),
              tipo, kwargs.get('valor_descuento') or kwargs.get('valor'), kwargs.get('precio_oferta'),
              producto_id, productos_json, kwargs.get('fecha_inicio'), kwargs.get('fecha_fin'),
              kwargs.get('imagen'), activo))
        conn.commit()
        oferta_id = cursor.lastrowid
        conn.close()
        return oferta_id

    @staticmethod
    def obtener_por_id(oferta_id):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT o.*, p.nombre as producto_nombre, p.precio as producto_precio
            FROM ofertas o
            LEFT JOIN productos p ON o.producto_id = p.id
            WHERE o.id = {p}
        ''', (oferta_id,))
        oferta = cursor.fetchone()
        conn.close()
        return dict_from_row(oferta)

    @staticmethod
    def actualizar(oferta_id, **kwargs):
        import json
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()

        # Procesar productos_ids
        productos = kwargs.get('productos')
        productos_json = None
        if productos:
            productos_json = json.dumps(productos) if isinstance(productos, list) else productos

        cursor.execute(f'''
            UPDATE ofertas SET
                titulo = {p}, descripcion = {p}, tipo = {p}, valor_descuento = {p},
                precio_oferta = {p}, producto_id = {p}, productos_ids = {p},
                fecha_inicio = {p}, fecha_fin = {p}, imagen = {p}, activo = {p}
            WHERE id = {p}
        ''', (kwargs.get('titulo'), kwargs.get('descripcion'),
              kwargs.get('tipo'), kwargs.get('valor_descuento'),
              kwargs.get('precio_oferta'), kwargs.get('producto_id'), productos_json,
              kwargs.get('fecha_inicio'), kwargs.get('fecha_fin'),
              kwargs.get('imagen'), kwargs.get('activo', 1), oferta_id))
        conn.commit()
        conn.close()

    @staticmethod
    def toggle(oferta_id):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        if DB_TYPE == 'mysql':
            cursor.execute(f'UPDATE ofertas SET activo = NOT activo WHERE id = {p}', (oferta_id,))
        else:
            cursor.execute(f'UPDATE ofertas SET activo = NOT activo WHERE id = {p}', (oferta_id,))
        conn.commit()
        cursor.execute(f'SELECT activo FROM ofertas WHERE id = {p}', (oferta_id,))
        result = cursor.fetchone()
        conn.close()
        return dict_from_row(result)['activo'] if result else None

    @staticmethod
    def eliminar(oferta_id):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'DELETE FROM ofertas WHERE id = {p}', (oferta_id,))
        conn.commit()
        conn.close()


# ============ CLASE CLIENTE ============
class Cliente:
    @staticmethod
    def buscar_por_telefono(tienda_id, telefono):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'SELECT * FROM clientes WHERE tienda_id = {p} AND telefono = {p}',
                       (tienda_id, telefono))
        cliente = cursor.fetchone()
        conn.close()
        return dict_from_row(cliente)

    @staticmethod
    def crear(tienda_id, nombre, telefono, direccion, email='', referencias=''):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            INSERT INTO clientes (tienda_id, nombre, telefono, email, direccion, referencias)
            VALUES ({p}, {p}, {p}, {p}, {p}, {p})
        ''', (tienda_id, nombre, telefono, email, direccion, referencias))
        conn.commit()
        cliente_id = cursor.lastrowid
        conn.close()
        return cliente_id


# ============ CLASE PEDIDO ============
class Pedido:
    @staticmethod
    def generar_numero_orden(tienda_id):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        if DB_TYPE == 'mysql':
            cursor.execute(f'''
                SELECT COUNT(*) + 1 as num FROM pedidos
                WHERE tienda_id = {p} AND DATE(fecha_pedido) = CURDATE()
            ''', (tienda_id,))
        else:
            cursor.execute(f'''
                SELECT COUNT(*) + 1 as num FROM pedidos
                WHERE tienda_id = {p} AND DATE(fecha_pedido) = DATE('now', 'localtime')
            ''', (tienda_id,))
        result = cursor.fetchone()
        num = dict_from_row(result)['num']
        conn.close()
        return f"{datetime.now().strftime('%Y%m%d')}-{num:04d}"

    @staticmethod
    def crear(tienda_id, cliente_id, tipo, subtotal, costo_domicilio, total, **kwargs):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        numero_orden = Pedido.generar_numero_orden(tienda_id)
        mesero_id = kwargs.get('mesero_id')
        cursor.execute(f'''
            INSERT INTO pedidos (tienda_id, cliente_id, mesero_id, numero_orden, tipo, subtotal,
                                costo_domicilio, total, direccion_entrega, notas)
            VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
        ''', (tienda_id, cliente_id, mesero_id, numero_orden, tipo, subtotal, costo_domicilio, total,
              kwargs.get('direccion_entrega', ''), kwargs.get('notas', '')))
        conn.commit()
        pedido_id = cursor.lastrowid
        conn.close()
        return pedido_id, numero_orden

    @staticmethod
    def agregar_detalle(pedido_id, producto_id, cantidad, precio_unitario, notas=''):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        subtotal = cantidad * precio_unitario
        cursor.execute(f'''
            INSERT INTO detalle_pedidos (pedido_id, producto_id, cantidad, precio_unitario, subtotal, notas)
            VALUES ({p}, {p}, {p}, {p}, {p}, {p})
        ''', (pedido_id, producto_id, cantidad, precio_unitario, subtotal, notas))
        conn.commit()
        conn.close()

    @staticmethod
    def agregar_detalle_oferta(pedido_id, oferta_id, cantidad, precio_unitario, notas=''):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        subtotal = cantidad * precio_unitario
        cursor.execute(f'''
            INSERT INTO detalle_pedidos (pedido_id, oferta_id, cantidad, precio_unitario, subtotal, notas)
            VALUES ({p}, {p}, {p}, {p}, {p}, {p})
        ''', (pedido_id, oferta_id, cantidad, precio_unitario, subtotal, notas))
        conn.commit()
        conn.close()

    @staticmethod
    def obtener_por_tienda(tienda_id, estado=None, limite=50):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        query = f'''
            SELECT p.*, c.nombre as cliente_nombre, c.telefono as cliente_telefono
            FROM pedidos p
            LEFT JOIN clientes c ON p.cliente_id = c.id
            WHERE p.tienda_id = {p}
        '''
        params = [tienda_id]

        if estado:
            query += f' AND p.estado = {p}'
            params.append(estado)

        query += f' ORDER BY p.fecha_pedido DESC LIMIT {limite}'
        cursor.execute(query, params)
        pedidos = [dict_from_row(row) for row in cursor.fetchall()]
        conn.close()
        return pedidos

    @staticmethod
    def obtener_para_cocina(tienda_id):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT p.*, c.nombre as cliente_nombre, c.telefono as cliente_telefono
            FROM pedidos p
            LEFT JOIN clientes c ON p.cliente_id = c.id
            WHERE p.tienda_id = {p} AND p.estado IN ('pendiente', 'confirmado', 'preparando')
            ORDER BY
                CASE p.estado
                    WHEN 'pendiente' THEN 1
                    WHEN 'confirmado' THEN 2
                    WHEN 'preparando' THEN 3
                END,
                p.fecha_pedido ASC
        ''', (tienda_id,))
        pedidos = [dict_from_row(row) for row in cursor.fetchall()]
        conn.close()
        return pedidos

    @staticmethod
    def obtener_detalle(pedido_id):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT dp.*, COALESCE(pr.nombre, 'Producto eliminado') as producto_nombre
            FROM detalle_pedidos dp
            LEFT JOIN productos pr ON dp.producto_id = pr.id
            WHERE dp.pedido_id = {p}
        ''', (pedido_id,))
        detalles = []
        for row in cursor.fetchall():
            item = dict_from_row(row)
            # Si es una oferta, extraer el nombre de las notas
            notas = item.get('notas', '') or ''
            if notas.startswith('[OFERTA]'):
                item['producto_nombre'] = notas.replace('[OFERTA] ', '').strip()
                item['es_oferta'] = True
            detalles.append(item)
        conn.close()
        return detalles

    @staticmethod
    def actualizar_estado(pedido_id, nuevo_estado):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()
        timestamp_field = {
            'confirmado': 'fecha_confirmado',
            'preparando': 'fecha_preparando',
            'listo': 'fecha_listo',
            'entregado': 'fecha_entrega'
        }.get(nuevo_estado)

        if timestamp_field:
            if DB_TYPE == 'mysql':
                cursor.execute(f'''
                    UPDATE pedidos SET estado = {p}, {timestamp_field} = NOW()
                    WHERE id = {p}
                ''', (nuevo_estado, pedido_id))
            else:
                cursor.execute(f'''
                    UPDATE pedidos SET estado = {p}, {timestamp_field} = CURRENT_TIMESTAMP
                    WHERE id = {p}
                ''', (nuevo_estado, pedido_id))
        else:
            cursor.execute(f'UPDATE pedidos SET estado = {p} WHERE id = {p}', (nuevo_estado, pedido_id))
        conn.commit()
        conn.close()

    @staticmethod
    def obtener_estadisticas(tienda_id):
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()

        if DB_TYPE == 'mysql':
            date_func = "CURDATE()"
        else:
            date_func = "DATE('now', 'localtime')"

        cursor.execute(f'''
            SELECT COUNT(*) as total_pedidos, COALESCE(SUM(total), 0) as total_ventas
            FROM pedidos
            WHERE tienda_id = {p} AND DATE(fecha_pedido) = {date_func}
            AND estado != 'cancelado'
        ''', (tienda_id,))
        stats = dict_from_row(cursor.fetchone())
        stats["total_ventas"] = float(stats.get("total_ventas", 0))

        cursor.execute(f'''
            SELECT estado, COUNT(*) as cantidad
            FROM pedidos
            WHERE tienda_id = {p} AND DATE(fecha_pedido) = {date_func}
            GROUP BY estado
        ''', (tienda_id,))
        stats['por_estado'] = {dict_from_row(row)['estado']: dict_from_row(row)['cantidad'] for row in cursor.fetchall()}

        # Top productos vendidos del día
        cursor.execute(f'''
            SELECT pr.nombre, SUM(dp.cantidad) as cantidad, SUM(dp.subtotal) as total_vendido
            FROM detalle_pedidos dp
            JOIN pedidos p ON dp.pedido_id = p.id
            JOIN productos pr ON dp.producto_id = pr.id
            WHERE p.tienda_id = {p} AND DATE(p.fecha_pedido) = {date_func}
            AND p.estado != 'cancelado'
            GROUP BY dp.producto_id, pr.nombre
            ORDER BY cantidad DESC
            LIMIT 5
        ''', (tienda_id,))
        stats['productos_top'] = []
        for row in cursor.fetchall():
            item = dict_from_row(row)
            item['cantidad'] = int(item.get('cantidad', 0) or 0)
            item['total_vendido'] = float(item.get('total_vendido', 0) or 0)
            stats['productos_top'].append(item)

        conn.close()
        return stats

    @staticmethod
    def reporte_ventas_periodo(tienda_id, fecha_inicio, fecha_fin):
        """Reporte de ventas por día en un período"""
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()

        if DB_TYPE == 'mysql':
            query = f"""
                SELECT
                    DATE(CONVERT_TZ(fecha_pedido, '+00:00', '-05:00')) as fecha,
                    COUNT(*) as total_pedidos,
                    COALESCE(SUM(total), 0) as total_ventas,
                    COALESCE(AVG(total), 0) as promedio
                FROM pedidos
                WHERE tienda_id = {p}
                AND DATE(CONVERT_TZ(fecha_pedido, '+00:00', '-05:00')) BETWEEN {p} AND {p}
                AND estado != 'cancelado'
                GROUP BY DATE(CONVERT_TZ(fecha_pedido, '+00:00', '-05:00'))
                ORDER BY fecha DESC
            """
        else:
            query = f"""
                SELECT
                    DATE(fecha_pedido) as fecha,
                    COUNT(*) as total_pedidos,
                    COALESCE(SUM(total), 0) as total_ventas,
                    COALESCE(AVG(total), 0) as promedio
                FROM pedidos
                WHERE tienda_id = {p}
                AND DATE(fecha_pedido) BETWEEN {p} AND {p}
                AND estado != 'cancelado'
                GROUP BY DATE(fecha_pedido)
                ORDER BY fecha DESC
            """

        cursor.execute(query, (tienda_id, fecha_inicio, fecha_fin))
        results = []
        for row in cursor.fetchall():
            item = dict_from_row(row)
            item['total_ventas'] = float(item.get('total_ventas', 0) or 0)
            item['promedio'] = float(item.get('promedio', 0) or 0)
            results.append(item)
        conn.close()
        return results

    @staticmethod
    def estadisticas_meseros(tienda_id, filtro='hoy', fecha_inicio=None, fecha_fin=None):
        """Estadísticas de ventas por mesero"""
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()

        # Construir filtro de fecha (Colombia es UTC-5)
        if DB_TYPE == 'mysql':
            if filtro == 'hoy':
                fecha_filter = "DATE(CONVERT_TZ(p.fecha_pedido, '+00:00', '-05:00')) = DATE(CONVERT_TZ(NOW(), '+00:00', '-05:00'))"
            elif filtro == 'semana':
                fecha_filter = "DATE(CONVERT_TZ(p.fecha_pedido, '+00:00', '-05:00')) >= DATE_SUB(DATE(CONVERT_TZ(NOW(), '+00:00', '-05:00')), INTERVAL 7 DAY)"
            elif filtro == 'mes':
                fecha_filter = "DATE(CONVERT_TZ(p.fecha_pedido, '+00:00', '-05:00')) >= DATE_SUB(DATE(CONVERT_TZ(NOW(), '+00:00', '-05:00')), INTERVAL 30 DAY)"
            elif filtro == 'rango' and fecha_inicio and fecha_fin:
                fecha_filter = f"DATE(CONVERT_TZ(p.fecha_pedido, '+00:00', '-05:00')) BETWEEN '{fecha_inicio}' AND '{fecha_fin}'"
            else:
                fecha_filter = "1=1"
        else:
            if filtro == 'hoy':
                fecha_filter = "DATE(p.fecha_pedido) = DATE('now', 'localtime')"
            elif filtro == 'semana':
                fecha_filter = "DATE(p.fecha_pedido) >= DATE('now', '-7 days')"
            elif filtro == 'mes':
                fecha_filter = "DATE(p.fecha_pedido) >= DATE('now', '-30 days')"
            elif filtro == 'rango' and fecha_inicio and fecha_fin:
                fecha_filter = f"DATE(p.fecha_pedido) BETWEEN '{fecha_inicio}' AND '{fecha_fin}'"
            else:
                fecha_filter = "1=1"

        query = f"""
            SELECT
                u.id as mesero_id,
                u.nombre as mesero_nombre,
                COUNT(p.id) as total_pedidos,
                COALESCE(SUM(p.total), 0) as total_ventas,
                COALESCE(AVG(p.total), 0) as promedio_pedido
            FROM usuarios u
            LEFT JOIN pedidos p ON p.mesero_id = u.id
                AND p.tienda_id = {p}
                AND p.estado != 'cancelado'
                AND {fecha_filter}
            WHERE u.tienda_id = {p} AND u.rol IN ('mesero', 'admin')
            GROUP BY u.id, u.nombre
            ORDER BY total_ventas DESC
        """

        cursor.execute(query, (tienda_id, tienda_id))
        results = []
        for row in cursor.fetchall():
            item = dict_from_row(row)
            item['total_ventas'] = float(item.get('total_ventas', 0) or 0)
            item['promedio_pedido'] = float(item.get('promedio_pedido', 0) or 0)
            results.append(item)
        conn.close()
        return results

    @staticmethod
    def obtener_por_mesero(tienda_id, mesero_id, filtro='hoy', fecha_inicio=None, fecha_fin=None):
        """Obtener pedidos de un mesero específico"""
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()

        # Construir filtro de fecha (Colombia es UTC-5)
        if DB_TYPE == 'mysql':
            if filtro == 'hoy':
                fecha_filter = "DATE(CONVERT_TZ(fecha_pedido, '+00:00', '-05:00')) = DATE(CONVERT_TZ(NOW(), '+00:00', '-05:00'))"
            elif filtro == 'semana':
                fecha_filter = "DATE(CONVERT_TZ(fecha_pedido, '+00:00', '-05:00')) >= DATE_SUB(DATE(CONVERT_TZ(NOW(), '+00:00', '-05:00')), INTERVAL 7 DAY)"
            elif filtro == 'mes':
                fecha_filter = "DATE(CONVERT_TZ(fecha_pedido, '+00:00', '-05:00')) >= DATE_SUB(DATE(CONVERT_TZ(NOW(), '+00:00', '-05:00')), INTERVAL 30 DAY)"
            elif filtro == 'rango' and fecha_inicio and fecha_fin:
                fecha_filter = f"DATE(CONVERT_TZ(fecha_pedido, '+00:00', '-05:00')) BETWEEN '{fecha_inicio}' AND '{fecha_fin}'"
            else:
                fecha_filter = "1=1"
        else:
            if filtro == 'hoy':
                fecha_filter = "DATE(fecha_pedido) = DATE('now', 'localtime')"
            elif filtro == 'semana':
                fecha_filter = "DATE(fecha_pedido) >= DATE('now', '-7 days')"
            elif filtro == 'mes':
                fecha_filter = "DATE(fecha_pedido) >= DATE('now', '-30 days')"
            elif filtro == 'rango' and fecha_inicio and fecha_fin:
                fecha_filter = f"DATE(fecha_pedido) BETWEEN '{fecha_inicio}' AND '{fecha_fin}'"
            else:
                fecha_filter = "1=1"

        query = f"""
            SELECT id, total, estado, fecha_pedido
            FROM pedidos
            WHERE tienda_id = {p} AND mesero_id = {p}
            AND estado != 'cancelado' AND {fecha_filter}
            ORDER BY fecha_pedido DESC
        """

        cursor.execute(query, (tienda_id, mesero_id))
        results = []
        for row in cursor.fetchall():
            item = dict_from_row(row)
            item['total'] = float(item.get('total', 0) or 0)
            results.append(item)
        conn.close()
        return results


if __name__ == '__main__':
    init_database()
