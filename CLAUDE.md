# Fontificar

Amplía la cobertura de una fuente TTF/OTF (ñ, acentos, ¡ ¿ y después otros símbolos y alfabetos latinos) generando una copia con glifos nuevos. v1: solo español. Fuente de prueba: Y2KBUG de Ray Larabie.

Forma de uso decidida: librería (paquete `fontificar/`) con un CLI delgado (`argparse`) y una página HTML estática de muestra (original contra nueva). Sin UI en la v1. CLI: `fontificar` (instalado con `pip install -e .`) o `python -I fontificar` desde la raíz (con `-I`, `-m fontificar` no encuentra el paquete). Sin argumentos procesa lo suelto en `fonts/in/` (.zip, .ttf, .otf) y escribe en `fonts/out/`; `--idioma` (por omisión `fontificata`, el más completo), `-o`, `--revisar`, `--abrir`.

Principio: trabajar con lo que traiga cada fuente. TrueType y OpenType CFF. Cada acento tiene una cadena de respaldos (`MARCAS` en `acentos.py`); lo que no se puede derivar se omite con su motivo, nunca se detiene todo. Las reglas que dependen de la forma de una letra se miden en la fuente, no se suponen a partir de Y2KBUG.

## Cómo trabajamos (no negociable)

- **Estado y traspaso en `steps.md`**: sección `## Siguiente sesión` arriba, la nota de alcance y las iteraciones abajo. Una sesión por tema. Al arrancar lee solo `steps.md` y lo que la tarea toque.
- **Orden**: `planeacion` (hecha, en `steps.md`) → `stack-selection` (decidido) → `ponytail` antes de cada pieza de código.
- **Ponytail**: no agregues dependencias. Solo `fontTools` (y la biblioteca estándar). Nunca recortes validación ni manejo de errores.
- **Checkpoints**: nunca corras `git commit`. Al cerrar una fase o sesión, entrega un conventional commit de una línea (`tipo(alcance): descripción`, tipo en inglés, descripción en español sin mayúscula inicial).
- **Español mexicano** en comentarios, docstrings, mensajes de commit y prosa. Identificadores del motor en español (`fuente`, `glifo`, `acento`). **Sin guión largo** (`—`) en ningún archivo; barrido antes de entregar: `grep -rn "—" .`. No asumas el género de la persona usuaria.
- **Pruebas**: lógica no trivial lleva su prueba con `unittest`; `python -m unittest discover -s tests` en verde antes de dar algo por terminado.
- Los comandos que lean archivos de fuentes de terceros se corren con `python -I`.

## Estructura

```
fonts/in/                fuentes de entrada (no se versionan); suelta solo `!y2kbug.ttf`, las de prueba extra y sus zips en subcarpetas
fonts/out/               fuentes generadas, su licencia y su muestra (no se versionan)
fontificar/idiomas.py    qué caracteres agrega cada idioma
fontificar/glifos.py     `Obra` (la fuente en construcción, escribe en glyf o CFF) y utilidades de contorno
fontificar/acentos.py    acentos derivados con sus respaldos (`MARCAS`) y letra más acento
fontificar/especiales.py Ø Æ ß Đ Ł Ĳ ı ĸ Ð Þ ŋ y giros (`ESPECIALES`, `GIROS`)
fontificar/simbolos.py  comillas, rayas, ª º, ¹ ² ³, ¼ ½ ¾, monedas y signos (`SIMBOLOS`)
fontificar/nucleo.py     `fontificar()`, cmap, nombres y métricas
fontificar/muestra.py    página HTML de muestra
fontificar/cli.py        CLI: lotes, zips leídos en memoria, rutas por omisión
pyproject.toml           instalación editable y el comando `fontificar`
README.md, LICENSE       README (readme-generator) y licencia MIT del código
docs/                    documentación (GitHub Pages): index.html, logo.svg y las fuentes del ejemplo con su licencia
tests/                   pruebas (`python -I -m unittest discover -s tests`); `sintetica.py` arma fuentes de prueba
steps.md                 plan y traspaso entre sesiones
```

## Fuentes de prueba extra (`fonts/in/<nombre>/`, 2026-10-20)

Solo para pruebas locales: ninguna salida de estas se publica.

- **Comic Runes** (`ComicRunes.otf`): CFF. Mapea é ñ á… y `` ` ´ ^ - / ' `` a glifos vacíos. CC BY-ND: no se comparten derivadas.
- **Fortuna Dot** (`fortd.ttf`): letras hechas de puntos, Latin-1 completo, trae `˜ ˆ` pero no `~ ^`, B simétrica.
- **Liverpool** (siete fuentes de Kreative): ya cubre Latin Extended-A salvo ẞ. **Su licencia prohíbe modificarla**: no generar salidas con ella.
- **Samarkan** (`samarn.ttf`): 2048 upem, `kern`, estilo devanagari: la puntuación trae la línea de cabecera; su `ˆ` no es un acento.

## Hechos de la fuente de prueba (`fonts/in/!y2kbug.ttf`)

Inspección del 2026-10-20:

- TrueType (`glyf`), 1000 unidades por em, 103 glifos, ASCII completo, sin ningún caracter español nuevo, sin `GPOS`/`GSUB`/`kern`.
- Es unicase: minúsculas y mayúsculas miden lo mismo (altura 712). Un solo juego de alturas para todos los acentos.
- Sin acento agudo ni diéresis. Existen `grave` (y 629 a 762), `asciitilde` (608 a 762) y `asciicircum` (471 a 781). Los tres se solapan con la letra si se ponen sin desplazar.
- `i` no tiene punto (barra completa): í no necesita `dotless i`.
- Las minúsculas son glifos compuestos (referencias a componentes).
- Trae `hdmx`, `fpgm`, `prep` y `cvt `. `hdmx` hay que quitarlo o recalcularlo al agregar glifos.
- Nombre de familia `!Y2KBUG`.

## Licencia de la fuente de prueba (Larabie Fonts, `fonts/in/read_me.txt`)

Se puede modificar si:

- No se altera ningún alfanumérico (a-z, 0-9) existente. Los glifos originales deben quedar idénticos.
- Se pueden agregar caracteres, usando curvas de alfanuméricos de fuentes con la misma licencia.
- El nombre original se mantiene y se puede aumentar (ejemplo: `!Y2KBUG Español`), no reemplazar.
- Si se daña o descarta el kerning, se declara en la documentación (esta fuente no tiene).
- Toda modificación se publica bajo esa misma licencia, con una copia de ella.
