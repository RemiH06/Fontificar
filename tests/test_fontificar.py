"""Pruebas de fontificar sobre la fuente real (fonts/in/!y2kbug.ttf, no versionada)."""
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))  # con `python -I` el directorio actual no entra solo

from fontTools.pens.areaPen import AreaPen  # noqa: E402
from fontTools.pens.boundsPen import BoundsPen  # noqa: E402
from fontTools.pens.recordingPen import DecomposingRecordingPen, RecordingPen  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402

import fontificar  # noqa: E402

ENTRADA = RAIZ / "fonts" / "in" / "!y2kbug.ttf"


class Comunes:
    """Pruebas que valen para cualquier idioma; cada subclase fija `IDIOMA`."""

    IDIOMA = None

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.salida_ruta = Path(cls.tmp.name) / "salida.ttf"
        cls.nuevos = fontificar.fontificar(ENTRADA, cls.salida_ruta, cls.IDIOMA)
        cls.original = TTFont(ENTRADA)
        cls.salida = TTFont(cls.salida_ruta)
        cls.objetivo = [ord(c) for c in fontificar.IDIOMAS[cls.IDIOMA].caracteres]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def contornos(self, fuente, nombre):
        """Contornos del glifo (componentes ya resueltos), cada uno como lista de trazos."""
        conjunto = fuente.getGlyphSet()
        grabado = DecomposingRecordingPen(conjunto)
        conjunto[nombre].draw(grabado)
        contornos, actual = [], []
        for op, args in grabado.value:
            actual.append((op, args))
            if op in ("closePath", "endPath"):
                contornos.append(actual)
                actual = []
        return contornos

    def caja(self, contorno):
        lapiz = BoundsPen(None)
        grabado = RecordingPen()
        grabado.value = contorno
        grabado.replay(lapiz)
        return lapiz.bounds

    def mover(self, contornos, dx):
        return [[(op, tuple((x + dx, y) for x, y in args)) for op, args in c] for c in contornos]

    def avance(self, caracter):
        return self.salida["hmtx"][self.salida.getBestCmap()[ord(caracter)]][0]

    def test_cada_codepoint_tiene_glifo_con_contorno(self):
        cmap = self.salida.getBestCmap()
        for codepoint in self.objetivo:
            with self.subTest(caracter=chr(codepoint)):
                self.assertIn(codepoint, cmap)
                self.assertTrue(self.contornos(self.salida, cmap[codepoint]))

    def test_glifos_originales_no_cambian(self):
        for nombre in self.original.getGlyphOrder():
            with self.subTest(glifo=nombre):
                self.assertEqual(self.contornos(self.original, nombre), self.contornos(self.salida, nombre))
                self.assertEqual(self.original["hmtx"][nombre], self.salida["hmtx"][nombre])
        for codepoint, nombre in self.original.getBestCmap().items():
            self.assertEqual(self.salida.getBestCmap()[codepoint], nombre)

    def test_acento_no_toca_la_letra_ni_la_vecina(self):
        """La base queda igual (a lo más recorrida si el avance creció), el acento queda
        todo arriba (o debajo, la cedilla) y dentro del avance del glifo."""
        cmap = self.salida.getBestCmap()
        for codepoint in self.objetivo:
            letra, *marcas = unicodedata.normalize("NFD", chr(codepoint))
            if len(marcas) != 1:
                continue
            with self.subTest(caracter=chr(codepoint)):
                nombre_base = cmap[ord(letra)]
                corrimiento = (self.avance(chr(codepoint)) - self.salida["hmtx"][nombre_base][0]) // 2
                de_base = self.mover(self.contornos(self.salida, nombre_base), corrimiento)
                todos = self.contornos(self.salida, cmap[codepoint])
                self.assertEqual(todos[: len(de_base)], de_base)
                piso = min(self.caja(c)[1] for c in de_base)
                techo = max(self.caja(c)[3] for c in de_base)
                for acento in todos[len(de_base):]:
                    x0, y0, x1, y1 = self.caja(acento)
                    if fontificar.MARCAS[ord(marcas[0])][2]:
                        self.assertLessEqual(y1, piso)
                    else:
                        self.assertGreater(y0, techo)
                    self.assertGreaterEqual(x0, 0)
                    self.assertLessEqual(x1, self.avance(chr(codepoint)))

    def test_familia_conserva_el_nombre_original(self):
        idioma = fontificar.IDIOMAS[self.IDIOMA]
        for nombre_id in (1, 4):
            original = self.original["name"].getDebugName(nombre_id)
            nuevo = self.salida["name"].getDebugName(nombre_id)
            self.assertEqual(nuevo, f"{original} {idioma.sufijo}")
        self.assertEqual(self.salida["name"].getDebugName(6), f"Y2KBUG-{idioma.sufijo_ps}")

    def test_hdmx_fuera_y_metricas_cubren_los_glifos(self):
        self.assertNotIn("hdmx", self.salida)
        self.assertGreaterEqual(self.salida["hhea"].ascent, self.salida["head"].yMax)
        self.assertGreaterEqual(self.salida["OS/2"].usWinAscent, self.salida["head"].yMax)
        self.assertLessEqual(self.salida["hhea"].descent, self.salida["head"].yMin)
        self.assertGreaterEqual(self.salida["OS/2"].usWinDescent, -self.salida["head"].yMin)

    def test_conserva_instrucciones_de_la_fuente(self):
        for tabla in ("fpgm", "prep", "cvt "):
            self.assertIn(tabla, self.salida)

    def test_fuente_ya_cubierta_no_se_vuelve_a_procesar(self):
        otra = Path(self.tmp.name) / "segunda.ttf"
        with self.assertRaises(ValueError):
            fontificar.fontificar(self.salida_ruta, otra, self.IDIOMA)
        self.assertFalse(otra.exists())

    def test_muestra_html_apunta_a_las_dos_fuentes(self):
        ruta = Path(self.tmp.name) / "muestra.html"
        fontificar.escribir_muestra(ENTRADA, self.salida_ruta, ruta, self.IDIOMA)
        texto = ruta.read_text(encoding="utf-8")
        self.assertIn("%21y2kbug.ttf", texto)
        self.assertIn("salida.ttf", texto)
        self.assertIn(fontificar.IDIOMAS[self.IDIOMA].muestra, texto)


