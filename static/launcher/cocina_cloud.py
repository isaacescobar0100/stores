"""
Vista de Cocina - CustomTkinter Modern UI
Muestra pedidos en tiempo real desde el servidor central
"""
import customtkinter as ctk
from tkinter import messagebox
import threading
import time
import os
import subprocess
import re
from datetime import datetime
from api_client import APIClient

# Configurar CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class Theme:
    """Colores del tema"""
    BG = '#0f172a'
    HEADER = '#1e293b'
    CARD_BG = '#1e293b'
    CARD_PENDIENTE = '#dc2626'
    CARD_PREPARANDO = '#f59e0b'
    CARD_LISTO = '#16a34a'
    TEXT = '#f8fafc'
    TEXT_MUTED = '#94a3b8'
    ACCENT = '#3b82f6'
    BORDER = '#334155'
    SUCCESS = '#22c55e'
    DANGER = '#ef4444'


def convertir_hora_utc_a_colombia(fecha_raw):
    """Convierte fecha UTC a hora Colombia (UTC-5) en formato 12h"""
    if not fecha_raw:
        return ''
    try:
        from datetime import datetime, timedelta
        fecha_str = str(fecha_raw).replace('T', ' ').replace('Z', '').split('.')[0]
        dt = datetime.strptime(fecha_str, '%Y-%m-%d %H:%M:%S')
        dt = dt - timedelta(hours=5)  # UTC a Colombia
        # Formato 12h sin ceros iniciales (ej: 9:50 PM)
        hora = dt.hour
        minuto = dt.minute
        am_pm = 'AM' if hora < 12 else 'PM'
        if hora == 0:
            hora = 12
        elif hora > 12:
            hora = hora - 12
        return f"{hora}:{minuto:02d} {am_pm}"
    except:
        # Fallback: extraer hora directamente
        if len(str(fecha_raw)) > 16:
            return str(fecha_raw)[11:16]
        return ''


class LoginWindow:
    """Ventana de inicio de sesion para cocina - CustomTkinter"""

    def __init__(self, root, on_login_success):
        self.root = root
        self.on_login_success = on_login_success
        self.api = APIClient()

        self.root.title("Cocina - Login")
        self.root.geometry("450x550")
        self.root.resizable(False, False)
        self.root.configure(fg_color=Theme.BG)

        # Centrar
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 450) // 2
        y = (self.root.winfo_screenheight() - 550) // 2
        self.root.geometry(f"+{x}+{y}")

        self._crear_widgets()

        # Auto-login si hay sesion (usar after para no bloquear)
        if self.api.esta_autenticado():
            self.root.after(100, lambda: self._auto_login())

    def _auto_login(self):
        """Realizar auto-login y cerrar ventana"""
        self.root.destroy()
        self.on_login_success(self.api)

    def _crear_widgets(self):
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.pack(expand=True, fill='both', padx=40, pady=40)

        # Logo
        ctk.CTkLabel(
            main_frame,
            text="👨‍🍳",
            font=ctk.CTkFont(size=64)
        ).pack(pady=(0, 10))

        ctk.CTkLabel(
            main_frame,
            text="COCINA",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=Theme.TEXT
        ).pack(pady=(0, 5))

        ctk.CTkLabel(
            main_frame,
            text="Sistema de Pedidos",
            font=ctk.CTkFont(size=14),
            text_color=Theme.TEXT_MUTED
        ).pack(pady=(0, 30))

        # Servidor
        ctk.CTkLabel(main_frame, text="Servidor:", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED).pack(anchor='w')
        self.servidor_entry = ctk.CTkEntry(main_frame, font=ctk.CTkFont(size=13), fg_color=Theme.CARD_BG, border_color=Theme.BORDER, text_color=Theme.TEXT, height=40, corner_radius=8)
        self.servidor_entry.pack(fill='x', pady=(0, 12))
        self.servidor_entry.insert(0, self.api.servidor_url)

        # Tienda
        ctk.CTkLabel(main_frame, text="Tienda (slug):", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED).pack(anchor='w')
        self.tienda_entry = ctk.CTkEntry(main_frame, font=ctk.CTkFont(size=13), fg_color=Theme.CARD_BG, border_color=Theme.BORDER, text_color=Theme.TEXT, height=40, corner_radius=8)
        self.tienda_entry.pack(fill='x', pady=(0, 12))
        self.tienda_entry.insert(0, self.api.tienda_slug)

        # Email
        ctk.CTkLabel(main_frame, text="Email:", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED).pack(anchor='w')
        self.email_entry = ctk.CTkEntry(main_frame, font=ctk.CTkFont(size=13), fg_color=Theme.CARD_BG, border_color=Theme.BORDER, text_color=Theme.TEXT, height=40, corner_radius=8)
        self.email_entry.pack(fill='x', pady=(0, 12))

        # Password
        ctk.CTkLabel(main_frame, text="Contrasena:", font=ctk.CTkFont(size=12), text_color=Theme.TEXT_MUTED).pack(anchor='w')
        self.password_entry = ctk.CTkEntry(main_frame, font=ctk.CTkFont(size=13), fg_color=Theme.CARD_BG, border_color=Theme.BORDER, text_color=Theme.TEXT, height=40, corner_radius=8, show="*")
        self.password_entry.pack(fill='x', pady=(0, 24))

        # Boton login
        self.login_btn = ctk.CTkButton(
            main_frame,
            text="ENTRAR",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=Theme.CARD_PENDIENTE,
            hover_color="#b91c1c",
            text_color="white",
            height=48,
            corner_radius=8,
            command=self._login
        )
        self.login_btn.pack(fill='x')

        self.status_label = ctk.CTkLabel(main_frame, text="", font=ctk.CTkFont(size=12), text_color=Theme.DANGER)
        self.status_label.pack(pady=12)

    def _login(self):
        self.status_label.configure(text="Conectando...")
        self.login_btn.configure(state="disabled")

        self.api.servidor_url = self.servidor_entry.get().strip()
        self.api.tienda_slug = self.tienda_entry.get().strip()
        email = self.email_entry.get().strip()
        password = self.password_entry.get()

        def login_async():
            result = self.api.login(email, password)
            self.root.after(0, lambda: self._login_callback(result))

        threading.Thread(target=login_async, daemon=True).start()

    def _login_callback(self, result):
        """Callback del login en hilo principal"""
        if result and result.get('success'):
            self.root.destroy()
            self.on_login_success(self.api)
        else:
            self.login_btn.configure(state="normal")
            self.status_label.configure(text=result.get('error', 'Error de conexion') if result else 'Error de conexion')


