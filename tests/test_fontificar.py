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
from fontificar.acentos import ARRIBA, MARCAS  # noqa: E402

ENTRADA = RAIZ / "fonts" / "in" / "!y2kbug.ttf"


class Comunes:
    """Pruebas que valen para cualquier idioma; cada subclase fija `IDIOMA`."""

    IDIOMA = None

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.salida_ruta = Path(cls.tmp.name) / "salida.ttf"
        cls.nuevos, cls.omitidos = fontificar.fontificar(ENTRADA, cls.salida_ruta, cls.IDIOMA)
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

    def area(self, conjunto, nombre):
        lapiz = AreaPen(conjunto)
        conjunto[nombre].draw(lapiz)
        return lapiz.value

    def glifo(self, caracter):
        return self.salida.getBestCmap()[ord(caracter)]

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
                    if MARCAS[ord(marcas[0])][2] != ARRIBA:
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

    def test_sobre_fuente_en_espanol_solo_agrega_lo_que_falta(self):
        espanol = Path(self.tmp.name) / "es.ttf"
        ampliada = Path(self.tmp.name) / "es-latin1.ttf"
        agregados_es = fontificar.fontificar(ENTRADA, espanol, "es").nuevos
        agregados = fontificar.fontificar(espanol, ampliada, "latin1").nuevos
        self.assertFalse(set(agregados) & set(agregados_es))
        self.assertEqual(set(agregados) | set(agregados_es), set(self.nuevos))


@unittest.skipUnless(ENTRADA.is_file(), "falta la fuente de prueba en fonts/in")
class PruebasLatinExt(Comunes, unittest.TestCase):
    IDIOMA = "latinext"

    def test_agrega_los_acentos_derivados(self):
        self.assertEqual(set(self.nuevos), set(self.objetivo) | {0x2C6, 0x2DA})

    def test_tabla_mac_usa_codigos_macroman(self):
        mac = next(t for t in self.salida["cmap"].tables if t.platformID == 1)
        self.assertEqual(mac.cmap[0xFF], "caron")  # ˇ en MacRoman
        self.assertEqual(mac.cmap[0xF5], "dotlessi")  # ı en MacRoman

    def test_caron_es_circunflejo_volteado(self):
        """Los puntos de ˆ reflejados en y (a una unidad, por el redondeo), con el mismo
        sentido de contorno."""
        conjunto = self.salida.getGlyphSet()
        caron, circunflejo = self.contornos(self.salida, self.glifo("ˇ")), self.contornos(self.salida, self.glifo("ˆ"))
        _, y0, _, y1 = self.caja([t for c in circunflejo for t in c])
        reflejados = [(x, y0 + y1 - y) for c in circunflejo for _, args in c for x, y in args]
        puntos = [p for c in caron for _, args in c for p in args]
        self.assertEqual(len(puntos), len(reflejados))
        for x, y in puntos:
            self.assertTrue(any(abs(x - rx) <= 1 and abs(y - ry) <= 1 for rx, ry in reflejados), (x, y))
        area = self.area(conjunto, self.glifo("ˆ"))
        self.assertAlmostEqual(self.area(conjunto, self.glifo("ˇ")), area, delta=abs(area) / 100)

    def test_ogonek_va_a_la_derecha_y_la_cedilla_al_centro(self):
        for con_marca, letra in (("ą", "a"), ("Ę", "E"), ("ų", "u"), ("ş", "s")):
            with self.subTest(caracter=con_marca):
                de_letra = self.contornos(self.salida, self.glifo(letra))
                marca = self.caja([t for c in self.contornos(self.salida, self.glifo(con_marca))[len(de_letra):] for t in c])
                _, _, lx1, _ = self.caja([t for c in de_letra for t in c])
                lx0 = self.caja([t for c in de_letra for t in c])[0]
                if con_marca == "ş":
                    self.assertAlmostEqual((marca[0] + marca[2]) / 2, (lx0 + lx1) / 2, delta=1)
                else:
                    self.assertAlmostEqual(marca[2], lx1, delta=1)

    def test_letras_tachadas_son_la_letra_mas_un_trazo_dentro_del_avance(self):
        for tachada, letra in (("Đ", "D"), ("đ", "d"), ("Ħ", "H"), ("ħ", "h"),
                               ("Ł", "L"), ("ł", "l"), ("Ŧ", "T"), ("ŧ", "t")):
            with self.subTest(caracter=tachada):
                de_letra = self.contornos(self.salida, self.glifo(letra))
                todos = self.contornos(self.salida, self.glifo(tachada))
                self.assertEqual(todos[: len(de_letra)], de_letra)
                self.assertEqual(len(todos), len(de_letra) + 1)
                x0, _, x1, _ = self.caja(todos[-1])
                self.assertGreaterEqual(x0, 0)
                self.assertLessEqual(x1, self.avance(tachada))
                self.assertEqual(self.avance(tachada), self.avance(letra))

    def test_copias_son_la_misma_letra(self):
        for copia, letra in (("ı", "i"), ("ĸ", "k"), ("ẞ", "ß")):
            with self.subTest(caracter=copia):
                self.assertEqual(self.contornos(self.salida, self.glifo(copia)),
                                 self.contornos(self.salida, self.glifo(letra)))
                self.assertEqual(self.avance(copia), self.avance(letra))

    def test_l_con_punto_medio(self):
        """Ŀ: la L más `·` a la altura del centro de `hyphen`, a la derecha del asta."""
        de_l = self.contornos(self.salida, self.glifo("L"))
        todos = self.contornos(self.salida, self.glifo("Ŀ"))
        self.assertEqual(todos[: len(de_l)], de_l)
        x0, y0, x1, y1 = self.caja([t for c in todos[len(de_l):] for t in c])
        _, gy0, _, gy1 = self.caja([t for c in self.contornos(self.salida, self.glifo("-")) for t in c])
        self.assertAlmostEqual((y0 + y1) / 2, (gy0 + gy1) / 2, delta=1)
        asta = self.caja([t for c in self.contornos(self.salida, self.glifo("i")) for t in c])
        self.assertGreater(x0, self.caja([t for c in de_l for t in c])[0] + asta[2] - asta[0])
        self.assertLessEqual(x1, self.avance("Ŀ"))

    def test_ij_es_una_letra_tras_otra(self):
        for ligadura, (i, j) in (("Ĳ", "IJ"), ("ĳ", "ij")):
            with self.subTest(caracter=ligadura):
                esperado = (self.contornos(self.salida, self.glifo(i))
                            + self.mover(self.contornos(self.salida, self.glifo(j)), self.avance(i)))
                self.assertEqual(self.contornos(self.salida, self.glifo(ligadura)), esperado)
                self.assertEqual(self.avance(ligadura), self.avance(i) + self.avance(j))

    def test_acentos_nuevos_quedan_a_la_altura_de_grave(self):
        conjunto = self.salida.getGlyphSet()
        piso = self.caja([t for c in self.contornos(self.salida, self.glifo("`")) for t in c])[1]
        # Cada acento con su origen: el sentido del contorno debe ser el mismo.
        for acento, origen in (("¯", "-"), ("˘", "("), ("˙", "."), ("˝", "`"), ("ˇ", "^")):
            with self.subTest(caracter=acento):
                self.assertAlmostEqual(self.caja([t for c in self.contornos(self.salida, self.glifo(acento))
                                                  for t in c])[1], piso, delta=1)
                self.assertGreater(self.area(conjunto, self.glifo(acento)) * self.area(conjunto, self.glifo(origen)), 0)