@unittest.skipUnless(ENTRADA.is_file(), "falta la fuente de prueba en fonts/in")
class PruebasEspanol(Comunes, unittest.TestCase):
    IDIOMA = "es"

    def test_solo_agrega_lo_del_idioma(self):
        """Los acentos que el español no usa (ˆ ˚ ¸) no se agregan."""
        self.assertEqual(set(self.nuevos), set(self.objetivo))

    def test_tabla_mac_usa_codigos_macroman(self):
        mac = next(t for t in self.salida["cmap"].tables if t.platformID == 1)
        self.assertEqual(mac.cmap[0x96], "ntilde")  # ñ en MacRoman
        self.assertEqual(mac.cmap[0xC1], "exclamdown")  # ¡ en MacRoman

    def test_rechaza_sobrescribir_la_entrada(self):
        with self.assertRaises(ValueError):
            fontificar.fontificar(ENTRADA, ENTRADA)

    def test_rechaza_idioma_desconocido(self):
        with self.assertRaises(ValueError):
            fontificar.fontificar(ENTRADA, Path(self.tmp.name) / "x.ttf", idioma="xx")


@unittest.skipUnless(ENTRADA.is_file(), "falta la fuente de prueba en fonts/in")
class PruebasLatin1(Comunes, unittest.TestCase):
    IDIOMA = "latin1"

    def test_agrega_los_acentos_derivados(self):
        self.assertEqual(set(self.nuevos), set(self.objetivo) | {0x2C6, 0x2DA})

    def test_tabla_mac_usa_codigos_macroman(self):
        mac = next(t for t in self.salida["cmap"].tables if t.platformID == 1)
        self.assertEqual(mac.cmap[0x8D], "ccedilla")  # ç en MacRoman
        self.assertEqual(mac.cmap[0xCE], "OE")  # Œ en MacRoman

    def test_o_barrada_es_o_mas_diagonal(self):
        cmap = self.salida.getBestCmap()
        for barrada, letra in (("ø", "o"), ("Ø", "O")):
            with self.subTest(caracter=barrada):
                todos = self.contornos(self.salida, cmap[ord(barrada)])
                de_letra = self.contornos(self.salida, cmap[ord(letra)])
                diagonal = self.contornos(self.salida, cmap[ord("/")])
                self.assertEqual(todos[: len(de_letra)], de_letra)
                self.assertEqual(len(todos), len(de_letra) + len(diagonal))
                self.assertEqual(self.avance(barrada), self.avance(letra))

    def test_ligaduras_comparten_un_asta(self):
        """La segunda letra empieza antes de que acabe la primera, y el ancho queda
        entre el de la primera y la suma de las dos."""
        cmap = self.salida.getBestCmap()
        for ligadura in ("æ", "Æ", "œ", "Œ"):
            with self.subTest(caracter=ligadura):
                primera, segunda = {"æ": "ae", "Æ": "AE", "œ": "oe", "Œ": "OE"}[ligadura]
                todos = self.contornos(self.salida, cmap[ord(ligadura)])
                de_primera = self.contornos(self.salida, cmap[ord(primera)])
                self.assertEqual(todos[: len(de_primera)], de_primera)
                fin_primera = max(self.caja(c)[2] for c in de_primera)
                inicio_segunda = min(self.caja(c)[0] for c in todos[len(de_primera):])
                self.assertLess(inicio_segunda, fin_primera)
                self.assertGreater(self.avance(ligadura), self.avance(primera))
                self.assertLess(self.avance(ligadura), self.avance(primera) + self.avance(segunda))

    def test_eszett_es_b_volteada(self):
        cmap = self.salida.getBestCmap()
        conjunto = self.salida.getGlyphSet()
        eszett, b = cmap[ord("ß")], cmap[ord("B")]
        _, y0, _, y1 = self.caja([t for c in self.contornos(self.salida, b) for t in c])
        esperado = {(x, y0 + y1 - y) for c in self.contornos(self.salida, b)
                    for _, args in c for x, y in args}
        obtenido = {p for c in self.contornos(self.salida, eszett) for _, args in c for p in args}
        self.assertEqual(obtenido, esperado)
        self.assertEqual(self.avance("ß"), self.avance("B"))
        self.assertAlmostEqual(self.area(conjunto, eszett), self.area(conjunto, b))

    def test_espejos_conservan_el_sentido_del_contorno(self):
        """El agudo (espejo de `grave`), la cedilla (`comma` volteada) y la ß (`B`
        volteada) giran en el mismo sentido que su origen."""
        cmap = self.salida.getBestCmap()
        conjunto = self.salida.getGlyphSet()
        for nuevo, origen in (("´", "`"), ("¸", ","), ("ß", "B")):
            with self.subTest(caracter=nuevo):
                self.assertGreater(self.area(conjunto, cmap[ord(nuevo)])
                                   * self.area(conjunto, cmap[ord(origen)]), 0)

    def area(self, conjunto, nombre):
        lapiz = AreaPen(conjunto)
        conjunto[nombre].draw(lapiz)
        return lapiz.value

    def test_sobre_fuente_en_espanol_solo_agrega_lo_que_falta(self):
        espanol = Path(self.tmp.name) / "es.ttf"
        ampliada = Path(self.tmp.name) / "es-latin1.ttf"
        agregados_es = fontificar.fontificar(ENTRADA, espanol, "es")
        agregados = fontificar.fontificar(espanol, ampliada, "latin1")
        self.assertFalse(set(agregados) & set(agregados_es))
        self.assertEqual(set(agregados) | set(agregados_es), set(self.nuevos))


if __name__ == "__main__":
    unittest.main()
