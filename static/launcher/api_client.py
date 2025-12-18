"""
Cliente API para conectar ejecutables (Admin/Cocina) al servidor en la nube
"""
import urllib.request
import urllib.error
import json
import os
import base64

class APIClient:
    """Cliente para comunicarse con la API del servidor"""

    def __init__(self, servidor_url=None, tienda_slug=None):
        """
        Inicializar cliente API

        Args:
            servidor_url: URL del servidor (ej: http://72.61.72.32:5000)
            tienda_slug: Slug de la tienda (ej: demo, pizzeria1)
        """
        # Cargar configuracion de archivo si existe
        self.config = self._cargar_config()

        self.servidor_url = servidor_url or self.config.get('servidor_url', 'http://localhost:5000')
        self.tienda_slug = tienda_slug or self.config.get('tienda_slug', 'demo')
        self.token = self.config.get('token', '')
        self.user = self.config.get('user', {})
        self.tienda = self.config.get('tienda', {})

    def _cargar_config(self):
        """Cargar configuracion desde archivo"""
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _guardar_config(self):
        """Guardar configuracion a archivo"""
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        config = {
            'servidor_url': self.servidor_url,
            'tienda_slug': self.tienda_slug,
            'token': self.token,
            'user': self.user,
            'tienda': self.tienda
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def _request(self, method, endpoint, data=None):
        """
        Hacer request a la API

        Args:
            method: GET, POST, PUT, DELETE
            endpoint: Ruta del endpoint (ej: /api/v1/productos)
            data: Datos a enviar (dict)

        Returns:
            dict con la respuesta o None si hay error
        """
        url = f"{self.servidor_url}{endpoint}"

        headers = {
            'Content-Type': 'application/json',
        }

        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        body = None
        if data:
            body = json.dumps(data).encode('utf-8')

        try:
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            try:
                error_body = json.loads(e.read().decode('utf-8'))
                return {'error': error_body.get('error', str(e)), '_status': e.code}
            except:
                return {'error': str(e), '_status': e.code}
        except urllib.error.URLError as e:
            return {'error': f'Error de conexion: {e.reason}', '_status': 0}
        except Exception as e:
            return {'error': str(e), '_status': 0}

    # ============ AUTENTICACION ============

    def login(self, email, password):
        """
        Iniciar sesion

        Returns:
            dict con token, user y tienda si es exitoso
        """
        result = self._request('POST', '/api/v1/login', {
            'tienda_slug': self.tienda_slug,
            'email': email,
            'password': password
        })

        if result and result.get('success'):
            self.token = result['token']
            self.user = result['user']
            self.tienda = result['tienda']
            self._guardar_config()

        return result

    def logout(self):
        """Cerrar sesion"""
        self.token = ''
        self.user = {}
        self._guardar_config()

    def esta_autenticado(self):
        """Verificar si hay sesion activa"""
        return bool(self.token)

    # ============ TIENDA ============

    def obtener_tienda(self):
        """Obtener informacion de la tienda"""
        return self._request('GET', '/api/v1/tienda')

    def actualizar_tienda(self, **datos):
        """Actualizar configuracion de la tienda"""
        return self._request('PUT', '/api/v1/tienda', datos)

    # ============ CATEGORIAS ============

    def obtener_categorias(self):
        """Obtener todas las categorias"""
        return self._request('GET', '/api/v1/categorias')

    def crear_categoria(self, nombre, descripcion=''):
        """Crear nueva categoria"""
        return self._request('POST', '/api/v1/categorias', {
            'nombre': nombre,
            'descripcion': descripcion
        })

    def actualizar_categoria(self, id, **datos):
        """Actualizar categoria"""
        return self._request('PUT', f'/api/v1/categorias/{id}', datos)

    def eliminar_categoria(self, id):
        """Eliminar categoria"""
        return self._request('DELETE', f'/api/v1/categorias/{id}')

    # ============ PRODUCTOS ============

    def obtener_productos(self):
        """Obtener todos los productos"""
        return self._request('GET', '/api/v1/productos')

    def crear_producto(self, nombre, precio, categoria_id=None, descripcion='', disponible=1, imagen='', tiene_variantes=False, variantes=None):
        """Crear nuevo producto con soporte de variantes"""
        data = {
            'nombre': nombre,
            'precio': precio,
            'categoria_id': categoria_id,
            'descripcion': descripcion,
            'disponible': disponible,
            'imagen': imagen
        }
        if tiene_variantes and variantes:
            data['tiene_variantes'] = True
            data['variantes'] = variantes
        return self._request('POST', '/api/v1/productos', data)

    def actualizar_producto(self, id, **datos):
        """Actualizar producto"""
        return self._request('PUT', f'/api/v1/productos/{id}', datos)

    def eliminar_producto(self, id):
        """Eliminar producto"""
        return self._request('DELETE', f'/api/v1/productos/{id}')

    # ============ PEDIDOS ============

    def obtener_pedidos(self, estado=None, limite=50):
        """Obtener pedidos"""
        params = f'?limite={limite}'
        if estado:
            params += f'&estado={estado}'
        return self._request('GET', f'/api/v1/pedidos{params}')

    def obtener_pedidos_cocina(self):
        """Obtener pedidos para vista cocina (pendientes/preparando)"""
        return self._request('GET', '/api/v1/pedidos/cocina')

    def obtener_detalle_pedido(self, pedido_id):
        """Obtener detalle de un pedido"""
        return self._request('GET', f'/api/v1/pedidos/{pedido_id}/detalle')

    def actualizar_estado_pedido(self, pedido_id, estado):
        """Cambiar estado de pedido"""
        return self._request('PUT', f'/api/v1/pedidos/{pedido_id}/estado', {
            'estado': estado
        })

    # ============ ESTADISTICAS MESEROS ============

    def obtener_estadisticas_meseros(self, filtro='hoy', fecha_inicio=None, fecha_fin=None):
        """Obtener estadísticas de ventas por mesero"""
        params = f'?filtro={filtro}'
        if fecha_inicio:
            params += f'&fecha_inicio={fecha_inicio}'
        if fecha_fin:
            params += f'&fecha_fin={fecha_fin}'
        return self._request('GET', f'/api/v1/estadisticas/meseros{params}')

    def obtener_pedidos_mesero(self, mesero_id, filtro='hoy', fecha_inicio=None, fecha_fin=None):
        """Obtener pedidos de un mesero específico"""
        params = f'?filtro={filtro}'
        if fecha_inicio:
            params += f'&fecha_inicio={fecha_inicio}'
        if fecha_fin:
            params += f'&fecha_fin={fecha_fin}'
        return self._request('GET', f'/api/v1/estadisticas/meseros/{mesero_id}/pedidos{params}')

    # ============ REPORTES AVANZADOS ============

    def reporte_ventas_periodo(self, fecha_inicio, fecha_fin):
        """Reporte de ventas por día en un período"""
        params = f'?fecha_inicio={fecha_inicio}&fecha_fin={fecha_fin}'
        return self._request('GET', f'/api/v1/reportes/ventas-periodo{params}')

    def reporte_productos_vendidos(self, fecha_inicio=None, fecha_fin=None, limite=20):
        """Top productos más vendidos"""
        params = f'?limite={limite}'
        if fecha_inicio:
            params += f'&fecha_inicio={fecha_inicio}'
        if fecha_fin:
            params += f'&fecha_fin={fecha_fin}'
        return self._request('GET', f'/api/v1/reportes/productos-vendidos{params}')

    def reporte_ventas_hora(self, fecha_inicio=None, fecha_fin=None):
        """Ventas por hora del día"""
        params = ''
        if fecha_inicio:
            params = f'?fecha_inicio={fecha_inicio}&fecha_fin={fecha_fin}'
        return self._request('GET', f'/api/v1/reportes/ventas-hora{params}')

    def reporte_ventas_categoria(self, fecha_inicio=None, fecha_fin=None):
        """Ventas por categoría"""
        params = ''
        if fecha_inicio:
            params = f'?fecha_inicio={fecha_inicio}&fecha_fin={fecha_fin}'
        return self._request('GET', f'/api/v1/reportes/ventas-categoria{params}')

    def reporte_productos_sin_ventas(self, dias=30):
        """Productos sin ventas en X días"""
        return self._request('GET', f'/api/v1/reportes/productos-sin-ventas?dias={dias}')

    # ============ UPLOAD DE IMAGENES ============

    def subir_imagen(self, ruta_archivo):
        """
        Subir imagen al servidor

        Args:
            ruta_archivo: Ruta local del archivo de imagen

        Returns:
            dict con 'success' y 'url' de la imagen subida
        """
        if not os.path.exists(ruta_archivo):
            return {'error': 'Archivo no encontrado'}

        # Leer archivo y convertir a base64
        with open(ruta_archivo, 'rb') as f:
            img_data = f.read()

        # Determinar tipo de imagen
        ext = ruta_archivo.rsplit('.', 1)[-1].lower()
        mime_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp'
        }
        mime = mime_types.get(ext, 'image/png')

        # Crear data URL
        img_base64 = base64.b64encode(img_data).decode('utf-8')
        data_url = f"data:{mime};base64,{img_base64}"

        return self._request('POST', '/api/v1/upload', {
            'imagen_base64': data_url
        })

    # ============ OFERTAS ============

    def obtener_ofertas(self):
        """Obtener ofertas de la tienda"""
        return self._request('GET', '/api/v1/ofertas')

    def crear_oferta(self, titulo, tipo, **datos):
        """Crear nueva oferta"""
        data = {
            'titulo': titulo,
            'tipo': tipo,
            **datos
        }
        return self._request('POST', '/api/v1/ofertas', data)

    def actualizar_oferta(self, oferta_id, **datos):
        """Actualizar oferta existente"""
        return self._request('PUT', f'/api/v1/ofertas/{oferta_id}', datos)

    def eliminar_oferta(self, oferta_id):
        """Eliminar oferta"""
        return self._request('DELETE', f'/api/v1/ofertas/{oferta_id}')


    # ============ ESTADISTICAS ============

    def obtener_estadisticas(self):
        """Obtener estadisticas del dia"""
        return self._request('GET', '/api/v1/estadisticas')

    # ============ USUARIOS ============

    def obtener_usuarios(self):
        """Obtener usuarios de la tienda"""
        return self._request('GET', '/api/v1/usuarios')

    def crear_usuario(self, nombre, email, password, rol):
        """Crear nuevo usuario"""
        return self._request('POST', '/api/v1/usuarios', {
            'nombre': nombre,
            'email': email,
            'password': password,
            'rol': rol
        })

    def actualizar_usuario(self, id, **datos):
        """Actualizar usuario"""
        return self._request('PUT', f'/api/v1/usuarios/{id}', datos)

    def eliminar_usuario(self, id):
        """Eliminar usuario"""
        return self._request('DELETE', f'/api/v1/usuarios/{id}')


