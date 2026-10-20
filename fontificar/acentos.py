"""Acentos derivados de glifos que la fuente ya trae, y la letra base más su acento.

Cada acento tiene una lista de derivaciones que se prueban en orden: la primera que
encuentra con qué trabajar gana. Así una fuente sin `~` usa `˜`, y una sin ninguna
de las dos acuesta la `s`.
"""
import unicodedata

from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen

from .glifos import (caja_de, componentes, contornos, exteriores, grosor_de_punto, limites, reducido,
                     trazo_de_punto, transformado)

# Espacio entre la letra y el acento, en fracción del em.
HUECO = 0.06

# Escalas de los acentos derivados (x, y). Se eligieron a ojo sobre Y2KBUG para que
# el trazo quede parecido al de `grave` sin subir de más el ascendente.
ESCALA_CIRCUNFLEJO = (0.6, 0.45)
ESCALA_ANILLO = (0.6, 0.6)
ESCALA_GRADO = (0.7, 0.7)  # `°` suele ser más grande que el anillo de å
ESCALA_CEDILLA = (0.6, -0.6)  # negativa en y: la coma se voltea
ESCALA_CARON = (0.6, -0.45)  # el circunflejo volteado
ESCALA_MACRON = (0.6, 1)  # solo se angosta, conserva el grosor del trazo
ESCALA_BREVE = (0.29, 0.6)  # (largo, grosor) del `(` acostado
ESCALA_DOBLE_AGUDO = 0.75

# Tamaños de los respaldos que no parten de un acento, en fracción del em.
ALTO_DE_ACENTO = 0.15  # anillo hecho con `o`, breve hecho con `u`
ANCHO_DE_TILDE = 0.3  # tilde hecha con la `s` acostada
ALTO_DE_TILDE = 0.12

# Dónde va el acento respecto a la letra base.
ARRIBA, DEBAJO, DEBAJO_DERECHA = "arriba", "debajo", "debajo a la derecha"


class SinAcento(ValueError):
    """No hay de dónde derivar un acento. `suelto` permite citarlo sin repetir sus motivos."""

    def __init__(self, suelto, motivos):
        self.suelto = suelto
        detalle = f" ({'; '.join(motivos)})" if motivos else ""
        super().__init__(f"no pude derivar el acento '{chr(suelto)}'{detalle}")


class _Ciclo(ValueError):
    """Un acento que se necesita para derivarse a sí mismo (agudo y grave, uno del otro)."""


def marca(obra, combinante):
    """Glifo del acento suelto de `combinante`: el que trae la fuente o, si falta o está
    vacío, el primero que salga de sus derivaciones (se agrega a la fuente)."""
    suelto, derivaciones, posicion = MARCAS[combinante]
    try:
        existente = obra.glifo(suelto)
        if _parece_acento(obra, existente, posicion):
            return existente
    except ValueError:
        pass
    if combinante in obra.derivados:
        return obra.derivados[combinante]
    if combinante in obra.en_curso:
        raise _Ciclo()
    obra.en_curso.add(combinante)
    motivos = []
    try:
        for derivar in derivaciones:
            try:
                grabado, avance = derivar(obra)
            except _Ciclo:
                continue
            except SinAcento as error:
                motivos.append(f"sin '{chr(error.suelto)}'")
                continue
            except ValueError as error:
                motivos.append(str(error))
                continue
            obra.derivados[combinante] = obra.agregar(suelto, grabado, avance)
            return obra.derivados[combinante]
    finally:
        obra.en_curso.discard(combinante)
    raise SinAcento(suelto, list(dict.fromkeys(motivos)))


def _parece_acento(obra, nombre, posicion):
    """¿Un glifo que la fuente ya trae sirve como acento? Hay fuentes que mapean los
    acentos sueltos a dibujos que no lo son (el `ˆ` de Samarkan mide más que una letra).
    Arriba: empieza por encima de media altura de la `o` y mide menos de media `o`.
    Abajo: no sube más de un cuarto de la `o`."""
    _, y0, _, y1 = limites(obra.conjunto, nombre)
    try:
        _, oy0, _, oy1 = limites(obra.conjunto, obra.letra("oxOX"))
    except ValueError:
        return True  # sin letra con qué comparar, se le cree a la fuente
    alto = oy1 - oy0
    if posicion == ARRIBA:
        return y0 > oy0 + alto / 2 and y1 - y0 <= alto / 2
    return y1 <= oy0 + alto / 4


