"""
Aplicacion Web Multi-Tenant para Sistema de Restaurantes
Soporta subdominios: tienda1.tudominio.com, tienda2.tudominio.com, etc.
"""
from flask import Flask, g, request, redirect, url_for, render_template, session, flash, jsonify, send_from_directory
from flask_caching import Cache
from decimal import Decimal
import json
import logging
import traceback
from functools import wraps
from werkzeug.utils import secure_filename
import uuid
import os
import hmac
import hashlib
import time

# Cargar variables de entorno desde .env o .env.local
from dotenv import load_dotenv
if os.path.exists('.env.local'):
    load_dotenv('.env.local')
else:
    load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('app')

from superadmin_routes import superadmin_bp
from models import (
    init_database, Tienda, Usuario, Categoria, Producto,
    Oferta, Cliente, Pedido, get_connection
)

app = Flask(__name__)

# ============ CONFIGURACION DE CACHE CON REDIS ============
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Configurar cache - usa Redis si esta disponible, sino memoria
try:
    import redis
    r = redis.from_url(REDIS_URL)
    r.ping()
    cache_config = {
        'CACHE_TYPE': 'RedisCache',
        'CACHE_REDIS_URL': REDIS_URL,
        'CACHE_DEFAULT_TIMEOUT': 300  # 5 minutos
    }
    print("Cache: Usando Redis")
except:
    cache_config = {
        'CACHE_TYPE': 'SimpleCache',
        'CACHE_DEFAULT_TIMEOUT': 300
    }
    print("Cache: Usando memoria (Redis no disponible)")

app.config.from_mapping(cache_config)
cache = Cache(app)

# ============ RATE LIMITING CON REDIS ============
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

def get_client_ip():
    """Obtener IP real del cliente (considerando proxies)"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return get_remote_address()

limiter = Limiter(
    app=app,
    key_func=get_client_ip,
    storage_uri=REDIS_URL,
    default_limits=["200 per minute", "50 per second"],
    strategy="fixed-window"
)

# Manejador para cuando se excede el limite
@app.errorhandler(429)
def ratelimit_handler(e):
    if request.path.startswith('/api/') or request.path.startswith('/superadmin/api/'):
        return jsonify(error="Demasiadas solicitudes. Intenta de nuevo en un momento.", retry_after=e.description), 429
    return render_template('error.html',
                          error="Demasiadas solicitudes",
                          mensaje="Por favor espera un momento antes de continuar."), 429


# Filtro para formatear precios sin decimales y con separador de miles
@app.template_filter('precio')
def formato_precio(value):
    try:
        num = int(float(value))
        return '{:,}'.format(num).replace(',', '.')
    except:
        return value

# JSONEncoder personalizado para Decimal
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

app.json_encoder = CustomJSONEncoder
app.secret_key = os.environ['SECRET_KEY']  # Obligatorio, sin fallback inseguro

# Configuracion de uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads", "productos")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB max

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def save_product_image(file):
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit(".", 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file.save(filepath)
        return f"/static/uploads/productos/{filename}"
    return None
app.register_blueprint(superadmin_bp, url_prefix="/superadmin")

# Configuraci??n
DOMINIO_BASE = os.environ.get('DOMINIO_BASE', 'localhost:5000')
DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

# Icono por defecto para categorias sin imagen
DEFAULT_CATEGORIA_ICON = 'https://cdn-icons-png.flaticon.com/128/1046/1046857.png'

def get_imagen_categoria(categoria):
    """Obtiene el icono de una categoria desde la DB o usa default"""
    # Si la categoria tiene icono guardado, usarlo
    if isinstance(categoria, dict):
        icono = categoria.get('icono') or categoria.get('icono_url')
        if icono:
            return icono
    return DEFAULT_CATEGORIA_ICON


# ============ MIDDLEWARE PARA DETECTAR TIENDA ============
@app.before_request
def detectar_tienda():
    """Detectar tienda basada en subdominio o parametro"""
    g.tienda = None
    g.modo_catalogo = False  # Nuevo: modo solo catalogo

    # En desarrollo, usar parametro ?tienda=slug
    if DEBUG:
        slug = request.args.get('tienda') or session.get('tienda_slug', 'demo')
        # Detectar modo catalogo en desarrollo
        if slug and slug.endswith('-menu'):
            slug = slug[:-5]  # Quitar -menu
            g.modo_catalogo = True
        if slug:
            g.tienda = Tienda.obtener_por_subdominio(slug)
            if g.tienda:
                session['tienda_slug'] = slug

    # En produccion, usar subdominio
    else:
        host = request.host.split(':')[0]  # quitar puerto
        parts = host.split('.')

        if len(parts) >= 3:  # subdominio.dominio.com
            subdominio = parts[0]
            # Detectar modo catalogo: tienda-menu.dominio.com
            if subdominio.endswith('-menu'):
                subdominio = subdominio[:-5]  # Quitar -menu
                g.modo_catalogo = True
            g.tienda = Tienda.obtener_por_subdominio(subdominio)

    # Si no hay tienda, usar demo o mostrar selector
    if not g.tienda:
        g.tienda = Tienda.obtener_por_subdominio('demo')


def requiere_tienda(f):
    """Decorador: requiere que haya una tienda activa"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not g.tienda:
            return render_template('error.html', mensaje="Tienda no encontrada"), 404
        return f(*args, **kwargs)
    return decorated


