"""Letras que no salen de letra base más acento: giros, ligaduras, tachadas y copias.

Las reglas que dependen de la forma de la letra (dónde está el asta de la `D`, si
la `i` tiene punto, si la `B` volteada parece ß) se miden en la fuente en vez de
suponerse.
"""
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen

from .acentos import puntos
from .glifos import (ancho_de_asta, caja_de, componentes, con_tinta, contornos, grosor_de_punto,
                     grupos_verticales, limites, trazo_de_punto, transformado)

# Letras que se giran 180° (destino: origen).
GIROS = {0xA1: 0x21, 0xBF: 0x3F}

# Trazos para cruzar letras, en orden de preferencia.
GUIONES = (0x2D, 0x2013, 0x2212, 0x5F)
DIAGONALES = (0x2F, 0x2215, 0x2044)

# Muestras por lado al medir la forma de una letra.
MUESTRAS = 20


def girado(obra, origen):
    """Giro de 180° alrededor del centro de la caja del glifo (conserva el avance)."""
    x0, y0, x1, y1 = limites(obra.conjunto, origen)
    return transformado(obra, (origen, (-1, 0, 0, -1, x0 + x1, y0 + y1))), obra.avance(origen)


def tiene_punto(obra, nombre):
    """¿La letra es un asta con un punto aparte arriba (i, j)? Dos grupos de contornos
    separados en vertical, el de arriba chico. Una `i` hecha de puntos (Fortuna Dot)
    tiene muchos grupos y no cuenta."""
    grupos = grupos_verticales(obra.conjunto, nombre)
    return len(grupos) == 2 and grupos[1][1] - grupos[1][0] < (grupos[0][1] - grupos[0][0]) / 2


def sin_punto(obra, letra):
    """La letra sin su punto (ı ȷ), o tal cual si no tiene."""
    origen = obra.letra(letra)
    if not tiene_punto(obra, origen):
        return componentes((origen, 0, 0)), obra.avance(origen)
    techo = grupos_verticales(obra.conjunto, origen)[0][1]
    grabado = RecordingPen()
    grabado.value = [t for c in contornos(obra.conjunto, origen) if caja_de(c)[3] <= techo for t in c]
    return grabado, obra.avance(origen)


def _lado_del_asta(obra, nombre):
    """'izquierda' o 'derecha': de qué lado la letra tiene un asta de arriba a abajo
    (en Y2KBUG la `D` es una `d`, con el asta a la derecha). Empate: izquierda."""
    conjunto = obra.conjunto
    x0, y0, x1, y1 = limites(conjunto, nombre)
    grosor = ancho_de_asta(obra)
    alturas = [y0 + (k + 0.5) * (y1 - y0) / MUESTRAS for k in range(MUESTRAS)]
    izquierda = sum(con_tinta(conjunto, nombre, x0 + grosor / 2, y) for y in alturas)
    derecha = sum(con_tinta(conjunto, nombre, x1 - grosor / 2, y) for y in alturas)
    return "derecha" if derecha > izquierda else "izquierda"


def _unida_solo_abajo(obra, nombre):
    """¿El asta izquierda de la letra se une al resto abajo pero no arriba? En Y2KBUG
    la `B` es un asta más un "3" unido abajo: volteada, la unión queda arriba como en
    la ß. En una `B` normal (unida arriba y abajo) volteada sigue siendo una B."""
    conjunto = obra.conjunto
    x0, y0, x1, y1 = limites(conjunto, nombre)
    grosor = ancho_de_asta(obra)
    xs = [x0 + grosor + k * ((x1 - x0) / 2 - grosor) / MUESTRAS for k in range(MUESTRAS + 1)]

    def unida(y):
        return all(con_tinta(conjunto, nombre, x, y) for x in xs)

    return unida(y0 + grosor / 2) and not unida(y1 - grosor / 2)


def auxiliar(obra, clave, grabado, ancho, piso):
    """Glifo sin mapear con `grabado` puesto en `piso` y un margen de un grosor por lado."""
    if clave not in obra.derivados:
        margen = grosor_de_punto(obra)
        salida = RecordingPen()
        x0, y0, _, _ = caja_de(grabado.value)
        grabado.replay(TransformPen(salida, (1, 0, 0, 1, margen - x0, piso - y0)))
        obra.derivados[clave] = obra.agregar(None, salida, ancho + 2 * margen, nombre=f"{clave}.fontificar")
    return obra.derivados[clave]


