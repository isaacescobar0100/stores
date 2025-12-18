#!/usr/bin/env python3
"""
Implementar variantes como tabs/filtros arriba de los productos
"""

template_file = '/var/www/restaurante/templates/cliente/index.html'

with open(template_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Primero revertir los cambios de variantes en las cards
# Buscar el patron con tiene_variantes y quitarlo

# Revertir product-footer a version simple
old_with_variantes = '''{% if producto.tiene_variantes %}
                        <div class="product-variantes">
                            {% for var in producto.variantes %}
                            <button class="variante-btn" onclick="addToCartVariante({{ producto.id }}, {{ var.id }}, {{ var.precio }}, '{{ var.nombre }}')">
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

simple_footer = '''<div class="product-footer">
                            <span class="product-price" data-base-price="{{ producto.precio }}" data-variantes='{{ producto.variantes | tojson if producto.variantes else "[]" }}'>${{ "{:,.0f}".format(producto.precio)|replace(",", ".") }}</span>
                            {% if tienda.modo_pedido != 'mesero' or forzar_carrito %}
                            <button class="btn-add" onclick="addToCartWithVariante({{ producto.id }})" id="btn-{{ producto.id }}">+</button>
                            {% endif %}
                        </div>'''

# Revertir todas las instancias
content = content.replace(old_with_variantes, simple_footer)
print("✓ Revertidos footers con variantes")

with open(template_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Template actualizado - Paso 1 completado")