def requiere_login(roles=None):
    """Decorador: requiere login y opcionalmente rol espec??fico"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                flash('Debes iniciar sesi??n', 'error')
                return redirect(url_for('login'))

            user = Usuario.obtener_por_id(session['user_id'])
            if not user:
                session.clear()
                return redirect(url_for('login'))

            if roles and user['rol'] not in roles:
                flash('No tienes permiso para acceder', 'error')
                return redirect(url_for('index'))

            g.user = user
            return f(*args, **kwargs)
        return decorated
    return decorator


# ============ CONTEXT PROCESSOR ============
@app.context_processor
def inject_tienda():
    """Inyectar datos de tienda en todos los templates"""
    return {
        'tienda': g.get('tienda'),
        'user': g.get('user')
    }


# ============ RUTAS P??BLICAS (CLIENTE) ============
@app.route('/')
@requiere_tienda
def index():
    """P??gina principal del men??"""
    categorias = Categoria.obtener_por_tienda(g.tienda['id'])
    productos = Producto.obtener_por_tienda(g.tienda['id'], solo_disponibles=True)
    ofertas = Oferta.obtener_por_tienda(g.tienda['id'], solo_activas=True)

    # Construir menu jerarquico con subcategorias
    menu = {}
    categoria_images = {}

    # Separar categorias padre y subcategorias
    categorias_padre = [c for c in categorias if c.get('padre_id') is None]
    subcategorias = [c for c in categorias if c.get('padre_id') is not None]

    for cat_padre in categorias_padre:
        # Obtener subcategorias de esta categoria padre
        subs = [s for s in subcategorias if s.get('padre_id') == cat_padre['id']]

        if subs:
            # Tiene subcategorias: crear estructura jerarquica
            menu[cat_padre['nombre']] = {
                'tipo': 'con_subcategorias',
                'icono': get_imagen_categoria(cat_padre),
                'subcategorias': {}
            }
            for sub in subs:
                prods_sub = [p for p in productos if p['categoria_id'] == sub['id']]
                menu[cat_padre['nombre']]['subcategorias'][sub['nombre']] = prods_sub
        else:
            # No tiene subcategorias: productos directos
            prods = [p for p in productos if p['categoria_id'] == cat_padre['id']]
            menu[cat_padre['nombre']] = {
                'tipo': 'simple',
                'icono': get_imagen_categoria(cat_padre),
                'productos': prods
            }

        categoria_images[cat_padre['nombre']] = get_imagen_categoria(cat_padre)

    return render_template('cliente/index.html', modo_catalogo=g.modo_catalogo,
                           menu=menu,
                           categorias=categorias,
                           ofertas=ofertas,
                           categoria_images=categoria_images, tienda=g.tienda)


@app.route('/<tienda_slug>')
def index_tienda(tienda_slug):
    """P??gina principal del men?? para tienda espec??fica"""
    tienda = Tienda.obtener_por_subdominio(tienda_slug)
    if not tienda:
        return render_template('error.html', mensaje='Tienda no encontrada'), 404

    session['tienda_slug'] = tienda_slug
    g.tienda = tienda

    categorias = Categoria.obtener_por_tienda(tienda['id'])
    productos = Producto.obtener_por_tienda(tienda['id'], solo_disponibles=True)
    ofertas = Oferta.obtener_por_tienda(tienda['id'], solo_activas=True)

    # Construir menu jerarquico con subcategorias
    menu = {}
    categoria_images = {}

    # Separar categorias padre y subcategorias
    categorias_padre = [c for c in categorias if c.get('padre_id') is None]
    subcategorias = [c for c in categorias if c.get('padre_id') is not None]

    for cat_padre in categorias_padre:
        # Obtener subcategorias de esta categoria padre
        subs = [s for s in subcategorias if s.get('padre_id') == cat_padre['id']]

        if subs:
            # Tiene subcategorias: crear estructura jerarquica
            menu[cat_padre['nombre']] = {
                'tipo': 'con_subcategorias',
                'icono': get_imagen_categoria(cat_padre),
                'subcategorias': {}
            }
            for sub in subs:
                prods_sub = [p for p in productos if p['categoria_id'] == sub['id']]
                menu[cat_padre['nombre']]['subcategorias'][sub['nombre']] = prods_sub
        else:
            # No tiene subcategorias: productos directos
            prods = [p for p in productos if p['categoria_id'] == cat_padre['id']]
            menu[cat_padre['nombre']] = {
                'tipo': 'simple',
                'icono': get_imagen_categoria(cat_padre),
                'productos': prods
            }

        categoria_images[cat_padre['nombre']] = get_imagen_categoria(cat_padre)

    return render_template('cliente/index.html',
                           menu=menu,
                           categorias=categorias,
                           ofertas=ofertas,
                           categoria_images=categoria_images, tienda=g.tienda)


@app.route('/checkout')
@requiere_tienda
def checkout():
    """P??gina de checkout"""
    return render_template('cliente/checkout.html')


# ============ API CARRITO ============
@app.route('/api/carrito')
def api_carrito():
    """Obtener carrito actual"""
    carrito = session.get('carrito', [])
    # Asegurar que precio sea float
    subtotal = sum(float(item.get('precio', 0)) * int(item.get('cantidad', 1)) for item in carrito)
    costo_domicilio = float(g.tienda.get('costo_domicilio', 0)) if g.tienda else 0
    return jsonify({
        'carrito': carrito,
        'total_items': sum(int(item.get('cantidad', 1)) for item in carrito),
        'subtotal': subtotal,
        'costo_domicilio': costo_domicilio,
        'total': subtotal + costo_domicilio
    })


@app.route('/api/carrito/agregar', methods=['POST'])
def api_carrito_agregar():
    """Agregar producto al carrito"""
    data = request.json
    producto = Producto.obtener_por_id(data['producto_id'])
    if not producto:
        return jsonify({'error': 'Producto no encontrado'}), 404

    carrito = session.get('carrito', [])
    cantidad_nueva = int(data.get('cantidad', 1))

    # Soportar precio y nombre override (para descuentos y variantes)
    precio = float(data.get('precio_override', producto['precio']))
    nombre = data.get('nombre_override', producto['nombre'])
    descuento = data.get('descuento', 0)

    # Key único para productos: incluye nombre para diferenciar variantes
    item_key = f"{producto['id']}_{nombre}_{descuento}"

    # Buscar si ya existe (usar .get() para evitar KeyError con ofertas)
    for item in carrito:
        item_existing_key = f"{item.get('producto_id')}_{item.get('nombre', '')}_{item.get('descuento', 0)}"
        if item_existing_key == item_key:
            item['cantidad'] = int(item.get('cantidad', 0)) + cantidad_nueva
            break
    else:
        carrito.append({
            'producto_id': producto['id'],
            'nombre': nombre,
            'precio': precio,
            'cantidad': cantidad_nueva,
            'descuento': descuento
        })

    session['carrito'] = carrito
    session.modified = True
    return jsonify({
        'success': True,
        'total_items': sum(int(item.get('cantidad', 0)) for item in carrito)
    })


@app.route('/api/oferta/<int:oferta_id>/productos')
def api_oferta_productos(oferta_id):
    """Obtener productos de una oferta"""
    oferta = Oferta.obtener_por_id(oferta_id)
    if not oferta:
        return jsonify({'error': 'Oferta no encontrada'}), 404

    productos = []
    productos_ids = oferta.get('productos_ids', [])

    # Si productos_ids es string JSON, parsearlo
    if isinstance(productos_ids, str):
        try:
            import json
            productos_ids = json.loads(productos_ids)
        except:
            productos_ids = []

    for pid in productos_ids:
        producto = Producto.obtener_por_id(pid)
        if producto:
            # Obtener variantes del producto
            variantes = Producto.obtener_variantes(pid)
            variantes_data = []
            for v in variantes:
                variantes_data.append({
                    'id': v['id'],
                    'nombre': v['nombre'],
                    'precio': float(v['precio'])
                })

            productos.append({
                'id': producto['id'],
                'nombre': producto['nombre'],
                'precio': float(producto['precio']),
                'imagen': producto.get('imagen', ''),
                'variantes': variantes_data
            })

    return jsonify({
        'oferta': {
            'id': oferta['id'],
            'titulo': oferta['titulo'],
            'valor_descuento': oferta.get('valor_descuento', 0)
        },
        'productos': productos
    })


@app.route('/api/carrito/agregar-oferta', methods=['POST'])
def api_carrito_agregar_oferta():
    """Agregar oferta al carrito"""
    data = request.json
    oferta = Oferta.obtener_por_id(data['oferta_id'])
    if not oferta:
        return jsonify({'error': 'Oferta no encontrada'}), 404

    carrito = session.get('carrito', [])
    cantidad_nueva = int(data.get('cantidad', 1))

    # Usar precio del frontend o de la oferta (manejar None)
    precio = data.get('precio', 0) or oferta.get('precio_oferta') or 0
    precio = float(precio) if precio else 0

    # Buscar si ya existe esta oferta en el carrito
    for item in carrito:
        if item.get('oferta_id') == oferta['id']:
            item['cantidad'] = int(item.get('cantidad', 0)) + cantidad_nueva
            break
    else:
        carrito.append({
            'oferta_id': oferta['id'],
            'nombre': data.get('titulo') or oferta['titulo'],
            'precio': precio,
            'cantidad': cantidad_nueva,
            'es_oferta': True
        })

    session['carrito'] = carrito
    return jsonify({
        'success': True,
        'total_items': sum(int(item.get('cantidad', 0)) for item in carrito)
    })


@app.route('/api/carrito/actualizar', methods=['POST'])
def api_carrito_actualizar():
    """Actualizar cantidad de producto o oferta"""
    data = request.json
    carrito = session.get('carrito', [])
    nueva_cantidad = int(data.get('cantidad', 0))

    for item in carrito:
        # Soportar tanto productos como ofertas
        if data.get('producto_id') and item.get('producto_id') == data['producto_id']:
            if nueva_cantidad <= 0:
                carrito.remove(item)
            else:
                item['cantidad'] = nueva_cantidad
            break
        elif data.get('oferta_id') and item.get('oferta_id') == int(data['oferta_id']):
            if nueva_cantidad <= 0:
                carrito.remove(item)
            else:
                item['cantidad'] = nueva_cantidad
            break

    session['carrito'] = carrito
    return api_carrito()


@app.route('/api/carrito/eliminar', methods=['POST'])
def api_carrito_eliminar():
    """Eliminar producto u oferta del carrito"""
    data = request.json
    carrito = session.get('carrito', [])
    if data.get('producto_id'):
        carrito = [item for item in carrito if item.get('producto_id') != data['producto_id']]
    elif data.get('oferta_id'):
        carrito = [item for item in carrito if item.get('oferta_id') != data['oferta_id']]
    session['carrito'] = carrito
    return api_carrito()


@app.route("/api/cliente/buscar", methods=["POST"])
@requiere_tienda
def api_buscar_cliente():
    """Buscar cliente por telefono"""
    data = request.json or {}
    telefono = data.get("telefono", "").strip()
    
    if not telefono or len(telefono) < 7:
        return jsonify({"encontrado": False})
    
    cliente = Cliente.buscar_por_telefono(g.tienda["id"], telefono)
    
    if cliente:
        return jsonify({
            "encontrado": True,
            "nombre": cliente.get("nombre", ""),
            "direccion": cliente.get("direccion", ""),
            "referencias": cliente.get("referencias", "")
        })
    
    return jsonify({"encontrado": False})


@app.route('/api/pedido', methods=['POST'])
@requiere_tienda
def api_crear_pedido():
    """Crear nuevo pedido"""
    data = request.json
    carrito = session.get('carrito', [])

    if not carrito:
        return jsonify({'error': 'Carrito vac??o'}), 400

    # Crear o buscar cliente
    cliente = Cliente.buscar_por_telefono(g.tienda['id'], data['telefono'])
    if not cliente:
        cliente_id = Cliente.crear(
            g.tienda['id'],
            data['nombre'],
            data['telefono'],
            data.get('direccion', ''),
            data.get('email', ''),
            data.get('referencias', '')
        )
    else:
        cliente_id = cliente['id']

    # Calcular totales
    # Validar pedido minimo
    pedido_minimo = float(g.tienda.get("pedido_minimo", 0) or 0)
    subtotal = sum(float(item["precio"]) * int(item["cantidad"]) for item in carrito)
    
    # Validar que el subtotal sea mayor o igual al pedido minimo
    if pedido_minimo > 0 and subtotal < pedido_minimo:
        return jsonify({'error': f'El pedido minimo es ${pedido_minimo:.0f}. Tu total es ${subtotal:.0f}'}), 400
    
    tipo = data.get('tipo', 'domicilio')
    costo_domicilio = float(g.tienda.get('costo_domicilio', 0) or 0) if tipo == 'domicilio' else 0
    total = subtotal + costo_domicilio

    # Crear pedido
    pedido_id, numero_orden = Pedido.crear(
        g.tienda['id'],
        cliente_id,
        tipo,
        subtotal,
        costo_domicilio,
        total,
        direccion_entrega=data.get('direccion', ''),
        notas=data.get('notas', '')
    )

    # Agregar detalles
    conn = get_connection()
    cursor = conn.cursor()

    # Obtener un producto valido de la tienda para usar como fallback
    cursor.execute('SELECT id FROM productos WHERE tienda_id = %s LIMIT 1', (g.tienda['id'],))
    fallback_row = cursor.fetchone()
    fallback_producto_id = fallback_row['id'] if fallback_row else 1

    for item in carrito:
        # Manejar tanto productos como ofertas
        if item.get('es_oferta') or item.get('oferta_id'):
            # Para ofertas, usar el producto_id de la oferta si existe, o fallback
            oferta_id = item.get('oferta_id')
            if oferta_id:
                cursor.execute('SELECT producto_id FROM ofertas WHERE id = %s', (oferta_id,))
                oferta_row = cursor.fetchone()
                producto_id = oferta_row['producto_id'] if oferta_row and oferta_row['producto_id'] else fallback_producto_id
            else:
                producto_id = fallback_producto_id
            nota_item = f"[OFERTA] {item.get('nombre', '')}"
        else:
            producto_id = item.get('producto_id', fallback_producto_id)
            # Si el nombre del item es diferente al producto base (variante), guardarlo en notas
            nombre_item = item.get('nombre', '')
            cursor.execute('SELECT nombre FROM productos WHERE id = %s', (producto_id,))
            prod_row = cursor.fetchone()
            nombre_producto_base = prod_row['nombre'] if prod_row else ''
            # Si el nombre incluye variante (es diferente al base), guardarlo
            if nombre_item and nombre_item != nombre_producto_base:
                nota_item = nombre_item
            else:
                nota_item = ''

        Pedido.agregar_detalle(
            pedido_id,
            producto_id,
            item['cantidad'],
            item['precio'],
            notas=nota_item
        )
    conn.close()

    # Limpiar carrito
    session['carrito'] = []

    return jsonify({
        'success': True,
        'pedido_id': pedido_id,
        'numero_orden': numero_orden
    })


@app.route('/api/pedido/rastrear', methods=['POST'])
@app.route('/api/pedido/rastrear/<numero_orden>', methods=['GET'])
@requiere_tienda
def rastrear_pedido_get(numero_orden):
    """Rastrear estado de un pedido por numero de orden (GET)"""
    if not numero_orden:
        return jsonify({'error': 'Numero de orden requerido'})

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT p.numero_orden, p.estado, p.total, p.fecha_pedido,
               c.nombre as cliente_nombre
        FROM pedidos p
        LEFT JOIN clientes c ON p.cliente_id = c.id
        WHERE p.numero_orden = %s AND p.tienda_id = %s
    ''', (numero_orden, g.tienda['id']))

    pedido = cursor.fetchone()
    conn.close()

    if not pedido:
        return jsonify({'error': 'Pedido no encontrado'})

    return jsonify({
        'numero_orden': pedido['numero_orden'],
        'estado': pedido['estado'],
        'total': float(pedido['total']),
        'fecha': pedido['fecha_pedido'].strftime('%Y-%m-%d %H:%M') if pedido['fecha_pedido'] else '',
        'cliente': pedido['cliente_nombre'] or 'Cliente'
    })
@requiere_tienda
def rastrear_pedido():
    """Rastrear estado de un pedido por numero de orden"""
    data = request.get_json() or {}
    numero_orden = data.get('numero_orden', '').strip()

    if not numero_orden:
        return jsonify({'error': 'Numero de orden requerido'})

    conn = get_connection()
    cursor = conn.cursor()

    # Buscar pedido con datos del cliente
    cursor.execute('''
        SELECT p.numero_orden, p.estado, p.total, p.fecha_pedido,
               c.nombre as cliente_nombre
        FROM pedidos p
        LEFT JOIN clientes c ON p.cliente_id = c.id
        WHERE p.numero_orden = %s AND p.tienda_id = %s
    ''', (numero_orden, g.tienda['id']))

    pedido = cursor.fetchone()
    conn.close()

    if pedido:
        return jsonify({
            'numero_orden': pedido['numero_orden'],
            'estado': pedido['estado'],
            'total': float(pedido['total']) if pedido['total'] else 0,
            'fecha': str(pedido['fecha_pedido'])[:16] if pedido['fecha_pedido'] else '',
            'cliente': pedido['cliente_nombre'] or 'Cliente'
        })
    else:
        return jsonify({'error': 'No se encontro ningun pedido con ese numero'})



@app.route('/ticket/<int:pedido_id>')
@requiere_tienda
def ticket_pedido(pedido_id):
    """Mostrar ticket de pedido para imprimir"""
    conn = get_connection()
    cursor = conn.cursor()

    # Obtener pedido
    cursor.execute('''
        SELECT p.*, c.nombre as cliente_nombre, c.telefono as cliente_telefono
        FROM pedidos p
        LEFT JOIN clientes c ON p.cliente_id = c.id
        WHERE p.id = %s AND p.tienda_id = %s
    ''', (pedido_id, g.tienda['id']))
    pedido = cursor.fetchone()

    if not pedido:
        conn.close()
        return "Pedido no encontrado", 404

    pedido = dict(pedido)

    # Obtener detalles
    cursor.execute('''
        SELECT dp.*,
               CASE
                   WHEN dp.notas LIKE '[OFERTA]%%' THEN REPLACE(dp.notas, '[OFERTA] ', '')
                   WHEN dp.notas IS NOT NULL AND dp.notas != '' THEN dp.notas
                   ELSE COALESCE(pr.nombre, 'Producto')
               END as producto_nombre
        FROM detalle_pedidos dp
        LEFT JOIN productos pr ON dp.producto_id = pr.id
        WHERE dp.pedido_id = %s
    ''', (pedido_id,))
    detalles = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return render_template('cliente/ticket.html',
                         tienda=g.tienda,
                         pedido=pedido,
                         detalles=detalles)


# ============ RUTAS AUTENTICACI??N ============
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])  # Limite estricto para intentos de login
@requiere_tienda
def login():
    """Login para admin/cocina"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = Usuario.validar(email, password, g.tienda['id'])
        if user:
            session['user_id'] = user['id']
            session['user_rol'] = user['rol']

            if user['rol'] in ['admin', 'superadmin']:
                return redirect(url_for('admin_dashboard'))
            elif user['rol'] == 'cocina':
                return redirect(url_for('cocina_pedidos'))
            elif user['rol'] == 'mesero':
                return redirect(url_for('mesero_pedidos'))

        flash('Credenciales incorrectas', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Cerrar sesion"""
    session.clear()
    return redirect(url_for('login'))


# ============ RUTAS ADMIN ============
@app.route('/admin')
@requiere_tienda
@requiere_login(roles=['admin', 'superadmin'])
def admin_dashboard():
    """Dashboard administrativo"""
    stats = Pedido.obtener_estadisticas(g.tienda['id'])
    pedidos_recientes = Pedido.obtener_por_tienda(g.tienda['id'], limite=5)
    return render_template('admin/dashboard.html', stats=stats, pedidos=pedidos_recientes)


@app.route('/admin/productos')
@requiere_tienda
@requiere_login(roles=['admin', 'superadmin'])
def admin_productos():
    """Gesti??n de productos"""
    categorias = Categoria.obtener_por_tienda(g.tienda['id'])
    productos = Producto.obtener_por_tienda(g.tienda['id'])
    return render_template('admin/productos.html', productos=productos, categorias=categorias)


@app.route('/admin/productos/crear', methods=['POST'])
@requiere_tienda
@requiere_login(roles=['admin', 'superadmin'])
def admin_producto_crear():
    """Crear producto con soporte de imagen y variantes"""
    imagen = None

    # Primero verificar si hay archivo subido
    if 'imagen_file' in request.files:
        file = request.files['imagen_file']
        if file and file.filename:
            imagen = save_product_image(file)

    # Si no hay archivo, usar URL
    if not imagen and request.form.get('imagen_url'):
        imagen = request.form.get('imagen_url')

    # Crear el producto
    producto_id = Producto.crear(
        g.tienda['id'],
        request.form['nombre'],
        float(request.form['precio']),
        int(request.form['categoria_id']) if request.form.get('categoria_id') else None,
        request.form.get('descripcion', ''),
        imagen or ''
    )

    # Si tiene variantes, crearlas
    if request.form.get('tiene_variantes'):
        variante_nombres = request.form.getlist('variante_nombre[]')
        variante_precios = request.form.getlist('variante_precio[]')

        for i, (nombre, precio) in enumerate(zip(variante_nombres, variante_precios)):
            if nombre and precio:
                Producto.crear_variante(producto_id, nombre, float(precio), orden=i)

    flash('Producto creado', 'success')
    return redirect(url_for('admin_productos'))


@app.route('/admin/productos/<int:id>/editar', methods=['POST'])
@requiere_tienda
@requiere_login(roles=['admin', 'superadmin'])
def admin_producto_editar(id):
    """Editar producto con soporte de imagen"""
    imagen = None

    # Primero verificar si hay archivo subido
    if 'imagen_file' in request.files:
        file = request.files['imagen_file']
        if file and file.filename:
            imagen = save_product_image(file)

    # Si no hay archivo nuevo, usar URL si se proporciono
    if not imagen and request.form.get('imagen_url'):
        imagen = request.form.get('imagen_url')

    update_data = {
        'nombre': request.form['nombre'],
        'precio': float(request.form['precio']),
        'categoria_id': int(request.form['categoria_id']) if request.form.get('categoria_id') else None,
        'descripcion': request.form.get('descripcion', ''),
        'disponible': 1 if request.form.get('disponible') else 0
    }

    # Solo actualizar imagen si se proporciono una nueva
    if imagen:
        update_data['imagen'] = imagen

    Producto.actualizar(id, **update_data)
    flash('Producto actualizado', 'success')
    return redirect(url_for('admin_productos'))


@app.route('/admin/productos/<int:id>/eliminar', methods=['POST'])
@requiere_tienda
@requiere_login(roles=['admin', 'superadmin'])
def admin_producto_eliminar(id):
    """Eliminar producto"""
    Producto.eliminar(id)
    flash('Producto eliminado', 'success')
    return redirect(url_for('admin_productos'))


@app.route('/admin/categorias')
@requiere_tienda
@requiere_login(roles=['admin', 'superadmin'])
def admin_categorias():
    """Gesti??n de categor??as"""
    categorias = Categoria.obtener_por_tienda(g.tienda['id'], solo_activas=False)
    return render_template('admin/categorias.html', categorias=categorias)


@app.route('/admin/categorias/crear', methods=['POST'])
@requiere_tienda
@requiere_login(roles=['admin', 'superadmin'])
def admin_categoria_crear():
    """Crear categor??a"""
    Categoria.crear(g.tienda['id'], request.form['nombre'], request.form.get('descripcion', ''))
    flash('Categor??a creada', 'success')
    return redirect(url_for('admin_categorias'))


@app.route('/admin/pedidos')
@requiere_tienda
@requiere_login(roles=['admin', 'superadmin'])
def admin_pedidos():
    """Ver pedidos"""
    estado = request.args.get('estado')
    pedidos = Pedido.obtener_por_tienda(g.tienda['id'], estado=estado)
    return render_template('admin/pedidos.html', pedidos=pedidos)


@app.route('/admin/ofertas')
@requiere_tienda
@requiere_login(roles=['admin', 'superadmin'])
def admin_ofertas():
    """Gesti??n de ofertas"""
    ofertas = Oferta.obtener_por_tienda(g.tienda['id'], solo_activas=False)
    productos = Producto.obtener_por_tienda(g.tienda['id'])
    return render_template('admin/ofertas.html', ofertas=ofertas, productos=productos)


@app.route('/admin/api/ofertas', methods=['POST'])
@requiere_tienda
@requiere_login(roles=['admin', 'superadmin'])
def admin_api_oferta_crear():
    """Crear oferta"""
    data = request.json
    oferta_id = Oferta.crear(
        g.tienda['id'],
        data['titulo'],
        data['tipo'],
        descripcion=data.get('descripcion'),
        valor_descuento=data.get('valor_descuento'),
        precio_oferta=data.get('precio_oferta'),
        producto_id=data.get('producto_id'),
        fecha_inicio=data.get('fecha_inicio'),
        fecha_fin=data.get('fecha_fin')
    )
    return jsonify({'success': True, 'id': oferta_id})


@app.route('/admin/api/ofertas/<int:id>')
@requiere_tienda
@requiere_login(roles=['admin', 'superadmin'])
def admin_api_oferta_get(id):
    """Obtener oferta"""
    oferta = Oferta.obtener_por_id(id)
    if not oferta:
        return jsonify({'error': 'No encontrada'}), 404
    return jsonify(oferta)


@app.route('/admin/api/ofertas/<int:id>', methods=['PUT'])
@requiere_tienda
@requiere_login(roles=['admin', 'superadmin'])
def admin_api_oferta_actualizar(id):
    """Actualizar oferta"""
    data = request.json
    Oferta.actualizar(id, **data)
    return jsonify({'success': True})


@app.route('/admin/api/ofertas/<int:id>/toggle', methods=['POST'])
@requiere_tienda
@requiere_login(roles=['admin', 'superadmin'])
def admin_api_oferta_toggle(id):
    """Toggle oferta"""
    Oferta.toggle(id)
    return jsonify({'success': True})


@app.route('/admin/api/ofertas/<int:id>', methods=['DELETE'])
@requiere_tienda
@requiere_login(roles=['admin', 'superadmin'])
def admin_api_oferta_eliminar(id):
    """Eliminar oferta"""
    Oferta.eliminar(id)
    return jsonify({'success': True})


@app.route('/admin/configuracion')
@requiere_tienda
@requiere_login(roles=['admin', 'superadmin'])
def admin_configuracion():
    """Configuraci??n de la tienda"""
    return render_template('admin/configuracion.html')


@app.route('/admin/configuracion/guardar', methods=['POST'])
@requiere_tienda
@requiere_login(roles=['admin', 'superadmin'])
def admin_configuracion_guardar():
    """Guardar configuraci??n"""
    Tienda.actualizar(g.tienda['id'],
        nombre=request.form.get('nombre'),
        telefono=request.form.get('telefono'),
        direccion=request.form.get('direccion'),
        horario=request.form.get('horario'),
        pedido_minimo=float(request.form.get('pedido_minimo', 50)),
        costo_domicilio=float(request.form.get('costo_domicilio', 20)),
        color_primario=request.form.get('color_primario', '#ff441f')
    )
    flash('Configuraci??n guardada', 'success')
    return redirect(url_for('admin_configuracion'))


# ============ RUTAS COCINA ============
@app.route('/cocina')
@requiere_tienda
@requiere_login(roles=['cocina', 'admin', 'superadmin'])
def cocina_pedidos():
    """Vista de cocina - pedidos en tiempo real"""
    pedidos = Pedido.obtener_para_cocina(g.tienda['id'])
    # Agregar detalles a cada pedido
    for pedido in pedidos:
        pedido['items'] = Pedido.obtener_detalle(pedido['id'])
    return render_template('cocina/pedidos.html', pedidos=pedidos)


@app.route('/api/cocina/pedidos')
@requiere_tienda
@requiere_login(roles=['cocina', 'admin', 'superadmin'])
def api_cocina_pedidos():
    """API para obtener pedidos de cocina (polling)"""
    pedidos = Pedido.obtener_para_cocina(g.tienda['id'])
    for pedido in pedidos:
        pedido['items'] = Pedido.obtener_detalle(pedido['id'])
    return jsonify(pedidos)


@app.route('/api/cocina/pedido/<int:id>/estado', methods=['POST'])
@requiere_tienda
@requiere_login(roles=['cocina', 'admin', 'superadmin'])
def api_cocina_cambiar_estado(id):
    """Cambiar estado de pedido"""
    data = request.json
    Pedido.actualizar_estado(id, data['estado'])
    return jsonify({'success': True})


# ============ SUPERADMIN - GESTI??N DE TIENDAS ============
@app.route('/superadmin/tiendas')
@requiere_login(roles=['superadmin'])
def superadmin_tiendas():
    """Gesti??n de tiendas (solo superadmin)"""
    tiendas = Tienda.obtener_todas()
    return render_template('superadmin/tiendas.html', tiendas=tiendas)


@app.route('/superadmin/tiendas/crear', methods=['POST'])
@requiere_login(roles=['superadmin'])
def superadmin_tienda_crear():
    """Crear nueva tienda"""
    tienda_id = Tienda.crear(
        request.form['nombre'],
        request.form['slug'],
        request.form['subdominio'],
        telefono=request.form.get('telefono', ''),
        direccion=request.form.get('direccion', '')
    )
    if tienda_id:
        # Crear usuario admin para la tienda
        Usuario.crear(
            tienda_id,
            f"admin@{request.form['slug']}.com",
            'admin123',
            f"Admin {request.form['nombre']}",
            'admin'
        )
        flash('Tienda creada exitosamente', 'success')
    else:
        flash('Error: El slug o subdominio ya existe', 'error')
    return redirect(url_for('superadmin_tiendas'))



# ============ RUTAS MESERO ============
@app.route('/mesero')
@requiere_tienda
@requiere_login(roles=['mesero', 'admin', 'superadmin'])
def mesero_pedidos():
    """Vista de mesero - tomar pedidos"""
    categorias = Categoria.obtener_por_tienda(g.tienda['id'])
    productos = Producto.obtener_por_tienda(g.tienda['id'], solo_disponibles=True)
    ofertas = Oferta.obtener_por_tienda(g.tienda['id'], solo_activas=True)

    # Construir menu jerarquico con subcategorias
    menu = {}

    # Separar categorias padre y subcategorias
    categorias_padre = [c for c in categorias if c.get('padre_id') is None]
    subcategorias = [c for c in categorias if c.get('padre_id') is not None]

    for cat_padre in categorias_padre:
        # Obtener subcategorias de esta categoria padre
        subs = [s for s in subcategorias if s.get('padre_id') == cat_padre['id']]

        if subs:
            # Tiene subcategorias: crear estructura jerarquica
            menu[cat_padre['nombre']] = {
                'tipo': 'con_subcategorias',
                'subcategorias': {}
            }
            for sub in subs:
                prods_sub = [p for p in productos if p['categoria_id'] == sub['id']]
                menu[cat_padre['nombre']]['subcategorias'][sub['nombre']] = prods_sub
        else:
            # No tiene subcategorias: productos directos
            prods = [p for p in productos if p['categoria_id'] == cat_padre['id']]
            menu[cat_padre['nombre']] = {
                'tipo': 'simple',
                'productos': prods
            }

    return render_template('mesero/pedidos.html', menu=menu, categorias=categorias, ofertas=ofertas)


@app.route('/api/mesero/pedido', methods=['POST'])
@requiere_tienda
@requiere_login(roles=['mesero', 'admin', 'superadmin'])
def api_mesero_crear_pedido():
    """API para crear pedido desde mesero"""
    data = request.json
    items = data.get('items', [])

    if not items:
        return jsonify({'error': 'No hay items en el pedido'}), 400

    # Calcular totales - frontend envia precio_unitario y cantidad
    subtotal = sum(item.get('precio_unitario', 0) * item.get('cantidad', 1) for item in items)
    total = subtotal

    # Crear cliente temporal o usar existente
    mesa = data.get('mesa', 'S/N')
    cliente_nombre = f"Mesa {mesa}"

    # Buscar o crear cliente
    conn = get_connection()
    cursor = conn.cursor()
    p = '%s'

    cursor.execute(f"SELECT id FROM clientes WHERE nombre = {p} AND tienda_id = {p}",
                   (cliente_nombre, g.tienda['id']))
    cliente = cursor.fetchone()

    if cliente:
        cliente_id = cliente['id'] if isinstance(cliente, dict) else cliente[0]
    else:
        cursor.execute(f"INSERT INTO clientes (tienda_id, nombre, telefono) VALUES ({p}, {p}, {p})",
                       (g.tienda['id'], cliente_nombre, ''))
        conn.commit()
        cliente_id = cursor.lastrowid

    conn.close()

    # Crear el pedido
    mesero_id = session.get('user_id')
    result = Pedido.crear(
        tienda_id=g.tienda['id'],
        cliente_id=cliente_id,
        mesero_id=mesero_id,
        tipo='local',
        subtotal=subtotal,
        costo_domicilio=0,
        total=total,
        notas=data.get('notas', ''),
        direccion_entrega=''
    )

    if result:
        pedido_id, numero_orden = result
        # Agregar items al pedido - frontend envia producto_id, cantidad, precio_unitario
        for item in items:
            item_id = item.get('producto_id')
            if item_id is None:
                continue

            Pedido.agregar_detalle(
                pedido_id=pedido_id,
                producto_id=item_id,
                cantidad=item.get('cantidad', 1),
                precio_unitario=item.get('precio_unitario', 0),
                notas=item.get('notas', '')
            )
        return jsonify({'success': True, 'pedido_id': pedido_id, 'numero_orden': numero_orden})
    return jsonify({'error': 'Error al crear pedido'}), 400

# ============ API SUPERADMIN TIENDAS ============
@app.route('/superadmin/api/tiendas', methods=['GET'])
@requiere_login(roles=['superadmin'])
def superadmin_api_tiendas_lista():
    """Lista todas las tiendas"""
    tiendas = Tienda.obtener_todas()
    return jsonify(tiendas)

@app.route('/superadmin/api/tiendas/<int:id>', methods=['GET'])
@requiere_login(roles=['superadmin'])
def superadmin_api_tienda_get(id):
    """Obtener una tienda por ID"""
    tienda = Tienda.obtener_por_id(id)
    if tienda:
        return jsonify(tienda)
    return jsonify({'error': 'Tienda no encontrada'}), 404

@app.route('/superadmin/api/tiendas', methods=['POST'])
@requiere_login(roles=['superadmin'])
def superadmin_api_tienda_crear():
    """Crear nueva tienda via API"""
    data = request.json
    tienda_id = Tienda.crear(
        data['nombre'],
        data['slug'],
        data['subdominio'],
        telefono=data.get('telefono', ''),
        direccion=data.get('direccion', '')
    )
    if tienda_id:
        # Actualizar campos adicionales
        Tienda.actualizar(tienda_id,
            slogan=data.get('slogan', ''),
            horario=data.get('horario', ''),
            logo=data.get('logo', ''),
            banner_url=data.get('banner_url', ''),
            color_primario=data.get('color_primario', '#ff441f'),
            color_secundario=data.get('color_secundario', '#00b14f'),
            color_terciario=data.get('color_terciario', '#f5f5f5'),
            domicilios_activo=data.get('domicilios_activo', '1') == '1',
            costo_domicilio=float(data.get('costo_domicilio', 0)),
            pedido_minimo=float(data.get('pedido_minimo', 0)),
            zona_cobertura=data.get('zona_cobertura', ''),
            modo_pedido=data.get('modo_pedido', 'normal')
        )
        # Crear usuarios
        email_admin = f"admin@{data['slug']}.com"
        email_mesero = f"mesero@{data['slug']}.com"
        email_cocina = f"cocina@{data['slug']}.com"
        password = 'admin123'
        password_mesero = 'mesero123'
        password_cocina = 'cocina123'
        Usuario.crear(tienda_id, email_admin, password, f"Admin {data['nombre']}", 'admin')
        Usuario.crear(tienda_id, email_mesero, password_mesero, f"Mesero {data['nombre']}", 'mesero')
        Usuario.crear(tienda_id, email_cocina, password_cocina, f"Cocina {data['nombre']}", 'cocina')
        return jsonify({
            'success': True,
            'id': tienda_id,
            'credenciales': {
                'admin': {'email': email_admin, 'password': password},
                'mesero': {'email': email_mesero, 'password': password_mesero},
                'cocina': {'email': email_cocina, 'password': password_cocina}
            }
        })
    return jsonify({'error': 'El slug o subdominio ya existe'}), 400

@app.route('/superadmin/api/tiendas/<int:id>', methods=['PUT'])
@requiere_login(roles=['superadmin'])
def superadmin_api_tienda_actualizar(id):
    """Actualizar tienda via API"""
    data = request.json
    Tienda.actualizar(id,
        nombre=data.get('nombre'),
        telefono=data.get('telefono'),
        direccion=data.get('direccion'),
        slogan=data.get('slogan'),
        horario=data.get('horario'),
        logo=data.get('logo'),
        banner_url=data.get('banner_url'),
        color_primario=data.get('color_primario'),
        color_secundario=data.get('color_secundario'),
        color_terciario=data.get('color_terciario'),
        domicilios_activo=data.get('domicilios_activo', '1') == '1',
        costo_domicilio=float(data.get('costo_domicilio', 0)) if data.get('costo_domicilio') else None,
        pedido_minimo=float(data.get('pedido_minimo', 0)) if data.get('pedido_minimo') else None,
        zona_cobertura=data.get('zona_cobertura'),
        modo_pedido=data.get('modo_pedido', 'normal')
    )
    return jsonify({'success': True})

@app.route('/superadmin/api/tiendas/<int:id>/toggle', methods=['POST'])
@requiere_login(roles=['superadmin'])
def superadmin_api_tienda_toggle(id):
    """Activar/desactivar tienda"""
    tienda = Tienda.obtener_por_id(id)
    if tienda:
        nuevo_estado = not tienda.get('activo', True)
        Tienda.actualizar(id, activo=nuevo_estado)
        return jsonify({'success': True, 'activo': nuevo_estado})
    return jsonify({'error': 'Tienda no encontrada'}), 404

@app.route('/superadmin/api/tiendas/<int:id>', methods=['DELETE'])
@requiere_login(roles=['superadmin'])
def superadmin_api_tienda_eliminar(id):
    """Eliminar tienda"""
    # Por seguridad, solo desactivamos
    Tienda.actualizar(id, activo=False)
    return jsonify({'success': True})

@app.route('/superadmin/api/tiendas/<int:id>/detalle', methods=['GET'])
@requiere_login(roles=['superadmin'])
def superadmin_api_tienda_detalle(id):
    """Obtener detalle de tienda con estadisticas"""
    tienda = Tienda.obtener_por_id(id)
    if tienda:
        # Agregar estadisticas basicas
        tienda['stats'] = {
            'productos': 0,
            'categorias': 0,
            'pedidos': 0,
            'usuarios': 0
        }
        return jsonify(tienda)
    return jsonify({'error': 'Tienda no encontrada'}), 404

@app.route('/superadmin/api/categorias-maestras', methods=['GET'])
@requiere_login(roles=['superadmin'])
def superadmin_api_categorias_maestras():
    """Lista categorias maestras"""
    return jsonify([])

@app.route('/superadmin/api/tiendas/<int:id>/categorias', methods=['GET'])
@requiere_login(roles=['superadmin'])
def superadmin_api_tienda_categorias(id):
    """Obtener categorias de una tienda"""
    return jsonify([])


# ============ API PARA EJECUTABLES (Admin/Cocina .exe) ============

# Token expira en 7 dias (en segundos)
TOKEN_EXPIRY = 7 * 24 * 60 * 60

def generar_token_seguro(tienda_id, user_id):
    """Genera un token HMAC seguro con timestamp"""
    timestamp = int(time.time())
    mensaje = f"{tienda_id}:{user_id}:{timestamp}"
    firma = hmac.new(
        app.secret_key.encode(),
        mensaje.encode(),
        hashlib.sha256
    ).hexdigest()[:20]
    return f"{tienda_id}:{user_id}:{timestamp}:{firma}"

def validar_token_seguro(token):
    """Valida un token HMAC y retorna (tienda_id, user_id) o None"""
    try:
        parts = token.split(':')
        if len(parts) != 4:
            return None

        tienda_id = int(parts[0])
        user_id = int(parts[1])
        timestamp = int(parts[2])
        firma_recibida = parts[3]

        # Verificar que no haya expirado
        if time.time() - timestamp > TOKEN_EXPIRY:
            return None

        # Recalcular firma
        mensaje = f"{tienda_id}:{user_id}:{timestamp}"
        firma_esperada = hmac.new(
            app.secret_key.encode(),
            mensaje.encode(),
            hashlib.sha256
        ).hexdigest()[:20]

        # Comparacion segura contra timing attacks
        if hmac.compare_digest(firma_recibida, firma_esperada):
            return (tienda_id, user_id)
        return None
    except:
        return None

def api_requiere_auth(f):
    """Decorador para API: requiere token de autenticacion"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Token requerido'}), 401

        # Validar token seguro
        resultado = validar_token_seguro(token)
        if not resultado:
            return jsonify({'error': 'Token invalido o expirado'}), 401

        tienda_id, user_id = resultado

        user = Usuario.obtener_por_id(user_id)
        if not user or user['tienda_id'] != tienda_id:
            return jsonify({'error': 'Token invalido'}), 401

        g.tienda = Tienda.obtener_por_id(tienda_id)
        g.user = user

        return f(*args, **kwargs)
    return decorated


@app.route('/api/v1/login', methods=['POST'])
@limiter.limit("5 per minute")  # Limite estricto para intentos de login API
def api_login():
    """Login desde ejecutables - devuelve token seguro"""
    data = request.json
    tienda = Tienda.obtener_por_subdominio(data.get('tienda_slug', ''))
    if not tienda:
        return jsonify({'error': 'Tienda no encontrada'}), 404

    user = Usuario.validar(data['email'], data['password'], tienda['id'])
    if not user:
        return jsonify({'error': 'Credenciales incorrectas'}), 401

    # Generar token seguro con HMAC
    token = generar_token_seguro(tienda['id'], user['id'])

    return jsonify({
        'success': True,
        'token': token,
        'user': {
            'id': user['id'],
            'nombre': user['nombre'],
            'rol': user['rol']
        },
        'tienda': {
            'id': tienda['id'],
            'nombre': tienda['nombre'],
            'slug': tienda['slug']
        }
    })


@app.route('/api/v1/tienda', methods=['GET'])
@api_requiere_auth
def api_get_tienda():
    """Obtener info de la tienda"""
    return jsonify(g.tienda)


@app.route('/api/v1/tienda', methods=['PUT'])
@api_requiere_auth
def api_update_tienda():
    """Actualizar tienda"""
    data = request.json
    Tienda.actualizar(g.tienda['id'], **data)
    return jsonify({'success': True})


# --- API Categor??as ---
@app.route('/api/v1/categorias', methods=['GET'])
@api_requiere_auth
def api_get_categorias():
    """Obtener categor??as"""
    categorias = Categoria.obtener_por_tienda(g.tienda['id'], solo_activas=False)
    return jsonify(categorias)


@app.route('/api/v1/categorias', methods=['POST'])
@api_requiere_auth
def api_crear_categoria():
    """Crear categor??a"""
    data = request.json
    cat_id = Categoria.crear(g.tienda['id'], data['nombre'], data.get('descripcion', ''))
    return jsonify({'success': True, 'id': cat_id})


@app.route('/api/v1/categorias/<int:id>', methods=['PUT'])
@api_requiere_auth
def api_update_categoria(id):
    """Actualizar categor??a"""
    data = request.json
    Categoria.actualizar(id, **data)
    return jsonify({'success': True})


@app.route('/api/v1/categorias/<int:id>', methods=['DELETE'])
@api_requiere_auth
def api_delete_categoria(id):
    """Eliminar categor??a"""
    Categoria.eliminar(id)
    return jsonify({'success': True})


# --- API Productos ---
@app.route('/api/v1/productos', methods=['GET'])
@api_requiere_auth
def api_get_productos():
    """Obtener productos"""
    productos = Producto.obtener_por_tienda(g.tienda['id'])
    return jsonify(productos)


@app.route('/api/v1/productos', methods=['POST'])
@api_requiere_auth
def api_crear_producto():
    """Crear producto con soporte de variantes"""
    data = request.json
    prod_id = Producto.crear(
        g.tienda['id'],
        data['nombre'],
        data['precio'],
        data.get('categoria_id'),
        data.get('descripcion', ''),
        data.get('imagen', '')
    )

    # Si tiene variantes, crearlas
    if data.get('tiene_variantes') and data.get('variantes'):
        for i, var in enumerate(data['variantes']):
            if var.get('nombre') and var.get('precio') is not None:
                Producto.crear_variante(prod_id, var['nombre'], float(var['precio']), orden=i)

    return jsonify({'success': True, 'id': prod_id})


@app.route('/api/v1/productos/<int:id>', methods=['PUT'])
@api_requiere_auth
def api_update_producto(id):
    """Actualizar producto"""
    data = request.json
    Producto.actualizar(id, **data)
    return jsonify({'success': True})


@app.route('/api/v1/productos/<int:id>', methods=['DELETE'])
@api_requiere_auth
def api_delete_producto(id):
    """Eliminar producto"""
    Producto.eliminar(id)
    return jsonify({'success': True})

# --- API Badges de Productos ---
@app.route('/api/v1/productos/<int:id>/badge', methods=['POST'])
@api_requiere_auth
def api_set_badge(id):
    """Asignar o quitar badge a un producto"""
    data = request.json
    badge = data.get('badge')  # nuevo, popular, mas_vendido, o None para quitar
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('UPDATE productos SET badge = %s WHERE id = %s AND tienda_id = %s',
                (badge, id, g.tienda['id']))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'badge': badge})


