"""Fontificar: amplía la cobertura de una fuente TTF con glifos derivados.

Idiomas: español (`es`) y Latin-1 (`latin1`: sus letras, más Œ œ Ÿ, sin Ð ð Þ þ).
Los glifos que la fuente ya trae no se tocan; solo se agregan los que faltan.
Los acentos se derivan de glifos existentes (`grave`, `asciitilde`,
`asciicircum`, `period`, `comma`) en vez de dibujar contornos nuevos.
"""
import argparse
import html
import os
import shutil
import sys
import unicodedata
from pathlib import Path
from typing import NamedTuple
from urllib.parse import quote

from fontTools.agl import UV2AGL
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont


class Idioma(NamedTuple):
    caracteres: str
    sufijo: str  # se agrega al nombre de la familia
    sufijo_ps: str  # el nombre PostScript solo admite ASCII
    muestra: str


IDIOMAS = {
    "es": Idioma("áéíóúüñÁÉÍÓÚÜÑ¡¿´¨", "Español", "Espanol",
                 "Canción, pingüino, ¿Qué tal? ¡Hola!"),
    "latin1": Idioma(
        "ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÑÒÓÔÕÖØÙÚÛÜÝßàáâãäåæçèéêëìíîïñòóôõöøùúûüýÿŒœŸ¡¿´¨¸",
        "Latino", "Latino",
        "Façade, crème brûlée, Ångström, smørrebrød, cœur, naïveté, Straße, ¿Qué tal?"),
}

# Letras que se giran 180° (destino: origen).
GIROS = {0xA1: 0x21, 0xBF: 0x3F}

# Espacio entre la letra y el acento, en fracción del em.
HUECO = 0.06

# Escalas de los acentos derivados (x, y). Se eligieron a ojo sobre Y2KBUG para que
# el trazo quede parecido al de `grave` sin subir de más el ascendente.
ESCALA_CIRCUNFLEJO = (0.6, 0.45)
ESCALA_ANILLO = (0.6, 0.6)
ESCALA_CEDILLA = (0.6, -0.6)  # negativa en y: la coma se voltea


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
    """Glifo simple con el contorno de `nombre` transformado por `matriz`.

    Un espejo (determinante negativo) invierte el sentido de los contornos; se
    revierten para conservar el del original, que decide qué es relleno y qué hueco.
    """
    conjunto = fuente.getGlyphSet()
    grabado = DecomposingRecordingPen(conjunto)
    conjunto[nombre].draw(grabado)
    lapiz = TTGlyphPen(conjunto)
    a, b, c, d = matriz[:4]
    destino = ReverseContourPen(lapiz) if a * d - b * c < 0 else lapiz
    grabado.replay(TransformPen(destino, matriz))
    return lapiz.glyph()


def _reducido(fuente, origen, escala, piso=None, techo=None):
    """Contorno de `origen` escalado por `escala` (x, y), centrado en su avance escalado
    y con la parte de abajo en `piso` o la de arriba en `techo`. Una y negativa lo voltea."""
    sx, sy = escala
    x0, y0, x1, y1 = _limites(fuente.getGlyphSet(), origen)
    xs, ys = sorted((x0 * sx, x1 * sx)), sorted((y0 * sy, y1 * sy))
    avance = round(fuente["hmtx"][origen][0] * abs(sx))
    dx = (avance - (xs[1] - xs[0])) / 2 - xs[0]
    dy = piso - ys[0] if piso is not None else techo - ys[1]
    return _transformado(fuente, origen, (sx, 0, 0, sy, dx, dy)), avance


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


def _circunflejo(fuente, cmap):
    """`asciicircum` reducido (completo es demasiado alto), con la base a la altura de `grave`."""
    piso = _limites(fuente.getGlyphSet(), _glifo_de(cmap, 0x60))[1]
    return _reducido(fuente, _glifo_de(cmap, 0x5E), ESCALA_CIRCUNFLEJO, piso=piso)


def _anillo(fuente, cmap):
    """`period` reducido (en Y2KBUG ya es un anillo), con la base a la altura de `grave`."""
    piso = _limites(fuente.getGlyphSet(), _glifo_de(cmap, 0x60))[1]
    return _reducido(fuente, _glifo_de(cmap, 0x2E), ESCALA_ANILLO, piso=piso)


def _cedilla(fuente, cmap):
    """`comma` volteada en vertical y reducida, colgando de la línea base:
    baja del centro y se enrosca hacia la izquierda."""
    return _reducido(fuente, _glifo_de(cmap, 0x2C), ESCALA_CEDILLA, techo=0)


