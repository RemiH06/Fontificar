"""Pruebas de cómo se adapta Fontificar a lo que trae cada fuente, sobre fuentes sintéticas
(ver `sintetica.py`): no dependen de fuentes de terceros."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))  # con `python -I` el directorio actual no entra solo
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fontTools.ttLib import TTFont  # noqa: E402

import fontificar  # noqa: E402
from fontificar.cli import principal  # noqa: E402
from fontificar.glifos import caja_de, contornos  # noqa: E402
from sintetica import caja, construir  # noqa: E402


class Adaptable(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def generar(self, idioma="es", cambios=None, vacios="", cff=False):
        extension = ".otf" if cff else ".ttf"
        entrada = Path(self.tmp.name) / f"entrada{extension}"
        salida = Path(self.tmp.name) / f"salida{extension}"
        construir(entrada, cambios, vacios, cff)
        resultado = fontificar.fontificar(entrada, salida, idioma)
        return resultado, TTFont(entrada), TTFont(salida)

    def contornos(self, fuente, caracter):
        return contornos(fuente.getGlyphSet(), fuente.getBestCmap()[ord(caracter)])

    def cajas(self, fuente, caracter):
        return [caja_de(c) for c in self.contornos(fuente, caracter)]

    def avance(self, fuente, caracter):
        return fuente["hmtx"][fuente.getBestCmap()[ord(caracter)]][0]

    def revisar_completa(self, resultado, original, salida, idioma):
        """Todo el idioma con dibujo, sin omitidos, y los glifos originales intactos."""
        self.assertEqual(resultado.omitidos, {})
        for caracter in fontificar.IDIOMAS[idioma].caracteres:
            with self.subTest(caracter=caracter):
                self.assertTrue(self.contornos(salida, caracter))
        for nombre in original.getGlyphOrder():
            self.assertEqual(contornos(original.getGlyphSet(), nombre), contornos(salida.getGlyphSet(), nombre))
            self.assertEqual(original["hmtx"][nombre][0], salida["hmtx"][nombre][0])

    def test_cff_cubre_latin_extended_a(self):
        resultado, original, salida = self.generar("latinext", cff=True)
        self.assertIn("CFF ", salida)
        self.assertNotIn("glyf", salida)
        self.revisar_completa(resultado, original, salida, "latinext")
        self.assertEqual(salida["CFF "].cff.fontNames, ["Prueba-Regular-LatinoExtendido"])
        self.assertEqual(salida["name"].getDebugName(1), "Prueba Latino Extendido")

    def test_truetype_cubre_latin_extended_a(self):
        resultado, original, salida = self.generar("latinext")
        self.revisar_completa(resultado, original, salida, "latinext")

    def test_subtabla_de_formato_0_solo_recibe_glifos_que_caben(self):
        _, _, salida = self.generar("latinext")
        mac = next(t for t in salida["cmap"].tables if t.format == 0)
        self.assertTrue(all(salida.getGlyphID(n) < 256 for n in mac.cmap.values()))
        self.assertNotIn(0x8E, mac.cmap)  # é en MacRoman: su glifo queda después del 256

    def test_omite_lo_que_no_puede_derivar_y_agrega_lo_demas(self):
        """Sin `~` ni `s` no hay de dónde sacar la tilde: ñ Ñ se omiten con su motivo."""
        resultado, _, salida = self.generar(cambios={"~": None, "s": None, "S": None})
        self.assertEqual(set(resultado.omitidos), {ord("ñ"), ord("Ñ")})
        self.assertIn("'~'", resultado.omitidos[ord("ñ")])
        for caracter in "áéíóúüÁÉÍÓÚÜ¡¿":
            self.assertTrue(self.contornos(salida, caracter))

    def test_falla_si_no_puede_derivar_nada(self):
        quitar = {chr(c): None for c in range(0x41, 0x7B)}
        quitar.update({".": None, "'": None, "!": None, "?": None})
        with self.assertRaisesRegex(ValueError, "no pude derivar ningún"):
            self.generar(cambios=quitar)

    def test_caracter_mapeado_a_glifo_vacio_se_rellena(self):
        resultado, original, salida = self.generar(vacios="é")
        self.assertIn(ord("é"), resultado.nuevos)
        self.assertTrue(self.contornos(salida, "é"))
        self.assertIn("vacio00E9", salida.getGlyphOrder())  # el vacío se queda, sin mapear
        self.assertNotEqual(salida.getBestCmap()[ord("é")], "vacio00E9")

    def test_tilde_de_respaldo_es_la_tilde_modificadora(self):
        tilde = [caja(50, 760, 330, 800)]
        resultado, _, salida = self.generar(cambios={"~": None, "˜": tilde})
        self.assertIn(0x7E, resultado.nuevos)
        self.assertEqual(self.cajas(salida, "~"), self.cajas(salida, "˜"))

    def test_grave_sale_del_agudo(self):
        agudo = [[(150, 850), (230, 850), (130, 750), (50, 750)]]
        resultado, _, salida = self.generar("latin1", cambios={"`": None, "´": agudo})
        self.assertIn(0x60, resultado.nuevos)
        self.assertEqual(self.cajas(salida, "`"), self.cajas(salida, "´"))

    def test_agudo_sale_del_apostrofo_sin_grave(self):
        resultado, _, salida = self.generar(cambios={"`": None})
        self.assertEqual(resultado.omitidos, {})
        x0, y0, x1, y1 = self.cajas(salida, "´")[0]
        self.assertGreater(x1 - x0, 80)  # inclinado: más ancho que el apóstrofo

    def test_acento_existente_sin_forma_de_acento_no_se_usa(self):
        _, _, salida = self.generar("latin1", cambios={"ˆ": [caja(0, 0, 600, 900)]})
        original = salida.getBestCmap()[0x2C6]
        componentes = [c.glyphName for c in salida["glyf"][salida.getBestCmap()[ord("â")]].components]
        self.assertNotIn(original, componentes)
        self.assertEqual(self.cajas(salida, "ˆ"), [(0, 0, 600, 900)])  # el original no se toca

    def test_signo_con_linea_de_cabecera(self):
        """El punto con una barra de cabecera (estilo Samarkan): la diéresis no la arrastra."""
        punto = [caja(-20, 650, 300, 700), caja(100, 0, 200, 100)]
        _, _, salida = self.generar(cambios={".": punto})
        de_u = len(self.contornos(salida, "u"))
        for x0, _, x1, _ in self.cajas(salida, "ü")[de_u:]:
            self.assertLessEqual(x1 - x0, 60)

    def test_i_pierde_el_punto_bajo_el_acento(self):
        resultado, _, salida = self.generar()
        self.assertIn(0x131, resultado.nuevos)
        self.assertEqual(len(self.contornos(salida, "ı")), 1)
        self.assertEqual(len(self.contornos(salida, "í")), 2)  # asta y acento, sin punto

    def test_eszett_de_b_simetrica_son_dos_s(self):
        _, _, salida = self.generar("latin1")
        self.assertEqual(len(self.contornos(salida, "ß")), 2 * len(self.contornos(salida, "s")))
        self.assertEqual(self.avance(salida, "ß"), 2 * self.avance(salida, "s"))

    def test_eszett_de_b_unida_solo_abajo_es_b_volteada(self):
        b = [caja(50, 0, 150, 700), caja(150, 0, 550, 100), caja(450, 0, 550, 700), caja(250, 600, 550, 700)]
        _, _, salida = self.generar("latin1", cambios={"B": b})
        volteada = sorted((x0, 700 - y1, x1, 700 - y0) for x0, y0, x1, y1 in self.cajas(salida, "B"))
        self.assertEqual(sorted(self.cajas(salida, "ß")), volteada)

    def test_lado_del_asta_se_mide(self):
        """Đ: el trazo va al asta. Con el asta a la derecha (como una `d`), a la derecha y a
        0.8 de alto; con asta a la izquierda, a la izquierda y a media altura."""
        d_derecha = [caja(450, 0, 550, 700), caja(50, 0, 450, 100), caja(50, 600, 450, 700)]
        d_izquierda = [caja(50, 0, 150, 700), caja(150, 0, 550, 100), caja(150, 600, 550, 700)]
        for d, lado, altura in ((d_derecha, "derecha", 560), (d_izquierda, "izquierda", 350)):
            with self.subTest(lado=lado):
                _, _, salida = self.generar("latinext", cambios={"D": d})
                x0, y0, x1, y1 = self.cajas(salida, "Đ")[-1]
                centro = (x0 + x1) / 2
                self.assertGreater(centro, 300) if lado == "derecha" else self.assertLess(centro, 300)
                self.assertAlmostEqual((y0 + y1) / 2, altura, delta=1)

    def test_acento_sale_de_una_letra_acentuada_de_la_fuente(self):
        """Sin `´`, `` ` `` ni apóstrofo, pero con é dibujada: el agudo es é menos e."""
        acento = [[(250, 720), (330, 720), (430, 820), (350, 820)]]
        cambios = {"`": None, "'": None, "é": acento + [caja(50, 0, 150, 700), caja(450, 0, 550, 700),
                                                         caja(50, 600, 550, 700)]}
        cambios["e"] = [caja(50, 0, 150, 700), caja(450, 0, 550, 700), caja(50, 600, 550, 700)]
        resultado, _, salida = self.generar(cambios=cambios)
        self.assertEqual(resultado.omitidos, {})
        (x0, y0, x1, y1), = self.cajas(salida, "´")
        self.assertEqual((x1 - x0, y1 - y0), (180, 100))


class Cli(unittest.TestCase):
    def test_copia_licencia_escribe_muestra_junto_a_la_salida_y_lista_omitidos(self):
        with tempfile.TemporaryDirectory() as tmp:
            entrada_dir, salida_dir = Path(tmp) / "in", Path(tmp) / "out"
            entrada_dir.mkdir()
            construir(entrada_dir / "prueba.ttf", {"~": None, "s": None, "S": None})
            (entrada_dir / "FreeLicense.txt").write_text("licencia de prueba", encoding="utf-8")
            texto = io.StringIO()
            with contextlib.redirect_stdout(texto):
                principal([str(entrada_dir / "prueba.ttf"), str(salida_dir / "prueba-es.ttf")])
            self.assertEqual((salida_dir / "prueba-es-licencia.txt").read_text(encoding="utf-8"), "licencia de prueba")
            self.assertTrue((salida_dir / "muestra.html").is_file())
            self.assertIn("2 omitidos", texto.getvalue())
            self.assertIn("U+00F1", texto.getvalue())


if __name__ == "__main__":
    unittest.main()