# ============ FUNCIONES DE UTILIDAD ============

def crear_config_tienda(servidor_url, tienda_slug):
    """
    Crear archivo de configuracion para una tienda

    Args:
        servidor_url: URL del servidor (ej: http://mitienda.com:5000)
        tienda_slug: Slug de la tienda (ej: pizzeria1)
    """
    config = {
        'servidor_url': servidor_url,
        'tienda_slug': tienda_slug,
        'token': '',
        'user': {},
        'tienda': {}
    }

    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"Configuracion creada: {config_path}")
    print(f"  Servidor: {servidor_url}")
    print(f"  Tienda: {tienda_slug}")


# Test basico
if __name__ == '__main__':
    # Ejemplo de uso
    print("=== Test API Client ===\n")

    # Crear cliente
    api = APIClient(
        servidor_url='http://localhost:5000',
        tienda_slug='demo'
    )

    print(f"Servidor: {api.servidor_url}")
    print(f"Tienda: {api.tienda_slug}")

    # Intentar login
    print("\nIntentando login...")
    result = api.login('admin@demo.com', 'admin123')

    if result and result.get('success'):
        print(f"Login exitoso!")
        print(f"  Usuario: {api.user['nombre']}")
        print(f"  Rol: {api.user['rol']}")
        print(f"  Tienda: {api.tienda['nombre']}")

        # Obtener productos
        print("\nProductos:")
        productos = api.obtener_productos()
        if isinstance(productos, list):
            for p in productos[:5]:
                print(f"  - {p['nombre']}: ${p['precio']}")

        # Obtener estadisticas
        print("\nEstadisticas:")
        stats = api.obtener_estadisticas()
        if stats and not stats.get('error'):
            print(f"  Pedidos hoy: {stats.get('total_pedidos', 0)}")
            print(f"  Ventas hoy: ${stats.get('ventas_hoy', 0)}")
    else:
        print(f"Error: {result.get('error', 'Desconocido')}")