# Marca combinante -> (codepoint del acento suelto, cómo obtenerlo si falta, va debajo).
# `grave` y la tilde (`asciitilde`) ya existen y se usan tal cual. `asciicircum`
# también existe, pero como acento es demasiado alto: se agrega reducido como U+02C6.
MARCAS = {
    0x0300: (0x60, None, False),
    0x0301: (0xB4, _acento_agudo, False),
    0x0302: (0x2C6, _circunflejo, False),
    0x0303: (0x7E, None, False),
    0x0308: (0xA8, _dieresis, False),
    0x030A: (0x2DA, _anillo, False),
    0x0327: (0xB8, _cedilla, True),
}


def _compuesto(fuente, base, marca, debajo=False):
    """Letra base más acento, centrado. Arriba queda a `HUECO` de la base; debajo
    (cedilla) queda pegado a ella.

    Usar la caja de la base (no una altura fija) hace que sirva igual con
    minúsculas bajas, mayúsculas altas o una fuente unicase.

    Si el acento más `HUECO` no cabe en el avance de la base (í, ï, î), el avance
    crece lo justo y la base se recorre a la mitad, para no chocar con la vecina.
    """
    conjunto = fuente.getGlyphSet()
    hueco = HUECO * fuente["head"].unitsPerEm
    bx0, by0, bx1, by1 = _limites(conjunto, base)
    mx0, my0, mx1, my1 = _limites(conjunto, marca)
    avance = fuente["hmtx"][base][0]
    extra = max(0, round(mx1 - mx0 + hueco) - avance)
    corrimiento = extra // 2
    dx = round((bx0 + bx1) / 2 - (mx0 + mx1) / 2) + corrimiento
    if debajo:
        dy = round(by0 - my1)
    else:
        dy = round(by1 + hueco - my0)
    lapiz = TTGlyphPen(conjunto)
    lapiz.addComponent(base, (1, 0, 0, 1, corrimiento, 0))
    lapiz.addComponent(marca, (1, 0, 0, 1, dx, dy))
    return lapiz.glyph(), avance + extra


def _superpuesto(fuente, cmap, base, encima):
    """`encima` centrado sobre `base` a la misma altura (Ø: O más `slash`)."""
    conjunto = fuente.getGlyphSet()
    base, encima = _glifo_de(cmap, ord(base)), _glifo_de(cmap, ord(encima))
    bx0, _, bx1, _ = _limites(conjunto, base)
    ex0, _, ex1, _ = _limites(conjunto, encima)
    lapiz = TTGlyphPen(conjunto)
    lapiz.addComponent(base, (1, 0, 0, 1, 0, 0))
    lapiz.addComponent(encima, (1, 0, 0, 1, round((bx0 + bx1) / 2 - (ex0 + ex1) / 2), 0))
    return lapiz.glyph(), fuente["hmtx"][base][0]


def _unido(fuente, cmap, izquierda, derecha):
    """Dos letras que comparten un asta (Æ, Œ): `derecha` se recorre hasta que su borde
    izquierdo cae dentro del borde derecho de `izquierda` el ancho de un asta.

    El ancho del asta se toma de la `i`, que en la mayoría de las fuentes es una barra.
    """
    conjunto = fuente.getGlyphSet()
    izquierda, derecha = _glifo_de(cmap, ord(izquierda)), _glifo_de(cmap, ord(derecha))
    ix0, _, ix1, _ = _limites(conjunto, _glifo_de(cmap, ord("i")))
    dx = round(_limites(conjunto, izquierda)[2] - (ix1 - ix0) - _limites(conjunto, derecha)[0])
    lapiz = TTGlyphPen(conjunto)
    lapiz.addComponent(izquierda, (1, 0, 0, 1, 0, 0))
    lapiz.addComponent(derecha, (1, 0, 0, 1, dx, 0))
    return lapiz.glyph(), dx + fuente["hmtx"][derecha][0]


def _volteado(fuente, cmap, letra):
    """Espejo vertical alrededor del centro de la caja (ß: en Y2KBUG la `B` es un asta
    más un "3" unido abajo; volteada, la unión queda arriba como en la ß)."""
    origen = _glifo_de(cmap, ord(letra))
    _, y0, _, y1 = _limites(fuente.getGlyphSet(), origen)
    return _transformado(fuente, origen, (1, 0, 0, -1, 0, y0 + y1)), fuente["hmtx"][origen][0]


# Letras que no salen por descomposición NFD (destino: cómo y de qué caracteres).
ESPECIALES = {
    0xD8: (_superpuesto, "O/"),
    0xF8: (_superpuesto, "o/"),
    0xC6: (_unido, "AE"),
    0xE6: (_unido, "ae"),
    0x152: (_unido, "OE"),
    0x153: (_unido, "oe"),
    0xDF: (_volteado, "B"),
}


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


