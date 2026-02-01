#!/usr/bin/env python3
"""
Script auxiliar para codificar tus API keys antes de compilar
"""

import base64

print("=" * 60)
print("Codificador de API Keys para distribución")
print("=" * 60)

print("\nEste script te ayudará a codificar tus credenciales de Last.fm")
print("para poder distribuir la aplicación de forma segura.\n")

api_key = input("Ingresa tu API Key de Last.fm: ").strip()
api_secret = input("Ingresa tu API Secret de Last.fm: ").strip()

if not api_key or not api_secret:
    print("\nError: Debes ingresar ambas credenciales")
    exit(1)

# Combinar ambas keys
config = f"{api_key}|{api_secret}"

# Codificar en base64
encoded = base64.b64encode(config.encode()).decode()

print("\n" + "=" * 60)
print("CÓDIGO GENERADO")
print("=" * 60)

print(f"\nCopia este código: b'{encoded}'")

print("\n" + "=" * 60)
print("INSTRUCCIONES")
print("=" * 60)

print("""
1. Abre el archivo rockbox_scrobbler_oauth.py

2. Busca las líneas 24-28 que dicen:

   _API_CONFIG = base64.b64decode(
       b''
   ).decode() if False else None

   API_KEY = "TU_API_KEY_AQUI"
   API_SECRET = "TU_API_SECRET_AQUI"

3. Reemplázalas con:

   _API_CONFIG = base64.b64decode(
       b'{}'
   ).decode()

   parts = _API_CONFIG.split('|')
   API_KEY = parts[0]
   API_SECRET = parts[1]

4. Guarda el archivo

5. Ahora puedes compilar con PyInstaller de forma segura

IMPORTANTE: No compartas el archivo con este código insertado en GitHub
o lugares públicos, ya que aunque está codificado, se puede decodificar.
Solo comparte el ejecutable compilado.
""".format(encoded))

print("=" * 60)

# Verificar que la codificación funcione
decoded = base64.b64decode(encoded).decode()
parts = decoded.split('|')

print("\nVerificación:")
print(f"API Key decodificada: {parts[0][:10]}... (primeros 10 caracteres)")
print(f"API Secret decodificada: {parts[1][:10]}... (primeros 10 caracteres)")

if parts[0] == api_key and parts[1] == api_secret:
    print("\n✓ La codificación funciona correctamente")
else:
    print("\n✗ Error en la codificación")
