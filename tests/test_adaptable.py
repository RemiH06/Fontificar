"""Pruebas de cómo se adapta Fontificar a lo que trae cada fuente, sobre fuentes sintéticas
(ver `sintetica.py`): no dependen de fuentes de terceros."""
import contextlib
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))  # con `python -I` el directorio actual no entra solo
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fontTools.ttLib import TTFont  # noqa: E402

import fontificar  # noqa: E402
from fontificar import cli  # noqa: E402
from fontificar.cli import principal  # noqa: E402
from fontificar.glifos import caja_de, contornos  # noqa: E402
from sintetica import PI, caja, construir  # noqa: E402


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

    def test_fontificata_sin_descendentes_omite_solo_thorn_y_eng(self):
        """La fuente sintética no trae `+ | < >`: ± × ¦ ‹ › « » salen del guion. Sin
        descendentes no hay þ ni ŋ Ŋ; lo demás sale, en TrueType y en CFF."""
        for cff in (False, True):
            with self.subTest(cff=cff):
                digitos = {str(d): PI for d in range(10)}  # sin ellos, ¹ ² ³ ¼ ½ ¾ se omiten
                resultado, original, salida = self.generar("fontificata", cambios=digitos, cff=cff)
                self.assertEqual(set(resultado.omitidos), {ord("þ"), ord("Ŋ"), ord("ŋ")})
                self.assertIn("descendente", resultado.omitidos[ord("þ")])
                for caracter in fontificar.IDIOMAS["fontificata"].caracteres:
                    if ord(caracter) not in resultado.omitidos:
                        self.assertTrue(self.contornos(salida, caracter), caracter)
                for nombre in original.getGlyphOrder():
                    self.assertEqual(contornos(original.getGlyphSet(), nombre),
                                     contornos(salida.getGlyphSet(), nombre))

    def test_simbolos_hechos_con_el_guion(self):
        """El guion sintético va de 50 a 350 (avance 400) con centro en 340."""
        _, _, salida = self.generar("fontificata")
        self.assertEqual(self.avance(salida, "\u2013"), 500)
        self.assertEqual(self.avance(salida, "\u2014"), 1000)
        x0, _, x1, _ = caja_de([t for c in self.contornos(salida, "\u2014") for t in c])
        self.assertAlmostEqual(x0, 50, delta=1)
        self.assertAlmostEqual(x1, 950, delta=1)
        for signo in "‹›×":
            with self.subTest(caracter=signo):
                _, y0, _, y1 = caja_de([t for c in self.contornos(salida, signo) for t in c])
                self.assertAlmostEqual((y0 + y1) / 2, 340, delta=2)
        # « es ‹ dos veces, encimados.
        self.assertEqual(len(self.contornos(salida, "«")), 2 * len(self.contornos(salida, "‹")))

    def test_letras_con_descendente(self):
        """Con `p` y `j` que bajan y `b` que sube: þ es la `b` encimada con la `p` y ŋ
        la `n` con el gancho de la `j` (sin su punto) a la derecha."""
        cambios = {
            "p": [caja(50, -250, 150, 500), caja(50, 400, 450, 500), caja(350, 200, 450, 500), caja(50, 200, 450, 300)],
            "b": [caja(50, 0, 150, 800), caja(50, 0, 450, 100), caja(350, 0, 450, 300), caja(50, 200, 450, 300)],
            "j": [caja(350, -250, 450, 500), caja(50, -250, 450, -150), caja(350, 600, 450, 700)],
            "J": [caja(350, -250, 450, 700), caja(50, -250, 450, -150)],
            "n": [caja(50, 0, 150, 500), caja(450, 0, 550, 500), caja(50, 400, 550, 500)],
        }
        resultado, _, salida = self.generar("fontificata", cambios=cambios)
        self.assertNotIn(ord("þ"), resultado.omitidos)
        _, y0, _, y1 = caja_de([t for c in self.contornos(salida, "þ") for t in c])
        self.assertEqual((y0, y1), (-250, 800))
        for eng, letra in (("ŋ", "n"), ("Ŋ", "N")):
            with self.subTest(caracter=eng):
                x0, y0, x1, y1 = caja_de([t for c in self.contornos(salida, eng) for t in c])
                self.assertEqual(y0, -250)
                self.assertEqual(x1, caja_de([t for c in self.contornos(salida, letra) for t in c])[2])
        _, _, _, y1 = caja_de([t for c in self.contornos(salida, "ŋ") for t in c])
        self.assertEqual(y1, 500)  # sin el punto de la `j`

    def test_circunflejo_de_agudo_y_grave_largos_se_reduce(self):
        """Sin `^` y con un grave de 300 de alto, el circunflejo hecho de agudo y grave
        no pasa de `ALTO_DE_ACENTO` (150 en 1000)."""
        grave = [[(50, 750), (130, 750), (330, 1050), (250, 1050)]]
        resultado, _, salida = self.generar("latinext", cambios={"^": None, "`": grave})
        self.assertIn(0x2C6, resultado.nuevos)
        _, y0, _, y1 = caja_de([t for c in self.contornos(salida, "ˆ") for t in c])
        self.assertLessEqual(y1 - y0, 150 + 1)

    def test_thorn_mayuscula_igual_a_la_minuscula_si_la_p_baja(self):
        p = [caja(50, -250, 150, 500), caja(50, 400, 450, 500), caja(350, 200, 450, 500), caja(50, 200, 450, 300)]
        b = [caja(50, 0, 150, 800), caja(50, 0, 450, 100), caja(350, 0, 450, 300), caja(50, 200, 450, 300)]
        _, _, salida = self.generar("fontificata", cambios={"p": p, "P": p, "b": b})
        self.assertEqual(self.contornos(salida, "Þ"), self.contornos(salida, "þ"))

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
                codigo = principal([str(entrada_dir / "prueba.ttf"), "-o", str(salida_dir / "prueba-es.ttf"),
                                    "--idioma", "es"])
            self.assertEqual(codigo, 0)
            self.assertEqual((salida_dir / "prueba-es-licencia.txt").read_text(encoding="utf-8"), "licencia de prueba")
            self.assertTrue((salida_dir / "prueba-es-muestra.html").is_file())
            self.assertIn("2 omitidos", texto.getvalue())
            self.assertIn("U+00F1", texto.getvalue())