def guion(obra):
    """El guion de la fuente o, si no trae ninguno, el punto estirado a lo ancho a media
    altura de la `x`."""
    try:
        return obra.signo(*GUIONES)
    except ValueError:
        pass
    grosor = grosor_de_punto(obra)
    ancho = 0.3 * obra.upm
    medio = limites(obra.conjunto, obra.letra("xoXO"))[3] / 2
    return auxiliar(obra, "guion", trazo_de_punto(obra, ancho, grosor), ancho, medio - grosor / 2)


def diagonal(obra):
    """La diagonal de la fuente o, si no trae ninguna, el punto estirado e inclinado de
    la línea base a la altura de las mayúsculas."""
    try:
        return obra.signo(*DIAGONALES)
    except ValueError:
        pass
    alto = limites(obra.conjunto, obra.letra("HIOA"))[3]
    trazo = trazo_de_punto(obra, grosor_de_punto(obra), alto, 0.5)
    x0, _, x1, _ = caja_de(trazo.value)
    return auxiliar(obra, "diagonal", trazo, x1 - x0, 0)


def asta_vertical(obra, ancho, alto):
    """El guion parado: un trazo vertical de `ancho` por `alto` con la esquina inferior
    izquierda en el origen. Conserva los remates del guion, a diferencia del punto
    estirado (que en una fuente de punto redondo sale como elipse)."""
    origen = guion(obra)
    gx0, gy0, gx1, gy1 = limites(obra.conjunto, origen)
    a, k = ancho / (gy1 - gy0), alto / (gx1 - gx0)
    # (x, y) pasa a (-a * y + dx, k * x + dy): lo largo del guion se vuelve lo alto.
    return transformado(obra, (origen, (0, k, -a, 0, a * gy1, -k * gx0)))


def _punto_medio(obra):
    """`·`: un punto a la altura del centro del guion."""
    _, y0, _, y1 = limites(obra.conjunto, guion(obra))
    return puntos(obra, 1, centro=(y0 + y1) / 2)


def _superpuesto(obra, base):
    """La diagonal (`/`) centrada sobre `base` a la misma altura (Ø: O más `slash`)."""
    conjunto = obra.conjunto
    base, encima = obra.letra(base), diagonal(obra)
    bx0, _, bx1, _ = limites(conjunto, base)
    ex0, _, ex1, _ = limites(conjunto, encima)
    return componentes((base, 0, 0), (encima, (bx0 + bx1) / 2 - (ex0 + ex1) / 2, 0)), obra.avance(base)


def _unido(obra, izquierda, derecha):
    """Dos letras que comparten un asta (Æ, Œ): `derecha` se recorre hasta que su borde
    izquierdo cae dentro del borde derecho de `izquierda` el grosor de un asta."""
    conjunto = obra.conjunto
    izquierda, derecha = obra.letra(izquierda), obra.letra(derecha)
    dx = round(limites(conjunto, izquierda)[2] - ancho_de_asta(obra) - limites(conjunto, derecha)[0])
    return componentes((izquierda, 0, 0), (derecha, dx, 0)), dx + obra.avance(derecha)


def _eszett(obra, b, s):
    """ß (o ẞ): la `B` volteada en vertical si su forma lo permite (ver
    `_unida_solo_abajo`); si no, dos `s` seguidas, que es como se escribe sin ß."""
    origen = obra.letra(b)
    if _unida_solo_abajo(obra, origen):
        _, y0, _, y1 = limites(obra.conjunto, origen)
        return transformado(obra, (origen, (1, 0, 0, -1, 0, y0 + y1))), obra.avance(origen)
    return _seguido(obra, s, s)


