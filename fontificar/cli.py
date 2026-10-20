"""CLI: `fontificar [entradas...]`. Sin entradas procesa lo que esté suelto en `fonts/in/`
(.zip, .ttf, .otf; las subcarpetas no) y escribe cada fuente nueva en `fonts/out/`."""
import argparse
import shutil
import sys
import webbrowser
import zipfile
from pathlib import Path, PurePosixPath
from typing import NamedTuple

from fontTools.ttLib import TTLibError

from .idiomas import IDIOMAS
from .muestra import escribir_muestra
from .nucleo import fontificar

RAIZ = Path(__file__).resolve().parent.parent
ENTRADAS = RAIZ / "fonts" / "in"
SALIDAS = RAIZ / "fonts" / "out"
FUENTES = (".ttf", ".otf")
ACEPTADAS = FUENTES + (".zip",)
# Nombres de archivo (sin extensión, en minúsculas) que suelen traer la licencia.
LICENCIAS = ("read_me", "readme", "readthis", "license", "licence", "licencia", "freelicense", "ofl")
# Tope por archivo dentro de un zip: una fuente pesa kilobytes; más es un zip dañado o malicioso.
MAXIMO_EN_ZIP = 64 * 2**20


class Fuente(NamedTuple):
    nombre: str  # nombre del archivo, de él sale el de la salida
    origen: str  # para los mensajes
    entrada: object  # ruta, o los bytes si viene de un zip
    licencia: object  # ruta, bytes o None


def _es_licencia(nombre):
    ruta = PurePosixPath(nombre)
    return ruta.suffix.lower() == ".txt" and ruta.stem.lower().replace(" ", "") in LICENCIAS


def _buscar_licencia(carpeta):
    """El primer .txt de `carpeta` cuyo nombre parece de licencia, o None."""
    candidatos = sorted(p for p in carpeta.glob("*.txt") if _es_licencia(p.name))
    return candidatos[0] if candidatos else None


def _del_zip(ruta):
    """Las fuentes de un zip, leídas en memoria: nada se extrae a disco."""
    leidas, licencia = [], None
    with zipfile.ZipFile(ruta) as archivo:
        for info in archivo.infolist():
            nombre = PurePosixPath(info.filename)
            # __MACOSX/ y ._* son metadatos de macOS, no fuentes.
            if info.is_dir() or "__MACOSX" in nombre.parts or nombre.name.startswith("._"):
                continue
            es_fuente = nombre.suffix.lower() in FUENTES
            if not es_fuente and not (licencia is None and _es_licencia(nombre.name)):
                continue
            if info.file_size > MAXIMO_EN_ZIP:
                raise ValueError(f"{info.filename} pesa más de {MAXIMO_EN_ZIP // 2**20} MB")
            datos = archivo.read(info)
            if es_fuente:
                leidas.append((nombre.name, f"{ruta.name}:{info.filename}", datos))
            else:
                licencia = datos
    if not leidas:
        raise ValueError("el zip no trae fuentes .ttf ni .otf")
    return [Fuente(nombre, origen, datos, licencia) for nombre, origen, datos in leidas]


def _archivos(argumentos):
    """Rutas a procesar. Cada argumento se busca tal cual y, si no existe, en `fonts/in/`;
    de una carpeta se toma su nivel superior. Sin argumentos, `fonts/in/`."""
    for argumento in argumentos or [ENTRADAS]:
        ruta = Path(argumento)
        if not ruta.exists() and (ENTRADAS / argumento).exists():
            ruta = ENTRADAS / argumento
        if ruta.is_dir():
            yield from sorted(h for h in ruta.iterdir() if h.is_file() and h.suffix.lower() in ACEPTADAS)
        else:
            yield ruta


def _abrir(ruta):
    """Las fuentes que aporta un archivo .ttf, .otf o .zip."""
    if not ruta.is_file():
        raise ValueError(f"no existe (tampoco en {ENTRADAS})")
    if ruta.suffix.lower() == ".zip":
        return _del_zip(ruta)
    if ruta.suffix.lower() in FUENTES:
        return [Fuente(ruta.name, str(ruta), ruta, _buscar_licencia(ruta.parent))]
    raise ValueError("no es .ttf, .otf ni .zip")


def _imprimir_omitidos(omitidos):
    if omitidos:
        print(f"  {len(omitidos)} omitidos (la fuente no trae de dónde derivarlos):")
        for codepoint, motivo in omitidos.items():
            print(f"    {chr(codepoint)} U+{codepoint:04X}: {motivo}")


