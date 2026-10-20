"""Símbolos de Latin-1 y Windows-1252 (comillas, rayas, ordinales, fracciones, monedas,
signos) armados con la puntuación, los dígitos y las letras que trae la fuente.

Las alturas se miden en la fuente: la de las mayúsculas (`_alto`) y el centro del
guion, que es donde van los signos de operación.
"""
import math

from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen

from .especiales import asta_vertical, auxiliar, diagonal, girado, guion, tachado
from .glifos import (ancho_de_asta, caja_de, componentes, contornos, exteriores, limites, reducido,
                     transformado)

# Tamaños, en fracción de la altura de las mayúsculas.
ALTO_DE_ORDINAL = 0.4  # ª º
ALTO_DE_GRADO = 0.35  # °
ESCALA_SUPERINDICE = 0.6  # ¹ ² ³
ESCALA_FRACCION = 0.5  # dígitos de ¼ ½ ¾
ESCALA_ANGULAR = 0.6  # ‹ › desde < >
ESCALA_VINETA = 2  # • respecto al punto
ALTO_DE_VINETA = 0.3  # tope de •, para fuentes de punto grande
ALTO_DE_ANGULAR = 0.4  # ‹ › hechos con el guion
ANGULO_DE_ANGULAR = 35  # grados de cada brazo de ‹ › contra la horizontal


def _alto(obra):
    """Altura de las mayúsculas."""
    return limites(obra.conjunto, obra.letra("HIOA"))[3]


def _juntos(*grabados):
    """Un solo grabado con los trazos de todos."""
    salida = RecordingPen()
    for grabado in grabados:
        salida.value += grabado.value
    return salida


def _movido(grabado, matriz):
    salida = RecordingPen()
    grabado.replay(TransformPen(salida, matriz))
    return salida


def _barra(obra, x0, x1, centro):
    """El guion de la fuente estirado o angostado de `x0` a `x1`, con su centro
    vertical en `centro`; conserva el grosor."""
    origen = guion(obra)
    gx0, gy0, gx1, gy1 = limites(obra.conjunto, origen)
    sx = (x1 - x0) / (gx1 - gx0)
    return transformado(obra, (origen, (sx, 0, 0, 1, x0 - sx * gx0, centro - (gy0 + gy1) / 2)))


def _centro_del_guion(obra):
    _, y0, _, y1 = limites(obra.conjunto, guion(obra))
    return (y0 + y1) / 2


def _grosor_del_guion(obra):
    _, y0, _, y1 = limites(obra.conjunto, guion(obra))
    return y1 - y0


def _punto(obra, diametro, cx, cy):
    """El contorno exterior del punto de la fuente (macizo) escalado a `diametro` de
    ancho y centrado en (cx, cy)."""
    trazos = RecordingPen()
    trazos.value = exteriores(obra.conjunto, obra.signo(0x2E))
    x0, y0, x1, y1 = caja_de(trazos.value)
    s = diametro / (x1 - x0)
    return _movido(trazos, (s, 0, 0, s, cx - s * (x0 + x1) / 2, cy - s * (y0 + y1) / 2))


def _brazo(obra, largo, angulo, x, y):
    """El guion a `largo` (conserva el grosor), girado `angulo` grados alrededor de su
    extremo izquierdo, que queda en (x, y)."""
    origen = guion(obra)
    gx0, gy0, gx1, gy1 = limites(obra.conjunto, origen)
    sx, tx, ty = largo / (gx1 - gx0), -largo / (gx1 - gx0) * gx0, -(gy0 + gy1) / 2
    c, s = math.cos(math.radians(angulo)), math.sin(math.radians(angulo))
    return transformado(obra, (origen, (c * sx, s * sx, -s, c, c * tx - s * ty + x, s * tx + c * ty + y)))


def _mas(obra):
    """`+` de la fuente o, si no trae, el guion cruzado con el guion parado (glifo
    auxiliar sin mapear)."""
    try:
        return obra.signo(0x2B)
    except ValueError:
        pass
    origen = guion(obra)
    x0, y0, x1, y1 = limites(obra.conjunto, origen)
    largo, grosor = x1 - x0, y1 - y0
    cruz = _juntos(_barra(obra, 0, largo, largo / 2),
                   _movido(asta_vertical(obra, grosor, largo), (1, 0, 0, 1, (largo - grosor) / 2, 0)))
    return auxiliar(obra, "mas", cruz, largo, (y0 + y1) / 2 - largo / 2)