def tachado(obra, letra, trazo, donde, altura):
    """Letra cruzada por un trazo (Đ Ħ Ł Ŧ), con el centro a `altura` (fracción de la
    caja; puede depender del lado del asta).

    El guion solo se angosta, para conservar el grosor; la diagonal se reduce parejo
    (si no hay de dónde sacarla, se usa el guion). El trazo mide tres astas de ancho
    y se centra en el asta (`donde="asta"`, el lado se mide) o en el `centro` de la
    caja. Nunca se sale del avance, para no invadir a la vecina.
    """
    conjunto = obra.conjunto
    base = obra.letra(letra)
    plano = trazo == "-"
    try:
        origen = guion(obra) if plano else diagonal(obra)
    except ValueError:
        if plano:
            raise
        origen, plano = guion(obra), True
    bx0, by0, bx1, by1 = limites(conjunto, base)
    tx0, ty0, tx1, ty1 = limites(conjunto, origen)
    asta = ancho_de_asta(obra)
    if donde == "asta":
        donde = _lado_del_asta(obra, base)
    centros = {"izquierda": bx0 + asta / 2, "derecha": bx1 - asta / 2, "centro": (bx0 + bx1) / 2}
    if donde not in centros:
        raise ValueError(f"posición de trazo desconocida '{donde}'")
    if isinstance(altura, dict):
        altura = altura[donde]
    ancho = 3 * asta
    avance = obra.avance(base)
    centro = min(max(centros[donde], ancho / 2), avance - ancho / 2)
    sx = ancho / (tx1 - tx0)
    sy = 1 if plano else sx
    medio = by0 + altura * (by1 - by0)
    matriz = (sx, 0, 0, sy, centro - sx * (tx0 + tx1) / 2, medio - sy * (ty0 + ty1) / 2)
    return transformado(obra, (base, (1, 0, 0, 1, 0, 0)), (origen, matriz)), avance


def _con_punto_medio(obra, letra):
    """Ŀ ŀ: la letra más `·`, centrado entre el asta izquierda y el borde derecho."""
    conjunto = obra.conjunto
    base, punto = obra.letra(letra), obra.glifo(0xB7)
    bx0, _, bx1, _ = limites(conjunto, base)
    px0, _, px1, _ = limites(conjunto, punto)
    centro = (bx0 + ancho_de_asta(obra) + bx1) / 2
    return componentes((base, 0, 0), (punto, round(centro - (px0 + px1) / 2), 0)), obra.avance(base)


def _seguido(obra, izquierda, derecha):
    """Ĳ ĳ (y ß como `ss`): las dos letras una tras otra, sin compartir asta."""
    izquierda, derecha = obra.letra(izquierda), obra.letra(derecha)
    avance = obra.avance(izquierda)
    return componentes((izquierda, 0, 0), (derecha, avance, 0)), avance + obra.avance(derecha)


def _kra(obra):
    """ĸ: la `k` tal cual, solo si la fuente es unicase (la `k` mide lo mismo que la
    `K`); en una fuente con ascendentes, la `k` no sirve."""
    k, mayuscula = obra.letra("k"), obra.letra("K")
    _, ky0, _, ky1 = limites(obra.conjunto, k)
    _, my0, _, my1 = limites(obra.conjunto, mayuscula)
    if abs((ky1 - ky0) - (my1 - my0)) > 0.02 * (my1 - my0):
        raise ValueError("ĸ solo se deriva en fuentes unicase")
    return componentes((k, 0, 0)), obra.avance(k)


def _copia(obra, letra):
    """Otra letra tal cual."""
    origen = obra.letra(letra)
    return componentes((origen, 0, 0)), obra.avance(origen)


def _baja(obra, nombre):
    """¿El glifo baja de la línea base al menos un décimo de em (tiene descendente)?"""
    return limites(obra.conjunto, nombre)[1] < -0.1 * obra.upm


def _encimadas(obra, piezas):
    """Contornos de varias piezas (nombre o grabado, dx) encimados en un solo glifo."""
    grabado = RecordingPen()
    for pieza, dx in piezas:
        if isinstance(pieza, str):
            grabado.value += transformado(obra, (pieza, (1, 0, 0, 1, dx, 0))).value
        else:
            pieza.replay(TransformPen(grabado, (1, 0, 0, 1, dx, 0)))
    return grabado


