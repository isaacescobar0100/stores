"""
Panel de Administracion - CustomTkinter Modern UI
Sistema de Gestion de Restaurante en la Nube
"""
import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
import os
import csv
from datetime import datetime
from api_client import APIClient

# Configurar CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class Theme:
    """Sistema de temas - Colores para CustomTkinter"""

    # Colores base
    BG_PRIMARY = '#0a0a0b'
    BG_SECONDARY = '#111113'
    BG_CARD = '#16161a'
    BG_ELEVATED = '#1c1c21'
    BG_INPUT = '#212126'

    # Colores de acento
    ACCENT = '#818cf8'
    ACCENT_HOVER = '#6366f1'
    ACCENT_SUBTLE = '#312e81'

    # Estados
    SUCCESS = '#34d399'
    SUCCESS_BG = '#064e3b'
    WARNING = '#fbbf24'
    WARNING_BG = '#78350f'
    DANGER = '#f87171'
    DANGER_BG = '#7f1d1d'
    INFO = '#60a5fa'

    # Texto
    TEXT_PRIMARY = '#fafafa'
    TEXT_SECONDARY = '#a1a1aa'
    TEXT_MUTED = '#52525b'

    # Bordes
    BORDER = '#27272a'
    BORDER_LIGHT = '#3f3f46'

    # Sidebar
    SIDEBAR_TOP = '#18181b'

    # Fuentes
    FONT_FAMILY = 'Segoe UI'


