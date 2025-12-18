#!/usr/bin/env python3
"""Update backend to track mesero in pedidos"""

import paramiko

host = "72.61.72.32"
user = "root"
password = "Isaacescobar0100."

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=password)

# Read app.py
stdin, stdout, stderr = client.exec_command('cat /var/www/restaurante/app.py')
app_content = stdout.read().decode('utf-8')

# Read models.py
stdin, stdout, stderr = client.exec_command('cat /var/www/restaurante/models.py')
models_content = stdout.read().decode('utf-8')

# ============ UPDATE APP.PY ============

# 1. Add mesero_id capture in api_mesero_crear_pedido
old_code1 = '''def api_mesero_crear_pedido():
    """API para crear pedido desde mesero"""
    data = request.json
    items = data.get('items', [])

    if not items:'''

new_code1 = '''def api_mesero_crear_pedido():
    """API para crear pedido desde mesero"""
    data = request.json
    items = data.get('items', [])

    # Obtener mesero_id del usuario logueado
    mesero_id = session.get('user_id')

    if not items:'''

if old_code1 in app_content:
    app_content = app_content.replace(old_code1, new_code1)
    print("1. Added mesero_id capture")
elif 'mesero_id = session.get' in app_content:
    print("1. mesero_id capture already exists")
else:
    print("1. Pattern not found for mesero_id capture")

# 2. Update Pedido.crear call
old_code2 = '''result = Pedido.crear(
        tienda_id=g.tienda['id'],
        cliente_id=cliente_id,
        tipo='local',
        subtotal=subtotal,
        costo_domicilio=0,
        total=total,
        notas=data.get('notas', ''),
        direccion_entrega=''
    )'''

new_code2 = '''result = Pedido.crear(
        tienda_id=g.tienda['id'],
        cliente_id=cliente_id,
        mesero_id=mesero_id,
        tipo='local',
        subtotal=subtotal,
        costo_domicilio=0,
        total=total,
        notas=data.get('notas', ''),
        direccion_entrega=''
    )'''

if old_code2 in app_content:
    app_content = app_content.replace(old_code2, new_code2)
    print("2. Updated Pedido.crear call")
elif 'mesero_id=mesero_id' in app_content:
    print("2. Pedido.crear already has mesero_id")
else:
    print("2. Pedido.crear pattern not found")

# 3. Add API endpoints for mesero stats
api_endpoints = '''

# ============ API ESTADISTICAS MESEROS ============
@app.route('/api/v1/estadisticas/meseros', methods=['GET'])
@api_requiere_auth
def api_estadisticas_meseros():
    """Obtener estadisticas de ventas por mesero"""
    filtro = request.args.get('filtro', 'hoy')
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    stats = Pedido.obtener_estadisticas_meseros(g.tienda['id'], filtro, fecha_inicio, fecha_fin)
    return jsonify(stats)


@app.route('/api/v1/estadisticas/meseros/<int:mesero_id>/pedidos', methods=['GET'])
@api_requiere_auth
def api_pedidos_mesero(mesero_id):
    """Obtener pedidos de un mesero especifico"""
    filtro = request.args.get('filtro', 'hoy')
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')
    pedidos = Pedido.obtener_pedidos_mesero(g.tienda['id'], mesero_id, filtro, fecha_inicio, fecha_fin)
    return jsonify(pedidos)

'''

if 'api_estadisticas_meseros' not in app_content:
    # Find a good place - after api_get_estadisticas
    marker = "return jsonify(stats)\n\n"
    idx = app_content.rfind(marker)
    if idx > 0:
        app_content = app_content[:idx + len(marker)] + api_endpoints + app_content[idx + len(marker):]
        print("3. Added API endpoints for mesero stats")
    else:
        # Try another approach - add before if __name__
        marker2 = "if __name__ == '__main__':"
        idx2 = app_content.find(marker2)
        if idx2 > 0:
            app_content = app_content[:idx2] + api_endpoints + "\n" + app_content[idx2:]
            print("3. Added API endpoints before main")
        else:
            app_content += api_endpoints
            print("3. Added API endpoints at end")
else:
    print("3. API endpoints already exist")

# ============ UPDATE MODELS.PY ============

# 4. Update INSERT in Pedido.crear
old_insert = "INSERT INTO pedidos (tienda_id, cliente_id, numero_orden, tipo, subtotal,"
new_insert = "INSERT INTO pedidos (tienda_id, cliente_id, mesero_id, numero_orden, tipo, subtotal,"

if old_insert in models_content and 'mesero_id, numero_orden' not in models_content:
    models_content = models_content.replace(old_insert, new_insert)
    print("4. Updated INSERT statement columns")
elif 'mesero_id, numero_orden' in models_content:
    print("4. INSERT already has mesero_id")
else:
    print("4. INSERT pattern not found")

# 5. Update VALUES in Pedido.crear
old_values = "VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})"
new_values = "VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})"

# Count current placeholders
if old_values in models_content:
    models_content = models_content.replace(old_values, new_values, 1)
    print("5. Updated VALUES placeholders")
else:
    print("5. VALUES pattern not found or already updated")

# 6. Update the tuple in Pedido.crear
old_tuple = "(kwargs['tienda_id'], kwargs.get('cliente_id'), numero_orden, kwargs.get('tipo', 'local'),"
new_tuple = "(kwargs['tienda_id'], kwargs.get('cliente_id'), kwargs.get('mesero_id'), numero_orden, kwargs.get('tipo', 'local'),"

if old_tuple in models_content:
    models_content = models_content.replace(old_tuple, new_tuple)
    print("6. Updated parameter tuple")
