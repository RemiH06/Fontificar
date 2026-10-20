"""Fontificar: amplía la cobertura de una fuente TTF con glifos derivados.

v1: español (á é í ó ú ü ñ, sus mayúsculas, ¡ ¿ y los acentos sueltos ´ ¨).
Los glifos que la fuente ya trae no se tocan; solo se agregan los que faltan.
Los acentos se derivan de glifos existentes (`grave`, `asciitilde`, `period`)
en vez de dibujar contornos nuevos.
"""
import argparse
import html
import os
import shutil
import sys
import unicodedata
from pathlib import Path
from urllib.parse import quote

from fontTools.agl import UV2AGL
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

IDIOMAS = {"es": "áéíóúüñÁÉÍÓÚÜÑ¡¿´¨"}

# Letras que se giran 180° (destino: origen).
GIROS = {0xA1: 0x21, 0xBF: 0x3F}

# Espacio entre la letra y el acento, en fracción del em.
HUECO = 0.06

SUFIJO_NOMBRE = "Español"
SUFIJO_NOMBRE_PS = "Espanol"  # el nombre PostScript solo admite ASCII

TEXTO_MUESTRA = "Canción, pingüino, ¿Qué tal? ¡Hola! ÁÉÍÓÚÜÑ áéíóúüñ"


def _limites(conjunto, nombre):
    """Caja (xmin, ymin, xmax, ymax) del glifo `nombre`; error si no tiene contorno."""
    lapiz = BoundsPen(conjunto)
    conjunto[nombre].draw(lapiz)
    if lapiz.bounds is None:
        raise ValueError(f"el glifo '{nombre}' no tiene contorno")
    return lapiz.bounds


def _glifo_de(cmap, codepoint):
    if codepoint not in cmap:
        raise ValueError(f"la fuente no trae U+{codepoint:04X} y hace falta para derivar los nuevos")
    return cmap[codepoint]


def _agregar(fuente, nombre, glifo, avance):
    """Registra el glifo nuevo en `glyf`, `hmtx` y el orden de glifos."""
    if nombre in fuente.getGlyphOrder():
        raise ValueError(f"el glifo '{nombre}' ya existe")
    fuente.setGlyphOrder(fuente.getGlyphOrder() + [nombre])
    fuente["glyf"][nombre] = glifo
    glifo.recalcBounds(fuente["glyf"])
    fuente["hmtx"][nombre] = (avance, glifo.xMin)


def _transformado(fuente, nombre, matriz):
    """Glifo simple con el contorno de `nombre` transformado por `matriz`."""
    conjunto = fuente.getGlyphSet()
    grabado = DecomposingRecordingPen(conjunto)
    conjunto[nombre].draw(grabado)
    lapiz = TTGlyphPen(conjunto)
    grabado.replay(TransformPen(lapiz, matriz))
    return lapiz.glyph()


def _primer_contorno(trazos):
    fin = next(i for i, (op, _) in enumerate(trazos) if op in ("closePath", "endPath"))
    return trazos[: fin + 1]


def _acento_agudo(fuente, cmap):
    """Espejo horizontal de `grave`, alrededor de su propio centro."""
    grave = _glifo_de(cmap, 0x60)
    x0, _, x1, _ = _limites(fuente.getGlyphSet(), grave)
    return _transformado(fuente, grave, (-1, 0, 0, 1, x0 + x1, 0)), fuente["hmtx"][grave][0]


def _dieresis(fuente, cmap):
    """Dos puntos macizos: el contorno exterior de `period`, a la mitad de tamaño,
    con la base a la misma altura que `grave`."""
    conjunto = fuente.getGlyphSet()
    punto = _glifo_de(cmap, 0x2E)
    grave = _glifo_de(cmap, 0x60)
    lapiz = BoundsPen(conjunto)
    rec = DecomposingRecordingPen(conjunto)
    conjunto[punto].draw(rec)
    rec.value = _primer_contorno(rec.value)
    rec.replay(lapiz)
    x0, y0, x1, _ = lapiz.bounds
    escala, separacion = 0.5, 60
    lado = (x1 - x0) * escala
    avance = fuente["hmtx"][punto][0]
    inicio = (avance - (2 * lado + separacion)) / 2
    base = _limites(conjunto, grave)[1]
    salida = TTGlyphPen(conjunto)
    for i in (0, 1):
        matriz = (escala, 0, 0, escala, inicio + i * (lado + separacion) - x0 * escala, base - y0 * escala)
        rec.replay(TransformPen(salida, matriz))
    return salida.glyph(), avance


