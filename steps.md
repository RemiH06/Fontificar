# Pendientes

## Siguiente sesión

Iteración 6 (`fontificata`) cerrada el 2026-10-20: 87 pruebas en verde, ya es el idioma por omisión del CLI. Skill de Fontificar actualizada (en `48.SkillShot` y sincronizada a `~/.claude/skills/`, más su línea en el README del hub). `fonts/in/` reordenada: suelta solo `!y2kbug.ttf` (y su `read_me.txt`), cada fuente de prueba extra con su zip en su subcarpeta (`ComicRunes/`, `FortunaDot/`, `Liverpool/` solo el zip, `Samarkan/`) y `Y2KBUG.zip` en `zips/`.

Logo hecho el 2026-10-20 (`docs/logo.svg`; se movió a `docs/` porque GitHub Pages solo publica esa carpeta): ñ minúscula en matriz de puntos de 5×7, dibujada con círculos y sin fuente de terceros (es obra propia, no arrastra licencias). La `n` va en tinta (`#1F2430`, `#F2F2F2` en modo oscuro por `prefers-color-scheme`) y la tilde en acento `#D9480F` (4.3:1 sobre blanco y 4.4:1 sobre `#0D1117`, sirve en los dos temas): la tilde es lo que Fontificar agrega. A 16 px se empasta; para favicon haría falta una versión simplificada.

Documentación hecha el 2026-10-20 en `docs/index.html` (lista para GitHub Pages desde `/docs`, sin compilar ni servidor): una sola página autocontenida con la piel de bookworm (paleta de claro del bosque y bosque nocturno, Libre Baskerville y Fira Code desde Bunny Fonts) y la base de `doc-prose` de iroFactory, recortadas y copiadas (MIT, crédito en el comentario de cabecera y en el pie). No se trajo el resto de bookworm (invernadero en WebGL, escritorio con ventanas): es pesado para una página de una herramienta. Secciones: espécimen en vivo (área de texto, original contra nueva; lo que la original no trae cae en Baskerville y se nota), rejilla de los 239 caracteres de `fontificata` con los omitidos punteados, qué hace, uso, idiomas, después de generar y licencias; índice que marca la sección actual; tema claro u oscuro según el sistema, con botón y `localStorage` envuelto en try/catch. Las fuentes del ejemplo van en `docs/fuentes/`: Y2KBUG original, su versión `fontificata` y la licencia de Larabie (la licencia permite redistribuir y publicar derivadas con copia de la licencia; Y2KBUG no trae kerning). La lista de caracteres de la rejilla está copiada de `idiomas.py`: si cambia el idioma, hay que regenerar `docs/fuentes/!y2kbug-fontificata.ttf` y actualizar la página. Revisada en Edge sin interfaz en claro, oscuro y a 390 px.

Ojo al revisar en esta máquina: Windows tiene instaladas `!y2kbug-es`, `-latin1` y `-latinext` (de pruebas en un editor), y el navegador puede usarlas de respaldo en otras páginas.

Siguiente:

1. README raíz con la skill `readme-generator` (enlazar a `docs/` y usar `docs/logo.svg`).

Mejoras visuales posibles (no bloquean): la tilde hecha con la `s` acostada sale chica y el caron de Samarkan, grande (viene de sus agudo y grave, que son altos). Þ de Samarkan sale rara (su `P` es una `p` con descendente). ¢ de Y2KBUG lleva una diagonal muy pesada (la `/` de la fuente es ancha).

Iteración 6, `fontificata` (implementada):

