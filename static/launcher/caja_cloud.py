"""
Panel de Caja - Sistema Restaurante
Gestión de pagos y cobros
"""
import customtkinter as ctk
from tkinter import messagebox
import threading
from datetime import datetime
import pytz
import os
import re
import tempfile

# Para generar QR
try:
    import qrcode
    from PIL import Image
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

# Configuración de CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def convertir_fecha_utc_a_colombia(fecha_str, formato_salida='%d %b %Y %H:%M'):
    """Convertir fecha UTC a hora Colombia"""
    if not fecha_str:
        return ''
    try:
        if isinstance(fecha_str, str):
            fecha_str = fecha_str.replace('T', ' ').split('.')[0]
            fecha_utc = datetime.strptime(fecha_str, '%Y-%m-%d %H:%M:%S')
        else:
            fecha_utc = fecha_str

        utc = pytz.UTC
        colombia = pytz.timezone('America/Bogota')
        fecha_utc = utc.localize(fecha_utc)
        fecha_colombia = fecha_utc.astimezone(colombia)
        return fecha_colombia.strftime(formato_salida)
    except:
        return str(fecha_str)[:16] if fecha_str else ''


class Theme:
    """Tema oscuro moderno"""
    BG_PRIMARY = "#0f0f0f"
    BG_SECONDARY = "#1a1a1a"
    BG_CARD = "#1e1e1e"
    BG_ELEVATED = "#2d2d2d"
    BG_INPUT = "#3d3d3d"

    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#a0a0a0"
    TEXT_MUTED = "#6b6b6b"

    ACCENT = "#f59e0b"  # Amarillo/naranja para caja
    SUCCESS = "#22c55e"
    WARNING = "#f59e0b"
    ERROR = "#ef4444"

    FONT_FAMILY = "Segoe UI"


