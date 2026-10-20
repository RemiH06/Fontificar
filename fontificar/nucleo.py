"""`fontificar()`: recorre los caracteres del idioma, agrega los que se puedan derivar
de lo que trae la fuente, omite (con su motivo) los que no y ajusta las tablas."""
import io
import unicodedata
from pathlib import Path
from typing import NamedTuple

from fontTools.ttLib import TTFont

from .acentos import ARRIBA, MARCAS, compuesto, marca
from .especiales import ESPECIALES, GIROS, girado, sin_punto, tiene_punto
from .glifos import Obra, limites
from .idiomas import IDIOMAS

# Letras que pierden el punto bajo un acento de arriba (í, ĵ) y su versión sin punto.
SIN_PUNTO = {"i": 0x131, "j": 0x237}


class Resultado(NamedTuple):
    nuevos: dict  # {codepoint: nombre de glifo} de lo agregado
    omitidos: dict  # {codepoint: motivo} de lo que no se pudo derivar


def _registrar_cmap(fuente, nuevos):
    """Agrega los codepoints a las subtablas Unicode y, con su código MacRoman, a la de Mac.
    Una subtabla de formato 0 guarda el índice de glifo en un byte: los glifos con
    índice de 256 en adelante no caben y se quedan fuera de ella."""
    for tabla in fuente["cmap"].tables:
        cabe = {c: n for c, n in nuevos.items() if tabla.format != 0 or fuente.getGlyphID(n) < 256}
        if tabla.isUnicode():
            tabla.cmap.update(cabe)
        elif tabla.platformID == 1 and tabla.platEncID == 0:
            for codepoint, nombre in cabe.items():
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
    if "CFF " in fuente:  # el nombre PostScript también vive dentro de la tabla CFF
        cff = fuente["CFF "].cff
        cff.fontNames = [f"{n}-{idioma.sufijo_ps}" for n in cff.fontNames]
        superior = cff.topDictIndex[0]
        for campo in ("FamilyName", "FullName"):
            if hasattr(superior, campo):
                setattr(superior, campo, f"{getattr(superior, campo)} {idioma.sufijo}")


def _ajustar_metricas(obra):
    """Sube el ascendente o baja el descendente si algún glifo nuevo se sale, para que
    no lo recorten."""
    fuente, conjunto = obra.fuente, obra.conjunto
    cajas = [limites(conjunto, n) for n in obra.nuevos.values()]
    techo = round(max(c[3] for c in cajas))
    sobra = techo - fuente["hhea"].ascent
    if sobra > 0:
        fuente["hhea"].ascent += sobra
        fuente["OS/2"].sTypoAscender += sobra
    fuente["OS/2"].usWinAscent = max(fuente["OS/2"].usWinAscent, techo)

    piso = round(min(c[1] for c in cajas))
    sobra = fuente["hhea"].descent - piso
    if sobra > 0:
        fuente["hhea"].descent -= sobra
        fuente["OS/2"].sTypoDescender -= sobra
    fuente["OS/2"].usWinDescent = max(fuente["OS/2"].usWinDescent, -piso)


def _base(obra, letra, posicion):
    """Glifo de la letra base. Bajo un acento de arriba, la i y la j van sin punto: la
    que trae la fuente (ı ȷ) o una derivada, que también se mapea."""
    nombre = obra.letra(letra)
    if posicion != ARRIBA or letra not in SIN_PUNTO or not tiene_punto(obra, nombre):
        return nombre
    try:
        return obra.glifo(SIN_PUNTO[letra])
    except ValueError:
        pass
    clave = ("sin punto", letra)
    if clave not in obra.derivados:
        obra.derivados[clave] = obra.agregar(SIN_PUNTO[letra], *sin_punto(obra, letra))
    return obra.derivados[clave]


def _derivar(obra, caracter):
    """(grabado, avance) del caracter, o ValueError con el motivo si no se puede."""
    codepoint = ord(caracter)
    if codepoint in GIROS:
        return girado(obra, obra.glifo(GIROS[codepoint]))
    if codepoint in ESPECIALES:
        derivar, argumentos = ESPECIALES[codepoint]
        return derivar(obra, *argumentos)
    letra, *resto = unicodedata.normalize("NFD", caracter)
    if len(resto) != 1 or ord(resto[0]) not in MARCAS:
        raise ValueError("no sé derivarlo")
    posicion = MARCAS[ord(resto[0])][2]
    return compuesto(obra, _base(obra, letra, posicion), marca(obra, ord(resto[0])), posicion)


def fontificar(entrada, salida, idioma="es"):
    """Genera `salida` a partir de `entrada` con los glifos que falten del idioma y se
    puedan derivar de lo que trae la fuente (TrueType u OpenType CFF). Un caracter
    mapeado a un glifo vacío cuenta como faltante: se mapea al glifo nuevo y el vacío
    se queda en la fuente sin tocar.

    `entrada` es una ruta o los bytes de la fuente (por ejemplo, leída de un zip). Con
    `salida=None` no se escribe nada: solo se averigua qué se agregaría y qué no.

    Devuelve un `Resultado` con lo agregado y lo omitido. Falla si no se agregó nada:
    porque la fuente ya cubre el idioma (así no se renombra dos veces) o porque nada
    se pudo derivar.
    """
    if idioma not in IDIOMAS:
        raise ValueError(f"idioma desconocido '{idioma}' (disponibles: {', '.join(IDIOMAS)})")
    clave, idioma = idioma, IDIOMAS[idioma]
    if isinstance(entrada, (bytes, bytearray)):
        fuente = TTFont(io.BytesIO(entrada))
    else:
        entrada = Path(entrada)
        if salida is not None and entrada.resolve() == Path(salida).resolve():
            raise ValueError("la salida no puede ser el mismo archivo que la entrada")
        fuente = TTFont(entrada)

    obra = Obra(fuente)
    omitidos = {}
    sueltos = {suelto: combinante for combinante, (suelto, _, _) in MARCAS.items()}
    for caracter in idioma.caracteres:
        codepoint = ord(caracter)
        if obra.cubre(codepoint):  # lo trae la fuente con dibujo o ya se agregó
            continue
        try:
            if codepoint in sueltos:
                marca(obra, sueltos[codepoint])
            else:
                obra.agregar(codepoint, *_derivar(obra, caracter))
        except ValueError as error:
            omitidos[codepoint] = str(error)

    if not obra.nuevos:
        if omitidos:
            raise ValueError(f"no pude derivar ningún caracter del idioma '{clave}': "
                             + "; ".join(f"{chr(c)}: {m}" for c, m in omitidos.items()))
        raise ValueError(f"la fuente ya cubre el idioma '{clave}', no hay nada que agregar")
    if salida is None:
        return Resultado(obra.nuevos, omitidos)
    salida = Path(salida)
    fuente = obra.fuente
    _registrar_cmap(fuente, obra.nuevos)
    _ajustar_metricas(obra)
    _renombrar(fuente, idioma)
    if "hdmx" in fuente:
        del fuente["hdmx"]  # sus anchos por tamaño no cubren los glifos nuevos
    fuente["OS/2"].recalcUnicodeRanges(fuente)

    salida.parent.mkdir(parents=True, exist_ok=True)
    fuente.save(salida)
    return Resultado(obra.nuevos, omitidos)