def _procesar(fuente, salida, args):
    """Fontifica una fuente: escribe la salida, su licencia y su muestra (o solo informa
    con `--revisar`). Devuelve el `Resultado`."""
    resultado = fontificar(fuente.entrada, None if args.revisar else salida, args.idioma)
    nuevos = "".join(chr(c) for c in resultado.nuevos)
    if args.revisar:
        print(f"{fuente.origen}: se pueden agregar {len(nuevos)}: {nuevos}")
        _imprimir_omitidos(resultado.omitidos)
        return resultado
    print(f"{fuente.origen}: {len(nuevos)} caracteres nuevos en {salida}")
    _imprimir_omitidos(resultado.omitidos)

    licencia = Path(args.licencia) if args.licencia else fuente.licencia
    destino = salida.with_name(f"{salida.stem}-licencia.txt")
    if isinstance(licencia, bytes):
        destino.write_bytes(licencia)
    elif licencia is not None and licencia.is_file():
        shutil.copyfile(licencia, destino)
    else:
        print(f"aviso: no encontré la licencia de {fuente.origen} ({licencia or 'junto a la entrada'}); "
              "publicar la fuente exige copiarla", file=sys.stderr)

    muestra = salida.resolve().with_name(f"{salida.stem}-muestra.html")
    escribir_muestra(fuente.entrada, salida, muestra, args.idioma)
    print(f"  muestra: {muestra}")
    if args.abrir:
        webbrowser.open(muestra.as_uri())
    return resultado


def principal(argumentos=None):
    """Corre el CLI. Devuelve 0 si todas las fuentes salieron bien, 1 si alguna falló."""
    analizador = argparse.ArgumentParser(
        prog="fontificar", description="Amplía la cobertura de fuentes TTF u OTF.",
        epilog=f"Sin entradas procesa lo que esté suelto en {ENTRADAS} y escribe en {SALIDAS}.")
    analizador.add_argument("entradas", nargs="*",
                            help=".ttf, .otf, .zip o carpeta; si no existe tal cual, se busca en fonts/in")
    analizador.add_argument("--idioma", default="fontificata", choices=sorted(IDIOMAS),
                            help="qué caracteres agregar (por omisión, fontificata: el más completo)")
    analizador.add_argument("-o", "--salida",
                            help="fuente de salida, solo con una fuente de entrada "
                            "(por omisión, fonts/out/<nombre>-<idioma>.<ext>)")
    analizador.add_argument("--licencia", help="licencia a copiar junto a cada salida (por omisión, "
                            "un read_me.txt, license.txt o parecido junto a la entrada o dentro del zip)")
    analizador.add_argument("--revisar", action="store_true",
                            help="solo decir qué se puede agregar y qué no, sin escribir nada")
    analizador.add_argument("--abrir", action="store_true", help="abrir cada muestra en el navegador")
    args = analizador.parse_args(argumentos)
    # Una consola cp1252 no sabe mostrar ˚ ˝ ł…: que los reemplace en vez de tronar
    # (el error se confundiría con una fuente dañada).
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(errors="replace")

    fuentes, fallas = [], []
    for ruta in _archivos(args.entradas):
        try:
            fuentes.extend(_abrir(ruta))
        except (ValueError, OSError, zipfile.BadZipFile) as error:
            fallas.append((str(ruta), error))
    if not fuentes and not fallas:
        analizador.error(f"no hay fuentes que procesar en {ENTRADAS}")
    if args.salida and len(fuentes) > 1:
        analizador.error(f"--salida pide una sola fuente de entrada y hay {len(fuentes)}")

    escritas, hechas, omitidos = {}, 0, 0
    for fuente in fuentes:
        salida = Path(args.salida) if args.salida else SALIDAS / (
            f"{Path(fuente.nombre).stem}-{args.idioma}{Path(fuente.nombre).suffix.lower()}")
        try:
            if not args.revisar and salida.resolve() in escritas:
                raise ValueError(f"su salida {salida} se encimaría con la de {escritas[salida.resolve()]}")
            omitidos += len(_procesar(fuente, salida, args).omitidos)
            escritas[salida.resolve()] = fuente.origen
            hechas += 1
        except (ValueError, OSError, TTLibError) as error:
            fallas.append((fuente.origen, error))

    for origen, error in fallas:
        print(f"error en {origen}: {error}", file=sys.stderr)
    if len(fuentes) + len(fallas) > 1:
        verbo = "revisadas" if args.revisar else "generadas"
        print(f"resumen: {hechas} {verbo}, "
              f"{len(fallas)} con error, {omitidos} caracteres omitidos")
    return 1 if fallas else 0
