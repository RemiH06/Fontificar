# Pendientes

## Siguiente sesión

Iteración 1 cerrada el 2026-10-20.

Iteración 2 (Latin-1) cerrada el 2026-10-20: `--idioma latin1` agrega 67 glifos, 25 pruebas en verde, `!y2kbug-latin1.ttf` y `!y2kbug-es.ttf` revisadas en un editor real sin problemas.

ß agregada a `latin1` el 2026-10-20 (68 glifos, 27 pruebas en verde, revisada en `fonts/muestra.html` con Edge sin interfaz). Ambas fuentes de `fonts/out` se regeneraron.

Siguiente:

1. Reinstalar `!y2kbug-latin1.ttf` (trae la ß) y `!y2kbug-es.ttf` (el agudo cambió de sentido de contorno, no de forma) y revisar la ß en un editor real.
2. Iteración 3 (Latin Extended-A): decidir de dónde sale el caron (ˇ), candidato `asciicircum` reducido y volteado. La ẞ (U+1E9E) puede apuntar al glifo de la ß porque la fuente es unicase. La ſ (U+017F) no se hace: no hace falta.

Decisiones tomadas al agregar la ß:

- ß: `B` volteada en vertical. En Y2KBUG la `B` es un asta más un "3" unido abajo; volteada, la unión queda arriba como en la ß. Se descartó `J` girada más `3`: sale del doble de ancho y se lee "[3".
- `_transformado` revierte los contornos cuando la matriz es un espejo, para conservar el sentido del original. Antes el agudo y la cedilla salían en sentido contrario al de `grave` y `comma`.
- Solo TTF por ahora: el camino OTF/CFF queda fuera hasta nuevo aviso.

Decisiones tomadas en la iteración 2:

- Idioma nuevo `latin1`: letras de Latin-1 más Œ œ Ÿ (Windows-1252) y los acentos sueltos ´ ¨ ¸; sufijo de familia `Latino` (`!Y2KBUG Latino`). Fuera: Ð ð Þ þ (no se derivan de nada que traiga la fuente) y los símbolos de Latin-1 que no son letras (« » ª º £ etc.).
- Los acentos sueltos se agregan solo si el idioma los usa: la salida `es` no cambia de lista.
- `˚`: `period` a 0.6 (en Y2KBUG `period` ya es un anillo; la `o` reducida a tamaño de acento dejaba un trazo de ~14 unidades). Cambia lo decidido al cierre de la iteración 1.
- `ˆ` (U+02C6): `asciicircum` a 0.6 de ancho y 0.45 de alto; completo mide 310 y subiría el ascendente a ~1080.
- `¸`: `comma` volteada en vertical a 0.6, pegada debajo de la base.
- `ø`: `o` + `slash` superpuestos, sin recortar: los extremos verticales de `slash` caen sobre las astas de la `o`.
- `æ œ`: la segunda letra se recorre hasta compartir el asta (ancho de la `i`). La fuente es proporcional, no monoespaciada.
- Si el acento más `HUECO` no cabe en el avance de la base, el avance crece y la base se centra: `í` 271, `ï` 352. Antes el acento invadía la letra vecina.
- `_ajustar_metricas` también baja el descendente si hace falta (la cedilla llega a -187, cabe en -200).

Decisiones tomadas en la iteración 1:

- Acento a `HUECO` (0.06 em) por encima de la caja de la base, centrado: sirve igual con unicase, minúsculas o mayúsculas.
- Agudo: espejo de `grave`. Diéresis: contorno exterior de `period` a la mitad de tamaño, dos veces. Tilde: `asciitilde` tal cual. ¡ ¿: giro de 180° de `!` y `?`.
- Se agregan también `´` (U+00B4) y `¨` (U+00A8), porque son los acentos derivados.
- Ascendente de `hhea`, `OS/2` typo y win sube de 800 a 928 (la ñ llega a 928). Cambia el interlineado de la fuente, no los glifos.
- La tabla `cmap` de Mac recibe los códigos MacRoman, no Unicode.
- Si la fuente ya cubre el idioma, `fontificar` falla en vez de renombrar otra vez.