@app.route('/api/v1/badges/recalcular', methods=['POST'])
@api_requiere_auth
def api_recalcular_badges():
    """Recalcular badges automaticamente para la tienda"""
    from datetime import datetime, timedelta
    
    tienda_id = g.tienda['id']
    conn = get_connection()
    cur = conn.cursor()
    
    # Primero, limpiar todos los badges automaticos (excepto manuales si los hay)
    cur.execute('UPDATE productos SET badge = NULL WHERE tienda_id = %s', (tienda_id,))
    
    # 1. Badge NUEVO: Productos creados en los ultimos 7 dias
    fecha_limite = datetime.now() - timedelta(days=7)
    cur.execute('''
        UPDATE productos 
        SET badge = 'nuevo'
        WHERE tienda_id = %s AND fecha_creacion >= %s
    ''', (tienda_id, fecha_limite))
    
    # 2. Badge MAS_VENDIDO: El producto #1 en ventas totales (por cantidad)
    cur.execute('''
        SELECT dp.producto_id, SUM(dp.cantidad) as total_vendido
        FROM detalle_pedidos dp
        JOIN pedidos p ON dp.pedido_id = p.id
        JOIN productos pr ON dp.producto_id = pr.id
        WHERE p.tienda_id = %s AND pr.tienda_id = %s
        GROUP BY dp.producto_id
        ORDER BY total_vendido DESC
        LIMIT 1
    ''', (tienda_id, tienda_id))
    
    top_vendido = cur.fetchone()
    if top_vendido:
        cur.execute('''
            UPDATE productos SET badge = 'mas_vendido' 
            WHERE id = %s AND badge IS NULL
        ''', (top_vendido['producto_id'],))
    
    # 3. Badge POPULAR: Productos con mas pedidos este mes (top 3, excluyendo el mas vendido)
    primer_dia_mes = datetime.now().replace(day=1, hour=0, minute=0, second=0)
    cur.execute('''
        SELECT dp.producto_id, COUNT(DISTINCT dp.pedido_id) as num_pedidos
        FROM detalle_pedidos dp
        JOIN pedidos p ON dp.pedido_id = p.id
        JOIN productos pr ON dp.producto_id = pr.id
        WHERE p.tienda_id = %s AND pr.tienda_id = %s
          AND p.fecha_pedido >= %s
        GROUP BY dp.producto_id
        ORDER BY num_pedidos DESC
        LIMIT 3
    ''', (tienda_id, tienda_id, primer_dia_mes))
    
    populares = cur.fetchall()
    for prod in populares:
        cur.execute('''
            UPDATE productos SET badge = 'popular' 
            WHERE id = %s AND badge IS NULL
        ''', (prod['producto_id'],))
    
    conn.commit()
    
    # Obtener resumen
    cur.execute('''
        SELECT badge, COUNT(*) as count 
        FROM productos 
        WHERE tienda_id = %s AND badge IS NOT NULL 
        GROUP BY badge
    ''', (tienda_id,))
    resumen = {row['badge']: row['count'] for row in cur.fetchall()}
    
    conn.close()
    
    return jsonify({
        'success': True,
        'badges_asignados': resumen
    })