def _acento_existente(obra, *codepoints):
    """El primer glifo de `codepoints` que la fuente trae y tiene forma de acento de arriba."""
    for codepoint in codepoints:
        try:
            nombre = obra.glifo(codepoint)
        except ValueError:
            continue
        if _parece_acento(obra, nombre, ARRIBA):
            return nombre
    raise ValueError(f"la fuente no trae {' ni '.join(f'U+{c:04X}' for c in codepoints)} con forma de acento")


def _referencia(obra):
    """El acento que marca la altura y el margen de los derivados: grave o agudo,
    sueltos o modificadores."""
    return _acento_existente(obra, 0x60, 0x2CB, 0xB4, 0x2CA)


def _piso_de_acento(obra):
    """Altura de la base del acento de referencia; sin él, la de las mayúsculas más `HUECO`."""
    try:
        return limites(obra.conjunto, _referencia(obra))[1]
    except ValueError:
        return limites(obra.conjunto, obra.letra("HIOA"))[3] + HUECO * obra.upm


def _margen_de_acento(obra):
    """Lo que le sobra al acento de referencia de avance a los lados de su contorno, sumado."""
    try:
        referencia = _referencia(obra)
    except ValueError:
        return 0.1 * obra.upm
    x0, _, x1, _ = limites(obra.conjunto, referencia)
    return obra.avance(referencia) - (x1 - x0)


def _colocado(obra, grabado):
    """Recorre `grabado` para que su base quede en el piso de los acentos, centrado en
    un avance de su ancho más el margen de acento."""
    x0, y0, x1, _ = caja_de(grabado.value)
    margen = _margen_de_acento(obra)
    salida = RecordingPen()
    grabado.replay(TransformPen(salida, (1, 0, 0, 1, margen / 2 - x0, _piso_de_acento(obra) - y0)))
    return salida, round(x1 - x0 + margen)


def _resta(conjunto, compuesto, base):
    """Contornos de `compuesto` que no son de `base` (é menos e), o None si la base no
    aparece entera dentro del compuesto (con el mismo corrimiento para todos sus contornos)."""
    de_compuesto, de_base = contornos(conjunto, compuesto), contornos(conjunto, base)
    if not de_base:
        return None

    def puntos(contorno):
        return [p for _, args in contorno for p in args]

    primero = puntos(de_base[0])
    for candidato in de_compuesto:
        otros = puntos(candidato)
        if len(otros) != len(primero) or not primero:
            continue
        dx, dy = otros[0][0] - primero[0][0], otros[0][1] - primero[0][1]
        resto = list(de_compuesto)
        for contorno in de_base:
            movido = [(op, tuple((x + dx, y + dy) for x, y in args)) for op, args in contorno]
            if movido not in resto:
                break
            resto.remove(movido)
        else:
            if resto:
                return [t for c in resto for t in c]
    return None


def _de_letra_acentuada(combinante):
    """Derivación: el acento tal como viene en una letra acentuada que ya trae la fuente
    (é menos e). Es el más fiel al diseño, por eso va primero. Arriba se coloca a la
    altura de los acentos; abajo (cedilla, ogonek) conserva su altura."""
    def derivar(obra):
        conjunto = obra.conjunto
        candidatos = []
        for codepoint in obra.cmap:
            letra, *marcas = unicodedata.normalize("NFD", chr(codepoint))
            if len(marcas) == 1 and ord(marcas[0]) == combinante and ord(letra) in obra.cmap:
                candidatos.append((not letra.islower(), codepoint, ord(letra)))
        for _, codepoint, letra in sorted(candidatos):  # minúsculas primero
            try:
                trazos = _resta(conjunto, obra.cmap[codepoint], obra.cmap[letra])
            except ValueError:
                continue
            if trazos is None:
                continue
            grabado = RecordingPen()
            grabado.value = trazos
            if MARCAS[combinante][2] == ARRIBA:
                return _colocado(obra, grabado)
            x0, _, x1, _ = caja_de(trazos)
            margen = _margen_de_acento(obra)
            salida = RecordingPen()
            grabado.replay(TransformPen(salida, (1, 0, 0, 1, margen / 2 - x0, 0)))
            return salida, round(x1 - x0 + margen)
        raise ValueError("ninguna letra acentuada de la fuente lo trae aparte")
    return derivar


