"""CLI delgado: `python -I fontificar entrada.ttf salida.ttf --idioma es`."""
import argparse
import shutil
import sys
from pathlib import Path

from .idiomas import IDIOMAS
from .muestra import escribir_muestra
from .nucleo import fontificar

# Nombres de archivo (sin extensión, en minúsculas) que suelen traer la licencia.
LICENCIAS = ("read_me", "readme", "readthis", "license", "licence", "licencia", "freelicense", "ofl")


def _buscar_licencia(carpeta):
    """El primer .txt de `carpeta` cuyo nombre parece de licencia, o None."""
    candidatos = sorted(p for p in carpeta.glob("*.txt") if p.stem.lower().replace(" ", "") in LICENCIAS)
    return candidatos[0] if candidatos else None


def principal(argumentos=None):
    analizador = argparse.ArgumentParser(prog="fontificar",
                                         description="Amplía la cobertura de una fuente TTF u OTF.")
    analizador.add_argument("entrada", help="fuente TTF u OTF de entrada")
    analizador.add_argument("salida", help="fuente de salida (mismo formato que la entrada)")
    analizador.add_argument("--idioma", default="es", choices=sorted(IDIOMAS))
    analizador.add_argument("--licencia", help="licencia de la fuente a copiar junto a la salida "
                            "(por omisión, un read_me.txt, license.txt o parecido junto a la entrada)")
    args = analizador.parse_args(argumentos)

    try:
        resultado = fontificar(args.entrada, args.salida, args.idioma)
    except (ValueError, OSError) as error:
        sys.exit(f"error: {error}")
    print(f"{len(resultado.nuevos)} glifos nuevos en {args.salida}")
    if resultado.omitidos:
        print(f"{len(resultado.omitidos)} omitidos (la fuente no trae de dónde derivarlos):")
        for codepoint, motivo in resultado.omitidos.items():
            print(f"  {chr(codepoint)} U+{codepoint:04X}: {motivo}")

    salida = Path(args.salida)
    licencia = Path(args.licencia) if args.licencia else _buscar_licencia(Path(args.entrada).parent)
    if licencia is not None and licencia.is_file():
        shutil.copyfile(licencia, salida.with_name(f"{salida.stem}-licencia.txt"))
    else:
        print(f"aviso: no encontré la licencia ({licencia or 'junto a la entrada'}); "
              "publicar la fuente exige copiarla", file=sys.stderr)

    muestra = salida.resolve().parent / "muestra.html"
    escribir_muestra(args.entrada, args.salida, muestra, args.idioma)
    print(f"muestra: {muestra}")
