"""La fuente en construcción (`Obra`) y utilidades de contorno que comparten los acentos
y las letras especiales.

Los glifos nuevos se arman como grabaciones (`RecordingPen`) que no dependen del
formato: `Obra.agregar` las escribe en `glyf` (TrueType, los componentes se conservan)
o en `CFF ` (OpenType CFF, los componentes se descomponen porque CFF no los tiene).
"""
from fontTools.agl import UV2AGL
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.pointInsidePen import PointInsidePen
from fontTools.pens.recordingPen import DecomposingRecordingPen, RecordingPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen


class Obra:
    """La fuente que se está ampliando: qué glifos trae, cuáles se agregaron y cómo
    se guarda uno nuevo. `cmap` incluye lo ya agregado, así que lo nuevo sirve de
    origen para lo que sigue."""

    def __init__(self, fuente):
        if "glyf" not in fuente and "CFF " not in fuente:
            raise ValueError("solo se admiten fuentes TrueType (glyf) u OpenType CFF; CFF2 (variables) no")
        if "CFF " in fuente:
            superior = fuente["CFF "].cff.topDictIndex[0]
            if hasattr(superior, "ROS"):
                raise ValueError("las fuentes CFF con CID (CJK) no se admiten")
        cmap = fuente.getBestCmap()
        if not cmap:
            raise ValueError("la fuente no tiene una tabla cmap Unicode")
        self.fuente = fuente
        self.cmap = dict(cmap)
        self.nuevos = {}
        self.derivados = {}  # glifos auxiliares ya hechos (acentos, ı), por clave
        self.en_curso = set()  # acentos que se están derivando, para cortar ciclos
        self.upm = fuente["head"].unitsPerEm

    @property
    def conjunto(self):
        return self.fuente.getGlyphSet()

    def avance(self, nombre):
        return self.fuente["hmtx"][nombre][0]

    def glifo(self, *codepoints):
        """Nombre del primer glifo con contorno entre `codepoints`; error si ninguno sirve.
        Un glifo vacío (hay fuentes que mapean caracteres a glifos sin dibujo) no cuenta."""
        conjunto = self.conjunto
        for codepoint in codepoints:
            nombre = self.cmap.get(codepoint)
            if nombre is not None and tiene_contorno(conjunto, nombre):
                return nombre
        faltan = " ni ".join(f"'{chr(c)}' (U+{c:04X})" for c in codepoints)
        raise ValueError(f"la fuente no trae {faltan} con contorno")

    def letra(self, caracteres):
        """Glifo de la primera letra de `caracteres` que tenga contorno."""
        return self.glifo(*map(ord, caracteres))

    def signo(self, *codepoints):
        """Como `glifo`, para signos de puntuación que sirven de materia prima: si el
        glifo trae una línea de cabecera (fuentes estilo devanagari como Samarkan, donde
        `.` es el punto más la barra de arriba), devuelve un glifo auxiliar sin ella."""
        nombre = self.glifo(*codepoints)
        clave = ("signo", nombre)
        if clave not in self.derivados:
            trazos = contornos(self.conjunto, nombre)
            sin_cabecera = [c for c in trazos if not self._es_cabecera(c, nombre)]
            if len(sin_cabecera) in (0, len(trazos)):
                self.derivados[clave] = nombre
            else:
                grabado = RecordingPen()
                grabado.value = [t for c in sin_cabecera for t in c]
                self.derivados[clave] = self.agregar(None, grabado, self.avance(nombre), nombre=f"{nombre}.fontificar")
        return self.derivados[clave]

    def _es_cabecera(self, contorno, nombre):
        """Un contorno plano (menos de 0.15 em) que cruza todo el avance del glifo."""
        x0, y0, x1, y1 = caja_de(contorno)
        return y1 - y0 < 0.15 * self.upm and x1 - x0 >= 0.9 * self.avance(nombre)

    def cubre(self, codepoint):
        """¿La fuente ya trae `codepoint` con dibujo? Mapeado a un glifo vacío no cuenta:
        hay fuentes que mapean letras que no dibujaron (Comic Runes deja é en blanco)."""
        nombre = self.cmap.get(codepoint)
        return nombre is not None and tiene_contorno(self.conjunto, nombre)

    def agregar(self, codepoint, grabado, avance, nombre=None):
        """Escribe el glifo nuevo y devuelve su nombre. Lo mapea a `codepoint` si la
        fuente no lo cubre; un glifo vacío que lo tuviera se queda, ya sin mapear.
        Con `codepoint=None` es un glifo auxiliar sin mapear, llamado `nombre`."""
        fuente = self.fuente
        orden = list(fuente.getGlyphOrder())
        nombre = base = nombre or nombre_glifo(codepoint)
        sufijo = 1
        while nombre in orden:  # la fuente ya usa ese nombre para otro glifo sin mapear
            nombre, sufijo = f"{base}.{sufijo}", sufijo + 1
        conjunto = self.conjunto
        avance = round(avance)
        if "glyf" in fuente:
            lapiz = TTGlyphPen(conjunto)
            grabado.replay(lapiz)
            glifo = lapiz.glyph()
            fuente.setGlyphOrder(orden + [nombre])
            fuente["glyf"][nombre] = glifo
            glifo.recalcBounds(fuente["glyf"])
            fuente["hmtx"][nombre] = (avance, glifo.xMin)
        else:
            cff = fuente["CFF "].cff
            superior = cff.topDictIndex[0]
            privado = superior.Private
            # El ancho en el charstring va relativo a nominalWidthX.
            lapiz = T2CharStringPen(avance - getattr(privado, "nominalWidthX", 0), conjunto)
            grabado.replay(lapiz)  # descompone los componentes con el conjunto de glifos
            trazo = lapiz.getCharString(private=privado, globalSubrs=cff.GlobalSubrs)
            cadenas = superior.CharStrings
            if cadenas.charStringsAreIndexed:
                cadenas.charStringsIndex.append(trazo)
                cadenas.charStrings[nombre] = len(cadenas.charStringsIndex) - 1
            else:
                cadenas.charStrings[nombre] = trazo
            fuente.setGlyphOrder(orden + [nombre])
            if nombre not in superior.charset:
                superior.charset.append(nombre)
            fuente["hmtx"][nombre] = (avance, 0)  # el conjunto de glifos CFF lo pide para dibujar
            fuente["hmtx"][nombre] = (avance, round(limites(self.conjunto, nombre)[0]))
        if codepoint is not None and not self.cubre(codepoint):
            self.cmap[codepoint] = nombre
            self.nuevos[codepoint] = nombre
        return nombre