def _copia_de(*codepoints):
    """Derivación que usa tal cual el primer glifo que exista de `codepoints` (ˋ por `,
    ˜ por ~)."""
    def derivar(obra):
        origen = _acento_existente(obra, *codepoints)
        return componentes((origen, 0, 0)), obra.avance(origen)
    return derivar


def _espejo_de(combinante):
    """Derivación: espejo horizontal de otro acento alrededor de su centro (el agudo
    sale de `grave` y al revés)."""
    def derivar(obra):
        origen = marca(obra, combinante)
        x0, _, x1, _ = limites(obra.conjunto, origen)
        return transformado(obra, (origen, (-1, 0, 0, 1, x0 + x1, 0))), obra.avance(origen)
    return derivar


def _agudo_de_apostrofo(obra):
    """Apóstrofo inclinado hacia la derecha y acortado, a la altura de los acentos."""
    origen = obra.signo(0x27, 0x2019, 0x2032)
    _, y0, _, y1 = limites(obra.conjunto, origen)
    alto = min(1, ALTO_DE_ACENTO * obra.upm / (y1 - y0))
    return _colocado(obra, transformado(obra, (origen, (1, 0, 0.6 * alto, alto, 0, 0))))


def _agudo_de_punto(obra):
    """El punto estirado en un trazo inclinado hacia la derecha, a la altura de los acentos."""
    return _colocado(obra, trazo_de_punto(obra, grosor_de_punto(obra), ALTO_DE_ACENTO * obra.upm, 0.8))


def puntos(obra, cuantos, piso=None, centro=None):
    """`cuantos` puntos macizos en fila: los contornos exteriores de `period`, a la mitad
    de tamaño, centrados en su avance y con la parte de abajo en `piso` o el centro en `centro`."""
    punto = obra.signo(0x2E)
    rec = RecordingPen()
    rec.value = exteriores(obra.conjunto, punto)
    x0, y0, x1, _ = caja_de(rec.value)
    escala, separacion = 0.5, 60
    lado = (x1 - x0) * escala
    if piso is None:
        piso = centro - lado / 2
    avance = obra.avance(punto)
    inicio = (avance - (cuantos * lado + (cuantos - 1) * separacion)) / 2
    salida = RecordingPen()
    for i in range(cuantos):
        matriz = (escala, 0, 0, escala, inicio + i * (lado + separacion) - x0 * escala, piso - y0 * escala)
        rec.replay(TransformPen(salida, matriz))
    return salida, avance


def _dieresis(obra):
    """Dos puntos con la base a la altura de los acentos."""
    return puntos(obra, 2, piso=_piso_de_acento(obra))


def _punto_superior(obra):
    """Un punto con la base a la altura de los acentos (Ċ, Ė, İ, Ż)."""
    return puntos(obra, 1, piso=_piso_de_acento(obra))


def _circunflejo(obra):
    """`asciicircum` reducido (completo es demasiado alto), con la base a la altura de los acentos."""
    return reducido(obra, obra.signo(0x5E), ESCALA_CIRCUNFLEJO, piso=_piso_de_acento(obra))


def _circunflejo_de_trazos(obra):
    """Un agudo y un grave que se tocan arriba, como un techo."""
    agudo, grave = marca(obra, 0x0301), marca(obra, 0x0300)
    ax0, ay0, ax1, _ = limites(obra.conjunto, agudo)
    gx0, gy0, _, _ = limites(obra.conjunto, grave)
    dx = ax1 - (ax1 - ax0) * 0.3 - gx0
    return _colocado(obra, transformado(obra, (agudo, (1, 0, 0, 1, 0, 0)), (grave, (1, 0, 0, 1, dx, ay0 - gy0))))


