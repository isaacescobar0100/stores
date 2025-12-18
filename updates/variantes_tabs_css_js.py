#!/usr/bin/env python3
"""
Agregar CSS y JavaScript para tabs de variantes
"""

template_file = '/var/www/restaurante/templates/cliente/index.html'

with open(template_file, 'r', encoding='utf-8') as f:
    content = f.read()

# CSS para tabs de variantes
css_variantes = '''
        /* Tabs de variantes */
        .variantes-tabs {
            display: flex;
            gap: 8px;
            padding: 10px 16px;
            overflow-x: auto;
            background: var(--gray-100);
            border-bottom: 1px solid var(--gray-200);
        }

        .variante-tab {
            padding: 8px 16px;
            border: 2px solid var(--primary);
            background: white;
            color: var(--primary);
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.2s ease;
        }

        .variante-tab:hover {
            background: var(--primary-light);
        }

        .variante-tab.active {
            background: var(--primary);
            color: white;
        }

        .variante-tab .precio {
            font-weight: 700;
            margin-left: 4px;
        }
'''

# JavaScript para manejar variantes
js_variantes = '''
        // Variables globales para variantes
        let variantesActuales = [];
        let varianteSeleccionada = null;

        // Funcion para mostrar tabs de variantes cuando se selecciona categoria
        function mostrarVariantesTabs(categoriaElement) {
            const tabsContainer = document.getElementById('variantesTabs');

            // Obtener productos de la categoria activa
            const categoriaId = categoriaElement.dataset.category;
            const section = document.querySelector('.category-section[data-category="' + categoriaId + '"]');

            if (!section) {
                tabsContainer.style.display = 'none';
                return;
            }

            // Obtener variantes del primer producto que tenga variantes
            const cards = section.querySelectorAll('.product-card');
            let variantes = [];

            cards.forEach(card => {
                const priceSpan = card.querySelector('.product-price');
                if (priceSpan && priceSpan.dataset.variantes) {
                    try {
                        const prodVariantes = JSON.parse(priceSpan.dataset.variantes);
                        if (prodVariantes.length > 0 && variantes.length === 0) {
                            variantes = prodVariantes;
                        }
                    } catch(e) {}
                }
            });

            if (variantes.length === 0) {
                tabsContainer.style.display = 'none';
                variantesActuales = [];
                varianteSeleccionada = null;
                return;
            }

            // Mostrar tabs
            variantesActuales = variantes;
            tabsContainer.innerHTML = '';

            variantes.forEach((v, index) => {
                const tab = document.createElement('button');
                tab.className = 'variante-tab' + (index === 0 ? ' active' : '');
                tab.innerHTML = v.nombre + ' <span class="precio">$' + formatPrice(v.precio) + '</span>';
                tab.onclick = function() { seleccionarVariante(v, this); };
                tabsContainer.appendChild(tab);
            });

            tabsContainer.style.display = 'flex';

            // Seleccionar primera variante por defecto
            if (variantes.length > 0) {
                varianteSeleccionada = variantes[0];
                actualizarPreciosConVariante(variantes[0]);
            }
        }

        // Seleccionar una variante
        function seleccionarVariante(variante, tabElement) {
            // Actualizar tabs activos
            document.querySelectorAll('.variante-tab').forEach(t => t.classList.remove('active'));
            tabElement.classList.add('active');

            varianteSeleccionada = variante;
            actualizarPreciosConVariante(variante);
        }

        // Actualizar precios de productos segun variante
        function actualizarPreciosConVariante(variante) {
            document.querySelectorAll('.product-card').forEach(card => {
                const priceSpan = card.querySelector('.product-price');
                if (priceSpan && priceSpan.dataset.variantes) {
                    try {
                        const variantes = JSON.parse(priceSpan.dataset.variantes);
                        const match = variantes.find(v => v.nombre === variante.nombre);
                        if (match) {
                            priceSpan.textContent = '$' + formatPrice(match.precio);
                            card.dataset.currentPrice = match.precio;
                            card.dataset.currentVarianteId = match.id;
                            card.dataset.currentVarianteNombre = match.nombre;
                        }
                    } catch(e) {}
                }
            });
        }

        // Formatear precio
        function formatPrice(precio) {
            return Number(precio).toLocaleString('es-CO', {maximumFractionDigits: 0}).replace(/,/g, '.');
        }

        // Modificar addToCart para usar variante seleccionada
        function addToCartWithVariante(productoId) {
            const card = document.querySelector('#btn-' + productoId).closest('.product-card');
            const varianteId = card.dataset.currentVarianteId || null;
            const varianteNombre = card.dataset.currentVarianteNombre || '';
            const precio = card.dataset.currentPrice || card.dataset.price;

            fetch('/api/carrito/agregar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    producto_id: productoId,
                    variante_id: varianteId,
                    variante_nombre: varianteNombre,
                    precio: parseFloat(precio),
                    cantidad: 1
                })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    updateCartCount(data.total_items);
                    const nombre = card.querySelector('.product-name').textContent;
                    showToast('Agregado: ' + nombre + (varianteNombre ? ' (' + varianteNombre + ')' : ''));
                }
            });
        }

        // Modificar filterCategory para mostrar variantes
        const originalFilterCategory = typeof filterCategory === 'function' ? filterCategory : null;

        function filterCategoryWithVariantes(categoryId, element) {
            // Llamar funcion original si existe
            if (originalFilterCategory) {
                originalFilterCategory(categoryId, element);
            }

            // Mostrar tabs de variantes
            setTimeout(() => {
                mostrarVariantesTabs(element);
            }, 100);
        }
'''

# Agregar CSS
if '.variantes-tabs' not in content:
    content = content.replace('</style>', css_variantes + '\n    </style>')
    print("✓ CSS de variantes tabs agregado")

# Agregar JS antes del ultimo </script>
if 'mostrarVariantesTabs' not in content:
    # Buscar el ultimo </script> antes de </body>
    last_script_idx = content.rfind('</script>')
    if last_script_idx > 0:
        content = content[:last_script_idx] + js_variantes + '\n        ' + content[last_script_idx:]
        print("✓ JavaScript de variantes tabs agregado")

with open(template_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("CSS y JS agregados!")
