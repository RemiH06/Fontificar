# Pendientes

## Siguiente sesión

Iteraciones 1, 2 y 3 cerradas el 2026-10-20 (`!y2kbug-latinext.ttf` revisada en un editor real: funciona).

Iteración 4 (paquete, fuentes cualesquiera y CFF) implementada el 2026-10-20: `fontificar.py` partido en el paquete `fontificar/`; ya no se detiene en el primer faltante, se adapta a lo que trae la fuente y escribe TrueType u OpenType CFF. 61 pruebas en verde (44 de Y2KBUG, sin cambiar ninguna aserción, y 17 sobre fuentes sintéticas). Y2KBUG sale idéntica en los tres idiomas (mismos contornos y avances que antes). Comic Runes, Fortuna Dot y Samarkan cubren los tres idiomas sin omitidos; revisadas en Edge sin interfaz.

Siguiente, en este orden:

1. Iteración 6, idioma `fontificata` (alcance confirmado el 2026-10-20, ver abajo). Al cerrarla, pasa a ser el idioma por omisión del CLI.
2. Iteración 5 cerrada el 2026-10-20 (70 pruebas en verde; probada con `Y2KBUG.zip` y con el comando instalado en un venv aparte).
3. Al final, la skill de Fontificar.

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

Iteración 6, `fontificata` (alcance confirmado, sin más símbolos por ahora): el idioma más completo posible en uno solo. `latinext` no lo es: deja fuera los símbolos de Latin-1 y Windows-1252. `fontificata` = `latinext` más lo que se pueda derivar de esos símbolos, y lo que no, se omite con su motivo como siempre:

- Comillas y raya: ‘ ’ ‚ “ ” „ (del apóstrofo y la coma), U+2013 y U+2014, las rayas (guion estirado; en el código van por su codepoint, no como caracter, por la regla del guion largo), … (tres puntos), • (punto), ‹ › « » (de `<` `>` reducidos).
- Ordinales y superíndices: ª º (a y o reducidas con raya), ¹ ² ³ ¼ ½ ¾ (dígitos reducidos, sin tocar los originales).
- Monedas y signos: € £ ¢ ¥ (letra más barras), © ® (letra dentro de la `o` o de un círculo), ° ± × ÷ ¬ ¦ § ¶ ¤ µ.
- Letras pendientes: Ð (es la forma de Đ), ð Þ þ Ŋ ŋ, intentarlas y omitirlas si no salen.
- Fuera: Latin Extended-B y vietnamita (acentos apilados, piden GPOS o compuestos dobles).

Mejoras visuales posibles (no bloquean): la tilde hecha con la `s` acostada sale chica y el caron de Samarkan, grande (viene de sus agudo y grave, que son altos).

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