# --- API Ofertas ---
@app.route('/api/v1/ofertas', methods=['GET'])
@api_requiere_auth
def api_get_ofertas():
    """Obtener ofertas de la tienda"""
    ofertas = Oferta.obtener_por_tienda(g.tienda['id'], solo_activas=False)
    return jsonify({'ofertas': ofertas})


@app.route('/api/v1/ofertas', methods=['POST'])
@api_requiere_auth
def api_crear_oferta():
    """Crear oferta"""
    data = request.json
    oferta_id = Oferta.crear(
        tienda_id=g.tienda['id'],
        titulo=data['titulo'],
        tipo=data['tipo'],
        valor_descuento=data.get('valor', 0),
        precio_oferta=data.get('precio_oferta'),
        descripcion=data.get('descripcion'),
        productos=data.get('productos'),  # Lista de IDs de productos
        producto_id=data.get('producto_id'),
        fecha_inicio=data.get('fecha_inicio'),
        fecha_fin=data.get('fecha_fin'),
        imagen=data.get('imagen')
    )
    return jsonify({'success': True, 'id': oferta_id})


@app.route('/api/v1/ofertas/<int:id>', methods=['PUT'])
@api_requiere_auth
def api_update_oferta(id):
    """Actualizar oferta"""
    data = request.json
    Oferta.actualizar(id, **data)
    return jsonify({'success': True})