- `latinext` más Ð ð Þ þ Ŋ ŋ y los símbolos de Latin-1 y Windows-1252: ‘ ’ ‚ “ ” „, rayas (U+2013, U+2014), … •, ‹ › « », ª º, ¹ ² ³, ¼ ½ ¾, € £ ¢ ¥, © ®, ° ± × ÷ ¬ ¦ § ¶ ¤ µ. Sufijo de familia `Fontificata`. Fuera: Latin Extended-B, vietnamita, ‰ † ‡ ™ ƒ.
- Letras en `especiales.py`; símbolos en `simbolos.py` (`SIMBOLOS`), que `_derivar` consulta después de `ESPECIALES`. `guion`, `diagonal`, `tachado` y `auxiliar` de `especiales.py` pasaron a públicos para reusarse.
- Ð es la forma de Đ; ð es la `d` con la diagonal a 0.8; Þ es la `P` aplastada a 0.75 desde la base más un asta completa (se refleja si la `P` tiene el asta a la derecha); þ es la `b` encimada con la `p` (solo si la `p` baja y la `b` sube); ŋ Ŋ son la `n` `N` encimadas con la `j` `J` sin punto, alineadas por la derecha (solo si la `j` baja). En Y2KBUG, Comic Runes y Fortuna se omiten þ Ŋ ŋ (sin descendentes).
- ’ es la coma subida a la altura de las mayúsculas (sin coma, el apóstrofo); ‘ es ’ girada; ‚ es ’ bajada a donde baja la coma; las dobles son la sencilla dos veces, a media tinta de distancia. ‹ › son `<` `>` a 0.6; « » son ‹ › dos veces, encimados.
- Rayas: el guion estirado a medio em y a un em, con los márgenes del guion. … son tres puntos con su avance; • es el punto macizo al doble (tope 0.3 de las mayúsculas) a la altura del guion.
- ª º: la letra a 0.4 de las mayúsculas, arriba, con una raya debajo. ¹ ² ³: el dígito a 0.6, arriba. ¼ ½ ¾: dígitos a 0.5 (arriba y en la línea base) con la diagonal entre ellos.
- € ¥: la letra con dos barras de guion; £: la `L` tachada a 0.4; ¢: la `c` con la diagonal a 1.3 de su alto; © ®: la letra dentro del hueco de la `O` (a la mitad de la `O` si no tiene hueco); °: la `o` a 0.35; ¤: la `o` con un punto en cada esquina.
- ± × ÷ ¬: `+` con barra, `+` girado 45°, guion con dos puntos, guion con pata. ¦: la `|` partida. §: dos `s` encimadas. ¶: la `P` reflejada más un asta. µ: la `μ` griega o la `u` con una pata hasta el descendente.
- Respaldos hechos con el guion para fuentes que no traen `+ | < >` (Comic Runes, Samarkan, Fortuna): `+` es el guion cruzado con el guion parado, `|` el guion parado, ‹ › dos brazos de guion a 35°. Las astas (Þ ¶ µ ¦) se hacen con el guion parado (`asta_vertical`), no con el punto estirado: en Y2KBUG el punto es redondo y salían elipses.
- Comic Runes, Fortuna y Samarkan cubren todo salvo þ Ŋ ŋ (Samarkan sí saca þ ŋ: tiene descendentes); revisadas en Edge sin interfaz.

Iteración 5, fácil de usar (implementada):

- `pyproject.toml` mínimo con `[project.scripts] fontificar = "fontificar.cli:principal"`; se instala con `pip install -e .`. `python -I fontificar` sigue funcionando.
- Flujo: se deja un `.zip`, `.ttf` u `.otf` en `fonts/in/` y se corre `fontificar`. Sin argumentos procesa todo el nivel superior de `fonts/in/` (las subcarpetas de prueba no, así Liverpool nunca entra por accidente). Con argumentos, cada uno se busca tal cual y, si no existe, dentro de `fonts/in/`. Las rutas son relativas a la raíz del proyecto (el paquete la conoce), no a la carpeta actual.
- Salida en `fonts/out/` como `<nombre>-<idioma>.<ext>`; `-o` la cambia. Licencia junto a la salida, como hoy.
- Zip: se leen en memoria solo los `.ttf`/`.otf` y la licencia; nada se extrae a disco. Un zip con varias fuentes (regular, bold…) genera una salida por cada una.
- En lote, una fuente que falla se reporta y se sigue con la siguiente; al final, resumen (generadas, fallidas, glifos omitidos).
- Una muestra por salida (`<salida>-muestra.html`), ya no se pisan; `--abrir` la abre en el navegador (`webbrowser`).
- `--revisar`: dice qué falta y qué se puede derivar, sin escribir nada.
- Idioma por omisión: `latinext` mientras no exista `fontificata`; después, `fontificata`.
- Fuera: interfaz gráfica, `.bat` de arrastrar y soltar, varios idiomas en una corrida.
- Detalles de la implementación: `fontificar()` acepta bytes y `salida=None` (no escribe, para `--revisar`); la muestra incrusta la original como `data:` cuando viene de un zip; el zip ignora `__MACOSX/` y `._*` y rechaza archivos de más de 64 MB; dos entradas con la misma salida dan error en vez de encimarse; el CLI devuelve 1 si alguna fuente falló; la consola cp1252 reemplaza lo que no sabe mostrar (antes `˚` tronaba y se reportaba como fuente dañada). Se instala solo editable: el comando busca `fonts/` junto al paquete.

Decisiones tomadas en la iteración 4:

