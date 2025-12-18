#!/usr/bin/env python3
"""
Actualizar template para mostrar variantes de productos
"""

template_file = '/var/www/restaurante/templates/cliente/index.html'

with open(template_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar el product-footer y reemplazarlo para incluir variantes
# Hay que hacerlo en ambos lugares (subcategorias y categorias simples)

old_footer = '''<div class="product-footer">
                            <span class="product-price">${{ "{:,.0f}".format(producto.precio)|replace(",", ".") }}</span>
                            {% if tienda.modo_pedido != 'mesero' or forzar_carrito %}
                            <button class="btn-add" onclick="addToCart({{ producto.id }})" id="btn-{{ producto.id }}">+</button>
                            {% endif %}
                        </div>'''

new_footer = '''{% if producto.tiene_variantes %}
                        <div class="product-variantes">
                            {% for var in producto.variantes %}
                            <button class="variante-btn" onclick="addToCartVariante({{ producto.id }}, {{ var.id }}, {{ var.precio }}, '{{ var.nombre }}')" data-precio="{{ var.precio }}">
                                {{ var.nombre }} - ${{ "{:,.0f}".format(var.precio)|replace(",", ".") }}
                            </button>
                            {% endfor %}
                        </div>
                        {% else %}
                        <div class="product-footer">
                            <span class="product-price">${{ "{:,.0f}".format(producto.precio)|replace(",", ".") }}</span>
                            {% if tienda.modo_pedido != 'mesero' or forzar_carrito %}
                            <button class="btn-add" onclick="addToCart({{ producto.id }})" id="btn-{{ producto.id }}">+</button>
                            {% endif %}
                        </div>
                        {% endif %}'''

count = content.count(old_footer)
if count > 0:
    content = content.replace(old_footer, new_footer)
    print(f"✓ Reemplazados {count} product-footer con soporte de variantes")
else:
    print("✗ No se encontro el product-footer exacto")

with open(template_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Template actualizado!")
