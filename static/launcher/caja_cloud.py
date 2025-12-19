"""
Panel de Caja - Sistema Restaurante
Gestión de pagos y cobros
"""
import customtkinter as ctk
from tkinter import messagebox
import threading
from datetime import datetime
import pytz

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

        # Auto-refresh cada 10 segundos
        self._auto_refresh()

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

                        # Pedidos pendientes de pago (efectivo no entregado)
                        if metodo != 'wompi' and estado not in ('entregado', 'cancelado'):
                            pedidos_pendientes.append(p)
                            total_pendientes += total

                self.parent.after(0, lambda: self._mostrar_pedidos(pedidos_pendientes))
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

        # Tipo de pedido
        tipo = pedido.get('tipo', 'local')
        tipo_colors = {
            'local': '#3b82f6',
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

        # Botón Link Wompi
        ctk.CTkButton(
            buttons_frame,
            text="📱 Link Pago",
            font=ctk.CTkFont(size=12),
            fg_color="#3b82f6",
            hover_color="#2563eb",
            text_color="white",
            height=32,
            corner_radius=6,
            command=lambda p=pedido: self._generar_link_pago(p)
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

    def _generar_link_pago(self, pedido):
        """Generar link de pago Wompi"""
        pedido_id = pedido.get('id')
        total = float(pedido.get('total', 0) or 0)
        numero_orden = pedido.get('numero_orden', pedido_id)

        # Mostrar diálogo de confirmación con QR placeholder
        dialog = ctk.CTkToplevel(self.parent)
        dialog.title(f"Link de Pago - Pedido #{numero_orden}")
        dialog.geometry("400x450")
        dialog.configure(fg_color=Theme.BG_PRIMARY)
        dialog.transient(self.parent)
        dialog.grab_set()

        # Centrar
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 400) // 2
        y = (dialog.winfo_screenheight() - 450) // 2
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

        # Generar link
        def generar():
            try:
                # Llamar al API para generar link
                result = self.api.generar_link_pago(pedido_id)

                if result and result.get('success'):
                    link = result.get('link', '')
                    self.parent.after(0, lambda: self._mostrar_link(dialog, container, status_label, progress, link, numero_orden, total))
                else:
                    error = result.get('error', 'Error desconocido') if result else 'Error de conexión'
                    self.parent.after(0, lambda: status_label.configure(text=f"Error: {error}", text_color=Theme.ERROR))
            except Exception as e:
                self.parent.after(0, lambda: status_label.configure(text=f"Error: {e}", text_color=Theme.ERROR))

        # Simular progreso mientras genera
        def update_progress(val):
            if val < 1:
                progress.set(val)
                self.parent.after(100, lambda: update_progress(val + 0.1))

        update_progress(0)
        threading.Thread(target=generar, daemon=True).start()

    def _mostrar_link(self, dialog, container, status_label, progress, link, numero_orden, total):
        """Mostrar el link generado"""
        progress.pack_forget()
        status_label.configure(text="¡Link generado!", text_color=Theme.SUCCESS)

        # Frame para el link
        link_frame = ctk.CTkFrame(container, fg_color=Theme.BG_CARD, corner_radius=8)
        link_frame.pack(fill='x', pady=16)

        link_content = ctk.CTkFrame(link_frame, fg_color="transparent")
        link_content.pack(fill='x', padx=16, pady=12)

        ctk.CTkLabel(
            link_content,
            text="Link de pago:",
            font=ctk.CTkFont(size=12),
            text_color=Theme.TEXT_MUTED
        ).pack(anchor='w')

        # Mostrar link truncado
        link_display = link[:50] + "..." if len(link) > 50 else link
        link_label = ctk.CTkLabel(
            link_content,
            text=link_display,
            font=ctk.CTkFont(size=11),
            text_color=Theme.ACCENT
        )
        link_label.pack(anchor='w', pady=(4, 0))

        # Botón copiar
        def copiar_link():
            self.parent.clipboard_clear()
            self.parent.clipboard_append(link)
            messagebox.showinfo("Copiado", "Link copiado al portapapeles")

        ctk.CTkButton(
            container,
            text="📋 Copiar Link",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=Theme.ACCENT,
            hover_color="#d97706",
            text_color="white",
            height=40,
            corner_radius=8,
            command=copiar_link
        ).pack(fill='x', pady=(8, 8))

        ctk.CTkLabel(
            container,
            text="Envía este link al cliente para que pague\ncon su celular",
            font=ctk.CTkFont(size=12),
            text_color=Theme.TEXT_MUTED,
            justify='center'
        ).pack(pady=(8, 16))

        ctk.CTkButton(
            container,
            text="Cerrar",
            font=ctk.CTkFont(size=13),
            fg_color=Theme.BG_ELEVATED,
            hover_color=Theme.BG_INPUT,
            text_color=Theme.TEXT_SECONDARY,
            height=36,
            corner_radius=6,
            command=dialog.destroy
        ).pack()

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

    def _auto_refresh(self):
        """Auto-refresh cada 10 segundos"""
        if self.running:
            self._cargar_pedidos()
            self.parent.after(10000, self._auto_refresh)
