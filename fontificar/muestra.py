"""Página HTML estática para comparar la fuente original con la nueva."""
import base64
import html
import os
from pathlib import Path
from urllib.parse import quote

from .idiomas import IDIOMAS


def escribir_muestra(original, nueva, ruta, idioma="es"):
    """Página HTML estática que pone el mismo texto con la fuente original y la nueva.
    Cada fuente es una ruta (se enlaza relativa a la página) o sus bytes (se incrustan,
    como la original que viene de un zip y no está en disco)."""
    base = Path(ruta).parent

    def url(fuente):
        if isinstance(fuente, (bytes, bytearray)):
            tipo = "font/otf" if fuente[:4] == b"OTTO" else "font/ttf"
            return f"data:{tipo};base64,{base64.b64encode(fuente).decode('ascii')}"
        try:
            return quote(Path(os.path.relpath(fuente, base)).as_posix())
        except ValueError:  # en Windows, otra unidad no tiene ruta relativa
            return Path(fuente).resolve().as_uri()

    idioma = IDIOMAS[idioma]
    texto = html.escape(f"{idioma.muestra} {idioma.caracteres}")
    Path(ruta).write_text(
        f"""<!doctype html>
<html lang="es">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Muestra de Fontificar</title>
<style>
@font-face {{ font-family: "Original"; src: url("{url(original)}"); }}
@font-face {{ font-family: "Nueva"; src: url("{url(nueva)}"); }}
body {{ font-family: sans-serif; margin: 2rem; line-height: 1.2; }}
h2 {{ font-size: 1rem; font-weight: normal; margin: 2rem 0 .25rem; }}
p {{ margin: 0; overflow-wrap: anywhere; }}
.original {{ font-family: "Original", monospace; }}
.nueva {{ font-family: "Nueva", monospace; }}
.chico {{ font-size: 2rem; }}
.grande {{ font-size: 6rem; }}
</style>
<h2>Original</h2>
<p class="original chico">{texto}</p>
<p class="original grande">{texto}</p>
<h2>Nueva</h2>
<p class="nueva chico">{texto}</p>
<p class="nueva grande">{texto}</p>
""",
        encoding="utf-8",
    )