class CocinaApp:
    """Aplicacion de cocina - CustomTkinter"""

    COLUMNS = 4

    def __init__(self, root, api):
        self.root = root
        self.api = api
        self.running = True
        self.pedidos_impresos = set()
        self.auto_print = True
        self.primera_carga = True

        self.root.title(f"COCINA - {api.tienda.get('nombre', 'Restaurante')}")
        self.root.state('zoomed')
        self.root.configure(fg_color=Theme.BG)

        self._crear_widgets()
        self._iniciar_actualizacion()

    def _crear_widgets(self):
        # Header moderno
        header = ctk.CTkFrame(self.root, fg_color=Theme.HEADER, height=70, corner_radius=0)
        header.pack(fill='x')
        header.pack_propagate(False)

        # Lado izquierdo - Titulo
        left_header = ctk.CTkFrame(header, fg_color="transparent")
        left_header.pack(side='left', fill='y', padx=20)

        ctk.CTkLabel(
            left_header,
            text="👨‍🍳 COCINA",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=Theme.TEXT
        ).pack(side='left', pady=15)

        ctk.CTkLabel(
            left_header,
            text=f"  {self.api.tienda.get('nombre', '')}",
            font=ctk.CTkFont(size=14),
            text_color=Theme.TEXT_MUTED
        ).pack(side='left', pady=15)

        # Lado derecho - Status y hora
        right_header = ctk.CTkFrame(header, fg_color="transparent")
        right_header.pack(side='right', fill='y', padx=20)

        self.lbl_status = ctk.CTkLabel(
            right_header,
            text="● CONECTADO",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Theme.SUCCESS
        )
        self.lbl_status.pack(side='right', pady=20)

        self.lbl_hora = ctk.CTkLabel(
            right_header,
            text="",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=Theme.TEXT
        )
        self.lbl_hora.pack(side='right', padx=20, pady=15)

        self.lbl_contador = ctk.CTkLabel(
            right_header,
            text="0 pedidos",
            font=ctk.CTkFont(size=13),
            text_color=Theme.TEXT_MUTED
        )
        self.lbl_contador.pack(side='right', padx=10, pady=15)

        # Container principal con scroll
        self.container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.container.pack(fill='both', expand=True, padx=20, pady=20)

        # Scrollable frame para pedidos
        self.pedidos_scroll = ctk.CTkScrollableFrame(self.container, fg_color="transparent")
        self.pedidos_scroll.pack(fill='both', expand=True)

        # Configurar columnas del grid
        for col in range(self.COLUMNS):
            self.pedidos_scroll.columnconfigure(col, weight=1, uniform='card')

    def _iniciar_actualizacion(self):
        """Iniciar hilo de actualizacion automatica"""
        def actualizar():
            while self.running:
                try:
                    self._cargar_pedidos_async()
                    self._actualizar_hora()
                except Exception as e:
                    print(f"Error: {e}")
                time.sleep(5)

        self.thread = threading.Thread(target=actualizar, daemon=True)
        self.thread.start()

        # Actualizar hora inmediatamente
        self._actualizar_hora()

    def _cargar_pedidos_async(self):
        """Cargar pedidos en hilo de background (llamada de red)"""
        pedidos = self.api.obtener_pedidos_cocina()

        if isinstance(pedidos, list):
            if self.primera_carga:
                for pedido in pedidos:
                    pedido_id = pedido.get('id')
                    estado = pedido.get('estado')
                    if pedido_id:
                        self.pedidos_impresos.add(pedido_id)
                        if self.auto_print and estado == 'pendiente':
                            self._imprimir_pedido(pedido)
                self.primera_carga = False
            else:
                for pedido in pedidos:
                    pedido_id = pedido.get('id')
                    estado = pedido.get('estado')
                    if pedido_id and pedido_id not in self.pedidos_impresos:
                        if self.auto_print and estado == 'pendiente':
                            self.pedidos_impresos.add(pedido_id)
                            self._imprimir_pedido(pedido)

            self.root.after(0, lambda p=pedidos: self._mostrar_pedidos(p))
            self.root.after(0, lambda: self.lbl_status.configure(text="● CONECTADO", text_color=Theme.SUCCESS))
            self.root.after(0, lambda p=pedidos: self.lbl_contador.configure(text=f"{len(p)} pedido{'s' if len(p) != 1 else ''}"))
        else:
            self.root.after(0, lambda: self.lbl_status.configure(text="● SIN CONEXION", text_color=Theme.DANGER))
            self.root.after(0, lambda: self.lbl_contador.configure(text="Error"))

    def _actualizar_hora(self):
        """Actualizar reloj en formato 12h"""
        now = datetime.now()
        h = now.hour
        m = now.minute
        s = now.second
        am_pm = 'AM' if h < 12 else 'PM'
        if h == 0:
            h = 12
        elif h > 12:
            h = h - 12
        hora = f"{h}:{m:02d}:{s:02d} {am_pm}"
        self.root.after(0, lambda: self.lbl_hora.configure(text=hora))

    def _imprimir_pedido(self, pedido):
        """Imprimir ticket de pedido automaticamente"""

        def limpiar_texto(texto):
            if not texto:
                return ''
            texto = re.sub(r'[\U0001F600-\U0001F64F]', '', texto)
            texto = re.sub(r'[\U0001F300-\U0001F5FF]', '', texto)
            texto = re.sub(r'[\U0001F680-\U0001F6FF]', '', texto)
            texto = re.sub(r'[\U0001F900-\U0001F9FF]', '', texto)
            texto = re.sub(r'[\U00002600-\U000026FF]', '', texto)
            texto = re.sub(r'[\U00002700-\U000027BF]', '', texto)
            reemplazos = {'á':'a','é':'e','í':'i','ó':'o','ú':'u',
                         'Á':'A','É':'E','Í':'I','Ó':'O','Ú':'U',
                         'ñ':'n','Ñ':'N','ü':'u','Ü':'U'}
            for orig, remp in reemplazos.items():
                texto = texto.replace(orig, remp)
            return texto.strip()

        def imprimir_async():
            try:
                tienda_nombre = self.api.tienda.get('nombre', 'Restaurante')
                pedido_id = pedido.get('numero_orden') or pedido.get('id')
                fecha = datetime.now().strftime('%d/%m/%Y')
                hora = datetime.now().strftime('%H:%M')

                ESC = chr(27)
                GS = chr(29)
                LF = chr(10)
                INIT = ESC + "@"
                CENTER = ESC + "a" + chr(1)
                LEFT = ESC + "a" + chr(0)
                BOLD_ON = ESC + "E" + chr(1)
                BOLD_OFF = ESC + "E" + chr(0)
                DOUBLE = GS + "!" + chr(17)
                DOBLE_ALTO = GS + "!" + chr(16)
                NORMAL = GS + "!" + chr(0)
                CUT = GS + "V" + chr(66) + chr(3)

                texto = ""
                texto += INIT
                texto += CENTER
                texto += BOLD_ON + DOUBLE
                texto += limpiar_texto(tienda_nombre.upper()) + LF
                texto += NORMAL + BOLD_OFF
                texto += "COMANDA DE COCINA" + LF
                texto += "================================" + LF
                texto += LF
                texto += BOLD_ON + DOUBLE
                texto += f"PEDIDO #{pedido_id}" + LF
                texto += NORMAL + BOLD_OFF
                texto += LF
                texto += "================================" + LF
                texto += BOLD_ON
                texto += "  PREPARAR INMEDIATAMENTE" + LF
                texto += BOLD_OFF
                texto += "================================" + LF
                texto += LF
                texto += LEFT

                texto += f"Fecha: {fecha}" + LF
                texto += f"Hora:  {hora}" + LF

                cliente = pedido.get('cliente_nombre') or 'N/A'
                texto += f"Cliente: {limpiar_texto(cliente)}" + LF

                telefono = pedido.get('cliente_telefono') or 'N/A'
                texto += f"Tel: {telefono}" + LF

                direccion = pedido.get('direccion_entrega') or ''
                if direccion:
                    texto += f"Dir: {limpiar_texto(direccion)}" + LF

                tipo = pedido.get('tipo', 'local').upper()
                texto += f"Tipo: {tipo}" + LF
                texto += LF

                texto += "--------------------------------" + LF
                texto += CENTER
                texto += BOLD_ON + "ITEMS DEL PEDIDO" + BOLD_OFF + LF
                texto += "--------------------------------" + LF
                texto += LEFT
                texto += LF

                items = pedido.get('items') or pedido.get('detalles') or []

                for item in items:
                    cantidad = item.get('cantidad', 1)
                    nombre = item.get('producto_nombre') or item.get('nombre') or 'Producto'
                    nombre = limpiar_texto(nombre)

                    texto += BOLD_ON + DOUBLE
                    texto += f"{cantidad}x {nombre}" + LF
                    texto += NORMAL + BOLD_OFF

                    notas_item = item.get('notas') or ''
                    if notas_item and notas_item.strip():
                        texto += BOLD_ON + DOBLE_ALTO
                        texto += f">> {limpiar_texto(notas_item)}" + LF
                        texto += NORMAL + BOLD_OFF

                    texto += LF

                total = pedido.get('total', 0)
                try:
                    total = float(total)
                except:
                    total = 0
                texto += "--------------------------------" + LF
                texto += BOLD_ON + DOUBLE
                texto += f"TOTAL: ${total:,.0f}" + LF
                texto += NORMAL + BOLD_OFF
                texto += "--------------------------------" + LF

                notas = pedido.get('notas') or ''
                if notas and notas.strip():
                    texto += LF
                    texto += BOLD_ON + DOBLE_ALTO
                    texto += "NOTAS:" + LF
                    texto += limpiar_texto(notas) + LF
                    texto += NORMAL + BOLD_OFF

                texto += LF
                texto += CENTER
                texto += "Verificar items antes de entregar" + LF
                texto += "================================" + LF
                texto += LF + LF + LF
                texto += CUT

                carpeta = "C:\\fast_comandas\\"
                if not os.path.exists(carpeta):
                    os.makedirs(carpeta, exist_ok=True)

                archivo = os.path.join(carpeta, f"comanda_{pedido_id}.txt")
                with open(archivo, 'w', encoding='latin-1', errors='replace') as f:
                    f.write(texto)

                impreso = False

                try:
                    import win32print
                    printer_name = win32print.GetDefaultPrinter()
                    hPrinter = win32print.OpenPrinter(printer_name)
                    try:
                        hJob = win32print.StartDocPrinter(hPrinter, 1, (f"Comanda_{pedido_id}", None, "RAW"))
                        try:
                            win32print.StartPagePrinter(hPrinter)
                            win32print.WritePrinter(hPrinter, texto.encode('latin-1', errors='replace'))
                            win32print.EndPagePrinter(hPrinter)
                        finally:
                            win32print.EndDocPrinter(hPrinter)
                    finally:
                        win32print.ClosePrinter(hPrinter)
                    impreso = True
                except:
                    pass

                if not impreso:
                    try:
                        raw_file = os.path.join(carpeta, f"raw_{pedido_id}.prn")
                        with open(raw_file, 'wb') as f:
                            f.write(texto.encode('latin-1', errors='replace'))
                        result = subprocess.run(
                            ['powershell', '-Command',
                             f'Get-Content -Path "{raw_file}" -Encoding Byte -Raw | Out-Printer'],
                            capture_output=True, text=True, timeout=10
                        )
                        if result.returncode == 0:
                            impreso = True
                    except:
                        pass

                if not impreso:
                    try:
                        import win32api
                        temp_path = os.path.join(os.environ.get('TEMP', '.'), f'ticket_{pedido.get("id", "0")}.txt')
                        ticket_simple = []
                        ticket_simple.append("=" * 40)
                        ticket_simple.append(f"  {limpiar_texto(tienda_nombre.upper())}")
                        ticket_simple.append("  COMANDA DE COCINA")
                        ticket_simple.append("=" * 40)
                        ticket_simple.append(f"  PEDIDO #{pedido_id}")
                        ticket_simple.append("================================")
                        ticket_simple.append("  PREPARAR INMEDIATAMENTE")
                        ticket_simple.append("================================")
                        ticket_simple.append(f"Fecha: {fecha}")
                        ticket_simple.append(f"Hora:  {hora}")
                        ticket_simple.append(f"Cliente: {limpiar_texto(cliente)}")
                        for item in items:
                            cantidad = item.get('cantidad', 1)
                            nombre = item.get('producto_nombre') or item.get('nombre') or 'Producto'
                            notas_item = item.get('notas', '')
                            if notas_item and not notas_item.startswith('[OFERTA]'):
                                nombre = f"{nombre} - {notas_item}"
                            ticket_simple.append(f"  {cantidad}x {limpiar_texto(nombre)}")
                        ticket_simple.append(f"  TOTAL: ${total:,.0f}")
                        ticket_simple.append("================================")
                        with open(temp_path, 'w', encoding='utf-8') as f:
                            f.write('\n'.join(ticket_simple))
                        win32api.ShellExecute(0, "print", temp_path, None, ".", 0)
                    except:
                        pass

            except Exception as e:
                print(f"[PRINT ERROR] Error al imprimir: {e}")

        threading.Thread(target=imprimir_async, daemon=True).start()

    def _mostrar_pedidos(self, pedidos):
        """Mostrar pedidos en la interfaz"""
        for widget in self.pedidos_scroll.winfo_children():
            widget.destroy()

        if not pedidos:
            lbl = ctk.CTkLabel(
                self.pedidos_scroll,
                text="No hay pedidos pendientes",
                font=ctk.CTkFont(size=20),
                text_color=Theme.TEXT_MUTED
            )
            lbl.grid(row=0, column=0, columnspan=self.COLUMNS, padx=50, pady=100)
            return

        for idx, pedido in enumerate(pedidos):
            row = idx // self.COLUMNS
            col = idx % self.COLUMNS
            self._crear_tarjeta_pedido(pedido, row, col)

    def _crear_tarjeta_pedido(self, pedido, row, col):
        """Crear tarjeta visual para un pedido"""
        estado = pedido.get('estado', 'pendiente')

        estado_colors = {
            'pendiente': {'accent': '#dc2626', 'badge_bg': '#fef2f2', 'badge_text': '#dc2626'},
            'preparando': {'accent': '#f59e0b', 'badge_bg': '#fffbeb', 'badge_text': '#d97706'},
            'listo': {'accent': '#16a34a', 'badge_bg': '#f0fdf4', 'badge_text': '#16a34a'}
        }
        colors = estado_colors.get(estado, estado_colors['pendiente'])

        # Card container
        card = ctk.CTkFrame(self.pedidos_scroll, fg_color=Theme.CARD_BG, corner_radius=12)
        card.grid(row=row, column=col, padx=8, pady=8, sticky='nsew')

        # Borde de color segun estado
        accent_bar = ctk.CTkFrame(card, fg_color=colors['accent'], height=4, corner_radius=0)
        accent_bar.pack(fill='x')

        # Header
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill='x', padx=12, pady=(10, 5))

        ctk.CTkLabel(
            header,
            text=f"#{pedido.get('numero_orden', pedido['id'])}",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=Theme.TEXT
        ).pack(side='left')

        tipo = pedido.get('tipo', 'local').upper()
        tipo_bg = '#3b82f6' if tipo == 'DOMICILIO' else '#8b5cf6'
        ctk.CTkLabel(
            header,
            text=tipo[:3],
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=tipo_bg,
            text_color="white",
            corner_radius=4,
            width=35,
            height=22
        ).pack(side='right')

        # Badge estado
        estado_frame = ctk.CTkFrame(card, fg_color="transparent")
        estado_frame.pack(fill='x', padx=12, pady=(0, 8))

        ctk.CTkLabel(
            estado_frame,
            text=estado.upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=colors['badge_bg'],
            text_color=colors['badge_text'],
            corner_radius=4,
            width=80,
            height=22
        ).pack(side='left')

        hora = convertir_hora_utc_a_colombia(pedido.get('fecha_hora', ''))
        if hora:
            ctk.CTkLabel(estado_frame, text=hora, font=ctk.CTkFont(size=11), text_color=Theme.TEXT_MUTED).pack(side='right')

        # Separador
        ctk.CTkFrame(card, fg_color=Theme.BORDER, height=1).pack(fill='x', padx=12)

        # Items del pedido
        items_frame = ctk.CTkFrame(card, fg_color="transparent")
        items_frame.pack(fill='both', expand=True, padx=12, pady=8)

        items = pedido.get('items', [])
        for i, item in enumerate(items[:4]):
            item_row = ctk.CTkFrame(items_frame, fg_color="transparent")
            item_row.pack(fill='x', pady=2)

            cantidad = item.get('cantidad', 1)
            nombre = item.get('producto_nombre', 'N/A')
            notas_item = item.get('notas', '')
            if notas_item and not notas_item.startswith('[OFERTA]'):
                nombre = f"{nombre} - {notas_item}"
            if len(nombre) > 25:
                nombre = nombre[:23] + '..'

            ctk.CTkLabel(item_row, text=f"{cantidad}x", font=ctk.CTkFont(size=12, weight="bold"), text_color=colors['accent'], width=30).pack(side='left')
            ctk.CTkLabel(item_row, text=nombre, font=ctk.CTkFont(size=12), text_color=Theme.TEXT).pack(side='left', fill='x')

        if len(items) > 4:
            ctk.CTkLabel(items_frame, text=f"+{len(items) - 4} items mas...", font=ctk.CTkFont(size=10), text_color=Theme.TEXT_MUTED).pack(anchor='w')

        # Notas
        notas = pedido.get('notas', '')
        if notas:
            notas_frame = ctk.CTkFrame(card, fg_color='#fef3c7', corner_radius=6)
            notas_frame.pack(fill='x', padx=12, pady=(0, 8))
            notas_text = notas[:40] + '..' if len(notas) > 40 else notas
            ctk.CTkLabel(notas_frame, text=f"Nota: {notas_text}", font=ctk.CTkFont(size=10), text_color='#92400e').pack(padx=8, pady=4)

        # Botones de accion
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(fill='x', padx=12, pady=(0, 12))

        ctk.CTkButton(
            btn_frame,
            text="VER DETALLES",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=Theme.BORDER,
            hover_color=Theme.HEADER,
            text_color=Theme.TEXT,
            height=32,
            corner_radius=6,
            command=lambda p=pedido: self._mostrar_detalles_pedido(p)
        ).pack(fill='x', pady=(0, 5))

        btn_config = {
            'pendiente': {'text': 'PREPARAR', 'bg': '#f59e0b', 'hover': '#d97706', 'fg': 'black', 'next': 'preparando'},
            'preparando': {'text': 'LISTO', 'bg': '#16a34a', 'hover': '#15803d', 'fg': 'white', 'next': 'listo'},
            'listo': {'text': 'ENTREGADO', 'bg': '#3b82f6', 'hover': '#2563eb', 'fg': 'white', 'next': 'entregado'}
        }
        config = btn_config.get(estado, btn_config['pendiente'])

        ctk.CTkButton(
            btn_frame,
            text=config['text'],
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=config['bg'],
            hover_color=config['hover'],
            text_color=config['fg'],
            height=38,
            corner_radius=6,
            command=lambda p=pedido['id'], s=config['next']: self._cambiar_estado(p, s)
        ).pack(fill='x')

    def _cambiar_estado(self, pedido_id, nuevo_estado):
        """Cambiar estado de un pedido"""
        result = self.api.actualizar_estado_pedido(pedido_id, nuevo_estado)
        if result and result.get('success'):
            self._cargar_pedidos()
        else:
            messagebox.showerror("Error", result.get('error', 'No se pudo actualizar'))

    def _mostrar_detalles_pedido(self, pedido):
        """Mostrar ventana popup con todos los detalles del pedido"""
        popup = ctk.CTkToplevel(self.root)
        popup.title(f"Pedido #{pedido.get('numero_orden', pedido['id'])}")
        popup.geometry("520x680")
        popup.configure(fg_color=Theme.BG)
        popup.transient(self.root)
        popup.grab_set()

        popup.update_idletasks()
        x = (popup.winfo_screenwidth() - 520) // 2
        y = (popup.winfo_screenheight() - 680) // 2
        popup.geometry(f"+{x}+{y}")

        estado = pedido.get('estado', 'pendiente')
        estado_colors = {
            'pendiente': '#dc2626',
            'preparando': '#f59e0b',
            'listo': '#16a34a'
        }
        accent_color = estado_colors.get(estado, '#dc2626')

        # Scrollable content
        content = ctk.CTkScrollableFrame(popup, fg_color="transparent")
        content.pack(fill='both', expand=True, padx=20, pady=20)

        # Header
        header_frame = ctk.CTkFrame(content, fg_color=Theme.CARD_BG, corner_radius=12)
        header_frame.pack(fill='x', pady=(0, 15))

        ctk.CTkFrame(header_frame, fg_color=accent_color, height=5, corner_radius=0).pack(fill='x')

        header_inner = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_inner.pack(fill='x', padx=15, pady=15)

        ctk.CTkLabel(header_inner, text=f"PEDIDO #{pedido.get('numero_orden', pedido['id'])}", font=ctk.CTkFont(size=24, weight="bold"), text_color=Theme.TEXT).pack(anchor='w')

        info_row = ctk.CTkFrame(header_inner, fg_color="transparent")
        info_row.pack(fill='x', pady=(10, 0))

        ctk.CTkLabel(info_row, text=estado.upper(), font=ctk.CTkFont(size=12, weight="bold"), fg_color=accent_color, text_color="white", corner_radius=4, width=90, height=26).pack(side='left')

        tipo = pedido.get('tipo', 'local').upper()
        tipo_bg = '#3b82f6' if tipo == 'DOMICILIO' else '#8b5cf6'
        ctk.CTkLabel(info_row, text=tipo, font=ctk.CTkFont(size=12, weight="bold"), fg_color=tipo_bg, text_color="white", corner_radius=4, width=90, height=26).pack(side='left', padx=(10, 0))

        # Seccion Cliente
        cliente_frame = ctk.CTkFrame(content, fg_color=Theme.CARD_BG, corner_radius=12)
        cliente_frame.pack(fill='x', pady=(0, 15))

        ctk.CTkLabel(cliente_frame, text="CLIENTE", font=ctk.CTkFont(size=13, weight="bold"), text_color=Theme.TEXT_MUTED).pack(anchor='w', padx=15, pady=(15, 5))
        ctk.CTkFrame(cliente_frame, fg_color=Theme.BORDER, height=1).pack(fill='x', padx=15)

        cliente_info = ctk.CTkFrame(cliente_frame, fg_color="transparent")
        cliente_info.pack(fill='x', padx=15, pady=10)

        cliente_nombre = pedido.get('cliente_nombre') or 'N/A'
        ctk.CTkLabel(cliente_info, text=f"Nombre: {cliente_nombre}", font=ctk.CTkFont(size=14), text_color=Theme.TEXT).pack(anchor='w', pady=2)

        cliente_tel = pedido.get('cliente_telefono') or 'N/A'
        ctk.CTkLabel(cliente_info, text=f"Telefono: {cliente_tel}", font=ctk.CTkFont(size=14), text_color=Theme.TEXT).pack(anchor='w', pady=2)

        if tipo == 'DOMICILIO':
            direccion = pedido.get('direccion_entrega') or 'N/A'
            ctk.CTkLabel(cliente_info, text=f"Direccion: {direccion}", font=ctk.CTkFont(size=14), text_color=Theme.TEXT, wraplength=400).pack(anchor='w', pady=2)

        hora = convertir_hora_utc_a_colombia(pedido.get('fecha_hora', ''))
        if hora:
            ctk.CTkLabel(cliente_info, text=f"Hora: {hora}", font=ctk.CTkFont(size=14), text_color=Theme.TEXT).pack(anchor='w', pady=2)

        # Seccion Items
        items_section = ctk.CTkFrame(content, fg_color=Theme.CARD_BG, corner_radius=12)
        items_section.pack(fill='x', pady=(0, 15))

        ctk.CTkLabel(items_section, text="ITEMS DEL PEDIDO", font=ctk.CTkFont(size=13, weight="bold"), text_color=Theme.TEXT_MUTED).pack(anchor='w', padx=15, pady=(15, 5))
        ctk.CTkFrame(items_section, fg_color=Theme.BORDER, height=1).pack(fill='x', padx=15)

        items_list = ctk.CTkFrame(items_section, fg_color="transparent")
        items_list.pack(fill='x', padx=15, pady=10)

        items = pedido.get('items') or pedido.get('detalles') or []
        for item in items:
            item_frame = ctk.CTkFrame(items_list, fg_color="transparent")
            item_frame.pack(fill='x', pady=5)

            cantidad = item.get('cantidad', 1)
            nombre = item.get('producto_nombre') or item.get('nombre') or 'Producto'
            notas_item = item.get('notas') or ''
            if notas_item and not notas_item.startswith('[OFERTA]'):
                nombre = f"{nombre} - {notas_item}"
            precio = float(item.get('precio_unitario', 0) or 0)

            ctk.CTkLabel(item_frame, text=f"{cantidad}x", font=ctk.CTkFont(size=15, weight="bold"), text_color=accent_color).pack(side='left')
            ctk.CTkLabel(item_frame, text=f" {nombre}", font=ctk.CTkFont(size=15), text_color=Theme.TEXT).pack(side='left')
            ctk.CTkLabel(item_frame, text=f"${precio:,.0f}", font=ctk.CTkFont(size=13), text_color=Theme.TEXT_MUTED).pack(side='right')

        # Total
        total_frame = ctk.CTkFrame(items_section, fg_color=Theme.HEADER, corner_radius=8)
        total_frame.pack(fill='x', padx=15, pady=(5, 15))

        total = pedido.get('total', 0)
        ctk.CTkLabel(total_frame, text=f"TOTAL: ${total:,.0f}", font=ctk.CTkFont(size=18, weight="bold"), text_color=Theme.TEXT).pack(anchor='e', padx=15, pady=10)

        # Notas generales
        notas = pedido.get('notas') or ''
        if notas and notas.strip():
            notas_section = ctk.CTkFrame(content, fg_color='#fef3c7', corner_radius=12)
            notas_section.pack(fill='x', pady=(0, 15))

            ctk.CTkLabel(notas_section, text="NOTAS DEL PEDIDO", font=ctk.CTkFont(size=12, weight="bold"), text_color='#92400e').pack(anchor='w', padx=15, pady=(10, 5))
            ctk.CTkLabel(notas_section, text=notas, font=ctk.CTkFont(size=13), text_color='#92400e', wraplength=430).pack(anchor='w', padx=15, pady=(0, 10))

        # Boton cerrar
        ctk.CTkButton(content, text="CERRAR", font=ctk.CTkFont(size=13, weight="bold"), fg_color=Theme.BORDER, hover_color=Theme.HEADER, text_color=Theme.TEXT, height=45, corner_radius=8, command=popup.destroy).pack(fill='x', pady=(10, 0))

    def on_closing(self):
        """Manejar cierre de ventana"""
        self.running = False
        self.root.destroy()


def check_updates_on_start():
    """Verificar actualizaciones antes de iniciar"""
    try:
        from updater import check_and_update
        check_and_update()
    except ImportError:
        print("[UPDATE] Modulo updater no encontrado, continuando sin verificar")
    except Exception as e:
        print(f"[UPDATE] Error verificando actualizaciones: {e}")


def main():
    """Punto de entrada principal"""
    check_updates_on_start()

    def on_login(api):
        # Crear nueva ventana principal para la app de cocina
        cocina_root = ctk.CTk()
        app = CocinaApp(cocina_root, api)
        cocina_root.protocol("WM_DELETE_WINDOW", app.on_closing)
        cocina_root.mainloop()

    # Ventana de login
    login_root = ctk.CTk()
    LoginWindow(login_root, on_login)
    login_root.mainloop()


if __name__ == '__main__':
    main()