def _vertical(obra):
    """`|` de la fuente o, si no trae, el guion parado de la línea base a la altura de
    las mayúsculas (glifo auxiliar sin mapear)."""
    try:
        return obra.signo(0x7C)
    except ValueError:
        pass
    grosor = _grosor_del_guion(obra)
    return auxiliar(obra, "vertical", asta_vertical(obra, grosor, _alto(obra)), grosor, 0)


# Comillas.

def _comilla_derecha(obra):
    """’: la coma subida a la altura de las mayúsculas; sin coma, el apóstrofo tal cual."""
    try:
        coma = obra.signo(0x2C)
    except ValueError:
        apostrofo = obra.signo(0x27)
        return componentes((apostrofo, 0, 0)), obra.avance(apostrofo)
    return componentes((coma, 0, _alto(obra) - limites(obra.conjunto, coma)[3])), obra.avance(coma)


def _comilla_izquierda(obra, derecha):
    """‘ (“): la derecha girada 180°."""
    return girado(obra, obra.glifo(derecha))


def _comilla_baja(obra, derecha):
    """‚ („): la derecha bajada hasta donde baja la coma."""
    conjunto = obra.conjunto
    origen = obra.glifo(derecha)
    dy = limites(conjunto, obra.signo(0x2C))[1] - limites(conjunto, origen)[1]
    return componentes((origen, 0, dy)), obra.avance(origen)


def _doble(obra, sencilla, juntura=0.5):
    """Dos veces el glifo `sencilla`, el segundo recorrido su ancho de tinta más
    `juntura` de ese ancho (negativa: se enciman, como en « »)."""
    origen = obra.glifo(sencilla)
    x0, _, x1, _ = limites(obra.conjunto, origen)
    dx = round((x1 - x0) * (1 + juntura))
    return componentes((origen, 0, 0), (origen, dx, 0)), obra.avance(origen) + dx


# Rayas y puntos.

def _raya(obra, ems):
    """Rayas (U+2013, U+2014): el guion estirado a un avance de `ems` em, con los mismos márgenes."""
    origen = guion(obra)
    x0, _, x1, _ = limites(obra.conjunto, origen)
    margenes = obra.avance(origen) - (x1 - x0)
    avance = ems * obra.upm
    _, y0, _, y1 = limites(obra.conjunto, origen)
    return _barra(obra, x0, avance - margenes + x0, (y0 + y1) / 2), avance


def _puntos_suspensivos(obra):
    """…: tres puntos, cada uno con su avance."""
    punto = obra.signo(0x2E)
    avance = obra.avance(punto)
    return componentes((punto, 0, 0), (punto, avance, 0), (punto, 2 * avance, 0)), 3 * avance


def _vineta(obra):
    """•: el punto macizo, al doble, centrado a la altura del guion."""
    punto = obra.signo(0x2E)
    x0, _, x1, _ = limites(obra.conjunto, punto)
    diametro = min(ESCALA_VINETA * (x1 - x0), ALTO_DE_VINETA * _alto(obra))
    margenes = obra.avance(punto) - (x1 - x0)
    return _punto(obra, diametro, margenes / 2 + diametro / 2, _centro_del_guion(obra)), diametro + margenes


def _angular(obra, signo):
    """‹ ›: `<` `>` reducidos alrededor de su centro; si la fuente no los trae, dos
    brazos de guion que se juntan en la punta, centrados a la altura del guion."""
    try:
        origen = obra.signo(signo)
    except ValueError:
        pass
    else:
        _, y0, _, y1 = limites(obra.conjunto, origen)
        alto = (y1 - y0) * ESCALA_ANGULAR
        return reducido(obra, origen, (ESCALA_ANGULAR,) * 2, piso=(y0 + y1) / 2 - alto / 2)
    angulo = ANGULO_DE_ANGULAR
    largo = ALTO_DE_ANGULAR * _alto(obra) / 2 / math.sin(math.radians(angulo))
    ancho = largo * math.cos(math.radians(angulo))
    centro = _centro_del_guion(obra)
    if signo == 0x3C:  # la punta a la izquierda
        brazos = [_brazo(obra, largo, a, 0, centro) for a in (angulo, -angulo)]
    else:
        brazos = [_brazo(obra, largo, 180 + a, ancho, centro) for a in (angulo, -angulo)]
    grabado = _juntos(*brazos)
    x0, _, x1, _ = caja_de(grabado.value)
    margen = _grosor_del_guion(obra)
    return _movido(grabado, (1, 0, 0, 1, margen - x0, 0)), round(x1 - x0 + 2 * margen)


