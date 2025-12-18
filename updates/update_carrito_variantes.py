#!/usr/bin/env python3
"""
Actualizar funcion de carrito para soportar variantes
"""

app_file = '/var/www/restaurante/app.py'

with open(app_file, 'r', encoding='utf-8') as f:
    content = f.read()

old_func = '''def api_carrito_agregar():
    """Agregar producto al carrito"""
    data = request.json
    producto = Producto.obtener_por_id(data['producto_id'])
    if not producto:
        return jsonify({'error': 'Producto no encontrado'}), 404

    carrito = session.get('carrito', [])
    cantidad_nueva = int(data.get('cantidad', 1))

    # Buscar si ya existe (usar .get() para evitar KeyError con ofertas)
    for item in carrito:
        if item.get('producto_id') == producto['id']:
            item['cantidad'] = int(item.get('cantidad', 0)) + cantidad_nueva
            break
    else:
        carrito.append({
            'producto_id': producto['id'],
            'nombre': producto['nombre'],
            'precio': float(producto['precio']),
            'cantidad': cantidad_nueva
        })

    session['carrito'] = carrito
    return jsonify({
        'success': True,
        'total_items': sum(int(item.get('cantidad', 0)) for item in carrito)
    })'''

new_func = '''def api_carrito_agregar():
    """Agregar producto al carrito (con soporte de variantes)"""
    data = request.json
    producto = Producto.obtener_por_id(data['producto_id'])
    if not producto:
        return jsonify({'error': 'Producto no encontrado'}), 404

    carrito = session.get('carrito', [])
    cantidad_nueva = int(data.get('cantidad', 1))

    # Verificar si viene con variante
    variante_id = data.get('variante_id')
    variante_nombre = data.get('variante_nombre', '')
    precio = float(data.get('precio', producto['precio']))

    # Crear key unico para buscar en carrito (producto + variante)
    item_key = f"{producto['id']}_{variante_id}" if variante_id else str(producto['id'])

    # Buscar si ya existe (usar .get() para evitar KeyError con ofertas)
    found = False
    for item in carrito:
        existing_key = f"{item.get('producto_id')}_{item.get('variante_id')}" if item.get('variante_id') else str(item.get('producto_id'))
        if existing_key == item_key:
            item['cantidad'] = int(item.get('cantidad', 0)) + cantidad_nueva
            found = True
            break

    if not found:
        nombre_completo = producto['nombre']
        if variante_nombre:
            nombre_completo = f"{producto['nombre']} ({variante_nombre})"

        carrito.append({
            'producto_id': producto['id'],
            'variante_id': variante_id,
            'variante_nombre': variante_nombre,
            'nombre': nombre_completo,
            'precio': precio,
            'cantidad': cantidad_nueva
        })

    session['carrito'] = carrito
    return jsonify({
        'success': True,
        'total_items': sum(int(item.get('cantidad', 0)) for item in carrito)
    })'''

if old_func in content:
    content = content.replace(old_func, new_func)
    print("✓ Funcion api_carrito_agregar actualizada con soporte de variantes")
else:
    print("✗ No se encontro la funcion exacta")

with open(app_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("app.py actualizado!")
