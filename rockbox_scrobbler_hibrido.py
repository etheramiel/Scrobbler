#!/usr/bin/env python3
"""
Rockbox Scrobbler to Last.fm - Versión Híbrida
- Para desarrollo: usa .env
- Para distribución: API keys embebidas, login en la app
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pylast
import os
import threading
from datetime import datetime, timedelta
import json

# =============================================================================
# CONFIGURACIÓN DE API
# =============================================================================
# MODO 1: Intentar cargar desde .env (para desarrollo)
try:
    from dotenv import load_dotenv
    load_dotenv()
    API_KEY = os.getenv('LASTFM_API_KEY', '')
    API_SECRET = os.getenv('LASTFM_API_SECRET', '')
    DEFAULT_USERNAME = os.getenv('LASTFM_USERNAME', '')
    DEFAULT_PASSWORD = os.getenv('LASTFM_PASSWORD', '')
except ImportError:
    # python-dotenv no está instalado (modo ejecutable)
    API_KEY = ''
    API_SECRET = ''
    DEFAULT_USERNAME = ''
    DEFAULT_PASSWORD = ''

# MODO 2: API keys embebidas (para distribución compilada)
# Si las de arriba están vacías, usa estas
if not API_KEY or API_KEY == 'TU_API_KEY_AQUI':
    # INSTRUCCIONES PARA COMPILAR:
    # 1. Ejecuta: python encode_keys.py
    # 2. Pega el código que te da aquí abajo:
    
    # import base64
    # _config = base64.b64decode(b'PEGA_TU_CODIGO_AQUI').decode()
    # _parts = _config.split('|')
    # API_KEY = _parts[0]
    # API_SECRET = _parts[1]
    
    # Por ahora (sin compilar), pon tus keys directamente:
    API_KEY = "TU_API_KEY_AQUI"
    API_SECRET = "TU_API_SECRET_AQUI"

# Archivo para guardar sesión del usuario
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".rockbox_scrobbler_session.json")

# =============================================================================
# FUNCIONES DE SESIÓN
# =============================================================================

def save_session(username, password):
    """Guarda la sesión del usuario localmente"""
    config = {
        'username': username,
        'password': password  # En producción podrías hashear esto
    }
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
    except:
        pass


def load_session():
    """Carga la sesión guardada"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return None
    return None


def clear_session():
    """Elimina la sesión guardada"""
    if os.path.exists(CONFIG_FILE):
        try:
            os.remove(CONFIG_FILE)
        except:
            pass


# =============================================================================
# FUNCIONES DE PROCESAMIENTO
# =============================================================================

def adjust_timestamp(timestamp, hours_offset):
    """Ajusta el timestamp sumando/restando horas"""
    return timestamp + (hours_offset * 3600)


def adjust_old_scrobbles(scrobbles, two_weeks_limit):
    """
    Ajusta scrobbles antiguos para que quepan dentro del límite de 2 semanas.
    Mantiene el orden relativo y la hora del día.
    """
    adjusted = []
    old_scrobbles = []
    
    for scrobble in scrobbles:
        scrobble_date = datetime.fromtimestamp(scrobble['timestamp'])
        if scrobble_date < two_weeks_limit:
            old_scrobbles.append(scrobble)
        else:
            adjusted.append(scrobble)
    
    if not old_scrobbles:
        return adjusted, 0
    
    old_scrobbles.sort(key=lambda x: x['timestamp'])
    
    oldest_date = datetime.fromtimestamp(old_scrobbles[0]['timestamp'])
    newest_old_date = datetime.fromtimestamp(old_scrobbles[-1]['timestamp'])
    original_span = (newest_old_date - oldest_date).total_seconds()
    
    limit_date = two_weeks_limit
    
    for i, scrobble in enumerate(old_scrobbles):
        original_date = datetime.fromtimestamp(scrobble['timestamp'])
        
        if original_span > 0:
            proportion = (scrobble['timestamp'] - old_scrobbles[0]['timestamp']) / original_span
            available_span = (datetime.now() - limit_date).total_seconds()
            new_offset = proportion * available_span
            new_timestamp = int(limit_date.timestamp() + new_offset)
        else:
            days_span = 13
            interval = (days_span * 24 * 3600) / len(old_scrobbles) if len(old_scrobbles) > 1 else 0
            new_timestamp = int(limit_date.timestamp() + (i * interval))
        
        original_time = original_date.time()
        new_date = datetime.fromtimestamp(new_timestamp)
        new_date = new_date.replace(
            hour=original_time.hour,
            minute=original_time.minute,
            second=original_time.second
        )
        
        adjusted_scrobble = scrobble.copy()
        adjusted_scrobble['timestamp'] = int(new_date.timestamp())
        adjusted_scrobble['date_str'] = new_date.strftime('%Y-%m-%d %H:%M:%S')
        adjusted_scrobble['was_adjusted'] = True
        adjusted_scrobble['original_date'] = original_date.strftime('%Y-%m-%d %H:%M:%S')
        
        adjusted.append(adjusted_scrobble)
    
    return adjusted, len(old_scrobbles)


