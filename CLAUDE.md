# Fontificar

Amplía la cobertura de una fuente TTF/OTF (ñ, acentos, ¡ ¿ y después otros símbolos y alfabetos latinos) generando una copia con glifos nuevos. v1: solo español. Fuente de prueba: Y2KBUG de Ray Larabie.

Forma de uso decidida: librería (`fontificar.py`) con un CLI delgado (`argparse`) y una página HTML estática de muestra (original contra nueva). Sin UI en la v1.

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
fonts/in/      fuentes de entrada (no se versionan)
fonts/out/     fuentes generadas (no se versionan)
fontificar.py  núcleo y CLI (por crear)
tests/         pruebas (por crear)
steps.md       plan y traspaso entre sesiones
```

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