def _thorn_minuscula(obra):
    """þ: la `b` encimada con la `p` (el asta de la `b` sube, el de la `p` baja y la
    panza es la misma), alineadas por la izquierda. Solo si la `p` tiene descendente
    y la `b` ascendente."""
    b, p = obra.letra("b"), obra.letra("p")
    conjunto = obra.conjunto
    if not _baja(obra, p):
        raise ValueError("la 'p' no tiene descendente")
    if limites(conjunto, b)[3] < limites(conjunto, p)[3] + 0.1 * obra.upm:
        raise ValueError("la 'b' no tiene ascendente")
    dx = round(limites(conjunto, b)[0] - limites(conjunto, p)[0])
    return _encimadas(obra, [(b, 0), (p, dx)]), max(obra.avance(b), obra.avance(p) + dx)


def _thorn_mayuscula(obra):
    """Þ: la `P` aplastada a 0.75 desde la base (su panza queda a media altura) más un
    asta de toda la altura encimada en la suya (si la `P` la tiene a la derecha, se
    refleja)."""
    conjunto = obra.conjunto
    p = obra.letra("P")
    x0, y0, x1, y1 = limites(conjunto, p)
    asta = ancho_de_asta(obra)
    espejo = _lado_del_asta(obra, p) == "derecha"
    matriz = (-1 if espejo else 1, 0, 0, 0.75, x0 + x1 if espejo else 0, 0.25 * y0)
    grabado = transformado(obra, (p, matriz))
    asta_vertical(obra, asta, y1 - y0).replay(TransformPen(grabado, (1, 0, 0, 1, x0, y0)))
    return grabado, obra.avance(p)


def _eng(obra, letra, jota):
    """ŋ (Ŋ): la `n` encimada con la `j` sin punto, alineadas por la derecha: el asta
    derecha de la `n` baja con el gancho de la `j`. Solo si la `j` tiene descendente."""
    conjunto = obra.conjunto
    base, j = obra.letra(letra), obra.letra(jota)
    if not _baja(obra, j):
        raise ValueError(f"la '{jota}' no tiene descendente")
    gancho = sin_punto(obra, jota)[0] if tiene_punto(obra, j) else j
    derecha = caja_de(gancho.value)[2] if gancho is not j else limites(conjunto, j)[2]
    dx = round(limites(conjunto, base)[2] - derecha)
    return _encimadas(obra, [(base, 0), (gancho, dx)]), obra.avance(base)



# Letras que no salen por descomposición NFD (destino: cómo y con qué argumentos).
# Usan `obra.cmap`, que incluye lo ya agregado: `·` va antes que Ŀ en los idiomas.
ESPECIALES = {
    0xD8: (_superpuesto, "O"),
    0xF8: (_superpuesto, "o"),
    0xC6: (_unido, "AE"),
    0xE6: (_unido, "ae"),
    0x152: (_unido, "OE"),
    0x153: (_unido, "oe"),
    0xDF: (_eszett, "Bs"),
    0x1E9E: (_eszett, "BS"),
    0xB7: (_punto_medio, ()),
    0x110: (tachado, ("D", "-", "asta", {"izquierda": 0.5, "derecha": 0.8})),
    0x111: (tachado, ("d", "-", "asta", 0.8)),
    0x126: (tachado, ("H", "-", "asta", 0.8)),
    0x127: (tachado, ("h", "-", "asta", 0.8)),
    0x141: (tachado, ("L", "/", "asta", 0.5)),
    0x142: (tachado, ("l", "/", "asta", 0.5)),
    0x166: (tachado, ("T", "-", "centro", 0.5)),
    0x167: (tachado, ("t", "-", "centro", 0.5)),
    0x13F: (_con_punto_medio, "L"),
    0x140: (_con_punto_medio, "l"),
    0x132: (_seguido, "IJ"),
    0x133: (_seguido, "ij"),
    0x131: (sin_punto, "i"),
    0x138: (_kra, ()),
    0xD0: (tachado, ("D", "-", "asta", {"izquierda": 0.5, "derecha": 0.8})),  # Ð tiene la forma de Đ
    0xF0: (tachado, ("d", "/", "asta", 0.8)),
    0xDE: (_thorn_mayuscula, ()),
    0xFE: (_thorn_minuscula, ()),
    0x14A: (_eng, ("N", "J")),
    0x14B: (_eng, ("n", "j")),
}