def tiene_contorno(conjunto, nombre):
    lapiz = BoundsPen(conjunto)
    conjunto[nombre].draw(lapiz)
    return lapiz.bounds is not None


def limites(conjunto, nombre):
    """Caja (xmin, ymin, xmax, ymax) del glifo `nombre`; error si no tiene contorno."""
    lapiz = BoundsPen(conjunto)
    conjunto[nombre].draw(lapiz)
    if lapiz.bounds is None:
        raise ValueError(f"el glifo '{nombre}' no tiene contorno")
    return lapiz.bounds


def nombre_glifo(codepoint):
    return UV2AGL.get(codepoint) or f"uni{codepoint:04X}"


def con_tinta(conjunto, nombre, x, y):
    """¿El punto (x, y) cae dentro del relleno del glifo?"""
    lapiz = PointInsidePen(conjunto, (x, y))
    conjunto[nombre].draw(lapiz)
    return lapiz.getResult()


def contornos(conjunto, nombre):
    """Contornos del glifo (componentes resueltos), cada uno como lista de trazos."""
    grabado = DecomposingRecordingPen(conjunto)
    conjunto[nombre].draw(grabado)
    resultado, actual = [], []
    for op, args in grabado.value:
        actual.append((op, args))
        if op in ("closePath", "endPath"):
            resultado.append(actual)
            actual = []
    return resultado


def caja_de(trazos):
    lapiz = BoundsPen(None)
    grabado = RecordingPen()
    grabado.value = trazos
    grabado.replay(lapiz)
    return lapiz.bounds


def componentes(*piezas):
    """Glifo hecho de otros glifos (nombre, dx, dy), sin copiar sus contornos."""
    grabado = RecordingPen()
    for nombre, dx, dy in piezas:
        grabado.addComponent(nombre, (1, 0, 0, 1, round(dx), round(dy)))
    return grabado


def transformado(obra, *piezas):
    """Contornos de cada pieza (nombre, matriz) transformados.

    Un espejo (determinante negativo) invierte el sentido de los contornos; se
    revierten para conservar el del original, que decide qué es relleno y qué hueco.
    """
    conjunto = obra.conjunto
    grabado = RecordingPen()
    for nombre, matriz in piezas:
        origen = DecomposingRecordingPen(conjunto)
        conjunto[nombre].draw(origen)
        a, b, c, d = matriz[:4]
        destino = ReverseContourPen(grabado) if a * d - b * c < 0 else grabado
        origen.replay(TransformPen(destino, matriz))
    return grabado


