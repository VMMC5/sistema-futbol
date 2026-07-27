"""
Normalización de fotos de perfil.

Toda foto subida se recorta al cuadrado centrado, se lleva a 512x512 y se
re-guarda como JPEG. Así el disco no crece sin control y el front siempre
recibe el mismo formato y relación de aspecto.
"""
import io

from PIL import Image, ImageOps

LADO = 512
CALIDAD = 85


def normalizar_a_jpeg(datos: bytes) -> bytes:
    try:
        img = Image.open(io.BytesIO(datos))
        img.load()
    except Exception as exc:  # PIL lanza varios tipos; se unifican
        raise ValueError("No se pudo procesar la imagen") from exc

    img = ImageOps.exif_transpose(img)          # respeta orientación de la cámara
    img = img.convert("RGB")                     # descarta alfa/paleta
    img = ImageOps.fit(img, (LADO, LADO), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))

    salida = io.BytesIO()
    img.save(salida, format="JPEG", quality=CALIDAD, optimize=True)
    return salida.getvalue()
