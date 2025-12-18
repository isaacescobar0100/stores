#!/usr/bin/env python3
"""
Actualizar TODOS los product-footer para mostrar variantes
"""
import re

template_file = '/var/www/restaurante/templates/cliente/index.html'

with open(template_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Patron para encontrar product-footer con cualquier indentacion
# Buscar desde <div class="product-footer"> hasta </div> que cierra el footer

pattern = r'(<div class="product-footer">)\s*\n\s*(<span class="product-price">\$\{\{ "\{:,\.0f\}"\.format\(producto\.precio\)\|replace\(",", "\."\) \}\}</span>)\s*\n\s*(\{% if tienda\.modo_pedido != \'mesero\' or forzar_carrito %\})\s*\n\s*(<button class="btn-add" onclick="addToCart\(\{\{ producto\.id \}\}\)" id="btn-\{\{ producto\.id \}\}">\+</button>)\s*\n\s*(\{% endif %\})\s*\n\s*(</div>)'

def replacement(match):
    # Detectar la indentacion del match
    indent = ' ' * 24  # indentacion base
    return f'''{{% if producto.tiene_variantes %}}
{indent}<div class="product-variantes">
{indent}    {{% for var in producto.variantes %}}
{indent}    <button class="variante-btn" onclick="addToCartVariante({{{{ producto.id }}}}, {{{{ var.id }}}}, {{{{ var.precio }}}}, '{{{{ var.nombre }}}}')" data-precio="{{{{ var.precio }}}}">
{indent}        {{{{ var.nombre }}}} - ${{{{ "{{:,.0f}}".format(var.precio)|replace(",", ".") }}}}
{indent}    </button>
{indent}    {{% endfor %}}
{indent}</div>
{indent}{{% else %}}
{indent}<div class="product-footer">
{indent}    <span class="product-price">${{{{ "{{:,.0f}}".format(producto.precio)|replace(",", ".") }}}}</span>
{indent}    {{% if tienda.modo_pedido != 'mesero' or forzar_carrito %}}
{indent}    <button class="btn-add" onclick="addToCart({{{{ producto.id }}}})" id="btn-{{{{ producto.id }}}}">+</button>
{indent}    {{% endif %}}
{indent}</div>
{indent}{{% endif %}}'''

# En lugar de regex complicado, hacer reemplazo simple buscando lineas
lines = content.split('\n')
new_lines = []
i = 0
replacements = 0

while i < len(lines):
    line = lines[i]

    # Detectar inicio de product-footer
    if '<div class="product-footer">' in line and 'tiene_variantes' not in lines[max(0,i-1)]:
        # Obtener indentacion
        indent = len(line) - len(line.lstrip())
        ind = ' ' * indent

        # Verificar que las siguientes lineas son el patron esperado
        if i + 5 < len(lines):
            next_lines = '\n'.join(lines[i:i+6])
            if 'product-price' in next_lines and 'btn-add' in next_lines:
                # Reemplazar con version con variantes
                new_lines.append(f'{ind}{{% if producto.tiene_variantes %}}')
                new_lines.append(f'{ind}<div class="product-variantes">')
                new_lines.append(f'{ind}    {{% for var in producto.variantes %}}')
                new_lines.append(f'{ind}    <button class="variante-btn" onclick="addToCartVariante({{{{ producto.id }}}}, {{{{ var.id }}}}, {{{{ var.precio }}}}, \'{{{{ var.nombre }}}}\')">')
                new_lines.append(f'{ind}        {{{{ var.nombre }}}} - ${{{{ "{{:,.0f}}".format(var.precio)|replace(",", ".") }}}}')
                new_lines.append(f'{ind}    </button>')
                new_lines.append(f'{ind}    {{% endfor %}}')
                new_lines.append(f'{ind}</div>')
                new_lines.append(f'{ind}{{% else %}}')
                # Agregar las lineas originales
                for j in range(6):
                    new_lines.append(lines[i+j])
                new_lines.append(f'{ind}{{% endif %}}')
                i += 6
                replacements += 1
                continue

    new_lines.append(line)
    i += 1

content = '\n'.join(new_lines)

with open(template_file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"✓ Actualizados {replacements} product-footer adicionales")
print("Template actualizado!")