class CajaApp:
    """Aplicación de Caja"""

    def __init__(self, parent, api):
        self.parent = parent
        self.api = api
        self.running = True

        # Variables de filtro y búsqueda
        self.filtro_activo = "todos"  # todos, efectivo, transferencia
        self.busqueda_texto = ""
        self.pedidos_cache = []  # Cache de pedidos para filtrar

        # Configurar ventana
        self.parent.title("Panel de Caja")
        self.parent.geometry("1000x700")
        self.parent.configure(fg_color=Theme.BG_PRIMARY)

        # Centrar
        self.parent.update_idletasks()
        x = (self.parent.winfo_screenwidth() - 1000) // 2
        y = (self.parent.winfo_screenheight() - 700) // 2
        self.parent.geometry(f"+{x}+{y}")

        self._crear_widgets()
        self._cargar_pedidos()

    def _crear_widgets(self):
        """Crear interfaz"""
        # Header
        header = ctk.CTkFrame(self.parent, fg_color=Theme.BG_SECONDARY, height=70)
        header.pack(fill='x')
        header.pack_propagate(False)

        header_content = ctk.CTkFrame(header, fg_color="transparent")
        header_content.pack(fill='both', expand=True, padx=24, pady=12)

        # Título
        title_frame = ctk.CTkFrame(header_content, fg_color="transparent")
        title_frame.pack(side='left')

        ctk.CTkLabel(
            title_frame,
            text="💰 Panel de Caja",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=22, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(side='left')

        # Info tienda
        tienda_nombre = self.api.tienda.get('nombre', '')
        if tienda_nombre:
            ctk.CTkLabel(
                title_frame,
                text=f"  •  {tienda_nombre}",
                font=ctk.CTkFont(size=14),
                text_color=Theme.TEXT_MUTED
            ).pack(side='left', padx=(10, 0))

        # Botón actualizar
        ctk.CTkButton(
            header_content,
            text="🔄 Actualizar",
            font=ctk.CTkFont(size=13),
            fg_color=Theme.BG_ELEVATED,
            hover_color=Theme.BG_INPUT,
            text_color=Theme.TEXT_SECONDARY,
            height=38,
            corner_radius=8,
            command=self._cargar_pedidos
        ).pack(side='right')

        # Container principal
        main_container = ctk.CTkFrame(self.parent, fg_color="transparent")
        main_container.pack(fill='both', expand=True, padx=24, pady=16)

        # Layout: 2 columnas
        main_container.grid_columnconfigure(0, weight=2)
        main_container.grid_columnconfigure(1, weight=1)
        main_container.grid_rowconfigure(0, weight=1)

        # Columna izquierda - Pedidos pendientes de pago
        left_frame = ctk.CTkFrame(main_container, fg_color=Theme.BG_CARD, corner_radius=12)
        left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 12))

        # Header pedidos
        pedidos_header = ctk.CTkFrame(left_frame, fg_color="transparent")
        pedidos_header.pack(fill='x', padx=20, pady=16)

        ctk.CTkLabel(
            pedidos_header,
            text="Pedidos Pendientes de Pago",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(side='left')

        self.pedidos_count_label = ctk.CTkLabel(
            pedidos_header,
            text="0 pedidos",
            font=ctk.CTkFont(size=12),
            text_color=Theme.TEXT_MUTED
        )
        self.pedidos_count_label.pack(side='right')

        # Barra de búsqueda y filtros
        search_filter_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        search_filter_frame.pack(fill='x', padx=20, pady=(0, 12))

        # Campo de búsqueda
        search_frame = ctk.CTkFrame(search_filter_frame, fg_color="transparent")
        search_frame.pack(side='left', fill='x', expand=True)

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 Buscar por # orden...",
            font=ctk.CTkFont(size=13),
            fg_color=Theme.BG_INPUT,
            border_color=Theme.BG_ELEVATED,
            text_color=Theme.TEXT_PRIMARY,
            height=36,
            corner_radius=8,
            width=180
        )
        self.search_entry.pack(side='left')
        self.search_entry.bind('<KeyRelease>', self._on_search)

        # Botones de filtro
        filter_frame = ctk.CTkFrame(search_filter_frame, fg_color="transparent")
        filter_frame.pack(side='right')

        # Filtro: Todos
        self.btn_filtro_todos = ctk.CTkButton(
            filter_frame,
            text="Todos",
            font=ctk.CTkFont(size=12),
            fg_color=Theme.ACCENT,
            hover_color=Theme.WARNING,
            text_color="white",
            height=32,
            width=70,
            corner_radius=6,
            command=lambda: self._set_filtro("todos")
        )
        self.btn_filtro_todos.pack(side='left', padx=(0, 6))

        # Filtro: Efectivo
        self.btn_filtro_efectivo = ctk.CTkButton(
            filter_frame,
            text="💵 Efectivo",
            font=ctk.CTkFont(size=12),
            fg_color=Theme.BG_ELEVATED,
            hover_color=Theme.BG_INPUT,
            text_color=Theme.TEXT_SECONDARY,
            height=32,
            width=90,
            corner_radius=6,
            command=lambda: self._set_filtro("efectivo")
        )
        self.btn_filtro_efectivo.pack(side='left', padx=(0, 6))

        # Filtro: Transferencia
        self.btn_filtro_transferencia = ctk.CTkButton(
            filter_frame,
            text="💳 Transfer",
            font=ctk.CTkFont(size=12),
            fg_color=Theme.BG_ELEVATED,
            hover_color=Theme.BG_INPUT,
            text_color=Theme.TEXT_SECONDARY,
            height=32,
            width=90,
            corner_radius=6,
            command=lambda: self._set_filtro("transferencia")
        )
        self.btn_filtro_transferencia.pack(side='left')

        # Lista de pedidos
        self.pedidos_scroll = ctk.CTkScrollableFrame(left_frame, fg_color="transparent")
        self.pedidos_scroll.pack(fill='both', expand=True, padx=12, pady=(0, 12))

        # Columna derecha - Resumen del día
        right_frame = ctk.CTkFrame(main_container, fg_color=Theme.BG_CARD, corner_radius=12)
        right_frame.grid(row=0, column=1, sticky='nsew')

        # Header resumen
        ctk.CTkLabel(
            right_frame,
            text="Resumen del Día",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor='w', padx=20, pady=(16, 12))

        # Stats container
        self.stats_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        self.stats_frame.pack(fill='x', padx=16, pady=(0, 16))

        # Stat cards
        self._crear_stat_card(self.stats_frame, "Total Ventas", "$0", Theme.SUCCESS, "total_ventas")
        self._crear_stat_card(self.stats_frame, "Efectivo", "$0", Theme.WARNING, "efectivo")
        self._crear_stat_card(self.stats_frame, "Transferencia", "$0", "#3b82f6", "transferencia")
        self._crear_stat_card(self.stats_frame, "Pendientes", "$0", Theme.ERROR, "pendientes")

    def _crear_stat_card(self, parent, label, value, color, key):
        """Crear tarjeta de estadística"""
        card = ctk.CTkFrame(parent, fg_color=Theme.BG_ELEVATED, corner_radius=8)
        card.pack(fill='x', pady=6)

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill='x', padx=16, pady=12)

        ctk.CTkLabel(
            content,
            text=label,
            font=ctk.CTkFont(size=12),
            text_color=Theme.TEXT_MUTED
        ).pack(anchor='w')

        value_label = ctk.CTkLabel(
            content,
            text=value,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=color
        )
        value_label.pack(anchor='w', pady=(4, 0))

        # Guardar referencia
        setattr(self, f"stat_{key}", value_label)

    def _on_search(self, event=None):
        """Manejar búsqueda en tiempo real"""
        self.busqueda_texto = self.search_entry.get().strip()
        self._aplicar_filtros()

    def _set_filtro(self, filtro):
        """Cambiar filtro activo"""
        self.filtro_activo = filtro

        # Actualizar estilo de botones
        # Reset todos los botones
        self.btn_filtro_todos.configure(
            fg_color=Theme.BG_ELEVATED,
            text_color=Theme.TEXT_SECONDARY
        )
        self.btn_filtro_efectivo.configure(
            fg_color=Theme.BG_ELEVATED,
            text_color=Theme.TEXT_SECONDARY
        )
        self.btn_filtro_transferencia.configure(
            fg_color=Theme.BG_ELEVATED,
            text_color=Theme.TEXT_SECONDARY
        )

        # Resaltar botón activo
        if filtro == "todos":
            self.btn_filtro_todos.configure(fg_color=Theme.ACCENT, text_color="white")
        elif filtro == "efectivo":
            self.btn_filtro_efectivo.configure(fg_color=Theme.SUCCESS, text_color="white")
        elif filtro == "transferencia":
            self.btn_filtro_transferencia.configure(fg_color="#3b82f6", text_color="white")

        self._aplicar_filtros()

    def _aplicar_filtros(self):
        """Aplicar filtros y búsqueda a los pedidos en cache"""
        pedidos_filtrados = []

        for p in self.pedidos_cache:
            metodo = p.get('metodo_pago', 'efectivo')
            numero_orden = str(p.get('numero_orden', p.get('id', '')))

            # Filtrar por tipo de pago
            if self.filtro_activo == "efectivo" and metodo == 'wompi':
                continue
            if self.filtro_activo == "transferencia" and metodo != 'wompi':
                continue

            # Filtrar por búsqueda
            if self.busqueda_texto:
                if self.busqueda_texto.lower() not in numero_orden.lower():
                    continue

            pedidos_filtrados.append(p)

        self._mostrar_pedidos(pedidos_filtrados)

    def _cargar_pedidos(self):
        """Cargar pedidos pendientes de pago"""
        def load():
            try:
                pedidos = self.api.obtener_pedidos(limite=100)

                # Filtrar pedidos pendientes (no pagados con wompi)
                pedidos_pendientes = []
                total_ventas = 0
                total_efectivo = 0
                total_transferencia = 0
                total_pendientes = 0

                if isinstance(pedidos, list):
                    for p in pedidos:
                        metodo = p.get('metodo_pago', 'efectivo')
                        estado = p.get('estado', '')
                        total = float(p.get('total', 0) or 0)

                        # Contar ventas por tipo
                        if estado in ('listo', 'entregado'):
                            total_ventas += total
                            if metodo == 'wompi':
                                total_transferencia += total
                            else:
                                total_efectivo += total

                        # Pedidos pendientes de pago (no entregados ni cancelados)
                        if estado not in ('entregado', 'cancelado'):
                            pedidos_pendientes.append(p)
                            total_pendientes += total

                # Guardar en cache para filtros
                self.pedidos_cache = pedidos_pendientes

                self.parent.after(0, self._aplicar_filtros)
                self.parent.after(0, lambda: self._actualizar_stats(
                    total_ventas, total_efectivo, total_transferencia, total_pendientes
                ))
            except Exception as e:
                print(f"Error cargando pedidos: {e}")

        threading.Thread(target=load, daemon=True).start()

    def _actualizar_stats(self, total_ventas, efectivo, transferencia, pendientes):
        """Actualizar estadísticas"""
        self.stat_total_ventas.configure(text=f"${total_ventas:,.0f}")
        self.stat_efectivo.configure(text=f"${efectivo:,.0f}")
        self.stat_transferencia.configure(text=f"${transferencia:,.0f}")
        self.stat_pendientes.configure(text=f"${pendientes:,.0f}")

    def _mostrar_pedidos(self, pedidos):
        """Mostrar lista de pedidos"""
        # Limpiar lista
        for widget in self.pedidos_scroll.winfo_children():
            widget.destroy()

        self.pedidos_count_label.configure(text=f"{len(pedidos)} pedidos")

        if not pedidos:
            ctk.CTkLabel(
                self.pedidos_scroll,
                text="No hay pedidos pendientes de pago",
                font=ctk.CTkFont(size=14),
                text_color=Theme.TEXT_MUTED
            ).pack(pady=40)
            return

        for pedido in pedidos:
            self._crear_pedido_card(pedido)

    def _crear_pedido_card(self, pedido):
        """Crear tarjeta de pedido"""
        card = ctk.CTkFrame(self.pedidos_scroll, fg_color=Theme.BG_ELEVATED, corner_radius=10)
        card.pack(fill='x', pady=6)

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill='x', padx=16, pady=12)

        # Fila superior: número orden y cliente
        top_row = ctk.CTkFrame(content, fg_color="transparent")
        top_row.pack(fill='x')

        numero_orden = pedido.get('numero_orden', pedido.get('id', ''))
        ctk.CTkLabel(
            top_row,
            text=f"#{numero_orden}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(side='left')

        cliente = pedido.get('cliente_nombre', 'Sin nombre')
        ctk.CTkLabel(
            top_row,
            text=cliente,
            font=ctk.CTkFont(size=13),
            text_color=Theme.TEXT_SECONDARY
        ).pack(side='left', padx=(12, 0))

        # Badge de método de pago
        metodo = pedido.get('metodo_pago', 'efectivo')
        if metodo == 'wompi':
            metodo_text = "💳 TRANSFER"
            metodo_color = "#3b82f6"
        else:
            metodo_text = "💵 EFECTIVO"
            metodo_color = Theme.SUCCESS

        ctk.CTkLabel(
            top_row,
            text=metodo_text,
            font=ctk.CTkFont(size=9, weight="bold"),
            fg_color=metodo_color,
            text_color="white",
            corner_radius=4,
            padx=6,
            pady=2
        ).pack(side='right', padx=(6, 0))

        # Tipo de pedido
        tipo = pedido.get('tipo', 'local')
        tipo_colors = {
            'local': '#6b7280',
            'domicilio': '#8b5cf6',
            'para_llevar': '#06b6d4'
        }
        ctk.CTkLabel(
            top_row,
            text=tipo.upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=tipo_colors.get(tipo, '#6b7280'),
            text_color="white",
            corner_radius=4,
            padx=8,
            pady=2
        ).pack(side='right')

        # Fila inferior: total y botones
        bottom_row = ctk.CTkFrame(content, fg_color="transparent")
        bottom_row.pack(fill='x', pady=(10, 0))

        total = float(pedido.get('total', 0) or 0)
        ctk.CTkLabel(
            bottom_row,
            text=f"${total:,.0f}",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=Theme.SUCCESS
        ).pack(side='left')

        # Botones
        buttons_frame = ctk.CTkFrame(bottom_row, fg_color="transparent")
        buttons_frame.pack(side='right')

        # Botón QR Pago (imprimir comanda con QR)
        ctk.CTkButton(
            buttons_frame,
            text="🖨️ QR Pago",
            font=ctk.CTkFont(size=12),
            fg_color="#3b82f6",
            hover_color="#2563eb",
            text_color="white",
            height=32,
            corner_radius=6,
            command=lambda p=pedido: self._generar_qr_pago(p)
        ).pack(side='left', padx=(0, 8))

        # Botón Cobrar Efectivo
        ctk.CTkButton(
            buttons_frame,
            text="💵 Efectivo",
            font=ctk.CTkFont(size=12),
            fg_color=Theme.SUCCESS,
            hover_color="#16a34a",
            text_color="white",
            height=32,
            corner_radius=6,
            command=lambda p=pedido: self._cobrar_efectivo(p)
        ).pack(side='left')

    def _limpiar_texto(self, texto):
        """Limpiar texto para impresión térmica"""
        if not texto:
            return ''
        # Remover emojis
        texto = re.sub(r'[\U0001F600-\U0001F64F]', '', texto)
        texto = re.sub(r'[\U0001F300-\U0001F5FF]', '', texto)
        texto = re.sub(r'[\U0001F680-\U0001F6FF]', '', texto)
        texto = re.sub(r'[\U0001F900-\U0001F9FF]', '', texto)
        texto = re.sub(r'[\U00002600-\U000026FF]', '', texto)
        texto = re.sub(r'[\U00002700-\U000027BF]', '', texto)
        # Reemplazar acentos
        reemplazos = {'á':'a','é':'e','í':'i','ó':'o','ú':'u',
                     'Á':'A','É':'E','Í':'I','Ó':'O','Ú':'U',
                     'ñ':'n','Ñ':'N','ü':'u','Ü':'U'}
        for orig, remp in reemplazos.items():
            texto = texto.replace(orig, remp)
        return texto.strip()

    def _generar_qr_pago(self, pedido):
        """Generar QR de pago e imprimir comanda"""
        pedido_id = pedido.get('id')
        total = float(pedido.get('total', 0) or 0)
        numero_orden = pedido.get('numero_orden', pedido_id)

        # Mostrar diálogo de progreso
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title(f"QR de Pago - Pedido #{numero_orden}")
        dialog.geometry("400x300")
        dialog.configure(fg_color=Theme.BG_PRIMARY)
        dialog.transient(self.parent)
        dialog.grab_set()

        # Centrar
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 400) // 2
        y = (dialog.winfo_screenheight() - 300) // 2
        dialog.geometry(f"+{x}+{y}")

        container = ctk.CTkFrame(dialog, fg_color="transparent")
        container.pack(fill='both', expand=True, padx=24, pady=20)

        ctk.CTkLabel(
            container,
            text=f"Pedido #{numero_orden}",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(pady=(0, 8))

        ctk.CTkLabel(
            container,
            text=f"Total: ${total:,.0f}",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=Theme.SUCCESS
        ).pack(pady=(0, 20))

        # Estado de generación
        status_label = ctk.CTkLabel(
            container,
            text="Generando link de pago...",
            font=ctk.CTkFont(size=14),
            text_color=Theme.ACCENT
        )
        status_label.pack(pady=10)

        # Progress bar
        progress = ctk.CTkProgressBar(container, width=250)
        progress.pack(pady=10)
        progress.set(0)

        def generar_e_imprimir():
            try:
                # 1. Generar link de pago
                self.parent.after(0, lambda: status_label.configure(text="Generando link de pago..."))
                result = self.api.generar_link_pago(pedido_id)

                if not result or not result.get('success'):
                    error = result.get('error', 'Error desconocido') if result else 'Error de conexión'
                    self.parent.after(0, lambda: status_label.configure(text=f"Error: {error}", text_color=Theme.ERROR))
                    return

                link = result.get('link', '')
                self.parent.after(0, lambda: progress.set(0.3))
                self.parent.after(0, lambda: status_label.configure(text="Generando código QR..."))

                # 2. Generar imagen QR
                qr_path = self._generar_imagen_qr(link, numero_orden)
                if not qr_path:
                    self.parent.after(0, lambda: status_label.configure(
                        text="Error: No se pudo generar QR", text_color=Theme.ERROR))
                    return

                self.parent.after(0, lambda: progress.set(0.6))
                self.parent.after(0, lambda: status_label.configure(text="Imprimiendo comanda..."))

                # 3. Imprimir comanda con QR
                self._imprimir_comanda_qr(pedido, link, qr_path)

                self.parent.after(0, lambda: progress.set(1.0))
                self.parent.after(0, lambda: status_label.configure(
                    text="¡Comanda impresa!", text_color=Theme.SUCCESS))

                # Cerrar diálogo después de 1.5 segundos
                self.parent.after(1500, dialog.destroy)

            except Exception as e:
                self.parent.after(0, lambda: status_label.configure(
                    text=f"Error: {e}", text_color=Theme.ERROR))

        # Simular progreso inicial
        def update_progress(val):
            if val < 0.2:
                progress.set(val)
                self.parent.after(50, lambda: update_progress(val + 0.02))

        update_progress(0)
        threading.Thread(target=generar_e_imprimir, daemon=True).start()

    def _generar_imagen_qr(self, link, numero_orden):
        """Generar imagen QR para el link de pago"""
        if not HAS_QRCODE:
            # Si no tiene qrcode, no podemos generar
            return None

        try:
            # Crear QR
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=6,
                border=2,
            )
            qr.add_data(link)
            qr.make(fit=True)

            # Crear imagen
            img = qr.make_image(fill_color="black", back_color="white")

            # Guardar en archivo temporal
            carpeta = "C:\\fast_comandas\\"
            if not os.path.exists(carpeta):
                os.makedirs(carpeta, exist_ok=True)

            qr_path = os.path.join(carpeta, f"qr_pago_{numero_orden}.png")
            img.save(qr_path)

            return qr_path
        except Exception as e:
            print(f"Error generando QR: {e}")
            return None

    def _generar_qr_escpos(self, link):
        """Generar comandos ESC/POS nativos para QR Code"""
        # Comando QR nativo ESC/POS (funciona en la mayoría de impresoras térmicas modernas)
        # GS ( k - QR Code commands

        data = link.encode('utf-8')
        data_len = len(data) + 3

        qr_commands = bytearray()

        # 1. Seleccionar modelo QR (Model 2)
        # GS ( k pL pH cn fn n
        qr_commands.extend([0x1D, 0x28, 0x6B, 0x04, 0x00, 0x31, 0x41, 0x32, 0x00])

        # 2. Configurar tamaño del módulo (tamaño 6 - mediano/grande)
        # GS ( k pL pH cn fn n
        qr_commands.extend([0x1D, 0x28, 0x6B, 0x03, 0x00, 0x31, 0x43, 0x06])

        # 3. Configurar nivel de corrección de errores (M = 49)
        # GS ( k pL pH cn fn n
        qr_commands.extend([0x1D, 0x28, 0x6B, 0x03, 0x00, 0x31, 0x45, 0x31])

        # 4. Almacenar datos del QR
        # GS ( k pL pH cn fn m d1...dk
        pL = (data_len) % 256
        pH = (data_len) // 256
        qr_commands.extend([0x1D, 0x28, 0x6B, pL, pH, 0x31, 0x50, 0x30])
        qr_commands.extend(data)

        # 5. Imprimir QR almacenado
        # GS ( k pL pH cn fn m
        qr_commands.extend([0x1D, 0x28, 0x6B, 0x03, 0x00, 0x31, 0x51, 0x30])

        return bytes(qr_commands)

    def _imprimir_comanda_qr(self, pedido, link, qr_path):
        """Imprimir comanda con QR de pago"""
        try:
            tienda_nombre = self.api.tienda.get('nombre', 'Restaurante')
            pedido_id = pedido.get('numero_orden') or pedido.get('id')
            fecha = datetime.now().strftime('%d/%m/%Y')
            hora = datetime.now().strftime('%H:%M')
            total = float(pedido.get('total', 0) or 0)
            cliente = pedido.get('cliente_nombre') or 'Cliente'

            # Comandos ESC/POS
            ESC = chr(27)
            GS = chr(29)
            LF = chr(10)
            INIT = ESC + "@"
            CENTER = ESC + "a" + chr(1)
            LEFT = ESC + "a" + chr(0)
            BOLD_ON = ESC + "E" + chr(1)
            BOLD_OFF = ESC + "E" + chr(0)
            DOUBLE = GS + "!" + chr(17)
            NORMAL = GS + "!" + chr(0)
            CUT = GS + "V" + chr(66) + chr(3)

            # Construir ticket completo
            texto = ""
            texto += INIT
            texto += CENTER
            texto += BOLD_ON + DOUBLE
            texto += self._limpiar_texto(tienda_nombre.upper()) + LF
            texto += NORMAL + BOLD_OFF
            texto += LF
            texto += "================================" + LF
            texto += BOLD_ON + DOUBLE
            texto += "PAGAR CON QR" + LF
            texto += NORMAL + BOLD_OFF
            texto += "================================" + LF
            texto += LF
            texto += f"Pedido: #{pedido_id}" + LF
            texto += f"Fecha: {fecha}  Hora: {hora}" + LF
            texto += f"Cliente: {self._limpiar_texto(cliente)}" + LF
            texto += LF
            texto += "--------------------------------" + LF
            texto += BOLD_ON + DOUBLE
            texto += f"TOTAL: ${total:,.0f}" + LF
            texto += NORMAL + BOLD_OFF
            texto += "--------------------------------" + LF
            texto += LF
            texto += "Escanea el codigo QR" + LF
            texto += "para pagar:" + LF
            texto += LF

            # Texto después del QR
            texto_final = ""
            texto_final += LF + LF
            texto_final += CENTER
            texto_final += "--------------------------------" + LF
            texto_final += "Pago seguro con Wompi" + LF
            texto_final += "================================" + LF
            texto_final += LF + LF + LF
            texto_final += CUT

            # Imprimir todo junto
            try:
                import win32print
                printer_name = win32print.GetDefaultPrinter()

                # Generar comando QR nativo ESC/POS
                qr_cmd = self._generar_qr_escpos(link)
                center_cmd = bytes([0x1B, 0x61, 0x01])  # Centrar

                hPrinter = win32print.OpenPrinter(printer_name)
                try:
                    hJob = win32print.StartDocPrinter(hPrinter, 1, (f"PagoQR_{pedido_id}", None, "RAW"))
                    try:
                        win32print.StartPagePrinter(hPrinter)
                        # Texto inicial
                        win32print.WritePrinter(hPrinter, texto.encode('latin-1', errors='replace'))
                        # Centrar y QR
                        win32print.WritePrinter(hPrinter, center_cmd)
                        win32print.WritePrinter(hPrinter, qr_cmd)
                        # Texto final
                        win32print.WritePrinter(hPrinter, texto_final.encode('latin-1', errors='replace'))
                        win32print.EndPagePrinter(hPrinter)
                    finally:
                        win32print.EndDocPrinter(hPrinter)
                finally:
                    win32print.ClosePrinter(hPrinter)

            except Exception as e:
                print(f"Error imprimiendo: {e}")
                # Fallback: guardar en archivo
                pass

            # Guardar también en archivo (para debug)
            carpeta = "C:\\fast_comandas\\"
            if not os.path.exists(carpeta):
                os.makedirs(carpeta, exist_ok=True)
            archivo = os.path.join(carpeta, f"pago_{pedido_id}.txt")
            with open(archivo, 'w', encoding='latin-1', errors='replace') as f:
                f.write(texto)
                f.write(f"\n[QR LINK: {link}]\n")
                f.write(texto_final)

        except Exception as e:
            print(f"Error imprimiendo comanda: {e}")

    def _cobrar_efectivo(self, pedido):
        """Marcar pedido como pagado en efectivo"""
        pedido_id = pedido.get('id')
        numero_orden = pedido.get('numero_orden', pedido_id)
        total = float(pedido.get('total', 0) or 0)

        result = messagebox.askyesno(
            "Confirmar Cobro",
            f"¿Confirmar cobro en efectivo?\n\n"
            f"Pedido: #{numero_orden}\n"
            f"Total: ${total:,.0f}"
        )

        if result:
            def cobrar():
                try:
                    # Cambiar estado a entregado (cobrado)
                    response = self.api.actualizar_estado_pedido(pedido_id, 'entregado')
                    if response and response.get('success'):
                        self.parent.after(0, lambda: messagebox.showinfo("Éxito", f"Pedido #{numero_orden} cobrado"))
                        self.parent.after(0, self._cargar_pedidos)
                    else:
                        self.parent.after(0, lambda: messagebox.showerror("Error", "No se pudo registrar el cobro"))
                except Exception as e:
                    self.parent.after(0, lambda: messagebox.showerror("Error", str(e)))

            threading.Thread(target=cobrar, daemon=True).start()

    def stop(self):
        """Detener la aplicación"""
        self.running = False