def _renombrar(fuente, idioma):
    """Aumenta (no reemplaza) el nombre de la familia, como pide la licencia de Larabie."""
    nombres = fuente["name"]
    for registro in list(nombres.names):
        if registro.nameID in (1, 4):
            texto = f"{registro.toUnicode()} {idioma.sufijo}"
        elif registro.nameID == 3:
            texto = f"{registro.toUnicode()} {idioma.sufijo_ps}"
        elif registro.nameID == 6:
            texto = f"{registro.toUnicode()}-{idioma.sufijo_ps}"
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
    clave, idioma = idioma, IDIOMAS[idioma]
    entrada, salida = Path(entrada), Path(salida)
    if entrada.resolve() == salida.resolve():
        raise ValueError("la salida no puede ser el mismo archivo que la entrada")

    fuente = TTFont(entrada)
    if "glyf" not in fuente:
        raise ValueError("solo se admiten fuentes TrueType (glyf); el camino CFF/OTF está pendiente")
    cmap = fuente.getBestCmap()
    nuevos = {}

    def marca(combinante):
        """Glifo del acento suelto: el que ya trae la fuente o, si falta, se deriva y
        se agrega. Solo se agregan los que el idioma usa."""
        suelto, derivar, _ = MARCAS[combinante]
        if suelto in cmap:
            return cmap[suelto]
        if suelto in nuevos:
            return nuevos[suelto]
        if derivar is None:
            raise ValueError(f"la fuente no trae U+{suelto:04X}, que hace falta como acento")
        nombre = _nombre_glifo(suelto)
        _agregar(fuente, nombre, *derivar(fuente, cmap))
        nuevos[suelto] = nombre
        return nombre

    sueltos = {suelto: combinante for combinante, (suelto, _, _) in MARCAS.items()}
    for caracter in idioma.caracteres:
        codepoint = ord(caracter)
        if codepoint in cmap or codepoint in nuevos:
            continue
        if codepoint in sueltos:
            marca(sueltos[codepoint])
            continue
        if codepoint in GIROS:
            glifo, avance = _girado(fuente, _glifo_de(cmap, GIROS[codepoint]))
        elif codepoint in ESPECIALES:
            derivar, letras = ESPECIALES[codepoint]
            glifo, avance = derivar(fuente, cmap, *letras)
        else:
            letra, *resto = unicodedata.normalize("NFD", caracter)
            if len(resto) != 1 or ord(resto[0]) not in MARCAS:
                raise ValueError(f"no sé derivar '{caracter}' (U+{codepoint:04X})")
            combinante = ord(resto[0])
            glifo, avance = _compuesto(fuente, _glifo_de(cmap, ord(letra)), marca(combinante),
                                       debajo=MARCAS[combinante][2])
        nombre = _nombre_glifo(codepoint)
        _agregar(fuente, nombre, glifo, avance)
        nuevos[codepoint] = nombre

    if not nuevos:
        raise ValueError(f"la fuente ya cubre el idioma '{clave}', no hay nada que agregar")
    _registrar_cmap(fuente, nuevos)
    _ajustar_metricas(fuente, nuevos.values())
    _renombrar(fuente, idioma)
    if "hdmx" in fuente:
        del fuente["hdmx"]  # sus anchos por tamaño no cubren los glifos nuevos
    fuente["OS/2"].recalcUnicodeRanges(fuente)

    salida.parent.mkdir(parents=True, exist_ok=True)
    fuente.save(salida)
    return nuevos


def _ajustar_metricas(fuente, nombres):
    """Sube el ascendente o baja el descendente si algún glifo nuevo se sale, para que
    no lo recorten."""
    techo = max(fuente["glyf"][n].yMax for n in nombres)
    sobra = techo - fuente["hhea"].ascent
    if sobra > 0:
        fuente["hhea"].ascent += sobra
        fuente["OS/2"].sTypoAscender += sobra
    fuente["OS/2"].usWinAscent = max(fuente["OS/2"].usWinAscent, techo)

    piso = min(fuente["glyf"][n].yMin for n in nombres)
    sobra = fuente["hhea"].descent - piso
    if sobra > 0:
        fuente["hhea"].descent -= sobra
        fuente["OS/2"].sTypoDescender -= sobra
    fuente["OS/2"].usWinDescent = max(fuente["OS/2"].usWinDescent, -piso)


def escribir_muestra(original, nueva, ruta, idioma="es"):
    """Página HTML estática que pone el mismo texto con la fuente original y la nueva."""
    base = Path(ruta).parent

    def url(fuente):
        return quote(Path(os.path.relpath(fuente, base)).as_posix())

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
    escribir_muestra(args.entrada, args.salida, muestra, args.idioma)
    print(f"muestra: {muestra}")


if __name__ == "__main__":
    principal()
