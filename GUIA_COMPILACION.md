# Guía para Crear Ejecutable Distribuible

## Resumen

Esta versión usa OAuth para que cada usuario inicie sesión con su propia cuenta de Last.fm. Las credenciales API quedan ocultas en el código compilado.

## Características de la versión OAuth

1. **Autenticación individual**: Cada usuario usa su propia cuenta
2. **Seguridad**: API keys ocultas en el ejecutable
3. **Sesión persistente**: La autenticación se guarda localmente
<!-- 4. **Filtro automático**: Solo muestra canciones de las últimas 2 semanas -->

## Paso 1: Preparar el código para distribución

### Ofuscar las API keys

Antes de compilar, necesitas codificar tus API keys en base64:

```python
import base64

api_key = "tu_api_key_real"
api_secret = "tu_api_secret_real"

# Crear string con ambas keys
config = f"{api_key}|{api_secret}"
encoded = base64.b64encode(config.encode()).decode()

print(f"Encoded: {encoded}")
```

Luego, en el archivo `rockbox_scrobbler_oauth.py`, reemplaza:

```python
# Línea 24-28, cambia de:
_API_CONFIG = base64.b64decode(
    b''
).decode() if False else None

API_KEY = "TU_API_KEY_AQUI"
API_SECRET = "TU_API_SECRET_AQUI"

# A:
_API_CONFIG = base64.b64decode(
    b'TU_STRING_CODIFICADO_AQUI'  # Pega el resultado del script anterior
).decode()

parts = _API_CONFIG.split('|')
API_KEY = parts[0]
API_SECRET = parts[1]
```

Esto hace que las keys no sean visibles fácilmente en el código compilado.

## Paso 2: Instalar PyInstaller

PyInstaller convierte scripts de Python en ejecutables.

```bash
pip install pyinstaller
```

## Paso 3: Crear el ejecutable

### En Windows:

```bash
pyinstaller --onefile --windowed --name "Rockbox Scrobbler" --icon=icon.ico rockbox_scrobbler_oauth.py
```

### En macOS:

```bash
pyinstaller --onefile --windowed --name "Rockbox Scrobbler" --icon=icon.icns rockbox_scrobbler_oauth.py
```

### En Linux:

```bash
pyinstaller --onefile --name "rockbox-scrobbler" rockbox_scrobbler_oauth.py
```

### Parámetros explicados:

- `--onefile`: Crea un único archivo ejecutable
- `--windowed`: No muestra ventana de consola (solo Windows/Mac)
- `--name`: Nombre del ejecutable
- `--icon`: Icono de la aplicación (opcional)

## Paso 4: Resultado

Después de compilar, encontrarás:

- `dist/`: Carpeta con el ejecutable final
- `build/`: Archivos temporales (puedes borrar)
- `*.spec`: Archivo de configuración (puedes guardar para recompilar)

El ejecutable estará en `dist/Rockbox Scrobbler.exe` (Windows) o `dist/Rockbox Scrobbler.app` (Mac).

## Paso 5: Crear un icono (opcional)

Puedes crear un icono personalizado:

### Windows (.ico):
- Tamaños: 16x16, 32x32, 48x48, 256x256
- Usa herramientas online como: https://www.icoconverter.com/

### macOS (.icns):
- Usa `iconutil` en Mac o herramientas online

### Comando con icono:
```bash
pyinstaller --onefile --windowed --name "Rockbox Scrobbler" --icon=mi_icono.ico rockbox_scrobbler_oauth.py
```

## Paso 6: Distribución

### Opción 1: Archivo único
El ejecutable en `dist/` se puede compartir directamente. Los usuarios solo necesitan:
1. Descargar el ejecutable
2. Ejecutarlo
3. Autenticarse con Last.fm

### Opción 2: Instalador

Para una experiencia más profesional, puedes crear un instalador:

**Windows:**
- Usa Inno Setup: https://jrsoftware.org/isinfo.php
- NSIS: https://nsis.sourceforge.io/

**macOS:**
- Usa `create-dmg`: https://github.com/create-dmg/create-dmg

**Linux:**
- Crea un paquete .deb o .rpm
- O distribuye el AppImage

## Cómo funciona la autenticación OAuth