def reducido(obra, origen, escala, piso=None, techo=None):
    """Contorno de `origen` escalado por `escala` (x, y), centrado en su avance escalado
    y con la parte de abajo en `piso` o la de arriba en `techo`. Una y negativa lo voltea."""
    sx, sy = escala
    x0, y0, x1, y1 = limites(obra.conjunto, origen)
    xs, ys = sorted((x0 * sx, x1 * sx)), sorted((y0 * sy, y1 * sy))
    avance = round(obra.avance(origen) * abs(sx))
    dx = (avance - (xs[1] - xs[0])) / 2 - xs[0]
    dy = piso - ys[0] if piso is not None else techo - ys[1]
    return transformado(obra, (origen, (sx, 0, 0, sy, dx, dy))), avance


def exteriores(conjunto, nombre):
    """Trazos de los contornos de `nombre` que no caen dentro de otro (sin huecos): el
    punto de Y2KBUG, que es un anillo, queda macizo."""
    todos = [(c, caja_de(c)) for c in contornos(conjunto, nombre)]

    def dentro(a, b):
        return a is not b and b[0] <= a[0] and b[1] <= a[1] and a[2] <= b[2] and a[3] <= b[3]

    return [t for c, caja in todos if not any(dentro(caja, otra) for _, otra in todos) for t in c]


def grosor_de_punto(obra):
    """Grosor de los trazos hechos con el punto: un poco más delgado que el punto."""
    x0, _, x1, _ = caja_de(exteriores(obra.conjunto, obra.signo(0x2E)))
    return 0.6 * (x1 - x0)


def trazo_de_punto(obra, ancho, alto, inclinacion=0):
    """El contorno exterior de `period` estirado a una caja de `ancho` por `alto`, con su
    esquina inferior izquierda en el origen; `inclinacion` recorre x según la altura
    (positiva: hacia la derecha arriba). Último recurso para guiones, diagonales y
    acentos en fuentes que no traen nada mejor."""
    trazos = exteriores(obra.conjunto, obra.signo(0x2E))
    x0, y0, x1, y1 = caja_de(trazos)
    sx, sy = ancho / (x1 - x0), alto / (y1 - y0)
    origen = RecordingPen()
    origen.value = trazos
    salida = RecordingPen()
    origen.replay(TransformPen(salida, (sx, 0, inclinacion * sy, sy, -sx * x0 - inclinacion * sy * y0, -sy * y0)))
    return salida


def _borde(conjunto, nombre, y, dentro, fuera):
    """Bisección del borde del relleno sobre la línea `y`, entre un x con tinta y uno sin."""
    for _ in range(40):
        medio = (dentro + fuera) / 2
        if con_tinta(conjunto, nombre, medio, y):
            dentro = medio
        else:
            fuera = medio
    return dentro


def tramo_de_tinta(conjunto, nombre, y, desde, hasta, pasos=200):
    """(inicio, fin) del primer tramo con tinta sobre la línea `y` yendo de `desde` a
    `hasta`, o None si no hay tinta."""
    paso = (hasta - desde) / pasos
    previo = desde
    for k in range(pasos + 1):
        x = desde + k * paso
        if con_tinta(conjunto, nombre, x, y):
            inicio = _borde(conjunto, nombre, y, x, previo) if k else x
            fin = x
            while fin + paso <= hasta and con_tinta(conjunto, nombre, fin + paso, y):
                fin += paso
            siguiente = min(fin + paso, hasta)
            if not con_tinta(conjunto, nombre, siguiente, y):
                siguiente = _borde(conjunto, nombre, y, fin, siguiente)
            return inicio, siguiente
        previo = x
    return None


def ancho_de_asta(obra):
    """Grosor de un asta vertical: el tramo de tinta a un tercio de la altura de la `i`
    (debajo de su punto, si tiene), o de la `l` o la `I`. Medir el tramo y no la caja
    deja fuera las serifas."""
    conjunto = obra.conjunto
    nombre = obra.letra("ilI")
    x0, y0, x1, y1 = limites(conjunto, nombre)
    tramo = tramo_de_tinta(conjunto, nombre, y0 + (y1 - y0) / 3, x0, x1)
    if tramo is None:
        raise ValueError(f"no encontré el asta de '{nombre}'")
    return round(tramo[1] - tramo[0])


def grupos_verticales(conjunto, nombre):
    """Intervalos [ymin, ymax] de los contornos, unidos cuando se traslapan; de abajo a arriba."""
    intervalos = sorted(caja_de(c)[1::2] for c in contornos(conjunto, nombre) if caja_de(c))
    grupos = []
    for piso, techo in intervalos:
        if grupos and piso <= grupos[-1][1]:
            grupos[-1][1] = max(grupos[-1][1], techo)
        else:
            grupos.append([piso, techo])
    return grupos