class Lote(unittest.TestCase):
    """El flujo de dejar fuentes o zips en fonts/in y correr `fontificar` sin argumentos."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.entradas, self.salidas = Path(tmp.name) / "in", Path(tmp.name) / "out"
        self.entradas.mkdir()
        for nombre, valor in (("ENTRADAS", self.entradas), ("SALIDAS", self.salidas)):
            parche = mock.patch.object(cli, nombre, valor)
            parche.start()
            self.addCleanup(parche.stop)

    def correr(self, *argumentos):
        salida, errores = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(errores):
            codigo = principal(list(argumentos))
        return codigo, salida.getvalue(), errores.getvalue()

    def zip_con(self, nombre, miembros):
        ruta = self.entradas / nombre
        with zipfile.ZipFile(ruta, "w") as archivo:
            for miembro, datos in miembros.items():
                archivo.writestr(miembro, datos)
        return ruta

    def bytes_de_fuente(self, nombre="prueba.ttf", cff=False):
        ruta = self.entradas.parent / nombre
        construir(ruta, cff=cff)
        return ruta.read_bytes()

    def test_zip_sin_argumentos_sale_en_out_con_licencia_y_muestra_incrustada(self):
        self.zip_con("Prueba.zip", {"Prueba/prueba.ttf": self.bytes_de_fuente(),
                                    "Prueba/read_me.txt": b"licencia del zip",
                                    "__MACOSX/Prueba/._prueba.ttf": b"basura de mac"})
        codigo, salida, errores = self.correr()
        self.assertEqual(codigo, 0, errores)
        nueva = self.salidas / "prueba-fontificata.ttf"
        self.assertIn(ord("ñ"), TTFont(nueva).getBestCmap())
        self.assertEqual((self.salidas / "prueba-fontificata-licencia.txt").read_bytes(), b"licencia del zip")
        muestra = (self.salidas / "prueba-fontificata-muestra.html").read_text(encoding="utf-8")
        self.assertIn("data:font/ttf;base64,", muestra)  # la original no está en disco
        self.assertNotIn("aviso", errores)
        self.assertNotIn("_prueba", salida)

    def test_zip_con_varias_fuentes_da_una_salida_por_cada_una(self):
        self.zip_con("Familia.zip", {"regular.ttf": self.bytes_de_fuente("r.ttf"),
                                     "negrita.otf": self.bytes_de_fuente("n.otf", cff=True)})
        codigo, salida, _ = self.correr("Familia.zip", "--idioma", "es")  # se busca en fonts/in
        self.assertEqual(codigo, 0)
        self.assertTrue((self.salidas / "regular-es.ttf").is_file())
        self.assertTrue((self.salidas / "negrita-es.otf").is_file())
        self.assertIn("resumen: 2 generadas, 0 con error", salida)

    def test_una_fuente_danada_no_detiene_el_lote_y_las_subcarpetas_no_entran(self):
        construir(self.entradas / "buena.ttf")
        (self.entradas / "rota.ttf").write_bytes(b"esto no es una fuente")
        (self.entradas / "rota.zip").write_bytes(b"ni esto un zip")
        (self.entradas / "notas.txt").write_text("se ignora", encoding="utf-8")
        (self.entradas / "pruebas").mkdir()
        construir(self.entradas / "pruebas" / "ajena.ttf")
        codigo, salida, errores = self.correr("--idioma", "es")
        self.assertEqual(codigo, 1)
        self.assertTrue((self.salidas / "buena-es.ttf").is_file())
        self.assertFalse((self.salidas / "ajena-es.ttf").exists())
        self.assertIn("rota.ttf", errores)
        self.assertIn("rota.zip", errores)
        self.assertIn("resumen: 1 generadas, 2 con error", salida)

    def test_revisar_no_escribe_nada(self):
        construir(self.entradas / "prueba.ttf", {"~": None, "s": None, "S": None})
        codigo, salida, _ = self.correr("--revisar", "--idioma", "es")
        self.assertEqual(codigo, 0)
        self.assertFalse(self.salidas.exists())
        self.assertIn("se pueden agregar", salida)
        self.assertIn("U+00F1", salida)  # la ñ se omite: no hay tilde ni de dónde sacarla

    def test_una_consola_cp1252_no_confunde_caracteres_con_errores(self):
        construir(self.entradas / "prueba.ttf")
        crudo = io.BytesIO()
        consola = io.TextIOWrapper(crudo, encoding="cp1252")
        with contextlib.redirect_stdout(consola), contextlib.redirect_stderr(io.StringIO()):
            codigo = principal(["--revisar"])  # fontificata lista ł ˝ ˚, fuera de cp1252
        consola.flush()
        self.assertEqual(codigo, 0)
        self.assertIn(b"se pueden agregar", crudo.getvalue())

    def test_salida_explicita_pide_una_sola_fuente(self):
        construir(self.entradas / "a.ttf")
        construir(self.entradas / "b.ttf")
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            principal(["-o", str(self.salidas / "x.ttf")])

    def test_dos_entradas_con_la_misma_salida_no_se_enciman(self):
        construir(self.entradas / "prueba.ttf")
        self.zip_con("prueba.zip", {"prueba.ttf": self.bytes_de_fuente()})
        codigo, _, errores = self.correr("--idioma", "es")
        self.assertEqual(codigo, 1)
        self.assertIn("se encimaría", errores)

    def test_carpeta_vacia_y_archivo_inexistente_dan_error_claro(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            principal([])
        codigo, _, errores = self.correr("no-existe.ttf")
        self.assertEqual(codigo, 1)
        self.assertIn("no existe", errores)

    def test_zip_con_un_archivo_enorme_se_rechaza_sin_leerlo(self):
        self.zip_con("grande.zip", {"grande.ttf": b"0" * 2048})
        with mock.patch.object(cli, "MAXIMO_EN_ZIP", 1024):
            codigo, _, errores = self.correr()
        self.assertEqual(codigo, 1)
        self.assertIn("pesa más de", errores)


if __name__ == "__main__":
    unittest.main()