@app.route('/api/v1/ofertas/<int:id>', methods=['DELETE'])
@api_requiere_auth
def api_delete_oferta(id):
    """Eliminar oferta"""
    Oferta.eliminar(id)
    return jsonify({'success': True})


# --- API Pedidos ---
@app.route('/api/v1/pedidos', methods=['GET'])
@api_requiere_auth
def api_get_pedidos():
    """Obtener pedidos"""
    estado = request.args.get('estado')
    limite = request.args.get('limite', 50, type=int)
    pedidos = Pedido.obtener_por_tienda(g.tienda['id'], estado=estado, limite=limite)
    return jsonify(pedidos)


@app.route('/api/v1/pedidos/cocina', methods=['GET'])
@api_requiere_auth
def api_get_pedidos_cocina():
    """Obtener pedidos para cocina"""
    pedidos = Pedido.obtener_para_cocina(g.tienda['id'])
    for pedido in pedidos:
        pedido['items'] = Pedido.obtener_detalle(pedido['id'])
    return jsonify(pedidos)


@app.route('/api/v1/pedidos/<int:id>/detalle', methods=['GET'])
@api_requiere_auth
def api_get_pedido_detalle(id):
    """Obtener detalle de pedido"""
    # Obtener info del pedido
    pedidos = Pedido.obtener_por_tienda(g.tienda['id'])
    pedido = None
    for p in pedidos:
        if p['id'] == id:
            pedido = p
            break
    
    if not pedido:
        return jsonify({'error': 'Pedido no encontrado'}), 404
    
    # Obtener items del pedido
    items = Pedido.obtener_detalle(id)
    
    return jsonify({
        'pedido': pedido,
        'items': items
    })


