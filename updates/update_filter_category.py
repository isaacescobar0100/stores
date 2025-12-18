#!/usr/bin/env python3
"""
Modificar filterCategory para llamar mostrarVariantesTabs
"""

template_file = '/var/www/restaurante/templates/cliente/index.html'

with open(template_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar la funcion filterCategory y agregar llamada a mostrarVariantesTabs al final
old_func = '''function filterCategory(category, element) {
    // Actualizar botón activo
    document.querySelectorAll('.category-nav-item').forEach(el => el.classList.remove('active'));
    element.classList.add('active');

    // Ocultar sección destacados y ofertas
    var featuredSection = document.getElementById('featuredSection');
    var offersSection = document.querySelector('.offers-section');
    if (featuredSection) featuredSection.style.display = 'none';
    if (offersSection) offersSection.style.display = 'none';

    // Mostrar botón volver
    var btnBack = document.getElementById('btnBackHome');
    if (btnBack) btnBack.classList.add('visible');

    // Ocultar todas las categorías primero
    document.querySelectorAll('.category-section').forEach(section => {
        section.classList.remove('visible');
    });

    // Mostrar solo la categoría seleccionada
    const targetSection = document.querySelector('.category-section[data-category="' + category + '"]');
    if (targetSection) {
        targetSection.classList.add('visible');
        smoothScrollTo(targetSection);
    }

    // Scroll el nav de categorías para mostrar el elemento activo
    scrollCategoryNavToActive(element);
}'''

new_func = '''function filterCategory(category, element) {
    // Actualizar botón activo
    document.querySelectorAll('.category-nav-item').forEach(el => el.classList.remove('active'));
    element.classList.add('active');

    // Ocultar sección destacados y ofertas
    var featuredSection = document.getElementById('featuredSection');
    var offersSection = document.querySelector('.offers-section');
    if (featuredSection) featuredSection.style.display = 'none';
    if (offersSection) offersSection.style.display = 'none';

    // Mostrar botón volver
    var btnBack = document.getElementById('btnBackHome');
    if (btnBack) btnBack.classList.add('visible');

    // Ocultar todas las categorías primero
    document.querySelectorAll('.category-section').forEach(section => {
        section.classList.remove('visible');
    });

    // Mostrar solo la categoría seleccionada
    const targetSection = document.querySelector('.category-section[data-category="' + category + '"]');
    if (targetSection) {
        targetSection.classList.add('visible');
        smoothScrollTo(targetSection);
    }

    // Scroll el nav de categorías para mostrar el elemento activo
    scrollCategoryNavToActive(element);

    // Mostrar tabs de variantes si aplica
    setTimeout(function() {
        if (typeof mostrarVariantesTabs === 'function') {
            mostrarVariantesTabs(element);
        }
    }, 50);
}'''

if old_func in content:
    content = content.replace(old_func, new_func)
    print("✓ filterCategory actualizado con llamada a mostrarVariantesTabs")
else:
    print("✗ No se encontro la funcion exacta")

with open(template_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Template actualizado!")
