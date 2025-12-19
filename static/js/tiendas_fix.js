// tiendas_fix.js v20251219
// Fix para cargar valores de costo_domicilio, pedido_minimo, modo_pedido, categorias Y Wompi

(function() {
    console.log('tiendas_fix.js cargado v20251219');

    // Sobrescribir la funcion editarTienda
    window.editarTienda = function(id) {
        showLoading('Cargando datos...');

        Promise.all([
            fetch('/superadmin/api/tiendas/' + id).then(r => r.json()),
            fetch('/superadmin/api/tiendas/' + id + '/categorias').then(r => r.json()),
            fetch('/superadmin/api/categorias-maestras').then(r => r.json())
        ])
        .then(function(results) {
            var tienda = results[0];
            var catsAsignadas = results[1];
            var catsMaestras = results[2];

            // DEBUG: Ver qué devuelve la API
            console.log('=== DEBUG CATEGORIAS ===');
            console.log('catsAsignadas (raw):', JSON.stringify(catsAsignadas.slice(0, 3)));
            console.log('Ejemplo cat:', catsAsignadas[0]);
            if (catsAsignadas[0]) {
                console.log('asignada value:', catsAsignadas[0].asignada, 'tipo:', typeof catsAsignadas[0].asignada);
            }

            hideLoading();
            document.getElementById('modalTitulo').textContent = 'Editar Tienda';
            document.getElementById('tiendaId').value = tienda.id;
            document.getElementById('tiendaNombre').value = tienda.nombre;
            document.getElementById('tiendaSubdominio').value = tienda.subdominio;
            document.getElementById('tiendaEmail').value = tienda.email || '';
            document.getElementById('tiendaTelefono').value = tienda.telefono || '';
            document.getElementById('tiendaDireccion').value = tienda.direccion || '';
            document.getElementById('tiendaHorario').value = tienda.horario || '';
            document.getElementById('tiendaSlogan').value = tienda.slogan || '';

            if (typeof setLogoPreview === 'function') setLogoPreview(tienda.logo || '');
            if (typeof setBannerPreview === 'function') setBannerPreview(tienda.banner_url || '');

            var colorPrimario = tienda.color_primario || '#ff441f';
            var colorSecundario = tienda.color_secundario || '#00b14f';
            var colorTerciario = tienda.color_terciario || '#f5f5f5';
            document.getElementById('tiendaColorPrimario').value = colorPrimario;
            document.getElementById('tiendaColorPrimarioText').value = colorPrimario;
            document.getElementById('tiendaColorSecundario').value = colorSecundario;
            document.getElementById('tiendaColorSecundarioText').value = colorSecundario;
            document.getElementById('tiendaColorTerciario').value = colorTerciario;
            document.getElementById('tiendaColorTerciarioText').value = colorTerciario;

            var costoDomInput = document.getElementById('tiendaCostoDomicilio');
            if (costoDomInput) costoDomInput.value = tienda.costo_domicilio || 0;

            var pedidoMinInput = document.getElementById('tiendaPedidoMinimo');
            if (pedidoMinInput) pedidoMinInput.value = tienda.pedido_minimo || 0;

            var modoPedSelect = document.getElementById('tiendaModoPedido');
            if (modoPedSelect) modoPedSelect.value = tienda.modo_pedido || 'normal';

            // CARGAR CATEGORIAS - Renderizar directamente
            // Filtrar por asignada (puede ser 1, true, o "1")
            var asignadas = catsAsignadas.filter(function(c) {
                return c.asignada === 1 || c.asignada === true || c.asignada === "1";
            }).map(function(c) { return c.id; });
            console.log('IDs asignadas filtradas:', asignadas);
            window.categoriasSeleccionadas = asignadas;

            var container = document.getElementById('categoriasSelector');
            container.innerHTML = '';

            console.log('IDs catsMaestras:', catsMaestras.map(function(c) { return c.id; }));
            catsMaestras.forEach(function(cat) {
                var seleccionada = asignadas.indexOf(cat.id) !== -1;
                if (seleccionada) console.log('Categoria seleccionada:', cat.id, cat.nombre);
                var item = document.createElement('div');
                item.className = 'categoria-item' + (seleccionada ? ' seleccionada' : '');
                item.dataset.id = cat.id;
                item.onclick = function() { toggleCategoria(item, cat.id); };

                var img = document.createElement('img');
                img.src = cat.icono_url;
                img.style.cssText = 'width: 32px; height: 32px; object-fit: contain;';
                img.onerror = function() { this.src = 'https://cdn-icons-png.flaticon.com/128/1046/1046857.png'; };

                var span = document.createElement('span');
                span.style.cssText = 'font-size: 11px; text-align: center; margin-top: 4px;';
                span.textContent = cat.nombre;

                var check = document.createElement('div');
                check.className = 'check-mark';
                check.innerHTML = '<i class="fas fa-check"></i>';

                item.appendChild(img);
                item.appendChild(span);
                item.appendChild(check);
                container.appendChild(item);
            });

            if (typeof actualizarContadorCategorias === 'function') actualizarContadorCategorias();
            console.log('Categorias renderizadas:', catsMaestras.length, 'maestras,', asignadas.length, 'asignadas');

            // Cargar configuración Wompi
            var wompiActivo = tienda.wompi_activo == 1;
            var wompiCheckbox = document.getElementById('tiendaWompiActivo');
            if (wompiCheckbox) {
                wompiCheckbox.checked = wompiActivo;
                var wompiCreds = document.getElementById('wompiCredenciales');
                if (wompiCreds) wompiCreds.style.display = wompiActivo ? 'block' : 'none';
            }
            var wompiPublic = document.getElementById('tiendaWompiPublicKey');
            if (wompiPublic) wompiPublic.value = tienda.wompi_public_key || '';
            var wompiPrivate = document.getElementById('tiendaWompiPrivateKey');
            if (wompiPrivate) wompiPrivate.value = tienda.wompi_private_key ? '********' : '';
            var wompiEvento = document.getElementById('tiendaWompiEventoKey');
            if (wompiEvento) wompiEvento.value = tienda.wompi_evento_key ? '********' : '';
            var wompiIntegrity = document.getElementById('tiendaWompiIntegrityKey');
            if (wompiIntegrity) wompiIntegrity.value = tienda.wompi_integrity_key ? '********' : '';

            document.getElementById('modalTienda').classList.add('active');
        })
        .catch(function(err) {
            hideLoading();
            console.error('Error cargando tienda:', err);
            showToast('error', 'Error', 'No se pudieron cargar los datos');
        });
    };

    console.log('editarTienda sobrescrita correctamente');
})();
