#!/usr/bin/env python3
"""
Rockbox Scrobbler to Last.fm - Versión Distribuible con OAuth
Permite a los usuarios autenticarse con su propia cuenta de Last.fm
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pylast
import os
import threading
import webbrowser
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
import json
import base64

# =============================================================================
# CONFIGURACIÓN DE API (Ocultas en versión compilada)
# =============================================================================
# Estas se pueden ofuscar al compilar con PyInstaller
_API_CONFIG = base64.b64decode(
    # Aquí irían tus credenciales codificadas en base64
    # Por ahora las dejamos en texto plano para testing
    b''
).decode() if False else None

# Para desarrollo, usa estas (las reemplazaremos con base64 para distribución)
API_KEY = "TU_API_KEY_AQUI"
API_SECRET = "TU_API_SECRET_AQUI"

# Archivo para guardar sesión del usuario
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".rockbox_scrobbler_config.json")

# =============================================================================
# SERVIDOR HTTP TEMPORAL PARA OAUTH CALLBACK
# =============================================================================

class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    """Maneja el callback de OAuth"""
    token = None
    
    def do_GET(self):
        query = urlparse(self.path).query
        params = parse_qs(query)
        
        if 'token' in params:
            OAuthCallbackHandler.token = params['token'][0]
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = """
            <html>
            <head><title>Autenticación exitosa</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>✓ Autenticación exitosa</h1>
                <p>Ya puedes cerrar esta ventana y volver a la aplicación.</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        else:
            self.send_response(400)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Silenciar logs del servidor


# =============================================================================
# FUNCIONES DE AUTENTICACIÓN
# =============================================================================

def save_session(username, session_key):
    """Guarda la sesión del usuario"""
    config = {
        'username': username,
        'session_key': session_key
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)


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
        os.remove(CONFIG_FILE)


def authenticate_with_lastfm():
    """Autentica al usuario usando OAuth web auth"""
    
    # Crear network
    network = pylast.LastFMNetwork(
        api_key=API_KEY,
        api_secret=API_SECRET
    )
    
    # Obtener URL de autenticación
    sg = pylast.SessionKeyGenerator(network)
    auth_url = sg.get_web_auth_url()
    
    # Abrir navegador
    webbrowser.open(auth_url)
    
    return sg


# =============================================================================
# FUNCIONES DE PROCESAMIENTO
# =============================================================================

def parse_scrobbler_log(filepath):
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
                scrobble_date = datetime.fromtimestamp(timestamp_int)
                
                
            except ValueError:
                continue
            
            scrobbles.append({
                'artist': artist,
                'title': track,
                'album': album if album else '',
                'timestamp': timestamp_int,
                'date_str': scrobble_date.strftime('%Y-%m-%d %H:%M:%S')
            })
    
    return scrobbles


# =============================================================================
# INTERFAZ GRÁFICA
# =============================================================================

class ScrobblerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Rockbox Scrobbler to Last.fm")
        self.root.geometry("1200x750")
        
        self.scrobbles = []
        self.tree_items = {}
        self.network = None
        self.session_key = None
        self.username = None
        
        # Verificar configuración de API
        if API_KEY == "TU_API_KEY_AQUI":
            messagebox.showerror(
                "Error de Configuración",
                "Esta aplicación no está configurada correctamente.\n"
                "Contacta al desarrollador."
            )
            self.root.quit()
            return
        
        # Intentar cargar sesión guardada
        session = load_session()
        if session:
            self.username = session.get('username')
            self.session_key = session.get('session_key')
        
        self.create_widgets()
        
        # Si no hay sesión, mostrar diálogo de login
        if not self.session_key:
            self.show_login_dialog()
        else:
            self.update_user_status()
    
    def create_widgets(self):
        # Frame superior - Info de usuario y selección de archivo
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        
        # Info de usuario
        user_frame = ttk.Frame(top_frame)
        user_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(user_frame, text="Usuario:").pack(side=tk.LEFT, padx=5)
        self.user_label = ttk.Label(user_frame, text="No autenticado", font=('Arial', 10, 'bold'))
        self.user_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(user_frame, text="Cambiar cuenta", command=self.logout).pack(side=tk.LEFT, padx=20)
        
        # Selección de archivo
        file_frame = ttk.Frame(top_frame)
        file_frame.pack(fill=tk.X)
        
        ttk.Label(file_frame, text="Archivo .scrobbler.log:").pack(side=tk.LEFT, padx=5)
        
        self.file_entry = ttk.Entry(file_frame, width=50)
        self.file_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Button(file_frame, text="Seleccionar archivo", command=self.select_file).pack(side=tk.LEFT, padx=5)
        
        # Advertencia de 2 semanas
        warning_frame = ttk.Frame(self.root, padding="10")
        warning_frame.pack(fill=tk.X)
        
        warning_text = "NOTA: Last.fm solo acepta scrobbles de las últimas 2 semanas. Canciones más antiguas serán filtradas automáticamente."
        ttk.Label(warning_frame, text=warning_text, foreground='red', wraplength=1150).pack()
        
        # Frame medio - Botones de selección
        middle_frame = ttk.Frame(self.root, padding="10")
        middle_frame.pack(fill=tk.X)
        
        ttk.Button(middle_frame, text="Seleccionar todas", command=self.select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(middle_frame, text="Deseleccionar todas", command=self.deselect_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(middle_frame, text="Invertir selección", command=self.invert_selection).pack(side=tk.LEFT, padx=5)
        
        self.count_label = ttk.Label(middle_frame, text="Canciones: 0 | Seleccionadas: 0")
        self.count_label.pack(side=tk.RIGHT, padx=5)
        
        # Frame para la tabla
        table_frame = ttk.Frame(self.root, padding="10")
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("Artista", "Canción", "Álbum", "Fecha y Hora")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="tree headings", selectmode="extended")
        
        self.tree.column("#0", width=30, minwidth=30, stretch=False)
        self.tree.column("Artista", width=200, minwidth=150)
        self.tree.column("Canción", width=250, minwidth=150)
        self.tree.column("Álbum", width=200, minwidth=150)
        self.tree.column("Fecha y Hora", width=150, minwidth=130)
        
        self.tree.heading("#0", text="☑")
        self.tree.heading("Artista", text="Artista")
        self.tree.heading("Canción", text="Canción")
        self.tree.heading("Álbum", text="Álbum")
        self.tree.heading("Fecha y Hora", text="Fecha y Hora")
        
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
        
        # Frame inferior - Log y botones
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
    
    def show_login_dialog(self):
        """Muestra diálogo de autenticación"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Iniciar sesión en Last.fm")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Centrar ventana
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Iniciar sesión en Last.fm", font=('Arial', 14, 'bold')).pack(pady=10)
        
        ttk.Label(frame, text="Para usar esta aplicación necesitas autenticarte con Last.fm.",
                 wraplength=450).pack(pady=10)
        
        ttk.Label(frame, text="Al hacer clic en 'Autorizar', se abrirá tu navegador.\n"
                             "Inicia sesión en Last.fm y autoriza la aplicación.",
                 wraplength=450).pack(pady=10)
        
        token_frame = ttk.Frame(frame)
        token_frame.pack(pady=20)
        
        ttk.Label(token_frame, text="Después de autorizar, Last.fm te dará un token.\n"
                                   "Copia ese token y pégalo aquí:").pack()
        
        token_entry = ttk.Entry(token_frame, width=40)
        token_entry.pack(pady=10)
        
        def authorize():
            self.sg = authenticate_with_lastfm()
            messagebox.showinfo("Autorización", 
                              "Se abrirá tu navegador.\n\n"
                              "1. Inicia sesión en Last.fm\n"
                              "2. Autoriza la aplicación\n"
                              "3. Copia el token que aparece\n"
                              "4. Pégalo en la caja de texto")
        
        def complete_login():
            token = token_entry.get().strip()
            if not token:
                messagebox.showerror("Error", "Debes ingresar el token")
                return
            
            try:
                self.session_key = self.sg.get_web_auth_session_key(token)
                self.network = pylast.LastFMNetwork(
                    api_key=API_KEY,
                    api_secret=API_SECRET,
                    session_key=self.session_key
                )
                
                user = self.network.get_authenticated_user()
                self.username = user.get_name()
                
                save_session(self.username, self.session_key)
                
                self.update_user_status()
                dialog.destroy()
                
                messagebox.showinfo("Éxito", f"Autenticado como: {self.username}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error al autenticar:\n{str(e)}")
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="1. Autorizar en navegador", command=authorize).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="2. Completar autenticación", command=complete_login).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancelar", command=lambda: [dialog.destroy(), self.root.quit()]).pack(side=tk.LEFT, padx=5)
    
    def update_user_status(self):
        """Actualiza el estado del usuario en la UI"""
        if self.username:
            self.user_label.config(text=f"{self.username}", foreground='green')
        else:
            self.user_label.config(text="No autenticado", foreground='red')
    
    def logout(self):
        """Cierra sesión"""
        response = messagebox.askyesno("Cerrar sesión", 
                                      "¿Deseas cerrar sesión y autenticarte con otra cuenta?")
        if response:
            clear_session()
            self.session_key = None
            self.username = None
            self.network = None
            self.update_user_status()
            self.show_login_dialog()
    
    def select_file(self):
        """Abre diálogo para seleccionar archivo"""
        filename = filedialog.askopenfilename(
            title="Seleccionar archivo .scrobbler.log",
            filetypes=[("Scrobbler Log", "*.log"), ("Todos los archivos", "*.*")]
        )
        
        if filename:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filename)
            self.load_scrobbles(filename)
    
    def load_scrobbles(self, filepath):
        """Carga los scrobbles del archivo"""
        try:
            self.log("Leyendo archivo...")
            all_scrobbles = []
            filtered_count = 0
            
            # Parsear con filtro de 2 semanas
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    parts = line.split('\t')
                    if len(parts) < 7:
                        continue
                    
                    try:
                        timestamp_int = int(parts[6].strip())
                        scrobble_date = datetime.fromtimestamp(timestamp_int)

                        
                        all_scrobbles.append({
                            'artist': parts[0].strip(),
                            'title': parts[2].strip(),
                            'album': parts[1].strip(),
                            'timestamp': timestamp_int,
                            'date_str': scrobble_date.strftime('%Y-%m-%d %H:%M:%S')
                        })
                    except:
                        continue
            
            self.scrobbles = all_scrobbles
            
            if not self.scrobbles:
                messagebox.showwarning("Advertencia", 
                    "No se encontraron scrobbles válidos dentro de las últimas 2 semanas.\n\n"
                    f"Canciones filtradas (muy antiguas): {filtered_count}")
                return
            
            # Limpiar tabla
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            self.tree_items.clear()
            
            # Agregar scrobbles a la tabla
            for idx, scrobble in enumerate(self.scrobbles):
                item_id = self.tree.insert("", "end", text="☑", values=(
                    scrobble['artist'],
                    scrobble['title'],
                    scrobble['album'],
                    scrobble['date_str']
                ), tags=("checked",))
                self.tree_items[item_id] = idx
            
            self.update_count()
            self.log(f"Se cargaron {len(self.scrobbles)} canciones válidas")
            if filtered_count > 0:
                self.log(f"Se filtraron {filtered_count} canciones por ser más antiguas de 2 semanas")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al leer el archivo:\n{str(e)}")
            self.log(f"Error: {str(e)}")
    
    def on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "tree":
            item = self.tree.identify_row(event.y)
            if item:
                self.toggle_item(item)
    
    def on_space_press(self, event):
        selected = self.tree.selection()
        for item in selected:
            self.toggle_item(item)
    
    def toggle_item(self, item):
        current_tags = self.tree.item(item, "tags")
        
        if "checked" in current_tags:
            self.tree.item(item, text="☐", tags=("unchecked",))
        else:
            self.tree.item(item, text="☑", tags=("checked",))
        
        self.update_count()
    
    def select_all(self):
        for item in self.tree.get_children():
            self.tree.item(item, text="☑", tags=("checked",))
        self.update_count()
    
    def deselect_all(self):
        for item in self.tree.get_children():
            self.tree.item(item, text="☐", tags=("unchecked",))
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
        if not self.session_key:
            messagebox.showerror("Error", "Debes autenticarte primero")
            return
        
        selected = self.get_selected_scrobbles()
        
        if not selected:
            messagebox.showwarning("Advertencia", "No hay canciones seleccionadas para importar")
            return
        
        response = messagebox.askyesno(
            "Confirmar importación",
            f"¿Deseas importar {len(selected)} canciones a Last.fm?\n\n"
            f"Usuario: {self.username}"
        )
        
        if not response:
            return
        
        self.import_button.config(state='disabled')
        
        thread = threading.Thread(target=self.import_scrobbles, args=(selected,))
        thread.daemon = True
        thread.start()
    
    def import_scrobbles(self, scrobbles):
        try:
            # Crear network con session key
            if not self.network:
                self.network = pylast.LastFMNetwork(
                    api_key=API_KEY,
                    api_secret=API_SECRET,
                    session_key=self.session_key
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
                    self.log(f"[{idx}/{total}] OK: {scrobble['artist']} - {scrobble['title']} ({scrobble['date_str']})")
                    
                except Exception as e:
                    failed += 1
                    self.log(f"[{idx}/{total}] ERROR: {scrobble['artist']} - {scrobble['title']}")
                    self.log(f"    Razón: {str(e)}")
                
                self.progress['value'] = idx
                self.status_label.config(text=f"{idx}/{total}")
                self.root.update()
                
                time.sleep(0.1)
            
            self.log("\n" + "=" * 60)
            self.log("RESUMEN FINAL")
            self.log("=" * 60)
            self.log(f"Importadas exitosamente: {successful}")
            self.log(f"Fallidas: {failed}")
            self.log(f"Total procesadas: {total}")
            self.log("=" * 60)
            
            if successful > 0:
                self.log("\nImportación completada!")
                self.log("Los scrobbles pueden tardar unos minutos en aparecer")
                self.log(f"Verifica: https://www.last.fm/user/{self.username}")
                messagebox.showinfo("Éxito", 
                    f"Se importaron {successful} canciones exitosamente.\n\n"
                    f"Pueden tardar unos minutos en aparecer en Last.fm.")
            
        except Exception as e:
            self.log(f"\nError: {str(e)}")
            messagebox.showerror("Error", f"Error al importar:\n{str(e)}")
        
        finally:
            self.import_button.config(state='normal')
            self.status_label.config(text="Listo")


# =============================================================================
# MAIN
# =============================================================================

def main():
    root = tk.Tk()
    app = ScrobblerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