@app.route('/api/v1/pedidos/<int:id>/estado', methods=['PUT'])
@api_requiere_auth
def api_update_pedido_estado(id):
    """Actualizar estado de pedido"""
    data = request.json
    Pedido.actualizar_estado(id, data['estado'])
    return jsonify({'success': True})


@app.route('/api/v1/estadisticas', methods=['GET'])
@api_requiere_auth
def api_get_estadisticas():
    """Obtener estad??sticas del d??a"""
    stats = Pedido.obtener_estadisticas(g.tienda['id'])
    return jsonify(stats)


@app.route('/api/v1/reportes/ventas-periodo', methods=['GET'])
@api_requiere_auth
def api_reporte_ventas_periodo():
    """Reporte de ventas por día"""
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    if not fecha_inicio or not fecha_fin:
        return jsonify({'error': 'Se requiere fecha_inicio y fecha_fin'}), 400
    datos = Pedido.reporte_ventas_periodo(g.tienda['id'], fecha_inicio, fecha_fin)
    return jsonify(datos)


@app.route('/api/v1/usuarios', methods=['GET'])
@api_requiere_auth
def api_get_usuarios():
    """Obtener usuarios de la tienda"""
    print(f"[DEBUG] Obteniendo usuarios para tienda_id: {g.tienda['id']}")
    usuarios = Usuario.obtener_por_tienda(g.tienda['id'])
    print(f"[DEBUG] Usuarios encontrados: {len(usuarios)}")
    # Filtrar superadmin y quitar password_hash
    usuarios_filtrados = []
    for u in usuarios:
        print(f"[DEBUG] Usuario: {u.get('nombre')} - rol: {u.get('rol')}")
        if u.get('rol') != 'superadmin':
            u.pop('password_hash', None)
            usuarios_filtrados.append(u)
    print(f"[DEBUG] Usuarios filtrados: {len(usuarios_filtrados)}")
    return jsonify(usuarios_filtrados)


