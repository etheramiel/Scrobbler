# Guía Completa - Versión Híbrida

Esta versión funciona de DOS formas:

## MODO 1: Para tu uso personal (con .env)

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Crear .env
cp .env.example .env

# 3. Editar .env con tus credenciales
nano .env  # o usa cualquier editor

# 4. Ejecutar
python rockbox_scrobbler_hibrido.py
```

Login automático con tus credenciales del .env ✅

## MODO 2: Para distribuir a otros usuarios (ejecutable)

### Paso 1: Codificar API keys

```bash
python encode_keys.py
```

Te dará algo como:
```
b'YTFiMmMzZDRlNWY2fHg5eTh6N3c2djV1NA=='
```

### Paso 2: Editar el código

Abre `rockbox_scrobbler_hibrido.py` y busca las líneas 35-45:

```python
# MODO 2: API keys embebidas (para distribución compilada)
if not API_KEY or API_KEY == 'TU_API_KEY_AQUI':
    # INSTRUCCIONES PARA COMPILAR:
    # 1. Ejecuta: python encode_keys.py
    # 2. Pega el código que te da aquí abajo:
    
    import base64
    _config = base64.b64decode(b'PEGA_AQUI_TU_CODIGO').decode()
    _parts = _config.split('|')
    API_KEY = _parts[0]
    API_SECRET = _parts[1]
```

Reemplaza `PEGA_AQUI_TU_CODIGO` con el código que te dio `encode_keys.py`

### Paso 3: Compilar

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "Rockbox Scrobbler" rockbox_scrobbler_hibrido.py
```

### Paso 4: Distribuir

El ejecutable estará en `dist/`. Cuando otros usuarios lo ejecuten:

1. Se abre la aplicación
2. Ven un diálogo de login
3. Ingresan SU usuario y contraseña de Last.fm
4. Sus credenciales se guardan localmente en su PC
5. La próxima vez, login automático

## Cómo funciona el login para usuarios finales

### Primera vez:
```
┌─────────────────────────────────────┐
│  Iniciar sesión en Last.fm          │
│                                     │
│  Usuario:    [mi_usuario      ]    │
│  Contraseña: [●●●●●●●●●●●●●●]      │
│                                     │
│  ☑ Recordar mis credenciales        │
│                                     │
│  [Iniciar sesión]  [Cancelar]      │
└─────────────────────────────────────┘
```

### Próximas veces:
- Abre la app → Login automático → Listo

### Si quieren cambiar de cuenta:
- Click en "Cambiar cuenta" → Nuevo login

## Ventajas de esta versión

✅ **Para ti**: .env fácil, no editas código
✅ **Para distribuir**: Ejecutable con API keys ocultas
✅ **Para usuarios**: Login simple con su usuario/contraseña
✅ **Sesión persistente**: No piden credenciales cada vez
✅ **Checkbox "Recordar"**: El usuario decide si guardar o no

## Seguridad

- Las API keys quedan embebidas y ofuscadas en el ejecutable
- Cada usuario usa SU propia cuenta de Last.fm
- Las credenciales del usuario se guardan localmente en su PC en:
  - Windows: `C:\Users\Usuario\.rockbox_scrobbler_session.json`
  - Mac/Linux: `~/.rockbox_scrobbler_session.json`
- Si desmarcan "Recordar", no se guarda nada

## Archivos de sesión

El archivo de sesión contiene:
```json
{
  "username": "usuario",
  "password": "contraseña"
}
```

Si el usuario quiere borrar su sesión guardada:
- Windows: Buscar y borrar `.rockbox_scrobbler_session.json` en su carpeta de usuario
- O simplemente hacer click en "Cambiar cuenta" y no marcar "Recordar"

## Diferencias con versiones anteriores

| Característica | OAuth version | Versión .env | Versión HÍBRIDA |
|----------------|---------------|--------------|-----------------|
| Login fácil | ❌ (token manual) | ✅ | ✅ |
| Para distribuir | ✅ | ❌ | ✅ |
| Login automático | ❌ | ✅ | ✅ |
| API keys ocultas | ✅ | ❌ | ✅ |
| Desarrollo fácil | ❌ | ✅ | ✅ |

## Resumen ultra-simple

**Para ti (desarrollo):**
1. Crea .env con tus credenciales
2. Ejecuta el script
3. Login automático

**Para compartir (distribución):**
1. Ejecuta encode_keys.py
2. Pega el código en el script
3. Compila con PyInstaller
4. Comparte el ejecutable
5. Los usuarios solo ponen su usuario/contraseña de Last.fm

¡Listo! Esta es la versión definitiva que combina lo mejor de todo.