# Marca combinante -> (codepoint del acento suelto, cómo obtenerlo si falta).
# La tilde ya existe como `asciitilde` (U+007E) y se usa tal cual.
MARCAS = {
    0x0301: (0xB4, _acento_agudo),
    0x0308: (0xA8, _dieresis),
    0x0303: (0x7E, None),
}


def _compuesto(fuente, base, marca):
    """Letra base más acento, el acento centrado y a `HUECO` por encima de la base.

    Usar la caja de la base (no una altura fija) hace que sirva igual con
    minúsculas bajas, mayúsculas altas o una fuente unicase.
    """
    conjunto = fuente.getGlyphSet()
    bx0, _, bx1, by1 = _limites(conjunto, base)
    mx0, my0, mx1, _ = _limites(conjunto, marca)
    dx = round((bx0 + bx1) / 2 - (mx0 + mx1) / 2)
    dy = round(by1 + HUECO * fuente["head"].unitsPerEm - my0)
    lapiz = TTGlyphPen(conjunto)
    lapiz.addComponent(base, (1, 0, 0, 1, 0, 0))
    lapiz.addComponent(marca, (1, 0, 0, 1, dx, dy))
    return lapiz.glyph(), fuente["hmtx"][base][0]


def _girado(fuente, origen):
    """Giro de 180° alrededor del centro de la caja del glifo (conserva el avance)."""
    x0, y0, x1, y1 = _limites(fuente.getGlyphSet(), origen)
    return _transformado(fuente, origen, (-1, 0, 0, -1, x0 + x1, y0 + y1)), fuente["hmtx"][origen][0]


def _nombre_glifo(codepoint):
    return UV2AGL.get(codepoint) or f"uni{codepoint:04X}"


def _registrar_cmap(fuente, nuevos):
    """Agrega los codepoints a las subtablas Unicode y, con su código MacRoman, a la de Mac."""
    for tabla in fuente["cmap"].tables:
        if tabla.isUnicode():
            tabla.cmap.update(nuevos)
        elif tabla.platformID == 1 and tabla.platEncID == 0:
            for codepoint, nombre in nuevos.items():
                try:
                    tabla.cmap[chr(codepoint).encode("mac_roman")[0]] = nombre
                except UnicodeEncodeError:
                    pass  # ese caracter no existe en MacRoman


def _renombrar(fuente):
    """Aumenta (no reemplaza) el nombre de la familia, como pide la licencia de Larabie."""
    nombres = fuente["name"]
    for registro in list(nombres.names):
        if registro.nameID in (1, 4):
            texto = f"{registro.toUnicode()} {SUFIJO_NOMBRE}"
        elif registro.nameID == 3:
            texto = f"{registro.toUnicode()} {SUFIJO_NOMBRE_PS}"
        elif registro.nameID == 6:
            texto = f"{registro.toUnicode()}-{SUFIJO_NOMBRE_PS}"
        else:
            continue
        nombres.setName(texto, registro.nameID, registro.platformID, registro.platEncID, registro.langID)