def _caron(obra):
    """`asciicircum` reducido y volteado, con la base a la altura de los acentos."""
    return reducido(obra, obra.signo(0x5E), ESCALA_CARON, piso=_piso_de_acento(obra))


def _caron_de_circunflejo(obra):
    """El circunflejo (el que trae la fuente o el derivado) volteado en su lugar."""
    origen = marca(obra, 0x0302)
    _, y0, _, y1 = limites(obra.conjunto, origen)
    return transformado(obra, (origen, (1, 0, 0, -1, 0, y0 + y1))), obra.avance(origen)


def _macron(obra):
    """`hyphen` (o raya, menos o guion bajo) angostado, con la base a la altura de los acentos."""
    origen = obra.signo(0x2D, 0x2013, 0x2212, 0x5F)
    return reducido(obra, origen, ESCALA_MACRON, piso=_piso_de_acento(obra))


def _macron_de_punto(obra):
    """El punto estirado en una barra del ancho de un acento."""
    return _colocado(obra, trazo_de_punto(obra, 2 * ALTO_DE_ACENTO * obra.upm, grosor_de_punto(obra)))


def _anillo_de_grado(obra):
    """`°` reducido, con la base a la altura de los acentos."""
    return reducido(obra, obra.signo(0xB0), ESCALA_GRADO, piso=_piso_de_acento(obra))


def _anillo(obra):
    """`period` reducido, solo si ya es un anillo (un contorno con hueco, como en Y2KBUG)."""
    punto = obra.signo(0x2E)
    todos = contornos(obra.conjunto, punto)
    if len(todos) != 2 or len(exteriores(obra.conjunto, punto)) == sum(map(len, todos)):
        raise ValueError("el punto no es un anillo")
    return reducido(obra, punto, ESCALA_ANILLO, piso=_piso_de_acento(obra))


def _anillo_de_o(obra):
    """`o` reducida a la altura de un acento."""
    origen = obra.letra("oO")
    _, y0, _, y1 = limites(obra.conjunto, origen)
    escala = ALTO_DE_ACENTO * obra.upm / (y1 - y0)
    return reducido(obra, origen, (escala, escala), piso=_piso_de_acento(obra))


def _breve(obra):
    """`(` acostado (girado 90° para que abra hacia arriba), reducido a lo largo y a lo
    grueso por `ESCALA_BREVE`, con la base a la altura de los acentos."""
    parentesis = obra.signo(0x28)
    x0, y0, _, y1 = limites(obra.conjunto, parentesis)
    largo, grueso = ESCALA_BREVE
    margen = _margen_de_acento(obra)
    # (x, y) pasa a (-largo * y, grueso * x): el lomo del paréntesis queda abajo.
    matriz = (0, grueso, -largo, 0, margen / 2 + largo * y1, _piso_de_acento(obra) - grueso * x0)
    return transformado(obra, (parentesis, matriz)), round(largo * (y1 - y0) + margen)


def _breve_de_u(obra):
    """`u` aplastada a la altura de un acento."""
    origen = obra.letra("uU")
    x0, y0, x1, y1 = limites(obra.conjunto, origen)
    sy = ALTO_DE_ACENTO * obra.upm / (y1 - y0)
    return _colocado(obra, transformado(obra, (origen, (ESCALA_CIRCUNFLEJO[0], 0, 0, sy, 0, 0))))


def _tilde_de_s(obra):
    """`s` acostada (girada 90°): su lomo queda como la onda de la tilde."""
    origen = obra.letra("sS")
    x0, y0, x1, y1 = limites(obra.conjunto, origen)
    # (x, y) pasa a (sx * y, -sy * x): lo alto de la `s` se vuelve lo ancho.
    sx = ANCHO_DE_TILDE * obra.upm / (y1 - y0)
    sy = ALTO_DE_TILDE * obra.upm / (x1 - x0)
    return _colocado(obra, transformado(obra, (origen, (0, -sy, sx, 0, 0, 0))))


