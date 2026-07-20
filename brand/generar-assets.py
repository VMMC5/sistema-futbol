# -*- coding: utf-8 -*-
"""
Genera los recursos derivados del logo maestro (brand/logo.png).

Uso:
    ./api/.venv/bin/python brand/generar-assets.py

Lee brand/logo.png y escribe las versiones que consumen la web y el móvil.
No edita el maestro. Es idempotente: se puede correr las veces que haga falta.
"""
import os
import sys

from PIL import Image

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAESTRO = os.path.join(RAIZ, "brand", "logo.png")

# Fondo para la splash de la app (mismo color que app.json -> splash.backgroundColor)
SPLASH_BG = (7, 20, 13, 255)  # #07140d

# (ruta_destino, tamaño, ¿lienzo con fondo?)  -> None = mantiene transparencia/original
SALIDAS = [
    (os.path.join(RAIZ, "web", "app", "static", "logo.png"), 256, None),
    (os.path.join(RAIZ, "mobile", "assets", "icon.png"), 1024, None),
    (os.path.join(RAIZ, "mobile", "assets", "adaptive-icon.png"), 1024, None),
    (os.path.join(RAIZ, "mobile", "assets", "splash.png"), 1024, SPLASH_BG),
]


def main() -> int:
    if not os.path.exists(MAESTRO):
        print(f"ERROR: no existe el maestro {MAESTRO}\n"
              f"Coloca tu logo cuadrado (1024x1024 recomendado) en brand/logo.png.")
        return 1

    original = Image.open(MAESTRO).convert("RGBA")
    print(f"Maestro: {MAESTRO}  ({original.width}x{original.height})")

    for destino, tam, fondo in SALIDAS:
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        img = original.copy()
        img.thumbnail((tam, tam), Image.LANCZOS)
        if fondo is not None:
            lienzo = Image.new("RGBA", (tam, tam), fondo)
            off = ((tam - img.width) // 2, (tam - img.height) // 2)
            lienzo.paste(img, off, img)
            salida = lienzo
        else:
            salida = img
        salida.save(destino, "PNG")
        print(f"  -> {os.path.relpath(destino, RAIZ)}  ({salida.width}x{salida.height})")

    print("Listo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
