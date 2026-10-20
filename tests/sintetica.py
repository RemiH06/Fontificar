"""Fuentes sintéticas para probar cómo se adapta Fontificar a lo que trae cada fuente.

Cada glifo es una lista de polígonos. Por omisión: letras ASCII como una "Π" (dos astas
de 100 y una barra arriba, 700 de alto, unicase), la `i` con punto aparte, y los
signos que usan los acentos derivados. `cambios` reemplaza o agrega glifos (None lo
quita) y `vacios` mapea caracteres a glifos sin dibujo. Incluye 250 glifos de relleno
sin mapear y una subtabla Mac de formato 0, para probar el límite de 256 glifos.
"""
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib.tables._c_m_a_p import cmap_format_0


def caja(x0, y0, x1, y1):
    return [(x0, y0), (x0, y1), (x1, y1), (x1, y0)]


PI = [caja(50, 0, 150, 700), caja(450, 0, 550, 700), caja(50, 600, 550, 700)]
BASICOS = {
    "i": [caja(50, 0, 150, 500), caja(50, 600, 150, 700)],
    "I": [caja(50, 0, 150, 700)],
    ".": [caja(50, 0, 150, 100)],
    ",": [caja(50, -150, 150, 100)],
    "-": [caja(50, 300, 350, 380)],
    "/": [[(50, 0), (130, 0), (400, 700), (320, 700)]],
    "(": [caja(50, -100, 150, 800)],
    "'": [caja(50, 500, 130, 700)],
    "!": [caja(50, 200, 150, 700), caja(50, 0, 150, 100)],
    "?": [caja(50, 300, 350, 700), caja(150, 0, 250, 100)],
    "`": [[(50, 850), (130, 850), (230, 750), (150, 750)]],
    "^": [[(50, 750), (150, 750), (200, 850), (250, 750), (350, 750), (250, 900), (150, 900)]],
    "~": [caja(50, 750, 350, 820)],
}


def construir(ruta, cambios=None, vacios="", cff=False):
    glifos = {chr(c): PI for c in range(0x41, 0x5B)}
    glifos.update({chr(c): PI for c in range(0x61, 0x7B)})
    glifos.update(BASICOS)
    for caracter, poligonos in (cambios or {}).items():
        if poligonos is None:
            glifos.pop(caracter, None)
        else:
            glifos[caracter] = poligonos

    nombres = {caracter: f"g{ord(caracter):04X}" for caracter in glifos}
    nombres.update({caracter: f"vacio{ord(caracter):04X}" for caracter in vacios})
    relleno = [f"relleno{i}" for i in range(250)]
    orden = [".notdef"] + sorted(set(nombres.values())) + relleno
    dibujos = {nombres[c]: p for c, p in glifos.items()}

    fb = FontBuilder(1000, isTTF=not cff)
    fb.setupGlyphOrder(orden)
    fb.setupCharacterMap({ord(c): n for c, n in nombres.items()})
    metricas, trazos = {}, {}
    for nombre in orden:
        poligonos = dibujos.get(nombre, [])
        avance = max((x for p in poligonos for x, _ in p), default=0) + 50 if poligonos else 300
        lapiz = T2CharStringPen(avance, None) if cff else TTGlyphPen(None)
        for poligono in poligonos:
            lapiz.moveTo(poligono[0])
            for punto in poligono[1:]:
                lapiz.lineTo(punto)
            lapiz.closePath()
        trazos[nombre] = lapiz.getCharString() if cff else lapiz.glyph()
        metricas[nombre] = (avance, min((x for p in poligonos for x, _ in p), default=0))
    if cff:
        fb.setupCFF("Prueba-Regular", {"FullName": "Prueba Regular", "FamilyName": "Prueba"}, trazos, {})
    else:
        fb.setupGlyf(trazos)
    fb.setupHorizontalMetrics(metricas)
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": "Prueba", "styleName": "Regular", "psName": "Prueba-Regular"})
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    fb.setupPost()

    mac = cmap_format_0(0)
    mac.platformID, mac.platEncID, mac.language = 1, 0, 0
    mac.cmap = {ord(c): n for c, n in nombres.items() if ord(c) < 0x80}
    fb.font["cmap"].tables.append(mac)
    fb.save(ruta)
