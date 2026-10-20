"""Pruebas de fontificar sobre la fuente real (fonts/in/!y2kbug.ttf, no versionada)."""
import sys
import tempfile
import unicodedata
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))  # con `python -I` el directorio actual no entra solo

from fontTools.pens.boundsPen import BoundsPen  # noqa: E402
from fontTools.pens.recordingPen import DecomposingRecordingPen, RecordingPen  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402

import fontificar  # noqa: E402

ENTRADA = RAIZ / "fonts" / "in" / "!y2kbug.ttf"
OBJETIVO = [ord(c) for c in fontificar.IDIOMAS["es"]]


@unittest.skipUnless(ENTRADA.is_file(), "falta la fuente de prueba en fonts/in")
class PruebasFontificar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.salida_ruta = Path(cls.tmp.name) / "salida.ttf"
        cls.nuevos = fontificar.fontificar(ENTRADA, cls.salida_ruta)
        cls.original = TTFont(ENTRADA)
        cls.salida = TTFont(cls.salida_ruta)

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

    def test_cada_codepoint_tiene_glifo_con_contorno(self):
        cmap = self.salida.getBestCmap()
        for codepoint in OBJETIVO:
            with self.subTest(caracter=chr(codepoint)):
                self.assertIn(codepoint, cmap)
                self.assertTrue(self.contornos(self.salida, cmap[codepoint]))

    def test_tabla_mac_usa_codigos_macroman(self):
        mac = next(t for t in self.salida["cmap"].tables if t.platformID == 1)
        self.assertEqual(mac.cmap[0x96], "ntilde")  # ñ en MacRoman
        self.assertEqual(mac.cmap[0xC1], "exclamdown")  # ¡ en MacRoman

    def test_glifos_originales_no_cambian(self):
        for nombre in self.original.getGlyphOrder():
            with self.subTest(glifo=nombre):
                self.assertEqual(self.contornos(self.original, nombre), self.contornos(self.salida, nombre))
                self.assertEqual(self.original["hmtx"][nombre], self.salida["hmtx"][nombre])
        for codepoint, nombre in self.original.getBestCmap().items():
            self.assertEqual(self.salida.getBestCmap()[codepoint], nombre)

    def test_acento_no_toca_la_letra(self):
        """Los contornos de la base quedan iguales y los del acento están todos por encima."""
        cmap = self.salida.getBestCmap()
        for caracter in "áéíóúüñÁÉÍÓÚÜÑ":
            with self.subTest(caracter=caracter):
                letra = unicodedata.normalize("NFD", caracter)[0]
                nombre_base = cmap[ord(letra)]
                de_base = self.contornos(self.salida, nombre_base)
                todos = self.contornos(self.salida, cmap[ord(caracter)])
                self.assertEqual(todos[: len(de_base)], de_base)
                techo = max(self.caja(c)[3] for c in de_base)
                for acento in todos[len(de_base):]:
                    self.assertGreater(self.caja(acento)[1], techo)

    def test_familia_conserva_el_nombre_original(self):
        for nombre_id in (1, 4):
            original = self.original["name"].getDebugName(nombre_id)
            nuevo = self.salida["name"].getDebugName(nombre_id)
            self.assertEqual(nuevo, f"{original} {fontificar.SUFIJO_NOMBRE}")
        self.assertEqual(self.salida["name"].getDebugName(6), "Y2KBUG-Espanol")

    def test_hdmx_fuera_y_ascendente_cubre_los_acentos(self):
        self.assertNotIn("hdmx", self.salida)
        self.assertGreaterEqual(self.salida["hhea"].ascent, self.salida["head"].yMax)
        self.assertGreaterEqual(self.salida["OS/2"].usWinAscent, self.salida["head"].yMax)

    def test_conserva_instrucciones_de_la_fuente(self):
        for tabla in ("fpgm", "prep", "cvt "):
            self.assertIn(tabla, self.salida)

    def test_fuente_ya_cubierta_no_se_vuelve_a_procesar(self):
        otra = Path(self.tmp.name) / "segunda.ttf"
        with self.assertRaises(ValueError):
            fontificar.fontificar(self.salida_ruta, otra)
        self.assertFalse(otra.exists())

    def test_rechaza_sobrescribir_la_entrada(self):
        with self.assertRaises(ValueError):
            fontificar.fontificar(ENTRADA, ENTRADA)

    def test_rechaza_idioma_desconocido(self):
        with self.assertRaises(ValueError):
            fontificar.fontificar(ENTRADA, Path(self.tmp.name) / "x.ttf", idioma="xx")

    def test_muestra_html_apunta_a_las_dos_fuentes(self):
        ruta = Path(self.tmp.name) / "muestra.html"
        fontificar.escribir_muestra(ENTRADA, self.salida_ruta, ruta)
        texto = ruta.read_text(encoding="utf-8")
        self.assertIn("%21y2kbug.ttf", texto)
        self.assertIn("salida.ttf", texto)
        self.assertIn("¿Qué tal?", texto)


if __name__ == "__main__":
    unittest.main()