# Ordinales, superíndices y fracciones.

def _ordinal(obra, letra):
    """ª º: la letra reducida, arriba a la altura de las mayúsculas, con una raya
    debajo de su ancho a un grosor de distancia."""
    origen = obra.letra(letra)
    _, y0, _, y1 = limites(obra.conjunto, origen)
    escala = ALTO_DE_ORDINAL * _alto(obra) / (y1 - y0)
    grabado, avance = reducido(obra, origen, (escala, escala), techo=_alto(obra))
    x0, y0, x1, _ = caja_de(grabado.value)
    grosor = _grosor_del_guion(obra)
    return _juntos(grabado, _barra(obra, x0, x1, y0 - 1.5 * grosor)), avance


def _superindice(obra, digito):
    """¹ ² ³: el dígito reducido, arriba a la altura de las mayúsculas."""
    return reducido(obra, obra.glifo(digito), (ESCALA_SUPERINDICE,) * 2, techo=_alto(obra))


def _fraccion(obra, numerador, denominador):
    """¼ ½ ¾: el numerador reducido arriba, el denominador reducido en la línea base a
    su derecha y la diagonal, a la altura de las mayúsculas, entre los dos."""
    escala = (ESCALA_FRACCION,) * 2
    alto = _alto(obra)
    arriba, avance = reducido(obra, obra.glifo(numerador), escala, techo=alto)
    abajo, avance_abajo = reducido(obra, obra.glifo(denominador), escala, piso=0)
    barra = diagonal(obra)
    x0, y0, x1, y1 = limites(obra.conjunto, barra)
    s = alto / (y1 - y0)
    trazo = transformado(obra, (barra, (s, 0, 0, s, avance - s * (x0 + x1) / 2, -s * y0)))
    return _juntos(arriba, _movido(abajo, (1, 0, 0, 1, avance, 0)), trazo), avance + avance_abajo


# Monedas.

def _con_barras(obra, letra, alturas, desde, hasta):
    """La letra cruzada por barras horizontales (€ ¥) de `desde` a `hasta` (fracciones
    del ancho de la letra) con su centro en cada una de `alturas` (fracciones de su
    alto). Las barras no se salen del avance."""
    base = obra.letra(letra)
    x0, y0, x1, y1 = limites(obra.conjunto, base)
    avance = obra.avance(base)
    inicio = max(0, x0 + desde * (x1 - x0))
    fin = min(avance, x0 + hasta * (x1 - x0))
    barras = [_barra(obra, inicio, fin, y0 + a * (y1 - y0)) for a in alturas]
    return _juntos(transformado(obra, (base, (1, 0, 0, 1, 0, 0))), *barras), avance


def _centavo(obra):
    """¢: la `c` con la diagonal encima, de 1.3 veces su alto y centrada."""
    conjunto = obra.conjunto
    base, barra = obra.letra("cC"), diagonal(obra)
    bx0, by0, bx1, by1 = limites(conjunto, base)
    x0, y0, x1, y1 = limites(conjunto, barra)
    s = 1.3 * (by1 - by0) / (y1 - y0)
    matriz = (s, 0, 0, s, (bx0 + bx1) / 2 - s * (x0 + x1) / 2, (by0 + by1) / 2 - s * (y0 + y1) / 2)
    return transformado(obra, (base, (1, 0, 0, 1, 0, 0)), (barra, matriz)), obra.avance(base)


def _hueco(obra, nombre):
    """Caja del hueco más grande del glifo (un contorno dentro de la caja de otro), o None."""
    cajas = [caja_de(c) for c in contornos(obra.conjunto, nombre)]

    def dentro(a, b):
        return a is not b and b[0] < a[0] and b[1] < a[1] and a[2] < b[2] and a[3] < b[3]

    huecos = [a for a in cajas if any(dentro(a, b) for b in cajas)]
    return max(huecos, key=lambda c: (c[2] - c[0]) * (c[3] - c[1]), default=None)