elif "kwargs.get('mesero_id')" in models_content:
    print("6. Parameter tuple already has mesero_id")
else:
    print("6. Parameter tuple not found")

# 7. Add mesero statistics functions
mesero_funcs = '''
    @staticmethod
    def obtener_estadisticas_meseros(tienda_id, filtro='hoy', fecha_inicio=None, fecha_fin=None):
        """Obtener estadisticas de ventas por mesero"""
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()

        if DB_TYPE == 'mysql':
            if filtro == 'hoy':
                fecha_filter = "AND DATE(p.fecha_pedido) = CURDATE()"
            elif filtro == 'semana':
                fecha_filter = "AND p.fecha_pedido >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
            elif filtro == 'mes':
                fecha_filter = "AND p.fecha_pedido >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"
            elif filtro == 'rango' and fecha_inicio and fecha_fin:
                fecha_filter = f"AND DATE(p.fecha_pedido) BETWEEN '{fecha_inicio}' AND '{fecha_fin}'"
            else:
                fecha_filter = ""
        else:
            if filtro == 'hoy':
                fecha_filter = "AND DATE(p.fecha_pedido) = DATE('now', 'localtime')"
            elif filtro == 'semana':
                fecha_filter = "AND p.fecha_pedido >= DATE('now', '-7 days')"
            elif filtro == 'mes':
                fecha_filter = "AND p.fecha_pedido >= DATE('now', '-30 days')"
            elif filtro == 'rango' and fecha_inicio and fecha_fin:
                fecha_filter = f"AND DATE(p.fecha_pedido) BETWEEN '{fecha_inicio}' AND '{fecha_fin}'"
            else:
                fecha_filter = ""

        query = f"""
            SELECT
                u.id as mesero_id,
                u.nombre as mesero_nombre,
                COUNT(p.id) as total_pedidos,
                COALESCE(SUM(p.total), 0) as total_ventas,
                COALESCE(AVG(p.total), 0) as promedio_pedido
            FROM usuarios u
            LEFT JOIN pedidos p ON p.mesero_id = u.id AND p.tienda_id = {p} AND p.estado != 'cancelado' {fecha_filter}
            WHERE u.tienda_id = {p} AND u.rol = 'mesero' AND u.activo = 1
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
    def obtener_pedidos_mesero(tienda_id, mesero_id, filtro='hoy', fecha_inicio=None, fecha_fin=None):
        """Obtener pedidos de un mesero especifico"""
        p = get_placeholder()
        conn = get_connection()
        cursor = conn.cursor()

        if DB_TYPE == 'mysql':
            if filtro == 'hoy':
                fecha_filter = "AND DATE(p.fecha_pedido) = CURDATE()"
            elif filtro == 'semana':
                fecha_filter = "AND p.fecha_pedido >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
            elif filtro == 'mes':
                fecha_filter = "AND p.fecha_pedido >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"
            elif filtro == 'rango' and fecha_inicio and fecha_fin:
                fecha_filter = f"AND DATE(p.fecha_pedido) BETWEEN '{fecha_inicio}' AND '{fecha_fin}'"
            else:
                fecha_filter = ""
        else:
            if filtro == 'hoy':
                fecha_filter = "AND DATE(p.fecha_pedido) = DATE('now', 'localtime')"
            elif filtro == 'semana':
                fecha_filter = "AND p.fecha_pedido >= DATE('now', '-7 days')"
            elif filtro == 'mes':
                fecha_filter = "AND p.fecha_pedido >= DATE('now', '-30 days')"
            elif filtro == 'rango' and fecha_inicio and fecha_fin:
                fecha_filter = f"AND DATE(p.fecha_pedido) BETWEEN '{fecha_inicio}' AND '{fecha_fin}'"
            else:
                fecha_filter = ""

        query = f"""
            SELECT p.*, c.nombre as cliente_nombre
            FROM pedidos p
            LEFT JOIN clientes c ON p.cliente_id = c.id
            WHERE p.tienda_id = {p} AND p.mesero_id = {p} AND p.estado != 'cancelado' {fecha_filter}
            ORDER BY p.fecha_pedido DESC
        """
        cursor.execute(query, (tienda_id, mesero_id))
        pedidos = [dict_from_row(row) for row in cursor.fetchall()]
        conn.close()
        return pedidos

'''

if 'obtener_estadisticas_meseros' not in models_content:
    # Find the end of Pedido class - look for obtener_estadisticas function
    marker = "def obtener_estadisticas(tienda_id):"
    idx = models_content.find(marker)
    if idx > 0:
        # Find the end of this function
        next_class = models_content.find("\nclass ", idx)
        if next_class > 0:
            models_content = models_content[:next_class] + mesero_funcs + models_content[next_class:]
            print("7. Added mesero statistics functions")
        else:
            models_content += mesero_funcs
            print("7. Added mesero functions at end")
    else:
        models_content += mesero_funcs
        print("7. Added mesero functions at end (no marker)")
else:
    print("7. Mesero functions already exist")

# Write files
sftp = client.open_sftp()

with sftp.file('/var/www/restaurante/app.py', 'w') as f:
    f.write(app_content)
print("8. Written app.py")

with sftp.file('/var/www/restaurante/models.py', 'w') as f:
    f.write(models_content)
print("9. Written models.py")

sftp.close()

# Restart
stdin, stdout, stderr = client.exec_command('docker restart restaurante-web-1')
print("10. Restarting container...")
print(stdout.read().decode())

client.close()
print("\nBackend updated!")