## Fontificar: nota de alcance

**Objetivo:** a partir de una fuente que solo cubre un conjunto básico de caracteres, generar una copia que cubra español, y después otros idiomas con alfabeto latino, para poder usarla en texto real sin cuadros vacíos.

**Entra:**
- Leer una fuente TTF/OTF y generar otra con glifos nuevos (letras acentuadas, ñ, ü, ¡, ¿) y su entrada en `cmap`, `hmtx` y nombres de glifo.
- Construir cada letra acentuada componiendo la letra base con una marca de acento, ajustada a la altura de x o de mayúsculas.
- Si la fuente no trae acentos, derivarlos de glifos que sí tiene (apóstrofo, tilde `~`, `^`, comillas) en vez de dibujar contornos nuevos.
- Un script de CLI: fuente de entrada, lista de idiomas o rango, fuente de salida.

**No entra (v1):**
- Otros alfabetos (cirílico, griego, CJK).
- Fuentes variables.
- Kerning nuevo, hinting manual y ajuste fino glifo por glifo.
- Interfaz gráfica.

**Forma de uso (recomendada, pendiente de confirmar):** librería `fontificar.py` con una función principal, más un CLI delgado con `argparse`. Sin UI en la v1. El CLI genera también una página HTML estática de muestra (original contra nueva) para la revisión visual, sin servidor ni puerto.

**Stack (restricción tomada):** Python + `fontTools`, sin más dependencias. Mecanismo central: componer base + marca con la posición correcta. Aviso: en TTF los glifos compuestos son nativos (referencias a componentes); en OTF/CFF no existen, así que ahí se copia el contorno de la base y de la marca ya combinados con un pen. El script debe manejar ambos formatos.

**Listo cuando:**
- [x] Cada codepoint de la lista objetivo está en `cmap` y apunta a un glifo con contorno.
- [x] "Canción, pingüino, ¿Qué tal? ¡Hola! ÁÉÍÓÚÜÑ" se ve sin cuadros vacíos en un editor real.
- [x] Los acentos no se separan de su letra ni chocan con la línea de arriba, en minúsculas y mayúsculas (revisión visual en tamaño grande).
- [x] Los glifos que ya existían no cambian (mismos contornos y anchos antes y después).
- [x] La familia de salida conserva el nombre original y le agrega un sufijo (`!Y2KBUG Español`), como pide la licencia de Larabie, y sale con una copia de esa licencia.
- [x] Un auto-chequeo con asserts corre sobre la fuente de salida (ponytail: lógica no trivial lleva prueba).

### Iteraciones

| # | Meta | Incluye | Criterio de cierre |
|---|---|---|---|
| 1 | Español sobre una fuente | á é í ó ú ü ñ y sus mayúsculas, ¡ ¿ | Los criterios de arriba pasan con la fuente real |
| 2 | Latin-1 (letras) | ç â ê î ô û à è ì ò ù ä ë ï ö å ø æ œ, entre otros, y ß; sin Ð ð Þ þ | Mismo chequeo sobre la lista ampliada |
| 3 | Latin Extended-A | Polaco, checo, turco, etc.; anclas GPOS de marca si el posicionamiento fijo no alcanza | Mismo chequeo; acentos apilados legibles |

### Dudas abiertas

Ninguna.

Resueltas: OTF/CFF queda fuera, solo TTF por ahora (2026-10-20); v1 solo español; se aceptan acentos derivados de otros glifos; fuente de prueba Y2KBUG (TTF, licencia Larabie: modificar permitido sin tocar a-z ni 0-9, nombre se conserva y se aumenta); forma de uso: librería, CLI delgado y página de muestra.