- Paquete `fontificar/` (idiomas, glifos, acentos, especiales, nucleo, muestra, cli). CLI: `python -I fontificar ...` corre la carpeta; `__main__.py` cambia `sys.path[0]` por la raíz.
- Los glifos nuevos se arman como `RecordingPen` y `Obra.agregar` los escribe en `glyf` (componentes nativos) o en `CFF ` (componentes descompuestos con `T2CharStringPen`). CFF con CID y CFF2 se rechazan con error claro. En CFF también se renombran `fontNames`, `FamilyName` y `FullName`.
- `fontificar()` devuelve `Resultado(nuevos, omitidos)`; lo que no se deriva se omite con su motivo y el CLI lo lista. Solo falla si no agrega nada.
- Un caracter mapeado a un glifo vacío cuenta como faltante (Comic Runes): se mapea al glifo nuevo y el vacío se queda sin mapear. Los glifos con dibujo nunca se remapean.
- Respaldos por acento (en orden, ver `MARCAS`): el suelto de la fuente si tiene forma de acento; el modificador (ˋ ˊ ˜ ˉ); el acento sacado de una letra acentuada de la fuente (é menos e); y las derivaciones de siempre, más: grave y agudo uno del otro, agudo del apóstrofo inclinado o del punto estirado, circunflejo de agudo más grave, caron del circunflejo volteado, macrón del punto estirado, anillo de `°` o de la `o`, breve de la `u`, tilde de la `s` acostada.
- Un acento que la fuente ya trae se usa solo si tiene forma de acento (arriba: empieza sobre media `o` y mide menos de media `o`; abajo: no sube de un cuarto de `o`). El `ˆ` de Samarkan no pasa.
- `Obra.signo` quita la línea de cabecera (contorno plano que cruza el avance) de la puntuación que sirve de materia prima. Los puntos usan todos los contornos exteriores, no solo el primero.
- Guion y diagonal faltantes se hacen con el punto estirado, como glifos auxiliares sin mapear (`*.fontificar`).
- Reglas medidas en vez de supuestas: grosor del asta por el tramo de tinta a un tercio de la `i` (sin serifas); lado del asta de Đ đ Ħ ħ Ł ł por muestreo (Đ a 0.5 de alto si el asta está a la izquierda, 0.8 si a la derecha); ß como `B` volteada solo si la `B` se une al asta abajo y no arriba, si no `ss` (ẞ: `SS`); ı es la `i` sin su punto (dos grupos verticales, el de arriba chico) y í ì î ï ĵ usan la letra sin punto; ĸ solo en fuentes unicase.
- Subtablas de `cmap` de formato 0 solo reciben glifos con índice menor a 256 (Fortuna tronaba).
- La muestra se escribe junto a la salida (`fonts/out/muestra.html`); antes iba a la carpeta común de entrada y salida, que podía ser la carpeta personal.
- La licencia se busca con nombres comunes (`read_me`, `readme`, `license`, `FreeLicense`…) junto a la entrada.

Decisiones tomadas en la iteración 3:

- Idioma `latinext`: Latin-1 completo más U+0100 a U+017F, más `·` (lo usa Ŀ) y ẞ. Fuera: ŉ (Unicode lo da por obsoleto), Ŋ ŋ (la fuente no tiene descendentes ni de dónde sacar el gancho) y ſ (no hace falta).
- Acentos nuevos, todos apoyados a la altura de la base de `grave`: caron ˇ (`asciicircum` a 0.6 de ancho y -0.45 de alto, volteado), macron ¯ (`hyphen` angostado a 0.6, mismo grosor), breve ˘ (`(` girado 90° para abrir hacia arriba, 0.29 a lo largo y 0.6 a lo grueso; se descartó la `U` aplastada, sale muy alta), punto ˙ (un punto de la diéresis), doble agudo ˝ (dos agudos a 0.75).
- Ogonek ˛: el mismo contorno de la cedilla, pero alineado con el borde derecho de la letra (posición `DEBAJO_DERECHA`). Las cedillas de Ģ Ķ Ļ Ņ Ŗ se quedan como cedilla (no coma abajo).
- Caron siempre arriba, también en ď ľ ť: la fuente es unicase, así que no se usa la forma de apóstrofo.
- Barras: `hyphen` angostado a tres astas en Đ đ (asta derecha, a 0.8 de alto: en Y2KBUG la `D` es una `d`), Ħ ħ (asta izquierda, a 0.8: la `H` es una `h`) y Ŧ ŧ (centro, a 0.5). Ł ł llevan `slash` reducido parejo sobre el asta izquierda.
- Copias (glifo compuesto de un solo componente): ı es la `i` (ya no tiene punto), ĸ es la `k` (unicase) y ẞ es la ß. Ĳ ĳ son la `I` y la `J` una tras otra, sin compartir asta. Ŀ ŀ son la `L` más `·`, entre el asta y el borde derecho.
- `ESPECIALES` recibe el cmap con lo ya agregado; por eso `·` va antes que Ŀ y ß antes que ẞ en la lista del idioma.
- No hizo falta GPOS: en Latin Extended-A no hay acentos apilados.

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
| 3 | Latin Extended-A | Polaco, checo, turco, etc.; sin ŉ Ŋ ŋ ſ; con ẞ | Mismo chequeo sobre la lista ampliada |

### Dudas abiertas

Ninguna.

Resueltas: OTF/CFF queda fuera, solo TTF por ahora (2026-10-20); v1 solo español; se aceptan acentos derivados de otros glifos; fuente de prueba Y2KBUG (TTF, licencia Larabie: modificar permitido sin tocar a-z ni 0-9, nombre se conserva y se aumenta); forma de uso: librería, CLI delgado y página de muestra.
