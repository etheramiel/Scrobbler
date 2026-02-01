#!/usr/bin/env python3
"""
Script de compilación automática para Rockbox Scrobbler
Genera ejecutables para Windows, macOS y Linux
"""

import subprocess
import sys
import os
import platform

print("=" * 60)
print("Compilador de Rockbox Scrobbler")
print("=" * 60)

# Verificar que PyInstaller esté instalado
try:
    import PyInstaller
except ImportError:
    print("\nError: PyInstaller no está instalado")
    print("Instálalo con: pip install pyinstaller")
    sys.exit(1)

# Verificar que el archivo fuente exista
if not os.path.exists("rockbox_scrobbler_oauth.py"):
    print("\nError: No se encuentra rockbox_scrobbler_oauth.py")
    print("Asegúrate de estar en el directorio correcto")
    sys.exit(1)

# Verificar que las API keys estén configuradas
with open("rockbox_scrobbler_oauth.py", 'r') as f:
    content = f.read()
    if "TU_API_KEY_AQUI" in content:
        print("\nADVERTENCIA: Las API keys no están configuradas")
        print("Ejecuta primero: python encode_keys.py")
        response = input("\n¿Deseas continuar de todos modos? (s/n): ")
        if response.lower() not in ['s', 'si', 'sí', 'y', 'yes']:
            sys.exit(0)

print(f"\nSistema operativo: {platform.system()}")
print(f"Arquitectura: {platform.machine()}")

# Configuración según el sistema operativo
system = platform.system()

if system == "Windows":
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name", "Rockbox Scrobbler",
        "--clean",
        "rockbox_scrobbler_oauth.py"
    ]
    
    # Agregar icono si existe
    if os.path.exists("icon.ico"):
        cmd.extend(["--icon", "icon.ico"])
        print("\n✓ Usando icono: icon.ico")
    
elif system == "Darwin":  # macOS
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name", "Rockbox Scrobbler",
        "--clean",
        "rockbox_scrobbler_oauth.py"
    ]
    
    if os.path.exists("icon.icns"):
        cmd.extend(["--icon", "icon.icns"])
        print("\n✓ Usando icono: icon.icns")
    
elif system == "Linux":
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name", "rockbox-scrobbler",
        "--clean",
        "rockbox_scrobbler_oauth.py"
    ]
    
    if os.path.exists("icon.png"):
        cmd.extend(["--icon", "icon.png"])
        print("\n✓ Usando icono: icon.png")

else:
    print(f"\nAdvertencia: Sistema operativo no reconocido: {system}")
    print("Intentando compilación genérica...")
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name", "rockbox-scrobbler",
        "rockbox_scrobbler_oauth.py"
    ]

print("\n" + "=" * 60)
print("Iniciando compilación...")
print("=" * 60)
print(f"\nComando: {' '.join(cmd)}\n")

# Ejecutar PyInstaller
try:
    result = subprocess.run(cmd, check=True)
    
    print("\n" + "=" * 60)
    print("COMPILACIÓN EXITOSA")
    print("=" * 60)
    
    # Información sobre el ejecutable generado
    dist_dir = "dist"
    if os.path.exists(dist_dir):
        files = os.listdir(dist_dir)
        if files:
            print(f"\nEjecutable generado en: {dist_dir}/")
            for file in files:
                filepath = os.path.join(dist_dir, file)
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                print(f"  - {file} ({size_mb:.1f} MB)")
        
        print("\nPuedes distribuir el archivo en la carpeta 'dist/'")
        print("Los usuarios no necesitarán Python instalado.")
    
    print("\n" + "=" * 60)
    print("PRÓXIMOS PASOS")
    print("=" * 60)
    print("""
1. Prueba el ejecutable en una máquina sin Python
2. Crea un archivo README con instrucciones de uso
3. Considera firmar el ejecutable (para evitar advertencias)
4. Distribuye el archivo de la carpeta dist/

Para limpiar archivos temporales:
  - Puedes borrar la carpeta 'build/'
  - El archivo .spec se puede guardar para recompilar
    """)
    
except subprocess.CalledProcessError as e:
    print(f"\n✗ Error durante la compilación: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n✗ Error inesperado: {e}")
    sys.exit(1)