1. El usuario ejecuta la app
2. Primera vez: se le pide autenticarse
3. Se abre el navegador con la página de autorización de Last.fm
4. El usuario inicia sesión y autoriza la app
5. Last.fm da un token
6. El usuario pega el token en la app
7. La app guarda la sesión localmente (archivo `~/.rockbox_scrobbler_config.json`)
8. Próximas veces: la app usa la sesión guardada automáticamente

## Privacidad y seguridad

- Las API keys están ofuscadas (no visibles fácilmente)
- Cada usuario usa su propia cuenta
- La sesión se guarda localmente en el ordenador del usuario
- No se envían datos a terceros, solo a Last.fm directamente

## Advertencias para usuarios

Cuando distribuyas la app, incluye estas advertencias:

```
IMPORTANTE:

1. Last.fm solo acepta scrobbles de las últimas 2 semanas.
   Canciones más antiguas serán filtradas automáticamente.

2. Después de importar, los scrobbles pueden tardar 1-5 minutos
   en aparecer en tu perfil.

3. Tu sesión se guarda localmente en tu ordenador.
   Si cambias de ordenador, necesitarás autenticarte de nuevo.

4. Para cambiar de cuenta, usa el botón "Cambiar cuenta" en la app.
```

## Solución de problemas de compilación

### Error: "No module named 'tkinter'"
En Linux:
```bash
sudo apt-get install python3-tk
```

### Error: "No module named 'pylast'"
```bash
pip install pylast
```

### El ejecutable es muy grande
Es normal. PyInstaller incluye Python y todas las librerías.
Tamaño típico: 15-25 MB

### El antivirus bloquea el ejecutable
Esto es común con ejecutables de PyInstaller porque no están firmados.
Soluciones:
1. Firma el ejecutable (requiere certificado de código)
2. Advierte a los usuarios que es un falso positivo
3. Súbelo a VirusTotal para verificación

## Firmar el ejecutable (recomendado para distribución seria)

### Windows:
Necesitas un certificado de firma de código (~$100-300/año)
- Providers: DigiCert, Sectigo, GlobalSign

```bash
signtool sign /f certificado.pfx /p contraseña /t http://timestamp.digicert.com ejecutable.exe
```

### macOS:
Necesitas una cuenta de desarrollador de Apple ($99/año)

```bash
codesign --force --sign "Developer ID Application: Tu Nombre" "Rockbox Scrobbler.app"
```

## Alternativa: Distribuir como script

Si no quieres compilar, puedes distribuir el script directamente con instrucciones:

```
1. Instala Python 3.7+
2. Instala pylast: pip install pylast
3. Ejecuta: python rockbox_scrobbler_oauth.py
```

Crea un archivo `requirements.txt`:
```
pylast>=5.0.0
```

Y los usuarios solo necesitan:
```bash
pip install -r requirements.txt
python rockbox_scrobbler_oauth.py
```

## Recomendaciones finales

1. **Prueba en máquinas limpias**: Antes de distribuir, prueba en ordenadores sin Python instalado
2. **README claro**: Incluye instrucciones de uso
3. **Changelog**: Documenta versiones y cambios
4. **Licencia**: Agrega una licencia (MIT, GPL, etc.)
5. **GitHub/GitLab**: Considera usar repositorio público para mayor confianza

## Ejemplo de README para distribuir

```markdown
# Rockbox Scrobbler for Last.fm

Importa las canciones de tu iPod con Rockbox a Last.fm.

## Características

- Interfaz gráfica fácil de usar
- Autenticación segura con Last.fm
- Selección individual de canciones
- Filtrado automático (solo últimas 2 semanas)
- Sesión persistente

## Uso

1. Descarga el ejecutable
2. Ejecútalo
3. Inicia sesión con tu cuenta de Last.fm
4. Selecciona tu archivo .scrobbler.log
5. Revisa y selecciona las canciones
6. Haz clic en "Importar a Last.fm"

## Requisitos

- Cuenta de Last.fm
- Archivo .scrobbler.log de Rockbox

## Limitaciones

Last.fm solo acepta scrobbles de las últimas 2 semanas.

## Privacidad

Esta aplicación no recopila ni comparte tus datos.
Solo se comunica directamente con la API de Last.fm.

## Licencia

MIT License
```

---

¡Listo! Ahora puedes distribuir tu aplicación de forma segura y profesional.
