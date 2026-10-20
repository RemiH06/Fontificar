"""Fontificar: amplía la cobertura de una fuente TrueType u OpenType CFF con glifos derivados.

Idiomas: español (`es`), Latin-1 (`latin1`: sus letras, más Œ œ Ÿ, sin Ð ð Þ þ) y
Latin Extended-A (`latinext`: Latin-1 más el bloque U+0100 a U+017F sin ŉ Ŋ ŋ ſ, y ẞ).
Los glifos que la fuente ya trae no se tocan; solo se agregan los que faltan.
Los acentos se derivan de glifos existentes (`grave`, `asciitilde`, `asciicircum`,
`period`, `comma` y sus respaldos) en vez de dibujar contornos nuevos; lo que no se
puede derivar se omite y se informa.

Módulos: `idiomas` (qué se agrega), `glifos` (la fuente en construcción y utilidades
de contorno), `acentos` (acentos derivados y letra más acento), `especiales` (Ø Æ ß
Đ Ł Ĳ y giros), `nucleo` (`fontificar()` y las tablas), `muestra` (página HTML) y `cli`.
"""
from .idiomas import IDIOMAS, Idioma
from .muestra import escribir_muestra
from .nucleo import Resultado, fontificar

__all__ = ["IDIOMAS", "Idioma", "Resultado", "escribir_muestra", "fontificar"]