def parse_scrobbler_log(filepath, timezone_offset=0):
    """Parsea el archivo .scrobbler.log de Rockbox"""
    scrobbles = []
    
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            if not line:
                continue
            
            parts = line.split('\t')
            
            if len(parts) < 7:
                continue
            
            artist = parts[0].strip()
            album = parts[1].strip()
            track = parts[2].strip()
            timestamp = parts[6].strip()
            
            if not artist or not track:
                continue
            
            try:
                timestamp_int = int(timestamp)
                
                if timezone_offset != 0:
                    timestamp_int = adjust_timestamp(timestamp_int, timezone_offset)
                
                scrobble_date = datetime.fromtimestamp(timestamp_int)
                
            except ValueError:
                continue
            
            scrobbles.append({
                'artist': artist,
                'title': track,
                'album': album if album else '',
                'timestamp': timestamp_int,
                'date_str': scrobble_date.strftime('%Y-%m-%d %H:%M:%S'),
                'was_adjusted': False
            })
    
    return scrobbles


# =============================================================================
# INTERFAZ GRÁFICA
# =============================================================================

class ScrobblerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Rockbox Scrobbler to Last.fm")
        self.root.geometry("1200x800")
        
        self.scrobbles = []
        self.tree_items = {}
        self.network = None
        self.username = DEFAULT_USERNAME
        self.password = DEFAULT_PASSWORD
        self.timezone_offset = 0
        self.logged_in = False
        
        # Verificar configuración de API
        if not API_KEY or API_KEY == 'TU_API_KEY_AQUI':
            messagebox.showerror(
                "Error de Configuración",
                "Esta aplicación no está configurada correctamente.\n\n"
                "Para desarrollo: Crea un archivo .env con tus credenciales\n"
                "Para distribución: Usa encode_keys.py para embeber las API keys"
            )
            self.root.quit()
            return
        
        self.create_widgets()
        
        # Intentar cargar sesión guardada o usar .env
        session = load_session()
        if session:
            self.username = session.get('username', '')
            self.password = session.get('password', '')
        
        # Si hay credenciales, intentar login automático
        if self.username and self.password:
            self.root.after(100, self.try_auto_login)
        else:
            self.root.after(100, self.show_login_dialog)
    
    def create_widgets(self):
        # Frame superior - Info de usuario
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        
        user_frame = ttk.Frame(top_frame)
        user_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(user_frame, text="Usuario Last.fm:").pack(side=tk.LEFT, padx=5)
        self.user_label = ttk.Label(user_frame, text="No autenticado", font=('Arial', 10, 'bold'))
        self.user_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(user_frame, text="Cambiar cuenta", command=self.show_login_dialog).pack(side=tk.LEFT, padx=20)
        
        # Frame de configuración de zona horaria
        tz_frame = ttk.Frame(top_frame)
        tz_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(tz_frame, text="Ajuste de hora del iPod:").pack(side=tk.LEFT, padx=5)
        ttk.Label(tz_frame, text="Si tu iPod está desfasado, ajusta las horas aquí").pack(side=tk.LEFT, padx=5)
        
        self.tz_var = tk.IntVar(value=0)
        tz_spinbox = ttk.Spinbox(tz_frame, from_=-12, to=12, textvariable=self.tz_var, width=10)
        tz_spinbox.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(tz_frame, text="horas").pack(side=tk.LEFT, padx=2)
        
        ttk.Button(tz_frame, text="Aplicar", command=self.apply_timezone).pack(side=tk.LEFT, padx=5)
        
        self.example_label = ttk.Label(tz_frame, text="(Sin ajuste)", foreground='gray')
        self.example_label.pack(side=tk.LEFT, padx=10)
        
        # Selección de archivo
        file_frame = ttk.Frame(top_frame)
        file_frame.pack(fill=tk.X)
        
        ttk.Label(file_frame, text="Archivo .scrobbler.log:").pack(side=tk.LEFT, padx=5)
        
        self.file_entry = ttk.Entry(file_frame, width=50)
        self.file_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Button(file_frame, text="Seleccionar archivo", command=self.select_file).pack(side=tk.LEFT, padx=5)
        
        # Advertencia
        warning_frame = ttk.Frame(self.root, padding="10")
        warning_frame.pack(fill=tk.X)
        
        warning_text = ("NOTA: Last.fm solo acepta scrobbles de las últimas 2 semanas. "
                       "Las canciones más antiguas se ajustarán automáticamente manteniendo el orden y la hora.")
        ttk.Label(warning_frame, text=warning_text, foreground='blue', wraplength=1150).pack()
        
        # Botones de selección
        middle_frame = ttk.Frame(self.root, padding="10")
        middle_frame.pack(fill=tk.X)
        
        ttk.Button(middle_frame, text="Seleccionar todas", command=self.select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(middle_frame, text="Deseleccionar todas", command=self.deselect_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(middle_frame, text="Invertir selección", command=self.invert_selection).pack(side=tk.LEFT, padx=5)
        
        self.count_label = ttk.Label(middle_frame, text="Canciones: 0 | Seleccionadas: 0")
        self.count_label.pack(side=tk.RIGHT, padx=5)
        
        # Tabla
        table_frame = ttk.Frame(self.root, padding="10")
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("Artista", "Canción", "Álbum", "Fecha Original", "Fecha a Scrobblear")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="tree headings", selectmode="extended")
        
        self.tree.column("#0", width=30, minwidth=30, stretch=False)
        self.tree.column("Artista", width=180, minwidth=120)
        self.tree.column("Canción", width=200, minwidth=120)
        self.tree.column("Álbum", width=180, minwidth=100)
        self.tree.column("Fecha Original", width=150, minwidth=130)
        self.tree.column("Fecha a Scrobblear", width=150, minwidth=130)
        
        self.tree.heading("#0", text="☑")
        self.tree.heading("Artista", text="Artista")
        self.tree.heading("Canción", text="Canción")
        self.tree.heading("Álbum", text="Álbum")
        self.tree.heading("Fecha Original", text="Fecha Original")
        self.tree.heading("Fecha a Scrobblear", text="Fecha a Scrobblear")
        
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        self.tree.bind("<Button-1>", self.on_tree_click)
        self.tree.bind("<space>", self.on_space_press)
        
        # Log
        bottom_frame = ttk.Frame(self.root, padding="10")
        bottom_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(bottom_frame, text="Log de importación:").pack(anchor=tk.W)
        
        self.log_text = scrolledtext.ScrolledText(bottom_frame, height=6, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        action_frame = ttk.Frame(bottom_frame)
        action_frame.pack(fill=tk.X)
        
        self.import_button = ttk.Button(action_frame, text="Importar a Last.fm", command=self.start_import)
        self.import_button.pack(side=tk.LEFT, padx=5)
        
        self.progress = ttk.Progressbar(action_frame, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.status_label = ttk.Label(action_frame, text="Listo")
        self.status_label.pack(side=tk.LEFT, padx=5)
    
    def try_auto_login(self):
        """Intenta login automático con credenciales guardadas"""
        if self.username and self.password:
            try:
                self.log("Iniciando sesión...")
                password_hash = pylast.md5(self.password)
                self.network = pylast.LastFMNetwork(
                    api_key=API_KEY,
                    api_secret=API_SECRET,
                    username=self.username,
                    password_hash=password_hash
                )
                
                # Verificar conexión
                user = self.network.get_user(self.username)
                user.get_name()
                
                self.logged_in = True
                self.update_user_status()
                self.log(f"Sesión iniciada como: {self.username}")
                
            except Exception as e:
                self.log(f"Error en login automático: {str(e)}")
                self.show_login_dialog()
    
    def show_login_dialog(self):
        """Muestra diálogo de login"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Iniciar sesión en Last.fm")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Centrar
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 250
        y = (dialog.winfo_screenheight() // 2) - 150
        dialog.geometry(f"+{x}+{y}")
        
        dialog.resizable(False, False)
        
        main_frame = ttk.Frame(dialog, padding="30")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        ttk.Label(main_frame, text="Iniciar sesión en Last.fm", 
                 font=('Arial', 14, 'bold')).pack(pady=(0, 20))
        
        # Instrucciones
        instructions = ttk.Label(main_frame, 
                                text="Ingresa tu usuario y contraseña de Last.fm",
                                foreground='gray')
        instructions.pack(pady=(0, 15))
        
        # Frame para campos
        fields_frame = ttk.Frame(main_frame)
        fields_frame.pack(fill=tk.X, pady=10)
        
        # Usuario
        user_frame = ttk.Frame(fields_frame)
        user_frame.pack(fill=tk.X, pady=8)
        
        ttk.Label(user_frame, text="Usuario:", width=12, anchor='e').pack(side=tk.LEFT, padx=(0,10))
        user_entry = ttk.Entry(user_frame, width=30)
        user_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        user_entry.insert(0, self.username if self.username else '')
        
        # Contraseña
        pass_frame = ttk.Frame(fields_frame)
        pass_frame.pack(fill=tk.X, pady=8)
        
        ttk.Label(pass_frame, text="Contraseña:", width=12, anchor='e').pack(side=tk.LEFT, padx=(0,10))
        pass_entry = ttk.Entry(pass_frame, show="●", width=30)
        pass_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        pass_entry.insert(0, self.password if self.password else '')
        
        # Checkbox recordar
        remember_var = tk.BooleanVar(value=True)
        remember_check = ttk.Checkbutton(fields_frame, 
                                        text="Recordar mis credenciales en este equipo",
                                        variable=remember_var)
        remember_check.pack(pady=10)
        
        # Mensaje de estado
        status_label = ttk.Label(main_frame, text="", foreground='red')
        status_label.pack(pady=10)
        
        def do_login():
            username = user_entry.get().strip()
            password = pass_entry.get().strip()
            
            if not username or not password:
                status_label.config(text="Completa todos los campos")
                return
            
            try:
                status_label.config(text="Conectando con Last.fm...", foreground='blue')
                dialog.update()
                
                password_hash = pylast.md5(password)
                network = pylast.LastFMNetwork(
                    api_key=API_KEY,
                    api_secret=API_SECRET,
                    username=username,
                    password_hash=password_hash
                )
                
                # Verificar
                user = network.get_user(username)
                user.get_name()
                
                self.network = network
                self.username = username
                self.password = password
                self.logged_in = True
                
                # Guardar si el usuario quiere
                if remember_var.get():
                    save_session(username, password)
                
                self.update_user_status()
                dialog.destroy()
                
                messagebox.showinfo("Sesión iniciada", 
                                  f"Bienvenido, {username}!\n\nYa puedes importar tus scrobbles.")
                
            except pylast.WSError as e:
                if 'Invalid username or password' in str(e) or e.status == 4:
                    status_label.config(text="Usuario o contraseña incorrectos", foreground='red')
                else:
                    status_label.config(text=f"Error: {str(e)}", foreground='red')
            except Exception as e:
                status_label.config(text=f"Error de conexión: {str(e)}", foreground='red')
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Iniciar sesión", command=do_login, width=15).pack(side=tk.LEFT, padx=5)
        
        cancel_btn = ttk.Button(button_frame, text="Cancelar", width=15,
                               command=lambda: [dialog.destroy(), 
                                              self.root.quit() if not self.logged_in else None])
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Enter para login
        pass_entry.bind('<Return>', lambda e: do_login())
        user_entry.bind('<Return>', lambda e: pass_entry.focus())
        
        # Focus en usuario
        user_entry.focus()
    
    def update_user_status(self):
        if self.logged_in and self.username:
            self.user_label.config(text=f"{self.username}", foreground='green')
        else:
            self.user_label.config(text="No autenticado", foreground='red')
    
    def update_timezone_example(self):
        offset = self.tz_var.get()
        if offset > 0:
            example_time = 18 + offset
            if example_time >= 24:
                example_time -= 24
            self.example_label.config(text=f"(Ej: iPod 18:30 → Real {example_time:02d}:30)")
        elif offset < 0:
            example_time = 18 + offset
            if example_time < 0:
                example_time += 24
            self.example_label.config(text=f"(Ej: iPod 18:30 → Real {example_time:02d}:30)")
        else:
            self.example_label.config(text="(Sin ajuste)")
    
    def apply_timezone(self):
        self.timezone_offset = self.tz_var.get()
        self.update_timezone_example()
        
        filepath = self.file_entry.get()
        if filepath and os.path.exists(filepath):
            self.load_scrobbles(filepath)
            messagebox.showinfo("Ajuste aplicado", 
                              f"Se ajustaron {abs(self.timezone_offset)} horas {'adelante' if self.timezone_offset > 0 else 'atrás'}")
    
    def select_file(self):
        filename = filedialog.askopenfilename(
            title="Seleccionar archivo .scrobbler.log",
            filetypes=[("Scrobbler Log", "*.log"), ("Todos los archivos", "*.*")]
        )
        
        if filename:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filename)
            self.load_scrobbles(filename)
    
    def load_scrobbles(self, filepath):
        try:
            self.log("Leyendo archivo...")
            
            raw_scrobbles = parse_scrobbler_log(filepath, self.timezone_offset)
            
            if not raw_scrobbles:
                messagebox.showwarning("Advertencia", "No se encontraron scrobbles válidos")
                return
            
            two_weeks_ago = datetime.now() - timedelta(days=14)
            adjusted_scrobbles, adjusted_count = adjust_old_scrobbles(raw_scrobbles, two_weeks_ago)
            
            self.scrobbles = adjusted_scrobbles
            
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            self.tree_items.clear()
            
            for idx, scrobble in enumerate(self.scrobbles):
                original_date = scrobble.get('original_date', scrobble['date_str'])
                scrobble_date = scrobble['date_str']
                
                tags = ("checked",)
                if scrobble.get('was_adjusted'):
                    tags = ("checked", "adjusted")
                
                item_id = self.tree.insert("", "end", text="☑", values=(
                    scrobble['artist'],
                    scrobble['title'],
                    scrobble['album'],
                    original_date,
                    scrobble_date
                ), tags=tags)
                self.tree_items[item_id] = idx
            
            self.tree.tag_configure("adjusted", foreground='orange')
            
            self.update_count()
            self.log(f"Cargadas {len(self.scrobbles)} canciones")
            
            if adjusted_count > 0:
                self.log(f"Ajustadas {adjusted_count} canciones antiguas (naranja)")
                messagebox.showinfo("Canciones ajustadas",
                                  f"Se ajustaron {adjusted_count} canciones antiguas.\n\n"
                                  f"Se distribuyeron en los últimos 14 días manteniendo\n"
                                  f"el orden y la hora del día. Están en naranja.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al leer:\n{str(e)}")
            self.log(f"Error: {str(e)}")
    
    def on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "tree":
            item = self.tree.identify_row(event.y)
            if item:
                self.toggle_item(item)
    
    def on_space_press(self, event):
        for item in self.tree.selection():
            self.toggle_item(item)
    
    def toggle_item(self, item):
        current_tags = self.tree.item(item, "tags")
        is_adjusted = "adjusted" in current_tags
        
        if "checked" in current_tags:
            new_tags = ("unchecked", "adjusted") if is_adjusted else ("unchecked",)
            self.tree.item(item, text="☐", tags=new_tags)
        else:
            new_tags = ("checked", "adjusted") if is_adjusted else ("checked",)
            self.tree.item(item, text="☑", tags=new_tags)
        
        self.update_count()
    
    def select_all(self):
        for item in self.tree.get_children():
            current_tags = self.tree.item(item, "tags")
            is_adjusted = "adjusted" in current_tags
            new_tags = ("checked", "adjusted") if is_adjusted else ("checked",)
            self.tree.item(item, text="☑", tags=new_tags)
        self.update_count()
    
    def deselect_all(self):
        for item in self.tree.get_children():
            current_tags = self.tree.item(item, "tags")
            is_adjusted = "adjusted" in current_tags
            new_tags = ("unchecked", "adjusted") if is_adjusted else ("unchecked",)
            self.tree.item(item, text="☐", tags=new_tags)
        self.update_count()
    
    def invert_selection(self):
        for item in self.tree.get_children():
            self.toggle_item(item)
    
    def update_count(self):
        total = len(self.tree.get_children())
        selected = sum(1 for item in self.tree.get_children() 
                      if "checked" in self.tree.item(item, "tags"))
        self.count_label.config(text=f"Canciones: {total} | Seleccionadas: {selected}")
    
    def get_selected_scrobbles(self):
        selected = []
        for item in self.tree.get_children():
            if "checked" in self.tree.item(item, "tags"):
                idx = self.tree_items[item]
                selected.append(self.scrobbles[idx])
        return selected
    
    def log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update()
    
    def start_import(self):
        if not self.logged_in:
            messagebox.showerror("Error", "Debes iniciar sesión primero")
            self.show_login_dialog()
            return
        
        selected = self.get_selected_scrobbles()
        
        if not selected:
            messagebox.showwarning("Advertencia", "No hay canciones seleccionadas")
            return
        
        adjusted_count = sum(1 for s in selected if s.get('was_adjusted'))
        
        msg = f"¿Importar {len(selected)} canciones?\n\nUsuario: {self.username}"
        if adjusted_count > 0:
            msg += f"\n\nIncluye {adjusted_count} con fechas ajustadas"
        
        if not messagebox.askyesno("Confirmar", msg):
            return
        
        self.import_button.config(state='disabled')
        
        thread = threading.Thread(target=self.import_scrobbles, args=(selected,))
        thread.daemon = True
        thread.start()
    
    def import_scrobbles(self, scrobbles):
        try:
            if not self.network:
                password_hash = pylast.md5(self.password)
                self.network = pylast.LastFMNetwork(
                    api_key=API_KEY,
                    api_secret=API_SECRET,
                    username=self.username,
                    password_hash=password_hash
                )
            
            self.log(f"Importando como: {self.username}")
            
            total = len(scrobbles)
            successful = 0
            failed = 0
            
            self.progress['maximum'] = total
            self.progress['value'] = 0
            
            self.log(f"\nIniciando importación de {total} canciones...")
            self.log("=" * 60)
            
            import time
            
            for idx, scrobble in enumerate(scrobbles, 1):
                try:
                    self.network.scrobble(
                        artist=scrobble['artist'],
                        title=scrobble['title'],
                        timestamp=scrobble['timestamp'],
                        album=scrobble['album'] if scrobble['album'] else None
                    )
                    successful += 1
                    
                    status = "[AJUSTADA] " if scrobble.get('was_adjusted') else "[OK] "
                    self.log(f"[{idx}/{total}] {status}{scrobble['artist']} - {scrobble['title']}")
                    
                except Exception as e:
                    failed += 1
                    self.log(f"[{idx}/{total}] [ERROR] {scrobble['artist']} - {scrobble['title']}: {str(e)}")
                
                self.progress['value'] = idx
                self.status_label.config(text=f"{idx}/{total}")
                self.root.update()
                
                time.sleep(0.1)
            
            self.log("\n" + "=" * 60)
            self.log(f"Exitosas: {successful} | Fallidas: {failed}")
            self.log("=" * 60)
            
            if successful > 0:
                self.log(f"\nVerifica: https://www.last.fm/user/{self.username}")
                messagebox.showinfo("Importación completada", 
                                  f"Se importaron {successful} canciones exitosamente.\n\n"
                                  f"Pueden tardar 1-2 minutos en aparecer en Last.fm.")
            
        except Exception as e:
            self.log(f"\nError: {str(e)}")
            messagebox.showerror("Error", str(e))
        
        finally:
            self.import_button.config(state='normal')
            self.status_label.config(text="Listo")


def main():
    root = tk.Tk()
    app = ScrobblerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
