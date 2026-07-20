# Recursos de marca (brand kit)

Carpeta central de recursos visuales del proyecto. Aquí vive el **maestro** de
cada recurso; las versiones que consumen la web y la app móvil se **generan** a
partir de estos maestros (no se editan a mano).

## Archivos maestros

| Archivo | Qué es | Recomendado |
|---|---|---|
| `logo.png` | Logo/ícono principal del sistema (portapapeles táctico verde/dorado) | PNG cuadrado 1024×1024 |

> Coloca aquí tu `logo.png`. Es la única fuente de verdad; todo lo demás se deriva.

## Cómo se consume el logo

| Destino | Archivo generado | Uso |
|---|---|---|
| Panel web | `web/app/static/logo.png` | Marca en la barra lateral y en el login (sirve desde `'self'`, cumple la CSP) |
| App móvil | `mobile/assets/icon.png` | Ícono de la app (Expo) |
| App móvil | `mobile/assets/adaptive-icon.png` | Ícono adaptativo de Android |
| App móvil | `mobile/assets/splash.png` | Pantalla de carga (splash) |

## Regenerar los recursos derivados

Tras cambiar `brand/logo.png`, ejecuta:

```bash
./api/.venv/bin/python brand/generar-assets.py
```

El script redimensiona el maestro a los tamaños correctos y escribe las copias
en `web/app/static/` y `mobile/assets/`.
