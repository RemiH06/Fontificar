# Pendientes

## Siguiente sesión

Inspección hecha (hechos en `CLAUDE.md`). Arrancar la iteración 1 con `fontificar.py`:

1. Decidir cómo se ponen los acentos en una fuente unicase donde `grave`, `~` y `^` se solapan con la letra: subirlos ~100 unidades y ver si hay que subir `hhea`/`OS/2` ascent, o escalarlos. Probar con la página de muestra antes de fijar la regla.
2. Derivar lo que falta: agudo (espejo horizontal de `grave`), diéresis (dos cuadrados a partir de `period`, escalados), ¡ y ¿ (giro de 180° de `exclam` y `question`).
3. Componer las 14 letras (á é í ó ú ü ñ y mayúsculas, que aquí son el mismo glifo base en tamaño) como compuestos TrueType, registrar `cmap`, `hmtx`, nombres de glifo y `post`; quitar `hdmx`; renombrar la familia a `!Y2KBUG Español` sin quitar el nombre original.
4. Auto-chequeo con asserts (`tests/`) y la página HTML de muestra.

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
- [ ] Cada codepoint de la lista objetivo está en `cmap` y apunta a un glifo con contorno.
- [ ] "Canción, pingüino, ¿Qué tal? ¡Hola! ÁÉÍÓÚÜÑ" se ve sin cuadros vacíos en un editor real.
- [ ] Los acentos no se separan de su letra ni chocan con la línea de arriba, en minúsculas y mayúsculas (revisión visual en tamaño grande).
- [ ] Los glifos que ya existían no cambian (mismos contornos y anchos antes y después).
- [ ] La familia de salida conserva el nombre original y le agrega un sufijo (`!Y2KBUG Español`), como pide la licencia de Larabie, y sale con una copia de esa licencia.
- [ ] Un auto-chequeo con asserts corre sobre la fuente de salida (ponytail: lógica no trivial lleva prueba).

### Iteraciones

| # | Meta | Incluye | Criterio de cierre |
|---|---|---|---|
| 1 | Español sobre una fuente | á é í ó ú ü ñ y sus mayúsculas, ¡ ¿ | Los criterios de arriba pasan con la fuente real |
| 2 | Latin-1 completo | ç â ê î ô û à è ì ò ù ä ë ï ö å ø ß æ œ, entre otros | Mismo chequeo sobre la lista ampliada |
| 3 | Latin Extended-A | Polaco, checo, turco, etc.; anclas GPOS de marca si el posicionamiento fijo no alcanza | Mismo chequeo; acentos apilados legibles |

### Dudas abiertas

- OTF/CFF: la fuente de prueba es TTF, así que el camino CFF (aplanar contornos con un pen) se difiere hasta tener una fuente OTF real para probarlo.

Resueltas: v1 solo español; se aceptan acentos derivados de otros glifos; fuente de prueba Y2KBUG (TTF, licencia Larabie: modificar permitido sin tocar a-z ni 0-9, nombre se conserva y se aumenta); forma de uso: librería, CLI delgado y página de muestra.