@unittest.skipUnless(ENTRADA.is_file(), "falta la fuente de prueba en fonts/in")
class PruebasFontificata(Comunes, unittest.TestCase):
    IDIOMA = "fontificata"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Y2KBUG no tiene descendentes: þ Ŋ ŋ se omiten y no cuentan en lo demás.
        cls.objetivo = [c for c in cls.objetivo if c not in cls.omitidos]

    def test_solo_omite_las_letras_que_piden_descendente(self):
        self.assertEqual(set(self.omitidos), {ord("þ"), ord("Ŋ"), ord("ŋ")})

    def test_comillas_y_puntos_que_la_fuente_trae_no_se_tocan(self):
        for caracter in "‘’“”…":
            with self.subTest(caracter=caracter):
                self.assertNotIn(ord(caracter), self.nuevos)
                self.assertEqual(self.glifo(caracter), self.original.getBestCmap()[ord(caracter)])

    def test_rayas_miden_medio_y_un_em(self):
        self.assertEqual(self.avance("\u2013"), 500)
        self.assertEqual(self.avance("\u2014"), 1000)

    def test_por_es_mas_girado(self):
        conjunto = self.salida.getGlyphSet()
        area = self.area(conjunto, self.glifo("+"))
        self.assertAlmostEqual(self.area(conjunto, self.glifo("×")), area, delta=abs(area) / 100)

    def test_superindices_llegan_a_la_altura_de_las_mayusculas(self):
        alto = self.caja([t for c in self.contornos(self.salida, self.glifo("H")) for t in c])[3]
        for caracter in "¹²³ªº°":
            with self.subTest(caracter=caracter):
                techo = self.caja([t for c in self.contornos(self.salida, self.glifo(caracter)) for t in c])[3]
                self.assertAlmostEqual(techo, alto, delta=1)

    def test_encerradas_conservan_la_o(self):
        de_o = self.contornos(self.salida, self.glifo("O"))
        for caracter in "©®":
            with self.subTest(caracter=caracter):
                self.assertEqual(self.contornos(self.salida, self.glifo(caracter))[: len(de_o)], de_o)


if __name__ == "__main__":
    unittest.main()