def _encerrada(obra, letra):
    """© ®: la letra dentro de la `O`, a 0.7 de su hueco; si la `O` no tiene hueco
    (hecha de puntos), a la mitad de la `O`."""
    conjunto = obra.conjunto
    anillo, origen = obra.letra("O"), obra.letra(letra)
    caja = _hueco(obra, anillo)
    factor = 0.7
    if caja is None:
        caja, factor = limites(conjunto, anillo), 0.5
    hx0, hy0, hx1, hy1 = caja
    x0, y0, x1, y1 = limites(conjunto, origen)
    s = factor * min((hx1 - hx0) / (x1 - x0), (hy1 - hy0) / (y1 - y0))
    matriz = (s, 0, 0, s, (hx0 + hx1) / 2 - s * (x0 + x1) / 2, (hy0 + hy1) / 2 - s * (y0 + y1) / 2)
    return transformado(obra, (anillo, (1, 0, 0, 1, 0, 0)), (origen, matriz)), obra.avance(anillo)


def _moneda(obra):
    """¤: la `o` reducida a la altura de los ordinales, centrada a la altura del guion,
    con un punto en cada esquina."""
    origen = obra.letra("oO")
    _, y0, _, y1 = limites(obra.conjunto, origen)
    escala = ALTO_DE_ORDINAL * _alto(obra) / (y1 - y0)
    centro = _centro_del_guion(obra)
    anillo, avance = reducido(obra, origen, (escala, escala), piso=centro - escala * (y1 - y0) / 2)
    x0, y0, x1, y1 = caja_de(anillo.value)
    diametro = ancho_de_asta(obra)
    separacion = diametro / 5
    esquinas = [_punto(obra, diametro, x - separacion if x == x0 else x + separacion,
                       y - separacion if y == y0 else y + separacion)
                for x in (x0, x1) for y in (y0, y1)]
    return _movido(_juntos(anillo, *esquinas), (1, 0, 0, 1, diametro, 0)), avance + 2 * diametro


# Signos.

def _grado(obra):
    """°: la `o` reducida, arriba a la altura de las mayúsculas."""
    origen = obra.letra("oO")
    _, y0, _, y1 = limites(obra.conjunto, origen)
    escala = ALTO_DE_GRADO * _alto(obra) / (y1 - y0)
    return reducido(obra, origen, (escala, escala), techo=_alto(obra))


def _mas_menos(obra):
    """±: `+` con una barra de su ancho debajo, a un grosor de distancia; todo sube si
    la barra bajaría de la línea base."""
    mas = _mas(obra)
    x0, y0, x1, _ = limites(obra.conjunto, mas)
    grosor = _grosor_del_guion(obra)
    centro = y0 - 1.5 * grosor
    subida = max(0, grosor / 2 - centro)
    grabado = _juntos(transformado(obra, (mas, (1, 0, 0, 1, 0, 0))), _barra(obra, x0, x1, centro))
    return _movido(grabado, (1, 0, 0, 1, 0, subida)), obra.avance(mas)


def _por(obra):
    """×: `+` girado 45° alrededor de su centro."""
    mas = _mas(obra)
    x0, y0, x1, y1 = limites(obra.conjunto, mas)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    c = s = math.sqrt(0.5)
    return transformado(obra, (mas, (c, s, -s, c, cx - c * cx + s * cy, cy - s * cx - c * cy))), obra.avance(mas)


def _entre(obra):
    """÷: el guion con un punto arriba y otro abajo, a un grosor de distancia."""
    origen = guion(obra)
    x0, y0, x1, y1 = limites(obra.conjunto, origen)
    grosor, cx, cy = y1 - y0, (x0 + x1) / 2, (y0 + y1) / 2
    diametro = 1.3 * grosor
    distancia = grosor / 2 + grosor + diametro / 2
    puntos = [_punto(obra, diametro, cx, cy + signo * distancia) for signo in (1, -1)]
    return _juntos(transformado(obra, (origen, (1, 0, 0, 1, 0, 0))), *puntos), obra.avance(origen)


def _negacion(obra):
    """¬: el guion con una pata hacia abajo en su extremo derecho, del mismo grosor y
    de un tercio de su largo más el grosor."""
    origen = guion(obra)
    x0, y0, x1, y1 = limites(obra.conjunto, origen)
    largo, grosor = x1 - x0, y1 - y0
    k = (largo / 3 + grosor) / largo
    # (x, y) pasa a (-y + dx, k * x + dy): el guion se para y se acorta.
    pata = (origen, (0, k, -1, 0, x1 + y0, y1 - k * x1))
    return transformado(obra, (origen, (1, 0, 0, 1, 0, 0)), pata), obra.avance(origen)


def _barra_partida(obra):
    """¦: la `|` partida en dos tramos de 0.42 de su alto, uno abajo y otro arriba."""
    origen = _vertical(obra)
    _, y0, _, y1 = limites(obra.conjunto, origen)
    s = 0.42
    return transformado(obra, (origen, (1, 0, 0, s, 0, y0 - s * y0)),
                        (origen, (1, 0, 0, s, 0, y1 - s * y1))), obra.avance(origen)