class AdminApp:
    """Aplicacion principal de administracion - CustomTkinter"""

    def __init__(self, root, api):
        self.root = root
        self.api = api
        self.running = True
        self.dashboard_active = False
        self.current_view = 'dashboard'
        self.productos_data = []
        self.categorias = []
        self.usuarios_data = []

        # Configurar ventana
        self.root.title(f"RestaurantOS - {api.tienda.get('nombre', 'Panel Admin')}")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        self.root.configure(fg_color=Theme.BG_PRIMARY)

        # Configurar grid principal
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        self._create_layout()
        self._load_initial_data()

    def _create_layout(self):
        """Crear layout principal"""
        # Sidebar
        self._create_sidebar()

        # Main content area
        self.main_frame = ctk.CTkFrame(self.root, fg_color=Theme.BG_PRIMARY, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky='nsew')
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Header
        self._create_header()

        # Content area
        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color=Theme.BG_PRIMARY, corner_radius=0)
        self.content_frame.grid(row=1, column=0, sticky='nsew', padx=32, pady=(0, 24))

        # Mostrar dashboard por defecto
        self._show_dashboard()

    def _create_sidebar(self):
        """Crear sidebar moderna"""
        sidebar = ctk.CTkFrame(self.root, fg_color=Theme.SIDEBAR_TOP, width=260, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky='nsew')
        sidebar.grid_propagate(False)

        # Logo area
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.pack(fill='x', padx=24, pady=28)

        # Logo circular con emoji
        logo_label = ctk.CTkLabel(
            logo_frame,
            text="🍽️",
            font=ctk.CTkFont(size=36),
            fg_color=Theme.ACCENT,
            corner_radius=24,
            width=48,
            height=48
        )
        logo_label.pack(side='left')

        # Nombre app
        name_frame = ctk.CTkFrame(logo_frame, fg_color="transparent")
        name_frame.pack(side='left', padx=14)

        ctk.CTkLabel(
            name_frame,
            text="RestaurantOS",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=16, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor='w')

        ctk.CTkLabel(
            name_frame,
            text="Panel Admin",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=11),
            text_color=Theme.TEXT_MUTED
        ).pack(anchor='w')

        # Separador
        ctk.CTkFrame(sidebar, fg_color=Theme.BORDER, height=1).pack(fill='x', padx=20, pady=8)

        # Menu navigation
        nav_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav_frame.pack(fill='x', padx=12, pady=12)

        self.menu_buttons = {}
        menu_items = [
            ('dashboard', '📊', 'Dashboard', 'Resumen general'),
            ('productos', '📦', 'Productos', 'Gestionar catalogo'),
            ('categorias', '📁', 'Categorias', 'Ver categorias'),
            ('ofertas', '🏷️', 'Ofertas', 'Promociones activas'),
            ('pedidos', '🛒', 'Pedidos', 'Historial de ordenes'),
            ('usuarios', '👥', 'Usuarios', 'Gestionar usuarios'),
            ('meseros', '🧑‍🍳', 'Meseros', 'Ventas por mesero'),
            ('reportes', '📈', 'Reportes', 'Analisis y metricas'),
        ]

        for key, icon, title, subtitle in menu_items:
            self._create_menu_item(nav_frame, key, icon, title, subtitle)

        # Spacer
        ctk.CTkFrame(sidebar, fg_color="transparent").pack(fill='both', expand=True)

        # User section
        user_frame = ctk.CTkFrame(sidebar, fg_color=Theme.BG_ELEVATED, corner_radius=12)
        user_frame.pack(fill='x', padx=12, pady=12)

        user_content = ctk.CTkFrame(user_frame, fg_color="transparent")
        user_content.pack(fill='x', padx=16, pady=14)

        # Avatar con inicial
        initials = self.api.user.get('nombre', 'U')[0].upper()
        avatar_label = ctk.CTkLabel(
            user_content,
            text=initials,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=Theme.SUCCESS,
            corner_radius=18,
            width=36,
            height=36,
            text_color="white"
        )
        avatar_label.pack(side='left')

        user_info = ctk.CTkFrame(user_content, fg_color="transparent")
        user_info.pack(side='left', padx=12, fill='x', expand=True)

        ctk.CTkLabel(
            user_info,
            text=self.api.user.get('nombre', 'Usuario')[:20],
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor='w')

        ctk.CTkLabel(
            user_info,
            text=self.api.user.get('rol', 'admin').capitalize(),
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=10),
            text_color=Theme.TEXT_MUTED
        ).pack(anchor='w')

        # Logout button
        logout_btn = ctk.CTkButton(
            user_content,
            text="Salir",
            font=ctk.CTkFont(size=11),
            fg_color=Theme.DANGER_BG,
            hover_color=Theme.DANGER,
            text_color=Theme.DANGER,
            width=60,
            height=28,
            corner_radius=6,
            command=self._logout
        )
        logout_btn.pack(side='right')

    def _create_menu_item(self, parent, key, icon, title, subtitle):
        """Crear item de menu"""
        frame = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=8)
        frame.pack(fill='x', pady=2)

        # Boton principal
        btn = ctk.CTkButton(
            frame,
            text=f"  {icon}  {title}",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=13),
            fg_color="transparent",
            hover_color=Theme.BG_ELEVATED,
            text_color=Theme.TEXT_SECONDARY,
            anchor="w",
            height=44,
            corner_radius=8,
            command=lambda k=key: self._select_menu(k)
        )
        btn.pack(fill='x')

        self.menu_buttons[key] = {'frame': frame, 'btn': btn}

    def _update_menu_style(self, key):
        """Actualizar estilo del menu"""
        for k, widgets in self.menu_buttons.items():
            if k == key:
                widgets['btn'].configure(
                    fg_color=Theme.BG_ELEVATED,
                    text_color=Theme.TEXT_PRIMARY
                )
            else:
                widgets['btn'].configure(
                    fg_color="transparent",
                    text_color=Theme.TEXT_SECONDARY
                )
        self.current_view = key

    def _select_menu(self, key):
        """Seleccionar item de menu y mostrar vista"""
        if self.current_view == key:
            return

        self._update_menu_style(key)

        views = {
            'dashboard': self._show_dashboard,
            'productos': self._show_productos,
            'categorias': self._show_categorias,
            'ofertas': self._show_ofertas,
            'pedidos': self._show_pedidos,
            'usuarios': self._show_usuarios,
            'meseros': self._show_meseros,
            'reportes': self._show_reportes,
        }

        if key in views:
            views[key]()

    def _create_header(self):
        """Crear header"""
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky='ew', padx=32, pady=24)

        # Titulo de pagina
        self.page_title = ctk.CTkLabel(
            header,
            text="Dashboard",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=24, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        self.page_title.pack(side='left')

        # Subtitulo
        self.page_subtitle = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=13),
            text_color=Theme.TEXT_MUTED
        )
        self.page_subtitle.pack(side='left', padx=(12, 0))

        # Info tienda (derecha)
        store_frame = ctk.CTkFrame(header, fg_color="transparent")
        store_frame.pack(side='right')

        ctk.CTkLabel(
            store_frame,
            text="● En linea",
            font=ctk.CTkFont(size=11),
            text_color=Theme.SUCCESS
        ).pack(side='right', padx=(0, 8))

        store_name = self.api.tienda.get('nombre', 'Tienda')
        ctk.CTkLabel(
            store_frame,
            text=store_name,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=13, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(side='right')

    def _clear_content(self):
        """Limpiar area de contenido"""
        self.dashboard_active = False
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def _start_dashboard_refresh(self):
        """Iniciar refresco automatico del dashboard cada 15 segundos"""
        def refresh():
            if self.dashboard_active and self.running:
                self._load_stats()
                self.root.after(15000, refresh)
        self.root.after(15000, refresh)

    # ==================== DASHBOARD ====================

    def _show_dashboard(self):
        """Mostrar dashboard"""
        self._clear_content()
        self.page_title.configure(text="Dashboard")
        self.page_subtitle.configure(text="Resumen del dia")
        self._update_menu_style('dashboard')
        self.dashboard_active = True
        self._start_dashboard_refresh()

        # Stats row
        stats_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        stats_frame.pack(fill='x', pady=(0, 20))

        for i in range(4):
            stats_frame.columnconfigure(i, weight=1, uniform='stats')

        # Cards de estadisticas
        self.stat_pedidos = self._create_stat_card(stats_frame, "0", "Pedidos Hoy", Theme.ACCENT, "🛒")
        self.stat_pedidos.grid(row=0, column=0, padx=(0, 12), sticky='ew')

        self.stat_ventas = self._create_stat_card(stats_frame, "$0", "Ventas Hoy", Theme.SUCCESS, "💰")
        self.stat_ventas.grid(row=0, column=1, padx=12, sticky='ew')

        self.stat_pendientes = self._create_stat_card(stats_frame, "0", "Pendientes", Theme.WARNING, "⏳")
        self.stat_pendientes.grid(row=0, column=2, padx=12, sticky='ew')

        self.stat_productos = self._create_stat_card(stats_frame, "0", "Productos", Theme.INFO, "📦")
        self.stat_productos.grid(row=0, column=3, padx=(12, 0), sticky='ew')

        # Info panels row
        panels_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        panels_frame.pack(fill='x', pady=(0, 20))

        panels_frame.columnconfigure(0, weight=1)
        panels_frame.columnconfigure(1, weight=1)

        # Panel: Ultimos Pedidos
        self.panel_pedidos = self._create_list_panel(panels_frame, "🛒 Ultimos Pedidos", Theme.ACCENT)
        self.panel_pedidos.grid(row=0, column=0, padx=(0, 10), sticky='nsew')

        # Panel: Top Productos
        self.panel_top = self._create_list_panel(panels_frame, "⭐ Top Productos", Theme.SUCCESS)
        self.panel_top.grid(row=0, column=1, padx=(10, 0), sticky='nsew')

        # Actions row
        actions_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        actions_frame.pack(fill='x', pady=(0, 20))

        ctk.CTkButton(
            actions_frame,
            text="🔄 Actualizar",
            font=ctk.CTkFont(size=13),
            fg_color=Theme.BG_ELEVATED,
            hover_color=Theme.BG_INPUT,
            text_color=Theme.TEXT_SECONDARY,
            height=38,
            corner_radius=8,
            command=self._load_stats
        ).pack(side='left')

        # Quick access cards
        quick_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        quick_frame.pack(fill='x')

        quick_frame.columnconfigure(0, weight=1)
        quick_frame.columnconfigure(1, weight=1)

        # Card acceso rapido - Productos
        prod_card = ctk.CTkFrame(quick_frame, fg_color=Theme.BG_CARD, corner_radius=12)
        prod_card.grid(row=0, column=0, padx=(0, 12), sticky='nsew')

        ctk.CTkFrame(prod_card, fg_color=Theme.ACCENT, height=3, corner_radius=0).pack(fill='x')
        prod_content = ctk.CTkFrame(prod_card, fg_color="transparent")
        prod_content.pack(fill='both', expand=True, padx=24, pady=20)

        ctk.CTkLabel(prod_content, text="📦 Productos", font=ctk.CTkFont(size=15, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(anchor='w')
        ctk.CTkLabel(prod_content, text="Gestionar catalogo", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_MUTED).pack(anchor='w', pady=(4, 0))
        ctk.CTkButton(prod_content, text="Ver Productos", fg_color=Theme.BG_ELEVATED, hover_color=Theme.BG_INPUT, text_color=Theme.TEXT_SECONDARY, height=32, corner_radius=6, command=lambda: self._select_menu('productos')).pack(anchor='w', pady=(16, 0))

        # Card acceso rapido - Pedidos
        ped_card = ctk.CTkFrame(quick_frame, fg_color=Theme.BG_CARD, corner_radius=12)
        ped_card.grid(row=0, column=1, padx=(12, 0), sticky='nsew')

        ctk.CTkFrame(ped_card, fg_color=Theme.SUCCESS, height=3, corner_radius=0).pack(fill='x')
        ped_content = ctk.CTkFrame(ped_card, fg_color="transparent")
        ped_content.pack(fill='both', expand=True, padx=24, pady=20)

        ctk.CTkLabel(ped_content, text="🛒 Pedidos", font=ctk.CTkFont(size=15, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(anchor='w')
        ctk.CTkLabel(ped_content, text="Ultimos pedidos del dia", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_MUTED).pack(anchor='w', pady=(4, 0))
        ctk.CTkButton(ped_content, text="Ver Pedidos", fg_color=Theme.BG_ELEVATED, hover_color=Theme.BG_INPUT, text_color=Theme.TEXT_SECONDARY, height=32, corner_radius=6, command=lambda: self._select_menu('pedidos')).pack(anchor='w', pady=(16, 0))

        self._load_stats()

    def _create_stat_card(self, parent, value, label, color, icon):
        """Crear tarjeta de estadistica"""
        card = ctk.CTkFrame(parent, fg_color=Theme.BG_CARD, corner_radius=12)

        # Barra de color superior
        ctk.CTkFrame(card, fg_color=color, height=3, corner_radius=0).pack(fill='x')

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill='both', expand=True, padx=20, pady=16)

        # Icon y valor
        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill='x')

        ctk.CTkLabel(header, text=icon, font=ctk.CTkFont(size=24)).pack(side='left')

        value_label = ctk.CTkLabel(
            header,
            text=str(value),
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=28, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        )
        value_label.pack(side='right')

        # Etiqueta
        ctk.CTkLabel(
            content,
            text=label,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=12),
            text_color=Theme.TEXT_MUTED
        ).pack(anchor='w', pady=(8, 0))

        card.value_label = value_label
        return card

    def _create_list_panel(self, parent, title, accent_color):
        """Crear panel con lista de items"""
        card = ctk.CTkFrame(parent, fg_color=Theme.BG_CARD, corner_radius=12, height=200)
        card.pack_propagate(False)

        # Header con linea de acento
        ctk.CTkFrame(card, fg_color=accent_color, height=3, corner_radius=0).pack(fill='x')

        # Titulo
        title_frame = ctk.CTkFrame(card, fg_color="transparent")
        title_frame.pack(fill='x', padx=16, pady=12)

        ctk.CTkLabel(
            title_frame,
            text=title,
            font=ctk.CTkFont(family=Theme.FONT_FAMILY, size=14, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(side='left')

        # Container para items
        card.items_frame = ctk.CTkFrame(card, fg_color="transparent")
        card.items_frame.pack(fill='both', expand=True, padx=16, pady=(0, 12))

        # Mensaje inicial
        card.empty_label = ctk.CTkLabel(
            card.items_frame,
            text="Cargando...",
            font=ctk.CTkFont(size=12),
            text_color=Theme.TEXT_MUTED
        )
        card.empty_label.pack(pady=20)

        return card

    def _load_stats(self):
        """Cargar estadisticas"""
        def load():
            try:
                stats = self.api.obtener_estadisticas()
                productos = self.api.obtener_productos()
                pedidos = self.api.obtener_pedidos(limite=100)

                ventas_completadas = 0
                top_productos = []
                ultimos_pedidos = []

                if stats and not stats.get('error'):
                    por_estado = stats.get('por_estado', {})
                    if isinstance(por_estado, dict):
                        listos = por_estado.get('listo', 0)
                        entregados = por_estado.get('entregado', 0)
                        pedidos_completados = listos + entregados
                        pendientes = por_estado.get('pendiente', 0)
                    else:
                        pedidos_completados = 0
                        pendientes = 0

                    self.stat_pedidos.value_label.configure(text=str(pedidos_completados))
                    self.stat_pendientes.value_label.configure(text=str(pendientes))

                    top_productos = stats.get('productos_top', [])[:5]

                if isinstance(pedidos, list):
                    for p in pedidos:
                        estado = p.get('estado', '')
                        if estado in ('listo', 'entregado'):
                            total = float(p.get('total', 0) or 0)
                            ventas_completadas += total
                    ultimos_pedidos = pedidos[:5]

                self.stat_ventas.value_label.configure(text=f"${ventas_completadas:,.0f}")

                if isinstance(productos, list):
                    self.stat_productos.value_label.configure(text=str(len(productos)))

                self.root.after(50, lambda: self._update_panels(ultimos_pedidos, top_productos))

            except Exception as e:
                print(f"Error cargando stats: {e}")

        threading.Thread(target=load, daemon=True).start()

    def _update_panels(self, ultimos_pedidos, top_productos):
        """Actualizar paneles de lista con datos"""
        try:
            # Panel de ultimos pedidos
            if hasattr(self, 'panel_pedidos') and self.panel_pedidos.winfo_exists():
                frame = self.panel_pedidos.items_frame
                for widget in frame.winfo_children():
                    widget.destroy()

                if not ultimos_pedidos:
                    ctk.CTkLabel(frame, text="Sin pedidos recientes", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED).pack(pady=20)
                else:
                    estado_colors = {
                        'pendiente': Theme.WARNING,
                        'preparando': Theme.INFO,
                        'listo': Theme.SUCCESS,
                        'entregado': '#10b981',
                        'cancelado': Theme.DANGER
                    }
                    for p in ultimos_pedidos:
                        row = ctk.CTkFrame(frame, fg_color="transparent")
                        row.pack(fill='x', pady=3)

                        estado = p.get('estado', 'pendiente')
                        color = estado_colors.get(estado, Theme.TEXT_MUTED)

                        # Indicador de estado
                        ctk.CTkFrame(row, fg_color=color, width=4, height=20, corner_radius=2).pack(side='left', padx=(0, 8))

                        cliente = p.get('cliente_nombre', 'Cliente')
                        if len(cliente) > 15:
                            cliente = cliente[:13] + '..'
                        ctk.CTkLabel(row, text=cliente, font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(side='left')

                        total = float(p.get('total', 0) or 0)
                        ctk.CTkLabel(row, text=f"${total:,.0f}", font=ctk.CTkFont(size=12), text_color=Theme.SUCCESS).pack(side='right', padx=(0, 8))

                        ctk.CTkLabel(row, text=estado.capitalize(), font=ctk.CTkFont(size=10), text_color=color).pack(side='right', padx=8)

            # Panel de top productos
            if hasattr(self, 'panel_top') and self.panel_top.winfo_exists():
                frame = self.panel_top.items_frame
                for widget in frame.winfo_children():
                    widget.destroy()

                if not top_productos:
                    ctk.CTkLabel(frame, text="Sin datos de productos", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED).pack(pady=20)
                else:
                    colors = [Theme.ACCENT, Theme.SUCCESS, Theme.INFO, Theme.WARNING, '#a855f7']
                    for i, p in enumerate(top_productos):
                        row = ctk.CTkFrame(frame, fg_color="transparent")
                        row.pack(fill='x', pady=3)

                        color = colors[i % len(colors)]

                        ctk.CTkLabel(row, text=f"{i+1}.", font=ctk.CTkFont(size=12, weight="bold"), text_color=color, width=25).pack(side='left')

                        nombre = p.get('nombre', 'Producto')
                        if len(nombre) > 20:
                            nombre = nombre[:18] + '..'
                        ctk.CTkLabel(row, text=nombre, font=ctk.CTkFont(size=12), text_color=Theme.TEXT_PRIMARY).pack(side='left', fill='x', expand=True)

                        cantidad = p.get('cantidad', 0)
                        ctk.CTkLabel(row, text=f"x{cantidad}", font=ctk.CTkFont(size=12, weight="bold"), text_color=color).pack(side='right')

        except Exception as e:
            print(f"Error actualizando paneles: {e}")

    # ==================== PRODUCTOS ====================

    def _show_productos(self):
        """Mostrar vista de productos"""
        self._clear_content()
        self.page_title.configure(text="Productos")
        self.page_subtitle.configure(text=f"{len(self.productos_data)} productos")

        # Toolbar
        toolbar = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        toolbar.pack(fill='x', pady=(0, 20))

        # Botones izquierda
        btn_left = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_left.pack(side='left')

        ctk.CTkButton(btn_left, text="+ Nuevo", fg_color=Theme.SUCCESS, hover_color="#10b981", text_color="black", height=38, corner_radius=8, command=self._new_producto).pack(side='left', padx=(0, 8))
        ctk.CTkButton(btn_left, text="✏️ Editar", fg_color=Theme.BG_ELEVATED, hover_color=Theme.BG_INPUT, text_color=Theme.TEXT_SECONDARY, height=38, corner_radius=8, command=self._edit_producto).pack(side='left', padx=(0, 8))
        ctk.CTkButton(btn_left, text="🗑️ Eliminar", fg_color=Theme.DANGER_BG, hover_color=Theme.DANGER, text_color=Theme.DANGER, height=38, corner_radius=8, command=self._delete_producto).pack(side='left')

        # Busqueda y filtros (derecha)
        btn_right = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_right.pack(side='right')

        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(
            btn_right,
            textvariable=self.search_var,
            placeholder_text="🔍 Buscar producto...",
            font=ctk.CTkFont(size=13),
            fg_color=Theme.BG_INPUT,
            border_color=Theme.BORDER,
            text_color=Theme.TEXT_PRIMARY,
            width=250,
            height=38,
            corner_radius=8
        )
        self.search_entry.pack(side='left', padx=(0, 12))
        self.search_entry.bind('<KeyRelease>', lambda e: self._filter_productos())

        ctk.CTkButton(btn_right, text="🔄 Actualizar", fg_color=Theme.BG_ELEVATED, hover_color=Theme.BG_INPUT, text_color=Theme.TEXT_SECONDARY, height=38, corner_radius=8, command=self._load_productos).pack(side='left')

        # Tabla usando scrollable frame
        table_container = ctk.CTkFrame(self.content_frame, fg_color=Theme.BG_CARD, corner_radius=12)
        table_container.pack(fill='both', expand=True)

        # Header de tabla
        header_frame = ctk.CTkFrame(table_container, fg_color=Theme.BG_ELEVATED, corner_radius=0)
        header_frame.pack(fill='x')

        headers = [('Nombre', 350), ('Precio', 120), ('Categoria', 180), ('Estado', 100)]
        for text, width in headers:
            ctk.CTkLabel(header_frame, text=text, font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_MUTED, width=width, anchor='w').pack(side='left', padx=16, pady=10)

        # Scrollable frame para productos
        self.productos_scroll = ctk.CTkScrollableFrame(table_container, fg_color="transparent")
        self.productos_scroll.pack(fill='both', expand=True, padx=4, pady=4)

        self._load_productos()

    def _load_productos(self):
        """Cargar productos"""
        if not hasattr(self, 'productos_scroll'):
            return

        for widget in self.productos_scroll.winfo_children():
            widget.destroy()

        categorias = self.api.obtener_categorias()
        cat_map = {}
        if isinstance(categorias, list):
            self.categorias = categorias
            cat_map = {c['id']: c['nombre'] for c in categorias}

        productos = self.api.obtener_productos()
        if isinstance(productos, list):
            self.productos_data = productos
            self.page_subtitle.configure(text=f"{len(productos)} productos")

            for i, p in enumerate(productos):
                self._create_producto_row(p, cat_map, i)

    def _create_producto_row(self, producto, cat_map, index):
        """Crear fila de producto"""
        bg = Theme.BG_CARD if index % 2 == 0 else Theme.BG_SECONDARY

        row = ctk.CTkFrame(self.productos_scroll, fg_color=bg, corner_radius=0, height=50)
        row.pack(fill='x', pady=1)
        row.pack_propagate(False)

        # Almacenar ID del producto
        row.producto_id = producto['id']

        # Nombre
        ctk.CTkLabel(row, text=producto['nombre'], font=ctk.CTkFont(size=12), text_color=Theme.TEXT_PRIMARY, width=350, anchor='w').pack(side='left', padx=16, pady=10)

        # Precio
        precio = float(producto['precio']) if isinstance(producto['precio'], str) else producto['precio']
        ctk.CTkLabel(row, text=f"${precio:,.0f}", font=ctk.CTkFont(size=12), text_color=Theme.SUCCESS, width=120, anchor='w').pack(side='left', padx=16)

        # Categoria
        cat_nombre = cat_map.get(producto.get('categoria_id'), 'Sin categoria')
        ctk.CTkLabel(row, text=cat_nombre, font=ctk.CTkFont(size=12), text_color=Theme.TEXT_SECONDARY, width=180, anchor='w').pack(side='left', padx=16)

        # Estado
        estado = 'Disponible' if producto.get('disponible', 1) else 'No disponible'
        estado_color = Theme.SUCCESS if producto.get('disponible', 1) else Theme.DANGER
        ctk.CTkLabel(row, text=estado, font=ctk.CTkFont(size=11), text_color=estado_color, width=100, anchor='w').pack(side='left', padx=16)

        # Click para seleccionar
        def on_click(e, r=row, p=producto):
            self._select_producto_row(r, p)

        row.bind('<Button-1>', on_click)
        for child in row.winfo_children():
            child.bind('<Button-1>', on_click)

    def _select_producto_row(self, row, producto):
        """Seleccionar fila de producto"""
        # Deseleccionar todas
        for child in self.productos_scroll.winfo_children():
            child.configure(fg_color=Theme.BG_CARD if self.productos_scroll.winfo_children().index(child) % 2 == 0 else Theme.BG_SECONDARY)

        # Seleccionar esta
        row.configure(fg_color=Theme.ACCENT_SUBTLE)
        self.selected_producto = producto

    def _filter_productos(self):
        """Filtrar productos por busqueda"""
        search = self.search_var.get().lower()

        for widget in self.productos_scroll.winfo_children():
            widget.destroy()

        cat_map = {c['id']: c['nombre'] for c in self.categorias}

        filtered = [p for p in self.productos_data if search in p['nombre'].lower()]
        for i, p in enumerate(filtered):
            self._create_producto_row(p, cat_map, i)

    def _new_producto(self):
        """Crear nuevo producto"""
        ProductoDialog(self.root, self.api, self.categorias, on_save=self._load_productos)

    def _edit_producto(self):
        """Editar producto seleccionado"""
        if not hasattr(self, 'selected_producto') or not self.selected_producto:
            messagebox.showwarning("Aviso", "Selecciona un producto")
            return

        ProductoDialog(self.root, self.api, self.categorias, self.selected_producto, on_save=self._load_productos)

    def _delete_producto(self):
        """Eliminar producto"""
        if not hasattr(self, 'selected_producto') or not self.selected_producto:
            messagebox.showwarning("Aviso", "Selecciona un producto")
            return

        if messagebox.askyesno("Confirmar", "¿Eliminar este producto?"):
            result = self.api.eliminar_producto(self.selected_producto['id'])
            if result and result.get('success'):
                self.selected_producto = None
                self._load_productos()
            else:
                messagebox.showerror("Error", result.get('error', 'Error desconocido'))

    # ==================== CATEGORIAS ====================

    def _show_categorias(self):
        """Mostrar categorias"""
        self._clear_content()
        self.page_title.configure(text="Categorias")
        self.page_subtitle.configure(text="Administradas por SuperAdmin")

        # Info banner
        info_frame = ctk.CTkFrame(self.content_frame, fg_color=Theme.ACCENT_SUBTLE, corner_radius=8)
        info_frame.pack(fill='x', pady=(0, 12))

        ctk.CTkLabel(
            info_frame,
            text="ℹ️ Las categorias son administradas por el SuperAdmin del sistema",
            font=ctk.CTkFont(size=12),
            text_color=Theme.ACCENT
        ).pack(padx=16, pady=10)

        # Toolbar
        toolbar = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        toolbar.pack(fill='x', pady=(0, 12))

        ctk.CTkButton(toolbar, text="🔄 Actualizar", fg_color=Theme.BG_ELEVATED, hover_color=Theme.BG_INPUT, text_color=Theme.TEXT_SECONDARY, height=32, corner_radius=6, command=self._load_categorias_view).pack(side='right')

        # Grid de categorias
        self.categorias_scroll = ctk.CTkScrollableFrame(self.content_frame, fg_color=Theme.BG_CARD, corner_radius=12)
        self.categorias_scroll.pack(fill='both', expand=True)

        self._load_categorias_view()

    def _load_categorias_view(self):
        """Cargar vista de categorias"""
        for widget in self.categorias_scroll.winfo_children():
            widget.destroy()

        categorias = self.api.obtener_categorias()
        self.categorias = [c for c in categorias if c.get('activo', 1)] if isinstance(categorias, list) else []

        if not self.categorias:
            ctk.CTkLabel(self.categorias_scroll, text="No hay categorias disponibles", font=ctk.CTkFont(size=13), text_color=Theme.TEXT_MUTED).pack(pady=40)
            return

        # Grid frame
        grid_frame = ctk.CTkFrame(self.categorias_scroll, fg_color="transparent")
        grid_frame.pack(fill='x', padx=16, pady=16)

        row = 0
        col = 0
        max_cols = 4

        for cat in self.categorias:
            card = ctk.CTkFrame(grid_frame, fg_color=Theme.BG_ELEVATED, corner_radius=10, width=200, height=80)
            card.grid(row=row, column=col, padx=8, pady=8, sticky='nsew')
            card.grid_propagate(False)

            ctk.CTkFrame(card, fg_color=Theme.ACCENT, height=3, corner_radius=0).pack(fill='x')

            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(fill='both', expand=True, padx=16, pady=12)

            ctk.CTkLabel(content, text=f"📁 {cat['nombre'][:20]}", font=ctk.CTkFont(size=13, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(anchor='w')

            desc = cat.get('descripcion', '')
            if desc:
                ctk.CTkLabel(content, text=desc[:30], font=ctk.CTkFont(size=10), text_color=Theme.TEXT_MUTED).pack(anchor='w')

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        for i in range(max_cols):
            grid_frame.columnconfigure(i, weight=1)

    # ==================== OFERTAS ====================

    def _show_ofertas(self):
        """Mostrar ofertas"""
        self._clear_content()
        self.page_title.configure(text="Ofertas")
        self.page_subtitle.configure(text="Promociones y descuentos")

        # Toolbar
        toolbar = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        toolbar.pack(fill='x', pady=(0, 20))

        ctk.CTkButton(toolbar, text="+ Nueva Oferta", fg_color=Theme.SUCCESS, hover_color="#10b981", text_color="black", height=38, corner_radius=8, command=self._new_oferta).pack(side='left', padx=(0, 8))
        ctk.CTkButton(toolbar, text="✏️ Editar", fg_color=Theme.BG_ELEVATED, hover_color=Theme.BG_INPUT, text_color=Theme.TEXT_SECONDARY, height=38, corner_radius=8, command=self._edit_oferta).pack(side='left', padx=(0, 8))
        ctk.CTkButton(toolbar, text="🗑️ Eliminar", fg_color=Theme.DANGER_BG, hover_color=Theme.DANGER, text_color=Theme.DANGER, height=38, corner_radius=8, command=self._delete_oferta).pack(side='left')
        ctk.CTkButton(toolbar, text="🔄 Actualizar", fg_color=Theme.BG_ELEVATED, hover_color=Theme.BG_INPUT, text_color=Theme.TEXT_SECONDARY, height=38, corner_radius=8, command=self._load_ofertas).pack(side='right')

        # Grid de ofertas
        self.ofertas_scroll = ctk.CTkScrollableFrame(self.content_frame, fg_color=Theme.BG_CARD, corner_radius=12)
        self.ofertas_scroll.pack(fill='both', expand=True)

        self._load_ofertas()

    def _load_ofertas(self):
        """Cargar ofertas"""
        for widget in self.ofertas_scroll.winfo_children():
            widget.destroy()

        ofertas = self.api.obtener_ofertas()
        self.ofertas_data = ofertas if isinstance(ofertas, list) else []
        self.selected_oferta = None

        if not self.ofertas_data:
            ctk.CTkLabel(self.ofertas_scroll, text="No hay ofertas activas", font=ctk.CTkFont(size=13), text_color=Theme.TEXT_MUTED).pack(pady=40)
            return

        grid_frame = ctk.CTkFrame(self.ofertas_scroll, fg_color="transparent")
        grid_frame.pack(fill='x', padx=16, pady=16)

        for i, oferta in enumerate(self.ofertas_data):
            card = ctk.CTkFrame(grid_frame, fg_color=Theme.BG_ELEVATED, corner_radius=10)
            card.pack(fill='x', pady=6)

            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(fill='x', padx=20, pady=16)

            # Info
            info_frame = ctk.CTkFrame(content, fg_color="transparent")
            info_frame.pack(fill='x')

            ctk.CTkLabel(info_frame, text=f"🏷️ {oferta.get('titulo', 'Oferta')}", font=ctk.CTkFont(size=14, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(side='left')

            descuento = oferta.get('descuento', 0)
            ctk.CTkLabel(info_frame, text=f"-{descuento}%", font=ctk.CTkFont(size=16, weight="bold"), text_color=Theme.SUCCESS).pack(side='right')

            desc = oferta.get('descripcion', '')
            if desc:
                ctk.CTkLabel(content, text=desc[:60], font=ctk.CTkFont(size=11), text_color=Theme.TEXT_MUTED).pack(anchor='w', pady=(8, 0))

            # Click para seleccionar
            def on_click(e, o=oferta, c=card):
                self._select_oferta(o, c)

            card.bind('<Button-1>', on_click)
            for child in card.winfo_children():
                child.bind('<Button-1>', on_click)
                for subchild in child.winfo_children():
                    subchild.bind('<Button-1>', on_click)

    def _select_oferta(self, oferta, card):
        """Seleccionar oferta"""
        for child in self.ofertas_scroll.winfo_children():
            for subchild in child.winfo_children():
                if isinstance(subchild, ctk.CTkFrame):
                    subchild.configure(fg_color=Theme.BG_ELEVATED)

        card.configure(fg_color=Theme.ACCENT_SUBTLE)
        self.selected_oferta = oferta

    def _new_oferta(self):
        """Nueva oferta"""
        OfertaDialog(self.root, self.api, on_save=self._load_ofertas)

    def _edit_oferta(self):
        """Editar oferta"""
        if not hasattr(self, 'selected_oferta') or not self.selected_oferta:
            messagebox.showwarning("Aviso", "Selecciona una oferta")
            return

        OfertaDialog(self.root, self.api, self.selected_oferta, on_save=self._load_ofertas)

    def _delete_oferta(self):
        """Eliminar oferta"""
        if not hasattr(self, 'selected_oferta') or not self.selected_oferta:
            messagebox.showwarning("Aviso", "Selecciona una oferta")
            return

        if messagebox.askyesno("Confirmar", "¿Eliminar esta oferta?"):
            result = self.api.eliminar_oferta(self.selected_oferta['id'])
            if result and result.get('success'):
                self.selected_oferta = None
                self._load_ofertas()
            else:
                messagebox.showerror("Error", result.get('error', 'Error desconocido'))

    # ==================== PEDIDOS ====================

    def _show_pedidos(self):
        """Mostrar pedidos"""
        self._clear_content()
        self.page_title.configure(text="Pedidos")
        self.page_subtitle.configure(text="Historial de ordenes")

        # Toolbar
        toolbar = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        toolbar.pack(fill='x', pady=(0, 20))

        ctk.CTkButton(toolbar, text="👁️ Ver Detalle", fg_color=Theme.BG_ELEVATED, hover_color=Theme.BG_INPUT, text_color=Theme.TEXT_SECONDARY, height=38, corner_radius=8, command=self._ver_pedido).pack(side='left', padx=(0, 8))
        ctk.CTkButton(toolbar, text="🔄 Actualizar", fg_color=Theme.BG_ELEVATED, hover_color=Theme.BG_INPUT, text_color=Theme.TEXT_SECONDARY, height=38, corner_radius=8, command=self._load_pedidos).pack(side='right')

        # Tabla
        table_container = ctk.CTkFrame(self.content_frame, fg_color=Theme.BG_CARD, corner_radius=12)
        table_container.pack(fill='both', expand=True)

        # Header
        header_frame = ctk.CTkFrame(table_container, fg_color=Theme.BG_ELEVATED, corner_radius=0)
        header_frame.pack(fill='x')

        headers = [('#', 60), ('Cliente', 200), ('Tipo', 100), ('Total', 120), ('Estado', 100), ('Fecha', 150)]
        for text, width in headers:
            ctk.CTkLabel(header_frame, text=text, font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_MUTED, width=width, anchor='w').pack(side='left', padx=12, pady=10)

        # Scrollable
        self.pedidos_scroll = ctk.CTkScrollableFrame(table_container, fg_color="transparent")
        self.pedidos_scroll.pack(fill='both', expand=True, padx=4, pady=4)

        self._load_pedidos()

    def _load_pedidos(self):
        """Cargar pedidos"""
        for widget in self.pedidos_scroll.winfo_children():
            widget.destroy()

        pedidos = self.api.obtener_pedidos(limite=50)
        self.pedidos_data = pedidos if isinstance(pedidos, list) else []
        self.selected_pedido = None

        estado_colors = {
            'pendiente': Theme.WARNING,
            'preparando': Theme.INFO,
            'listo': Theme.SUCCESS,
            'entregado': '#10b981',
            'cancelado': Theme.DANGER
        }

        for i, p in enumerate(self.pedidos_data):
            bg = Theme.BG_CARD if i % 2 == 0 else Theme.BG_SECONDARY

            row = ctk.CTkFrame(self.pedidos_scroll, fg_color=bg, corner_radius=0, height=50)
            row.pack(fill='x', pady=1)
            row.pack_propagate(False)

            ctk.CTkLabel(row, text=f"#{p.get('numero_orden', p['id'])}", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED, width=60, anchor='w').pack(side='left', padx=12)
            ctk.CTkLabel(row, text=p.get('cliente_nombre', 'N/A')[:20], font=ctk.CTkFont(size=12), text_color=Theme.TEXT_PRIMARY, width=200, anchor='w').pack(side='left', padx=12)
            ctk.CTkLabel(row, text=p.get('tipo', 'mesa').capitalize(), font=ctk.CTkFont(size=11), text_color=Theme.TEXT_SECONDARY, width=100, anchor='w').pack(side='left', padx=12)

            total = float(p.get('total', 0) or 0)
            ctk.CTkLabel(row, text=f"${total:,.0f}", font=ctk.CTkFont(size=12), text_color=Theme.SUCCESS, width=120, anchor='w').pack(side='left', padx=12)

            estado = p.get('estado', 'pendiente')
            color = estado_colors.get(estado, Theme.TEXT_MUTED)
            ctk.CTkLabel(row, text=estado.capitalize(), font=ctk.CTkFont(size=11), text_color=color, width=100, anchor='w').pack(side='left', padx=12)

            fecha = p.get('fecha_pedido', '')[:16] if p.get('fecha_pedido') else ''
            ctk.CTkLabel(row, text=fecha, font=ctk.CTkFont(size=11), text_color=Theme.TEXT_MUTED, width=150, anchor='w').pack(side='left', padx=12)

            def on_click(e, r=row, pedido=p):
                self._select_pedido(r, pedido)

            row.bind('<Button-1>', on_click)
            for child in row.winfo_children():
                child.bind('<Button-1>', on_click)

    def _select_pedido(self, row, pedido):
        """Seleccionar pedido"""
        for child in self.pedidos_scroll.winfo_children():
            idx = self.pedidos_scroll.winfo_children().index(child)
            child.configure(fg_color=Theme.BG_CARD if idx % 2 == 0 else Theme.BG_SECONDARY)

        row.configure(fg_color=Theme.ACCENT_SUBTLE)
        self.selected_pedido = pedido

    def _ver_pedido(self):
        """Ver detalle de pedido"""
        if not hasattr(self, 'selected_pedido') or not self.selected_pedido:
            messagebox.showwarning("Aviso", "Selecciona un pedido")
            return

        # Obtener detalle completo del pedido con items
        pedido_id = self.selected_pedido.get('id')
        try:
            resultado = self.api.obtener_detalle_pedido(pedido_id)
            print(f"DEBUG API resultado: {resultado}")
            if resultado and 'items' in resultado:
                # Combinar info del pedido con los items del detalle
                pedido_completo = {**self.selected_pedido, 'items': resultado['items']}
                print(f"DEBUG items: {resultado['items']}")
                PedidoDetailDialog(self.root, pedido_completo)
            else:
                print(f"DEBUG: No items in resultado, using selected_pedido")
                PedidoDetailDialog(self.root, self.selected_pedido)
        except Exception as e:
            print(f"DEBUG Exception: {e}")
            PedidoDetailDialog(self.root, self.selected_pedido)

    # ==================== MESEROS ====================

    def _show_meseros(self):
        """Mostrar estadísticas de meseros"""
        self._clear_content()
        self.page_title.configure(text="Ventas por Mesero")
        self.page_subtitle.configure(text="Seguimiento de ventas del equipo")

        # Filtros
        filters_frame = ctk.CTkFrame(self.content_frame, fg_color=Theme.BG_CARD, corner_radius=12)
        filters_frame.pack(fill='x', pady=(0, 20))

        filters_content = ctk.CTkFrame(filters_frame, fg_color="transparent")
        filters_content.pack(fill='x', padx=20, pady=16)

        ctk.CTkLabel(filters_content, text="Período:", font=ctk.CTkFont(size=13), text_color=Theme.TEXT_SECONDARY).pack(side='left')

        self.mesero_filtro = ctk.CTkSegmentedButton(
            filters_content,
            values=["Hoy", "Semana", "Mes", "Todo"],
            command=self._filtrar_meseros,
            font=ctk.CTkFont(size=12)
        )
        self.mesero_filtro.set("Hoy")
        self.mesero_filtro.pack(side='left', padx=(10, 20))

        # Botón exportar CSV
        ctk.CTkButton(
            filters_content,
            text="📥 Exportar CSV",
            fg_color=Theme.SUCCESS,
            hover_color='#059669',
            width=120,
            height=32,
            command=self._exportar_meseros_csv
        ).pack(side='right')

        # Tabla de meseros
        table_frame = ctk.CTkFrame(self.content_frame, fg_color=Theme.BG_CARD, corner_radius=12)
        table_frame.pack(fill='both', expand=True)

        # Header de tabla
        header = ctk.CTkFrame(table_frame, fg_color=Theme.BG_ELEVATED, corner_radius=0)
        header.pack(fill='x', padx=2, pady=(2, 0))

        cols = [("Mesero", 200), ("Pedidos", 100), ("Total Ventas", 150), ("Promedio", 120), ("Acciones", 100)]
        for col_name, col_width in cols:
            ctk.CTkLabel(header, text=col_name, font=ctk.CTkFont(size=12, weight="bold"),
                        text_color=Theme.TEXT_MUTED, width=col_width).pack(side='left', padx=10, pady=12)

        # Contenedor scrollable para los datos
        self.meseros_container = ctk.CTkScrollableFrame(table_frame, fg_color="transparent")
        self.meseros_container.pack(fill='both', expand=True, padx=2, pady=2)

        # Cargar datos
        self._cargar_meseros()

    def _filtrar_meseros(self, value):
        """Filtrar meseros por período"""
        self._cargar_meseros()

    def _cargar_meseros(self):
        """Cargar estadísticas de meseros"""
        # Limpiar contenedor
        for widget in self.meseros_container.winfo_children():
            widget.destroy()

        filtro_map = {"Hoy": "hoy", "Semana": "semana", "Mes": "mes", "Todo": "todo"}
        filtro = filtro_map.get(self.mesero_filtro.get(), "hoy")

        try:
            stats = self.api.obtener_estadisticas_meseros(filtro=filtro)
            self.meseros_stats = stats  # Guardar para exportar

            if not stats:
                ctk.CTkLabel(self.meseros_container, text="No hay meseros registrados",
                            font=ctk.CTkFont(size=14), text_color=Theme.TEXT_MUTED).pack(pady=40)
                return

            for mesero in stats:
                row = ctk.CTkFrame(self.meseros_container, fg_color="transparent")
                row.pack(fill='x', pady=2)

                # Nombre
                ctk.CTkLabel(row, text=mesero.get('mesero_nombre', 'Sin nombre'),
                            font=ctk.CTkFont(size=13), text_color=Theme.TEXT_PRIMARY,
                            width=200, anchor='w').pack(side='left', padx=10, pady=10)

                # Pedidos
                ctk.CTkLabel(row, text=str(mesero.get('total_pedidos', 0)),
                            font=ctk.CTkFont(size=13, weight="bold"), text_color=Theme.INFO,
                            width=100).pack(side='left', padx=10)

                # Total ventas
                total = float(mesero.get('total_ventas', 0))
                ctk.CTkLabel(row, text=f"${total:,.0f}",
                            font=ctk.CTkFont(size=13, weight="bold"), text_color=Theme.SUCCESS,
                            width=150).pack(side='left', padx=10)

                # Promedio
                promedio = float(mesero.get('promedio_pedido', 0))
                ctk.CTkLabel(row, text=f"${promedio:,.0f}",
                            font=ctk.CTkFont(size=13), text_color=Theme.TEXT_SECONDARY,
                            width=120).pack(side='left', padx=10)

                # Botón ver pedidos
                mesero_id = mesero.get('mesero_id')
                ctk.CTkButton(row, text="Ver",
                            fg_color=Theme.BG_ELEVATED, hover_color=Theme.BG_INPUT,
                            text_color=Theme.ACCENT, width=60, height=28,
                            command=lambda m=mesero: self._ver_pedidos_mesero(m)).pack(side='left', padx=10)

                # Separador
                sep = ctk.CTkFrame(self.meseros_container, fg_color=Theme.BORDER, height=1)
                sep.pack(fill='x', padx=10)

        except Exception as e:
            ctk.CTkLabel(self.meseros_container, text=f"Error al cargar: {e}",
                        font=ctk.CTkFont(size=14), text_color=Theme.DANGER).pack(pady=40)

    def _ver_pedidos_mesero(self, mesero):
        """Ver pedidos de un mesero específico"""
        MeseroPedidosDialog(self.root, self.api, mesero, self.mesero_filtro.get())

    def _exportar_meseros_csv(self):
        """Exportar estadísticas a CSV"""
        if not hasattr(self, 'meseros_stats') or not self.meseros_stats:
            messagebox.showwarning("Aviso", "No hay datos para exportar")
            return

        from datetime import datetime
        filename = f"meseros_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=filename
        )

        if filepath:
            try:
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Mesero', 'Total Pedidos', 'Total Ventas', 'Promedio por Pedido'])
                    for m in self.meseros_stats:
                        writer.writerow([
                            m.get('mesero_nombre', ''),
                            m.get('total_pedidos', 0),
                            m.get('total_ventas', 0),
                            m.get('promedio_pedido', 0)
                        ])
                messagebox.showinfo("Éxito", f"Archivo exportado:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"Error al exportar: {e}")

    # ==================== REPORTES ====================

    def _show_reportes(self):
        """Mostrar reportes"""
        self._clear_content()
        self.page_title.configure(text="Reportes")
        self.page_subtitle.configure(text="Analisis y exportacion")

        # Cards de reportes
        cards_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        cards_frame.pack(fill='x', pady=(0, 20))

        cards_frame.columnconfigure(0, weight=1)
        cards_frame.columnconfigure(1, weight=1)

        # Card - Exportar Pedidos
        card1 = ctk.CTkFrame(cards_frame, fg_color=Theme.BG_CARD, corner_radius=12)
        card1.grid(row=0, column=0, padx=(0, 12), sticky='nsew')

        ctk.CTkFrame(card1, fg_color=Theme.ACCENT, height=3, corner_radius=0).pack(fill='x')
        content1 = ctk.CTkFrame(card1, fg_color="transparent")
        content1.pack(fill='both', expand=True, padx=24, pady=20)

        ctk.CTkLabel(content1, text="📊 Exportar Pedidos", font=ctk.CTkFont(size=15, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(anchor='w')
        ctk.CTkLabel(content1, text="Descargar historial de pedidos en CSV", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_MUTED).pack(anchor='w', pady=(4, 0))
        ctk.CTkButton(content1, text="📥 Exportar CSV", fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER, text_color="white", height=36, corner_radius=8, command=self._export_pedidos).pack(anchor='w', pady=(16, 0))

        # Card - Exportar Productos
        card2 = ctk.CTkFrame(cards_frame, fg_color=Theme.BG_CARD, corner_radius=12)
        card2.grid(row=0, column=1, padx=(12, 0), sticky='nsew')

        ctk.CTkFrame(card2, fg_color=Theme.SUCCESS, height=3, corner_radius=0).pack(fill='x')
        content2 = ctk.CTkFrame(card2, fg_color="transparent")
        content2.pack(fill='both', expand=True, padx=24, pady=20)

        ctk.CTkLabel(content2, text="📦 Exportar Productos", font=ctk.CTkFont(size=15, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(anchor='w')
        ctk.CTkLabel(content2, text="Descargar catalogo de productos", font=ctk.CTkFont(size=11), text_color=Theme.TEXT_MUTED).pack(anchor='w', pady=(4, 0))
        ctk.CTkButton(content2, text="📥 Exportar CSV", fg_color=Theme.SUCCESS, hover_color="#10b981", text_color="black", height=36, corner_radius=8, command=self._export_productos).pack(anchor='w', pady=(16, 0))

        # Estadisticas rapidas
        stats_frame = ctk.CTkFrame(self.content_frame, fg_color=Theme.BG_CARD, corner_radius=12)
        stats_frame.pack(fill='x', pady=(20, 0))

        ctk.CTkFrame(stats_frame, fg_color=Theme.INFO, height=3, corner_radius=0).pack(fill='x')
        stats_content = ctk.CTkFrame(stats_frame, fg_color="transparent")
        stats_content.pack(fill='x', padx=24, pady=20)

        ctk.CTkLabel(stats_content, text="📈 Estadisticas Rapidas", font=ctk.CTkFont(size=15, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(anchor='w')

        self.stats_info = ctk.CTkLabel(stats_content, text="Cargando...", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED)
        self.stats_info.pack(anchor='w', pady=(12, 0))

        self._load_reportes_stats()

    def _load_reportes_stats(self):
        """Cargar estadisticas para reportes"""
        def load():
            try:
                stats = self.api.obtener_estadisticas()
                productos = self.api.obtener_productos()

                total_productos = len(productos) if isinstance(productos, list) else 0

                if stats and not stats.get('error'):
                    por_estado = stats.get('por_estado', {})
                    total_pedidos = sum(por_estado.values()) if isinstance(por_estado, dict) else 0

                    info_text = f"Total de pedidos hoy: {total_pedidos} | Productos en catalogo: {total_productos}"
                    self.stats_info.configure(text=info_text)
            except Exception as e:
                print(f"Error: {e}")

        threading.Thread(target=load, daemon=True).start()

    def _export_pedidos(self):
        """Exportar pedidos a CSV"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfilename=f"pedidos_{datetime.now().strftime('%Y%m%d')}.csv"
        )

        if not filepath:
            return

        try:
            pedidos = self.api.obtener_pedidos(limite=1000)

            if isinstance(pedidos, list):
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['ID', 'Numero', 'Cliente', 'Tipo', 'Total', 'Estado', 'Fecha'])

                    for p in pedidos:
                        total = float(p.get('total', 0)) if p.get('total') else 0
                        writer.writerow([
                            p['id'],
                            p.get('numero_orden', ''),
                            p.get('cliente_nombre', 'N/A'),
                            p.get('tipo', ''),
                            total,
                            p.get('estado', ''),
                            p.get('fecha_pedido', '')
                        ])

                messagebox.showinfo("Exito", f"Reporte exportado a:\n{filepath}")
            else:
                messagebox.showerror("Error", "No se pudieron obtener los datos")

        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar: {e}")

    def _export_productos(self):
        """Exportar productos a CSV"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfilename=f"productos_{datetime.now().strftime('%Y%m%d')}.csv"
        )

        if not filepath:
            return

        try:
            productos = self.api.obtener_productos()

            if isinstance(productos, list):
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['ID', 'Nombre', 'Precio', 'Categoria', 'Disponible'])

                    cat_map = {c['id']: c['nombre'] for c in self.categorias}

                    for p in productos:
                        writer.writerow([
                            p['id'],
                            p['nombre'],
                            p['precio'],
                            cat_map.get(p.get('categoria_id'), 'Sin categoria'),
                            'Si' if p.get('disponible', 1) else 'No'
                        ])

                messagebox.showinfo("Exito", f"Reporte exportado a:\n{filepath}")
            else:
                messagebox.showerror("Error", "No se pudieron obtener los datos")

        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar: {e}")

    # ==================== USUARIOS ====================

    def _show_usuarios(self):
        """Mostrar gestion de usuarios"""
        self._clear_content()
        self.page_title.configure(text="Usuarios")
        self.page_subtitle.configure(text="Gestionar usuarios del sistema")

        # Toolbar
        toolbar = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        toolbar.pack(fill='x', pady=(0, 20))

        btn_left = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_left.pack(side='left')

        ctk.CTkButton(btn_left, text="+ Nuevo", fg_color=Theme.SUCCESS, hover_color="#10b981", text_color="black", height=38, corner_radius=8, command=self._new_usuario).pack(side='left', padx=(0, 8))
        ctk.CTkButton(btn_left, text="✏️ Editar", fg_color=Theme.BG_ELEVATED, hover_color=Theme.BG_INPUT, text_color=Theme.TEXT_SECONDARY, height=38, corner_radius=8, command=self._edit_usuario).pack(side='left', padx=(0, 8))
        ctk.CTkButton(btn_left, text="🗑️ Eliminar", fg_color=Theme.DANGER_BG, hover_color=Theme.DANGER, text_color=Theme.DANGER, height=38, corner_radius=8, command=self._delete_usuario).pack(side='left')

        ctk.CTkButton(toolbar, text="🔄 Actualizar", fg_color=Theme.BG_ELEVATED, hover_color=Theme.BG_INPUT, text_color=Theme.TEXT_SECONDARY, height=38, corner_radius=8, command=self._load_usuarios).pack(side='right')

        # Tabla
        table_container = ctk.CTkFrame(self.content_frame, fg_color=Theme.BG_CARD, corner_radius=12)
        table_container.pack(fill='both', expand=True)

        # Header
        header_frame = ctk.CTkFrame(table_container, fg_color=Theme.BG_ELEVATED, corner_radius=0)
        header_frame.pack(fill='x')

        headers = [('Nombre', 250), ('Email', 280), ('Rol', 120), ('Estado', 100)]
        for text, width in headers:
            ctk.CTkLabel(header_frame, text=text, font=ctk.CTkFont(size=11, weight="bold"), text_color=Theme.TEXT_MUTED, width=width, anchor='w').pack(side='left', padx=16, pady=10)

        # Scrollable
        self.usuarios_scroll = ctk.CTkScrollableFrame(table_container, fg_color="transparent")
        self.usuarios_scroll.pack(fill='both', expand=True, padx=4, pady=4)

        self._load_usuarios()

    def _load_usuarios(self):
        """Cargar usuarios"""
        for widget in self.usuarios_scroll.winfo_children():
            widget.destroy()

        result = self.api.obtener_usuarios()
        if result and result.get('success'):
            self.usuarios_data = result.get('usuarios', [])
        else:
            self.usuarios_data = []

        self.selected_usuario = None

        for i, u in enumerate(self.usuarios_data):
            bg = Theme.BG_CARD if i % 2 == 0 else Theme.BG_SECONDARY

            row = ctk.CTkFrame(self.usuarios_scroll, fg_color=bg, corner_radius=0, height=50)
            row.pack(fill='x', pady=1)
            row.pack_propagate(False)

            ctk.CTkLabel(row, text=u.get('nombre', ''), font=ctk.CTkFont(size=12), text_color=Theme.TEXT_PRIMARY, width=250, anchor='w').pack(side='left', padx=16)
            ctk.CTkLabel(row, text=u.get('email', ''), font=ctk.CTkFont(size=12), text_color=Theme.TEXT_SECONDARY, width=280, anchor='w').pack(side='left', padx=16)

            rol = u.get('rol', 'mesero').capitalize()
            rol_color = Theme.ACCENT if rol == 'Admin' else (Theme.SUCCESS if rol == 'Cocina' else Theme.TEXT_SECONDARY)
            ctk.CTkLabel(row, text=rol, font=ctk.CTkFont(size=11), text_color=rol_color, width=120, anchor='w').pack(side='left', padx=16)

            estado = 'Activo' if u.get('activo', 1) else 'Inactivo'
            estado_color = Theme.SUCCESS if u.get('activo', 1) else Theme.DANGER
            ctk.CTkLabel(row, text=estado, font=ctk.CTkFont(size=11), text_color=estado_color, width=100, anchor='w').pack(side='left', padx=16)

            def on_click(e, r=row, usuario=u):
                self._select_usuario(r, usuario)

            row.bind('<Button-1>', on_click)
            for child in row.winfo_children():
                child.bind('<Button-1>', on_click)

    def _select_usuario(self, row, usuario):
        """Seleccionar usuario"""
        for child in self.usuarios_scroll.winfo_children():
            idx = self.usuarios_scroll.winfo_children().index(child)
            child.configure(fg_color=Theme.BG_CARD if idx % 2 == 0 else Theme.BG_SECONDARY)

        row.configure(fg_color=Theme.ACCENT_SUBTLE)
        self.selected_usuario = usuario

    def _new_usuario(self):
        """Crear nuevo usuario"""
        UsuarioDialog(self.root, self.api, on_save=self._load_usuarios)

    def _edit_usuario(self):
        """Editar usuario seleccionado"""
        if not hasattr(self, 'selected_usuario') or not self.selected_usuario:
            messagebox.showwarning("Aviso", "Selecciona un usuario")
            return

        UsuarioDialog(self.root, self.api, self.selected_usuario, on_save=self._load_usuarios)

    def _delete_usuario(self):
        """Eliminar usuario"""
        if not hasattr(self, 'selected_usuario') or not self.selected_usuario:
            messagebox.showwarning("Aviso", "Selecciona un usuario")
            return

        if self.selected_usuario['id'] == self.api.user.get('id'):
            messagebox.showwarning("Aviso", "No puedes eliminarte a ti mismo")
            return

        if messagebox.askyesno("Confirmar", "¿Eliminar este usuario?"):
            result = self.api.eliminar_usuario(self.selected_usuario['id'])
            if result and result.get('success'):
                self.selected_usuario = None
                self._load_usuarios()
            else:
                messagebox.showerror("Error", result.get('error', 'Error desconocido'))

    # ==================== UTILIDADES ====================

    def _load_initial_data(self):
        """Cargar datos iniciales"""
        def load():
            self.categorias = self.api.obtener_categorias() or []
            if not isinstance(self.categorias, list):
                self.categorias = []

        threading.Thread(target=load, daemon=True).start()

    def _logout(self):
        """Cerrar sesion"""
        self.running = False
        self.api.logout()
        self.root.destroy()


# ==================== DIALOGOS ====================

class ProductoDialog(ctk.CTkToplevel):
    """Dialogo moderno para producto"""

    def __init__(self, parent, api, categorias, producto=None, on_save=None):
        super().__init__(parent)
        self.api = api
        self.on_save = on_save
        self.imagen_path = None
        self.imagen_url = producto.get('imagen', '') if producto else ''
        self.categorias = categorias

        self.title("Nuevo Producto" if not producto else "Editar Producto")
        self.geometry("500x600")
        self.configure(fg_color=Theme.BG_PRIMARY)
        self.transient(parent)
        self.grab_set()

        # Centrar
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 500) // 2
        y = (self.winfo_screenheight() - 600) // 2
        self.geometry(f"+{x}+{y}")

        # Container
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill='both', expand=True, padx=32, pady=28)

        # Titulo
        ctk.CTkLabel(
            container,
            text="Nuevo Producto" if not producto else "Editar Producto",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=Theme.TEXT_PRIMARY
        ).pack(anchor='w', pady=(0, 24))

        # Nombre
        ctk.CTkLabel(container, text="Nombre del producto", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED).pack(anchor='w', pady=(0, 4))
        self.nombre_entry = ctk.CTkEntry(container, font=ctk.CTkFont(size=13), fg_color=Theme.BG_INPUT, border_color=Theme.BORDER, text_color=Theme.TEXT_PRIMARY, height=40, corner_radius=8)
        self.nombre_entry.pack(fill='x')
        if producto:
            self.nombre_entry.insert(0, producto.get('nombre', ''))

        # Precio
        ctk.CTkLabel(container, text="Precio", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED).pack(anchor='w', pady=(16, 4))
        self.precio_entry = ctk.CTkEntry(container, font=ctk.CTkFont(size=13), fg_color=Theme.BG_INPUT, border_color=Theme.BORDER, text_color=Theme.TEXT_PRIMARY, height=40, corner_radius=8)
        self.precio_entry.pack(fill='x')
        if producto:
            self.precio_entry.insert(0, str(producto.get('precio', '')))

        # Categoria
        ctk.CTkLabel(container, text="Categoria", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED).pack(anchor='w', pady=(16, 4))

        self.cat_nombre_to_id = {c['nombre']: c['id'] for c in categorias}
        cat_values = ['Sin categoria'] + [c['nombre'] for c in categorias]

        self.cat_combo = ctk.CTkComboBox(container, values=cat_values, font=ctk.CTkFont(size=13), fg_color=Theme.BG_INPUT, border_color=Theme.BORDER, button_color=Theme.BG_ELEVATED, dropdown_fg_color=Theme.BG_CARD, height=40, corner_radius=8)
        self.cat_combo.pack(fill='x')

        if producto and producto.get('categoria_id'):
            for c in categorias:
                if c['id'] == producto['categoria_id']:
                    self.cat_combo.set(c['nombre'])
                    break
        else:
            self.cat_combo.set('Sin categoria')

        # Imagen
        img_frame = ctk.CTkFrame(container, fg_color="transparent")
        img_frame.pack(fill='x', pady=(20, 0))

        ctk.CTkLabel(img_frame, text="Imagen", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED).pack(anchor='w')

        img_btn_frame = ctk.CTkFrame(img_frame, fg_color="transparent")
        img_btn_frame.pack(fill='x', pady=(8, 0))

        ctk.CTkButton(img_btn_frame, text="📁 Seleccionar", fg_color=Theme.BG_ELEVATED, hover_color=Theme.BG_INPUT, text_color=Theme.TEXT_SECONDARY, height=32, corner_radius=6, command=self._select_imagen).pack(side='left')

        self.imagen_label = ctk.CTkLabel(img_btn_frame, text="Imagen actual" if self.imagen_url else "Sin imagen", font=ctk.CTkFont(size=12), text_color=Theme.SUCCESS if self.imagen_url else Theme.TEXT_MUTED)
        self.imagen_label.pack(side='left', padx=(12, 0))

        # Disponible
        self.disponible_var = ctk.BooleanVar(value=producto.get('disponible', 1) if producto else True)
        self.disponible_check = ctk.CTkCheckBox(container, text="Disponible para venta", variable=self.disponible_var, font=ctk.CTkFont(size=13), text_color=Theme.TEXT_PRIMARY, fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER)
        self.disponible_check.pack(anchor='w', pady=(20, 0))

        # Botones
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill='x', pady=(28, 0))

        ctk.CTkButton(btn_frame, text="💾 Guardar", fg_color=Theme.SUCCESS, hover_color="#10b981", text_color="black", height=42, corner_radius=8, command=lambda: self._save(producto)).pack(side='left', padx=(0, 12))
        ctk.CTkButton(btn_frame, text="Cancelar", fg_color=Theme.BG_ELEVATED, hover_color=Theme.BG_INPUT, text_color=Theme.TEXT_SECONDARY, height=42, corner_radius=8, command=self.destroy).pack(side='left')

    def _select_imagen(self):
        """Seleccionar imagen"""
        filepath = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[("Imagenes", "*.png *.jpg *.jpeg *.webp")]
        )
        if filepath:
            self.imagen_path = filepath
            self.imagen_label.configure(text=os.path.basename(filepath), text_color=Theme.SUCCESS)

    def _save(self, producto=None):
        """Guardar producto"""
        try:
            precio = float(self.precio_entry.get())
        except:
            messagebox.showerror("Error", "Precio invalido")
            return

        nombre = self.nombre_entry.get().strip()
        if not nombre:
            messagebox.showerror("Error", "El nombre es requerido")
            return

        cat_id = None
        cat_sel = self.cat_combo.get()
        if cat_sel and cat_sel != 'Sin categoria':
            cat_id = self.cat_nombre_to_id.get(cat_sel)

        # Subir imagen si hay nueva
        imagen_url = self.imagen_url
        if self.imagen_path:
            result = self.api.subir_imagen(self.imagen_path)
            if result and result.get('success'):
                imagen_url = result['url']
            else:
                messagebox.showwarning("Aviso", "No se pudo subir la imagen")

        data = {
            'nombre': nombre,
            'precio': precio,
            'categoria_id': cat_id,
            'disponible': 1 if self.disponible_var.get() else 0,
            'imagen': imagen_url
        }

        if producto:
            result = self.api.actualizar_producto(producto['id'], **data)
        else:
            result = self.api.crear_producto(**data)

        if result and result.get('success'):
            if self.on_save:
                self.on_save()
            self.destroy()
        else:
            messagebox.showerror("Error", result.get('error', 'Error desconocido'))


class OfertaDialog(ctk.CTkToplevel):
    """Dialogo moderno para oferta"""

    def __init__(self, parent, api, oferta=None, on_save=None):
        super().__init__(parent)
        self.api = api
        self.on_save = on_save
        self.imagen_path = None
        self.imagen_url = oferta.get('imagen', '') if oferta else ''

        self.title("Nueva Oferta" if not oferta else "Editar Oferta")
        self.geometry("500x600")
        self.configure(fg_color=Theme.BG_PRIMARY)
        self.transient(parent)
        self.grab_set()

        # Centrar
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 500) // 2
        y = (self.winfo_screenheight() - 600) // 2
        self.geometry(f"+{x}+{y}")

        # Container
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill='both', expand=True, padx=32, pady=28)

        # Titulo
        ctk.CTkLabel(container, text="Nueva Oferta" if not oferta else "Editar Oferta", font=ctk.CTkFont(size=22, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(anchor='w', pady=(0, 24))

        # Titulo oferta
        ctk.CTkLabel(container, text="Titulo de la oferta", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED).pack(anchor='w', pady=(0, 4))
        self.titulo_entry = ctk.CTkEntry(container, font=ctk.CTkFont(size=13), fg_color=Theme.BG_INPUT, border_color=Theme.BORDER, text_color=Theme.TEXT_PRIMARY, height=40, corner_radius=8)
        self.titulo_entry.pack(fill='x')
        if oferta:
            self.titulo_entry.insert(0, oferta.get('titulo', ''))

        # Descripcion
        ctk.CTkLabel(container, text="Descripcion", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED).pack(anchor='w', pady=(16, 4))
        self.desc_entry = ctk.CTkEntry(container, font=ctk.CTkFont(size=13), fg_color=Theme.BG_INPUT, border_color=Theme.BORDER, text_color=Theme.TEXT_PRIMARY, height=40, corner_radius=8)
        self.desc_entry.pack(fill='x')
        if oferta:
            self.desc_entry.insert(0, oferta.get('descripcion', ''))

        # Descuento
        ctk.CTkLabel(container, text="Descuento (%)", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED).pack(anchor='w', pady=(16, 4))
        self.descuento_entry = ctk.CTkEntry(container, font=ctk.CTkFont(size=13), fg_color=Theme.BG_INPUT, border_color=Theme.BORDER, text_color=Theme.TEXT_PRIMARY, height=40, corner_radius=8)
        self.descuento_entry.pack(fill='x')
        if oferta:
            self.descuento_entry.insert(0, str(oferta.get('descuento', '')))

        # Imagen
        img_frame = ctk.CTkFrame(container, fg_color="transparent")
        img_frame.pack(fill='x', pady=(20, 0))

        ctk.CTkLabel(img_frame, text="Imagen", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED).pack(anchor='w')

        img_btn_frame = ctk.CTkFrame(img_frame, fg_color="transparent")
        img_btn_frame.pack(fill='x', pady=(8, 0))

        ctk.CTkButton(img_btn_frame, text="📁 Seleccionar", fg_color=Theme.BG_ELEVATED, hover_color=Theme.BG_INPUT, text_color=Theme.TEXT_SECONDARY, height=32, corner_radius=6, command=self._select_imagen).pack(side='left')

        self.imagen_label = ctk.CTkLabel(img_btn_frame, text="Imagen actual" if self.imagen_url else "Sin imagen", font=ctk.CTkFont(size=12), text_color=Theme.SUCCESS if self.imagen_url else Theme.TEXT_MUTED)
        self.imagen_label.pack(side='left', padx=(12, 0))

        # Activa
        self.activa_var = ctk.BooleanVar(value=oferta.get('activa', 1) if oferta else True)
        self.activa_check = ctk.CTkCheckBox(container, text="Oferta activa", variable=self.activa_var, font=ctk.CTkFont(size=13), text_color=Theme.TEXT_PRIMARY, fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER)
        self.activa_check.pack(anchor='w', pady=(20, 0))

        # Botones
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill='x', pady=(28, 0))

        ctk.CTkButton(btn_frame, text="💾 Guardar", fg_color=Theme.SUCCESS, hover_color="#10b981", text_color="black", height=42, corner_radius=8, command=lambda: self._save(oferta)).pack(side='left', padx=(0, 12))
        ctk.CTkButton(btn_frame, text="Cancelar", fg_color=Theme.BG_ELEVATED, hover_color=Theme.BG_INPUT, text_color=Theme.TEXT_SECONDARY, height=42, corner_radius=8, command=self.destroy).pack(side='left')

    def _select_imagen(self):
        """Seleccionar imagen"""
        filepath = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[("Imagenes", "*.png *.jpg *.jpeg *.webp")]
        )
        if filepath:
            self.imagen_path = filepath
            self.imagen_label.configure(text=os.path.basename(filepath), text_color=Theme.SUCCESS)

    def _save(self, oferta=None):
        """Guardar oferta"""
        titulo = self.titulo_entry.get().strip()
        if not titulo:
            messagebox.showerror("Error", "El titulo es requerido")
            return

        try:
            descuento = int(self.descuento_entry.get())
            if descuento < 0 or descuento > 100:
                raise ValueError()
        except:
            messagebox.showerror("Error", "Descuento invalido (0-100)")
            return

        # Subir imagen si hay nueva
        imagen_url = self.imagen_url
        if self.imagen_path:
            result = self.api.subir_imagen(self.imagen_path)
            if result and result.get('success'):
                imagen_url = result['url']

        data = {
            'titulo': titulo,
            'descripcion': self.desc_entry.get().strip(),
            'descuento': descuento,
            'imagen': imagen_url,
            'activa': 1 if self.activa_var.get() else 0
        }

        if oferta:
            result = self.api.actualizar_oferta(oferta['id'], **data)
        else:
            result = self.api.crear_oferta(**data)

        if result and result.get('success'):
            if self.on_save:
                self.on_save()
            self.destroy()
        else:
            messagebox.showerror("Error", result.get('error', 'Error desconocido'))


class MeseroPedidosDialog(ctk.CTkToplevel):
    """Dialogo para ver pedidos de un mesero"""

    def __init__(self, parent, api, mesero, filtro_periodo):
        super().__init__(parent)
        self.api = api
        self.mesero = mesero

        self.title(f"Pedidos de {mesero.get('mesero_nombre', 'Mesero')}")
        self.geometry("700x500")
        self.configure(fg_color=Theme.BG_PRIMARY)
        self.transient(parent)
        self.grab_set()

        # Centrar
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 700) // 2
        y = (self.winfo_screenheight() - 500) // 2
        self.geometry(f"+{x}+{y}")

        # Container
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill='both', expand=True, padx=24, pady=20)

        # Header con stats
        header = ctk.CTkFrame(container, fg_color=Theme.BG_CARD, corner_radius=12)
        header.pack(fill='x', pady=(0, 16))

        header_content = ctk.CTkFrame(header, fg_color="transparent")
        header_content.pack(fill='x', padx=20, pady=16)

        ctk.CTkLabel(header_content, text=mesero.get('mesero_nombre', 'Mesero'),
                    font=ctk.CTkFont(size=18, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(anchor='w')

        stats_frame = ctk.CTkFrame(header_content, fg_color="transparent")
        stats_frame.pack(fill='x', pady=(8, 0))

        total_pedidos = mesero.get('total_pedidos', 0)
        total_ventas = float(mesero.get('total_ventas', 0))

        ctk.CTkLabel(stats_frame, text=f"📦 {total_pedidos} pedidos",
                    font=ctk.CTkFont(size=13), text_color=Theme.INFO).pack(side='left', padx=(0, 20))
        ctk.CTkLabel(stats_frame, text=f"💰 ${total_ventas:,.0f} en ventas",
                    font=ctk.CTkFont(size=13), text_color=Theme.SUCCESS).pack(side='left')

        # Lista de pedidos
        ctk.CTkLabel(container, text="Pedidos realizados:", font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=Theme.TEXT_PRIMARY).pack(anchor='w', pady=(0, 8))

        pedidos_frame = ctk.CTkScrollableFrame(container, fg_color=Theme.BG_CARD, corner_radius=12)
        pedidos_frame.pack(fill='both', expand=True)

        # Cargar pedidos
        filtro_map = {"Hoy": "hoy", "Semana": "semana", "Mes": "mes", "Todo": "todo"}
        filtro = filtro_map.get(filtro_periodo, "hoy")

        try:
            pedidos = api.obtener_pedidos_mesero(mesero.get('mesero_id'), filtro=filtro)

            if not pedidos:
                ctk.CTkLabel(pedidos_frame, text="No hay pedidos en este período",
                            font=ctk.CTkFont(size=13), text_color=Theme.TEXT_MUTED).pack(pady=30)
            else:
                for pedido in pedidos:
                    row = ctk.CTkFrame(pedidos_frame, fg_color="transparent")
                    row.pack(fill='x', padx=12, pady=8)

                    # Número de orden
                    ctk.CTkLabel(row, text=f"#{pedido.get('numero_orden', pedido.get('id'))}",
                                font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.ACCENT,
                                width=120, anchor='w').pack(side='left')

                    # Cliente
                    cliente = pedido.get('cliente_nombre', 'Cliente')
                    ctk.CTkLabel(row, text=cliente, font=ctk.CTkFont(size=12),
                                text_color=Theme.TEXT_SECONDARY, width=150, anchor='w').pack(side='left')

                    # Fecha
                    fecha = pedido.get('fecha_pedido', '')[:16] if pedido.get('fecha_pedido') else ''
                    ctk.CTkLabel(row, text=fecha, font=ctk.CTkFont(size=11),
                                text_color=Theme.TEXT_MUTED, width=130).pack(side='left')

                    # Total
                    total = float(pedido.get('total', 0) or 0)
                    ctk.CTkLabel(row, text=f"${total:,.0f}", font=ctk.CTkFont(size=12, weight="bold"),
                                text_color=Theme.SUCCESS).pack(side='right', padx=10)

                    # Estado
                    estado = pedido.get('estado', 'pendiente')
                    estado_colors = {
                        'pendiente': Theme.WARNING,
                        'confirmado': Theme.INFO,
                        'preparando': '#f59e0b',
                        'listo': Theme.SUCCESS,
                        'entregado': Theme.SUCCESS
                    }
                    ctk.CTkLabel(row, text=estado.upper(), font=ctk.CTkFont(size=10),
                                text_color=estado_colors.get(estado, Theme.TEXT_MUTED)).pack(side='right', padx=10)

                    # Separador
                    sep = ctk.CTkFrame(pedidos_frame, fg_color=Theme.BORDER, height=1)
                    sep.pack(fill='x', padx=12)

        except Exception as e:
            ctk.CTkLabel(pedidos_frame, text=f"Error: {e}",
                        font=ctk.CTkFont(size=13), text_color=Theme.DANGER).pack(pady=30)

        # Botón cerrar
        ctk.CTkButton(container, text="Cerrar", fg_color=Theme.BG_ELEVATED,
                     hover_color=Theme.BG_INPUT, text_color=Theme.TEXT_SECONDARY,
                     height=36, corner_radius=8, command=self.destroy).pack(pady=(16, 0))


class PedidoDetailDialog(ctk.CTkToplevel):
    """Dialogo para ver detalle de pedido"""

    def __init__(self, parent, pedido):
        super().__init__(parent)
        self.pedido = pedido

        self.title(f"Pedido #{pedido.get('numero_orden', pedido['id'])}")
        self.geometry("500x600")
        self.configure(fg_color=Theme.BG_PRIMARY)
        self.transient(parent)
        self.grab_set()

        # Centrar
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 500) // 2
        y = (self.winfo_screenheight() - 600) // 2
        self.geometry(f"+{x}+{y}")

        # Container
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill='both', expand=True, padx=32, pady=28)

        # Titulo
        ctk.CTkLabel(container, text=f"Pedido #{pedido.get('numero_orden', pedido['id'])}", font=ctk.CTkFont(size=22, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(anchor='w', pady=(0, 24))

        # Info card
        info_card = ctk.CTkFrame(container, fg_color=Theme.BG_CARD, corner_radius=12)
        info_card.pack(fill='x', pady=(0, 20))

        info_content = ctk.CTkFrame(info_card, fg_color="transparent")
        info_content.pack(fill='x', padx=20, pady=16)

        # Cliente
        self._add_info_row(info_content, "Cliente", pedido.get('cliente_nombre', 'N/A'))
        self._add_info_row(info_content, "Tipo", pedido.get('tipo', 'mesa').capitalize())
        self._add_info_row(info_content, "Estado", pedido.get('estado', 'pendiente').capitalize())
        self._add_info_row(info_content, "Fecha", pedido.get('fecha_pedido', '')[:16] if pedido.get('fecha_pedido') else '')

        total = float(pedido.get('total', 0) or 0)
        self._add_info_row(info_content, "Total", f"${total:,.0f}")

        # Productos
        ctk.CTkLabel(container, text="Productos", font=ctk.CTkFont(size=15, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(anchor='w', pady=(0, 12))

        productos_frame = ctk.CTkScrollableFrame(container, fg_color=Theme.BG_CARD, corner_radius=12, height=200)
        productos_frame.pack(fill='both', expand=True)

        items = pedido.get('items', [])
        if items:
            for item in items:
                row = ctk.CTkFrame(productos_frame, fg_color="transparent")
                row.pack(fill='x', padx=16, pady=8)

                ctk.CTkLabel(row, text=f"x{item.get('cantidad', 1)}", font=ctk.CTkFont(size=12, weight="bold"), text_color=Theme.ACCENT, width=40).pack(side='left')
                # Mostrar nombre del producto + variante/notas si existe
                nombre_producto = item.get('producto_nombre') or item.get('nombre', 'Producto')
                notas = item.get('notas', '')
                if notas and not notas.startswith('[OFERTA]'):
                    nombre_producto = f"{nombre_producto} - {notas}"
                ctk.CTkLabel(row, text=nombre_producto, font=ctk.CTkFont(size=12), text_color=Theme.TEXT_PRIMARY).pack(side='left', fill='x', expand=True)

                subtotal = float(item.get('subtotal', 0) or 0)
                ctk.CTkLabel(row, text=f"${subtotal:,.0f}", font=ctk.CTkFont(size=12), text_color=Theme.SUCCESS).pack(side='right')
        else:
            ctk.CTkLabel(productos_frame, text="Sin productos", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED).pack(pady=20)

        # Boton cerrar
        ctk.CTkButton(container, text="Cerrar", fg_color=Theme.BG_ELEVATED, hover_color=Theme.BG_INPUT, text_color=Theme.TEXT_SECONDARY, height=42, corner_radius=8, command=self.destroy).pack(pady=(20, 0))

    def _add_info_row(self, parent, label, value):
        """Agregar fila de info"""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill='x', pady=4)

        ctk.CTkLabel(row, text=label, font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED, width=100, anchor='w').pack(side='left')
        ctk.CTkLabel(row, text=value, font=ctk.CTkFont(size=12), text_color=Theme.TEXT_PRIMARY).pack(side='right')


class UsuarioDialog(ctk.CTkToplevel):
    """Dialogo moderno para usuario"""

    def __init__(self, parent, api, usuario=None, on_save=None):
        super().__init__(parent)
        self.api = api
        self.on_save = on_save

        self.title("Nuevo Usuario" if not usuario else "Editar Usuario")
        self.geometry("450x520")
        self.configure(fg_color=Theme.BG_PRIMARY)
        self.transient(parent)
        self.grab_set()

        # Centrar
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 450) // 2
        y = (self.winfo_screenheight() - 520) // 2
        self.geometry(f"+{x}+{y}")

        # Container
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill='both', expand=True, padx=32, pady=28)

        # Titulo
        ctk.CTkLabel(container, text="Nuevo Usuario" if not usuario else "Editar Usuario", font=ctk.CTkFont(size=22, weight="bold"), text_color=Theme.TEXT_PRIMARY).pack(anchor='w', pady=(0, 24))

        # Nombre
        ctk.CTkLabel(container, text="Nombre completo", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED).pack(anchor='w', pady=(0, 4))
        self.nombre_entry = ctk.CTkEntry(container, font=ctk.CTkFont(size=13), fg_color=Theme.BG_INPUT, border_color=Theme.BORDER, text_color=Theme.TEXT_PRIMARY, height=40, corner_radius=8)
        self.nombre_entry.pack(fill='x')
        if usuario:
            self.nombre_entry.insert(0, usuario.get('nombre', ''))

        # Email
        ctk.CTkLabel(container, text="Email", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED).pack(anchor='w', pady=(16, 4))
        self.email_entry = ctk.CTkEntry(container, font=ctk.CTkFont(size=13), fg_color=Theme.BG_INPUT, border_color=Theme.BORDER, text_color=Theme.TEXT_PRIMARY, height=40, corner_radius=8)
        self.email_entry.pack(fill='x')
        if usuario:
            self.email_entry.insert(0, usuario.get('email', ''))

        # Password
        password_label = "Nueva contrasena" if usuario else "Contrasena"
        if usuario:
            password_label += " (dejar vacio para no cambiar)"
        ctk.CTkLabel(container, text=password_label, font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED).pack(anchor='w', pady=(16, 4))
        self.password_entry = ctk.CTkEntry(container, font=ctk.CTkFont(size=13), fg_color=Theme.BG_INPUT, border_color=Theme.BORDER, text_color=Theme.TEXT_PRIMARY, height=40, corner_radius=8, show="*")
        self.password_entry.pack(fill='x')

        # Rol
        ctk.CTkLabel(container, text="Rol", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED).pack(anchor='w', pady=(16, 4))
        self.rol_combo = ctk.CTkComboBox(container, values=['admin', 'mesero', 'cocina'], font=ctk.CTkFont(size=13), fg_color=Theme.BG_INPUT, border_color=Theme.BORDER, button_color=Theme.BG_ELEVATED, dropdown_fg_color=Theme.BG_CARD, height=40, corner_radius=8)
        self.rol_combo.pack(fill='x')
        rol_actual = usuario.get('rol', 'mesero') if usuario else 'mesero'
        self.rol_combo.set(rol_actual)

        # Activo (solo para edicion)
        self.activo_var = None
        if usuario:
            self.activo_var = ctk.BooleanVar(value=usuario.get('activo', 1))
            self.activo_check = ctk.CTkCheckBox(container, text="Usuario activo", variable=self.activo_var, font=ctk.CTkFont(size=13), text_color=Theme.TEXT_PRIMARY, fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER)
            self.activo_check.pack(anchor='w', pady=(20, 0))

        # Botones
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill='x', pady=(28, 0))

        ctk.CTkButton(btn_frame, text="💾 Guardar", fg_color=Theme.SUCCESS, hover_color="#10b981", text_color="black", height=42, corner_radius=8, command=lambda: self._save(usuario)).pack(side='left', padx=(0, 12))
        ctk.CTkButton(btn_frame, text="Cancelar", fg_color=Theme.BG_ELEVATED, hover_color=Theme.BG_INPUT, text_color=Theme.TEXT_SECONDARY, height=42, corner_radius=8, command=self.destroy).pack(side='left')

    def _save(self, usuario=None):
        """Guardar usuario"""
        nombre = self.nombre_entry.get().strip()
        email = self.email_entry.get().strip().lower()
        password = self.password_entry.get()
        rol = self.rol_combo.get()

        if not nombre:
            messagebox.showerror("Error", "El nombre es requerido")
            return

        if not email or '@' not in email:
            messagebox.showerror("Error", "Email invalido")
            return

        if not usuario and not password:
            messagebox.showerror("Error", "La contrasena es requerida")
            return

        if usuario:
            data = {'nombre': nombre, 'email': email, 'rol': rol}
            if password:
                data['password'] = password
            if self.activo_var is not None:
                data['activo'] = self.activo_var.get()

            result = self.api.actualizar_usuario(usuario['id'], **data)
        else:
            result = self.api.crear_usuario(nombre, email, password, rol)

        if result and result.get('success'):
            if self.on_save:
                self.on_save()
            self.destroy()
        else:
            messagebox.showerror("Error", result.get('error', 'Error desconocido'))


def main():
    """Punto de entrada"""
    from launcher import LoginWindow

    app = ctk.CTk()
    app.withdraw()

    def on_login(api):
        app.destroy()
        admin_app = AdminApp(api)
        admin_app.mainloop()

    login_window = ctk.CTkToplevel(app)
    LoginWindow(login_window, 'admin', lambda api, w: [w.destroy(), on_login(api)], app.quit)

    app.mainloop()


if __name__ == '__main__':
    main()