@app.route('/api/v1/estadisticas/meseros', methods=['GET'])
@api_requiere_auth
def api_estadisticas_meseros():
    """Estadísticas de ventas por mesero"""
    filtro = request.args.get('filtro', 'hoy')
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    datos = Pedido.estadisticas_meseros(g.tienda['id'], filtro, fecha_inicio, fecha_fin)
    return jsonify(datos)


@app.route('/api/v1/estadisticas/meseros/<int:mesero_id>/pedidos', methods=['GET'])
@api_requiere_auth
def api_pedidos_mesero(mesero_id):
    """Obtener pedidos de un mesero específico"""
    filtro = request.args.get('filtro', 'hoy')
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    pedidos = Pedido.obtener_por_mesero(g.tienda['id'], mesero_id, filtro, fecha_inicio, fecha_fin)
    return jsonify(pedidos)


@app.route('/api/v1/usuarios', methods=['POST'])
@api_requiere_auth
def api_crear_usuario():
    """Crear nuevo usuario"""
    data = request.json
    user_id = Usuario.crear(
        g.tienda['id'],
        data['email'],
        data['password'],
        data['nombre'],
        data.get('rol', 'mesero')
    )
    if user_id:
        return jsonify({'success': True, 'id': user_id})
    return jsonify({'error': 'Error al crear usuario'}), 400


@app.route('/api/v1/usuarios/<int:id>', methods=['PUT'])
@api_requiere_auth
def api_actualizar_usuario(id):
    """Actualizar usuario"""
    data = request.json
    result = Usuario.actualizar(id, **data)
    if result:
        return jsonify({'success': True})
    return jsonify({'error': 'Error al actualizar usuario'}), 400


@app.route('/api/v1/usuarios/<int:id>', methods=['DELETE'])
@api_requiere_auth
def api_eliminar_usuario(id):
    """Eliminar usuario"""
    result = Usuario.eliminar(id)
    if result:
        return jsonify({'success': True})
    return jsonify({'error': 'Error al eliminar usuario'}), 400