def _seccion(obra):
    """§: dos `s` reducidas a 0.55 de la altura de las mayúsculas, una sobre otra y
    encimadas un décimo."""
    origen = obra.letra("sS")
    _, y0, _, y1 = limites(obra.conjunto, origen)
    alto = _alto(obra)
    escala = 0.55 * alto / (y1 - y0)
    arriba, avance = reducido(obra, origen, (escala, escala), techo=alto)
    abajo, _ = reducido(obra, origen, (escala, escala), piso=0)
    return _juntos(abajo, arriba), avance


def _calderon(obra):
    """¶: la `P` reflejada (la panza a la izquierda) más un asta a su derecha, a un
    asta de distancia."""
    p = obra.letra("P")
    x0, y0, x1, y1 = limites(obra.conjunto, p)
    asta = ancho_de_asta(obra)
    reflejada = transformado(obra, (p, (-1, 0, 0, 1, x0 + x1, 0)))
    segunda = _movido(asta_vertical(obra, asta, y1 - y0), (1, 0, 0, 1, x1 + asta, y0))
    return _juntos(reflejada, segunda), obra.avance(p) + 2 * asta


def _micro(obra):
    """µ: la `μ` griega si la fuente la trae; si no, la `u` con un asta que baja por
    la izquierda hasta el descendente de la `p` (o un quinto de em)."""
    try:
        griega = obra.glifo(0x3BC)
        return componentes((griega, 0, 0)), obra.avance(griega)
    except ValueError:
        pass
    conjunto = obra.conjunto
    u = obra.letra("u")
    x0, y0, _, _ = limites(conjunto, u)
    try:
        piso = min(limites(conjunto, obra.letra("p"))[1], -0.2 * obra.upm)
    except ValueError:
        piso = -0.2 * obra.upm
    asta = ancho_de_asta(obra)
    pata = _movido(asta_vertical(obra, asta, y0 + asta - piso), (1, 0, 0, 1, x0, piso))
    return _juntos(transformado(obra, (u, (1, 0, 0, 1, 0, 0))), pata), obra.avance(u)


# Símbolos (destino: cómo y con qué argumentos). Usan `obra.cmap`, que incluye lo ya
# agregado: ’ va antes que las demás comillas y ‹ › antes que « » en los idiomas.
SIMBOLOS = {
    0x2019: (_comilla_derecha, ()),
    0x2018: (_comilla_izquierda, (0x2019,)),
    0x201A: (_comilla_baja, (0x2019,)),
    0x201D: (_doble, (0x2019,)),
    0x201C: (_doble, (0x2018,)),
    0x201E: (_doble, (0x201A,)),
    0x2013: (_raya, (0.5,)),
    0x2014: (_raya, (1,)),
    0x2026: (_puntos_suspensivos, ()),
    0x2022: (_vineta, ()),
    0x2039: (_angular, (0x3C,)),
    0x203A: (_angular, (0x3E,)),
    0xAB: (_doble, (0x2039, -0.4)),
    0xBB: (_doble, (0x203A, -0.4)),
    0xAA: (_ordinal, ("aA",)),
    0xBA: (_ordinal, ("oO",)),
    0xB9: (_superindice, (0x31,)),
    0xB2: (_superindice, (0x32,)),
    0xB3: (_superindice, (0x33,)),
    0xBC: (_fraccion, (0x31, 0x34)),
    0xBD: (_fraccion, (0x31, 0x32)),
    0xBE: (_fraccion, (0x33, 0x34)),
    0x20AC: (_con_barras, ("C", (0.38, 0.62), -0.15, 0.7)),
    0xA3: (tachado, ("L", "-", "asta", 0.4)),
    0xA2: (_centavo, ()),
    0xA5: (_con_barras, ("Y", (0.22, 0.42), 0.1, 0.9)),
    0xA9: (_encerrada, ("C",)),
    0xAE: (_encerrada, ("R",)),
    0xB0: (_grado, ()),
    0xB1: (_mas_menos, ()),
    0xD7: (_por, ()),
    0xF7: (_entre, ()),
    0xAC: (_negacion, ()),
    0xA6: (_barra_partida, ()),
    0xA7: (_seccion, ()),
    0xB6: (_calderon, ()),
    0xA4: (_moneda, ()),
    0xB5: (_micro, ()),
}