def _doble_agudo(obra):
    """Dos agudos reducidos por `ESCALA_DOBLE_AGUDO`, lado a lado, con la base a la
    altura de los acentos."""
    agudo = marca(obra, 0x0301)
    x0, y0, x1, _ = limites(obra.conjunto, agudo)
    escala = ESCALA_DOBLE_AGUDO
    ancho = (x1 - x0) * escala
    separacion = ancho / 4
    margen = _margen_de_acento(obra)
    piezas = [(agudo, (escala, 0, 0, escala, margen / 2 + i * (ancho + separacion) - escala * x0,
                       y0 - escala * y0)) for i in (0, 1)]
    return transformado(obra, *piezas), round(2 * ancho + separacion + margen)


def _cedilla(obra):
    """`comma` volteada en vertical y reducida, colgando de la línea base:
    baja del centro y se enrosca hacia la izquierda. También sirve de ogonek,
    alineada a la derecha de la letra."""
    return reducido(obra, obra.signo(0x2C), ESCALA_CEDILLA, techo=0)


# Marca combinante -> (codepoint del acento suelto, derivaciones en orden de
# preferencia si la fuente no lo trae, dónde va). `asciicircum` no se usa tal cual:
# como acento es demasiado alto, se agrega reducido como U+02C6.
MARCAS = {
    0x0300: (0x60, (_copia_de(0x2CB), _de_letra_acentuada(0x0300), _espejo_de(0x0301)), ARRIBA),
    0x0301: (0xB4, (_copia_de(0x2CA), _de_letra_acentuada(0x0301), _espejo_de(0x0300),
                    _agudo_de_apostrofo, _agudo_de_punto), ARRIBA),
    0x0302: (0x2C6, (_de_letra_acentuada(0x0302), _circunflejo, _circunflejo_de_trazos), ARRIBA),
    0x0303: (0x7E, (_copia_de(0x2DC), _de_letra_acentuada(0x0303), _tilde_de_s), ARRIBA),
    0x0304: (0xAF, (_copia_de(0x2C9), _de_letra_acentuada(0x0304), _macron, _macron_de_punto), ARRIBA),
    0x0306: (0x2D8, (_de_letra_acentuada(0x0306), _breve, _breve_de_u), ARRIBA),
    0x0307: (0x2D9, (_de_letra_acentuada(0x0307), _punto_superior), ARRIBA),
    0x0308: (0xA8, (_de_letra_acentuada(0x0308), _dieresis), ARRIBA),
    0x030A: (0x2DA, (_de_letra_acentuada(0x030A), _anillo_de_grado, _anillo, _anillo_de_o), ARRIBA),
    0x030B: (0x2DD, (_de_letra_acentuada(0x030B), _doble_agudo), ARRIBA),
    0x030C: (0x2C7, (_de_letra_acentuada(0x030C), _caron, _caron_de_circunflejo), ARRIBA),
    0x0327: (0xB8, (_de_letra_acentuada(0x0327), _cedilla), DEBAJO),
    0x0328: (0x2DB, (_de_letra_acentuada(0x0328), _cedilla), DEBAJO_DERECHA),
}


def compuesto(obra, base, acento, posicion=ARRIBA):
    """Letra base más acento. Arriba queda centrado a `HUECO` de la base; debajo
    (cedilla) queda centrado y pegado a ella; debajo a la derecha (ogonek) queda
    pegado y con su borde derecho en el de la base.

    Usar la caja de la base (no una altura fija) hace que sirva igual con
    minúsculas bajas, mayúsculas altas o una fuente unicase.

    Si el acento más `HUECO` no cabe en el avance de la base (í, ï, î), el avance
    crece lo justo y la base se recorre a la mitad, para no chocar con la vecina.
    """
    conjunto = obra.conjunto
    hueco = HUECO * obra.upm
    bx0, by0, bx1, by1 = limites(conjunto, base)
    mx0, my0, mx1, my1 = limites(conjunto, acento)
    avance = obra.avance(base)
    extra = max(0, round(mx1 - mx0 + hueco) - avance)
    corrimiento = extra // 2
    if posicion == DEBAJO_DERECHA:
        dx = round(bx1 - mx1) + corrimiento
    else:
        dx = round((bx0 + bx1) / 2 - (mx0 + mx1) / 2) + corrimiento
    if posicion == ARRIBA:
        dy = round(by1 + hueco - my0)
    else:
        dy = round(by0 - my1)
    return componentes((base, corrimiento, 0), (acento, dx, dy)), avance + extra