@app.route('/api/v1/upload', methods=['POST'])
@api_requiere_auth
def api_upload_imagen():
    """Subir imagen en base64 y guardarla en el servidor"""
    import base64
    import uuid
    from datetime import datetime

    data = request.json
    imagen_base64 = data.get('imagen_base64', '')

    if not imagen_base64:
        return jsonify({'error': 'No se proporcion?? imagen'}), 400

    try:
        # Extraer tipo y datos del base64
        if ';base64,' in imagen_base64:
            header, encoded = imagen_base64.split(';base64,')
            ext = header.split('/')[-1]
            if ext == 'jpeg':
                ext = 'jpg'
        else:
            encoded = imagen_base64
            ext = 'png'

        # Decodificar imagen
        img_data = base64.b64decode(encoded)

        # Crear nombre ??nico
        filename = f"{uuid.uuid4().hex[:12]}.{ext}"

        # Crear directorio de uploads si no existe
        upload_dir = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)

        # Guardar archivo
        filepath = os.path.join(upload_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(img_data)

        # Retornar URL relativa
        url = f"/static/uploads/{filename}"
        return jsonify({'success': True, 'url': url})

    except Exception as e:
        return jsonify({'error': f'Error al procesar imagen: {str(e)}'}), 500


# --- API Crear Tienda (solo con clave maestra) ---
@app.route('/api/v1/tiendas/crear', methods=['POST'])
def api_crear_tienda():
    """Crear nueva tienda con clave maestra"""
    data = request.json

    # Verificar clave maestra
    clave = data.get('clave_maestra', '')
    if clave != app.secret_key:
        return jsonify({'error': 'Clave maestra incorrecta'}), 401

    # Crear tienda
    nombre = data.get('nombre', '')
    slug = data.get('slug', '').lower().replace(' ', '-')
    subdominio = data.get('subdominio', slug)

    if not nombre or not slug:
        return jsonify({'error': 'Nombre y slug son requeridos'}), 400

    tienda_id = Tienda.crear(
        nombre=nombre,
        slug=slug,
        subdominio=subdominio,
        telefono=data.get('telefono', ''),
        direccion=data.get('direccion', '')
    )

    if not tienda_id:
        return jsonify({'error': 'El slug o subdominio ya existe'}), 400

    # Crear usuario admin para la tienda
    email_admin = data.get('email_admin', f'admin@{slug}.com')
    password_admin = data.get('password_admin', 'admin123')

    Usuario.crear(
        tienda_id,
        email_admin,
        password_admin,
        f"Admin {nombre}",
        'admin'
    )

    # Crear usuario cocina
    Usuario.crear(
        tienda_id,
        f'cocina@{slug}.com',
        'cocina123',
        f"Cocina {nombre}",
        'cocina'
    )

    return jsonify({
        'success': True,
        'tienda_id': tienda_id,
        'mensaje': f'Tienda "{nombre}" creada',
        'credenciales': {
            'admin': {'email': email_admin, 'password': password_admin},
            'cocina': {'email': f'cocina@{slug}.com', 'password': 'cocina123'}
        }
    })


# ============ ERROR HANDLERS MEJORADOS ============
@app.errorhandler(400)
def bad_request(e):
    logger.warning(f"Bad request: {request.url} - {e}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Solicitud invalida', 'details': str(e)}), 400
    return render_template('error.html', mensaje="Solicitud invalida"), 400


@app.errorhandler(404)
def not_found(e):
    logger.info(f"Not found: {request.url}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Recurso no encontrado'}), 404
    return render_template('error.html', mensaje="Pagina no encontrada"), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {request.url} - {e}\n{traceback.format_exc()}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Error interno del servidor'}), 500
    return render_template('error.html', mensaje="Error del servidor"), 500


@app.errorhandler(Exception)
def handle_exception(e):
    """Captura todas las excepciones no manejadas"""
    logger.error(f"Excepcion no manejada: {request.url} - {e}\n{traceback.format_exc()}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Error inesperado', 'type': type(e).__name__}), 500
    return render_template('error.html', mensaje="Error inesperado"), 500


# ============ INICIALIZACI??N ============
if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=5000, debug=DEBUG)



# ============ API DE ACTUALIZACIONES ============
APP_VERSIONS = {
    'launcher': {'version': '2.8.2', 'file': 'RestaurantOS.exe'},
    'admin': {'version': '2.8.2', 'file': 'RestaurantOS.exe'},
    'cocina': {'version': '2.8.2', 'file': 'RestaurantOS.exe'},
}

@app.route('/api/app/version')
def api_app_version():
    """Retorna versiones disponibles de las apps"""
    return jsonify({
        'success': True,
        'apps': APP_VERSIONS,
        'download_base': '/static/apps/'
    })

@app.route('/api/app/download/<app_name>')
def api_app_download(app_name):
    """Descargar app ejecutable"""
    if app_name not in APP_VERSIONS:
        return jsonify({'error': 'App no encontrada'}), 404
    
    app_info = APP_VERSIONS[app_name]
    file_path = os.path.join(os.path.dirname(__file__), 'static', 'apps', app_info['file'])
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'Archivo no disponible'}), 404
    
    from flask import send_file
    return send_file(file_path, as_attachment=True, download_name=app_info['file'])

# ============ LAUNCHER AUTO-UPDATE ============
@app.route('/api/launcher/version')
def get_launcher_version():
    """Devuelve la version actual del launcher"""
    version_file = os.path.join(app.static_folder, 'launcher', 'version.json')
    if os.path.exists(version_file):
        with open(version_file, 'r') as f:
            return jsonify(json.load(f))
    return jsonify({'version': '1.0.0', 'files': []})

@app.route('/api/launcher/download/<filename>')
def download_launcher_file(filename):
    """Descarga un archivo del launcher"""
    return send_from_directory(os.path.join(app.static_folder, 'launcher'), filename)

@app.route('/api/pedido/rastrear-telefono/<telefono>', methods=['GET'])
@requiere_tienda
def rastrear_pedido_telefono(telefono):
    """Rastrear todos los pedidos activos por telefono del cliente"""
    if not telefono:
        return jsonify({'error': 'Telefono requerido', 'encontrado': False})

    conn = get_connection()
    cursor = conn.cursor()

    # Buscar pedidos activos del cliente de HOY (no entregados ni cancelados)
    cursor.execute('''
        SELECT p.numero_orden, p.estado, p.total, p.fecha_pedido,
               c.nombre as cliente_nombre
        FROM pedidos p
        LEFT JOIN clientes c ON p.cliente_id = c.id
        WHERE c.telefono = %s AND p.tienda_id = %s
        AND p.estado NOT IN ('entregado', 'cancelado')
        AND DATE(p.fecha_pedido) = CURDATE()
        ORDER BY p.fecha_pedido DESC
    ''', (telefono, g.tienda['id']))

    pedidos = cursor.fetchall()
    conn.close()

    if not pedidos:
        return jsonify({'error': 'No tienes pedidos activos', 'encontrado': False})

    # Retornar lista de pedidos
    pedidos_list = []
    for pedido in pedidos:
        pedidos_list.append({
            'numero_orden': pedido['numero_orden'],
            'estado': pedido['estado'],
            'total': float(pedido['total']) if pedido['total'] else 0,
            'fecha': pedido['fecha_pedido'].strftime('%Y-%m-%d %H:%M') if pedido['fecha_pedido'] else '',
            'cliente': pedido['cliente_nombre'] or 'Cliente'
        })

    return jsonify({
        'encontrado': True,
        'pedidos': pedidos_list,
        'total_pedidos': len(pedidos_list)
    })


# ============ HEALTH CHECK PARA MONITOREO ============
@app.route('/health')
def health_check():
    """Endpoint para verificar estado del sistema"""
    status = {
        'status': 'healthy',
        'timestamp': time.time(),
        'services': {}
    }

    # Verificar MySQL
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.fetchone()
        conn.close()
        status['services']['mysql'] = 'ok'
    except Exception as e:
        status['services']['mysql'] = f'error: {str(e)}'
        status['status'] = 'degraded'

    # Verificar Redis
    try:
        import redis
        r = redis.from_url(REDIS_URL)
        r.ping()
        status['services']['redis'] = 'ok'
    except:
        status['services']['redis'] = 'unavailable'

    # Info del sistema
    status['info'] = {
        'workers': os.environ.get('GUNICORN_WORKERS', '4'),
        'cache_type': app.config.get('CACHE_TYPE', 'unknown')
    }

    http_status = 200 if status['status'] == 'healthy' else 503
    return jsonify(status), http_status


@app.route('/ready')
def readiness_check():
    """Endpoint para verificar si la app esta lista para recibir trafico"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.fetchone()
        conn.close()
        return jsonify({'ready': True}), 200
    except:
        return jsonify({'ready': False}), 503