def fontificar(entrada, salida, idioma="es"):
    """Genera `salida` a partir de `entrada` con los glifos que falten del idioma.

    Devuelve {codepoint: nombre de glifo} de lo agregado; si no falta nada, falla
    (así no se renombra dos veces una fuente ya ampliada).
    """
    if idioma not in IDIOMAS:
        raise ValueError(f"idioma desconocido '{idioma}' (disponibles: {', '.join(IDIOMAS)})")
    entrada, salida = Path(entrada), Path(salida)
    if entrada.resolve() == salida.resolve():
        raise ValueError("la salida no puede ser el mismo archivo que la entrada")

    fuente = TTFont(entrada)
    if "glyf" not in fuente:
        raise ValueError("solo se admiten fuentes TrueType (glyf); el camino CFF/OTF está pendiente")
    cmap = fuente.getBestCmap()
    nuevos = {}

    # Acentos sueltos: se usa el que ya trae la fuente o se deriva y se agrega.
    marcas = {}
    for combinante, (suelto, derivar) in MARCAS.items():
        if suelto in cmap:
            marcas[combinante] = cmap[suelto]
        elif derivar is None:
            raise ValueError(f"la fuente no trae U+{suelto:04X}, que hace falta como acento")
        else:
            nombre = _nombre_glifo(suelto)
            _agregar(fuente, nombre, *derivar(fuente, cmap))
            marcas[combinante] = nuevos[suelto] = nombre

    for caracter in IDIOMAS[idioma]:
        codepoint = ord(caracter)
        if codepoint in cmap or codepoint in nuevos:
            continue
        if codepoint in GIROS:
            glifo, avance = _girado(fuente, _glifo_de(cmap, GIROS[codepoint]))
        else:
            letra, *resto = unicodedata.normalize("NFD", caracter)
            if len(resto) != 1 or ord(resto[0]) not in marcas:
                raise ValueError(f"no sé derivar '{caracter}' (U+{codepoint:04X})")
            glifo, avance = _compuesto(fuente, _glifo_de(cmap, ord(letra)), marcas[ord(resto[0])])
        nombre = _nombre_glifo(codepoint)
        _agregar(fuente, nombre, glifo, avance)
        nuevos[codepoint] = nombre

    if not nuevos:
        raise ValueError(f"la fuente ya cubre el idioma '{idioma}', no hay nada que agregar")
    _registrar_cmap(fuente, nuevos)
    _ajustar_metricas(fuente, nuevos.values())
    _renombrar(fuente)
    if "hdmx" in fuente:
        del fuente["hdmx"]  # sus anchos por tamaño no cubren los glifos nuevos
    fuente["OS/2"].recalcUnicodeRanges(fuente)

    salida.parent.mkdir(parents=True, exist_ok=True)
    fuente.save(salida)
    return nuevos


def _ajustar_metricas(fuente, nombres):
    """Sube el ascendente si algún acento nuevo se sale, para que no lo recorten."""
    techo = max(fuente["glyf"][n].yMax for n in nombres)
    sobra = techo - fuente["hhea"].ascent
    if sobra > 0:
        fuente["hhea"].ascent += sobra
        fuente["OS/2"].sTypoAscender += sobra
    fuente["OS/2"].usWinAscent = max(fuente["OS/2"].usWinAscent, techo)


def escribir_muestra(original, nueva, ruta):
    """Página HTML estática que pone el mismo texto con la fuente original y la nueva."""
    base = Path(ruta).parent

    def url(fuente):
        return quote(Path(os.path.relpath(fuente, base)).as_posix())

    texto = html.escape(TEXTO_MUESTRA)
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
p {{ margin: 0; }}
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


def principal(argumentos=None):
    analizador = argparse.ArgumentParser(description="Amplía la cobertura de una fuente TTF.")
    analizador.add_argument("entrada", help="fuente TTF de entrada")
    analizador.add_argument("salida", help="fuente TTF de salida")
    analizador.add_argument("--idioma", default="es", choices=sorted(IDIOMAS))
    analizador.add_argument("--licencia", help="licencia de la fuente a copiar junto a la salida "
                            "(por omisión, read_me.txt junto a la entrada)")
    args = analizador.parse_args(argumentos)

    try:
        nuevos = fontificar(args.entrada, args.salida, args.idioma)
    except (ValueError, OSError) as error:
        sys.exit(f"error: {error}")
    print(f"{len(nuevos)} glifos nuevos en {args.salida}")

    salida = Path(args.salida)
    licencia = Path(args.licencia) if args.licencia else Path(args.entrada).parent / "read_me.txt"
    if licencia.is_file():
        shutil.copyfile(licencia, salida.with_name(f"{salida.stem}-licencia.txt"))
    else:
        print(f"aviso: no encontré la licencia ({licencia}); publicar la fuente exige copiarla", file=sys.stderr)

    muestra = Path(os.path.commonpath([Path(args.entrada).resolve().parent, salida.resolve().parent])) / "muestra.html"
    escribir_muestra(args.entrada, args.salida, muestra)
    print(f"muestra: {muestra}")


if __name__ == "__main__":
    principal()
