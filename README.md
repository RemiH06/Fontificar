![Made with Python](https://forthebadge.com/images/badges/made-with-python.svg)

```ascii
███████╗ ██████╗ ███╗   ██╗████████╗██╗███████╗██╗ ██████╗ █████╗ ██████╗ 
██╔════╝██╔═══██╗████╗  ██║╚══██╔══╝██║██╔════╝██║██╔════╝██╔══██╗██╔══██╗
█████╗  ██║   ██║██╔██╗ ██║   ██║   ██║█████╗  ██║██║     ███████║██████╔╝
██╔══╝  ██║   ██║██║╚██╗██║   ██║   ██║██╔══╝  ██║██║     ██╔══██║██╔══██╗
██║     ╚██████╔╝██║ ╚████║   ██║   ██║██║     ██║╚██████╗██║  ██║██║  ██║
╚═╝      ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝     ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝
       by Hex (@RemiH06)          version 0.6.0
```

![License](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)

## Fontificar

### Descripción general

Fontificar amplía la cobertura de una fuente TTF u OTF: genera una copia con ñ, acentos, ¡ ¿, las letras de Latin-1 y Latin Extended-A, y los símbolos de Windows-1252 (comillas, rayas, « », ª º, ½, €, ©, ±…). No dibuja nada nuevo: arma cada caracter que falta con los glifos que la fuente ya trae, midiendo sus letras en vez de suponer su forma.

Los glifos originales quedan idénticos. Lo que no se puede derivar se omite y se reporta con su motivo; el proceso nunca se detiene por un faltante. La [documentación](docs/index.html) compara en vivo Y2KBUG de Ray Larabie, original contra ampliada.

```diff
- Lee la licencia de la fuente antes de generar: hay fuentes que prohíben modificarlas o compartir derivadas.
- Revisa la muestra a ojo: según la fuente, un acento derivado puede salir chico o grande y un símbolo armado puede verse forzado.
- La licencia MIT cubre el código. Las fuentes de ejemplo en docs/fuentes/ conservan la licencia de Larabie Fonts.
```

## Instalación

1. Instala Python 3.10 o posterior.
2. Clona el repositorio e instala el comando en modo editable (el comando busca `fonts/in/` y `fonts/out/` junto al paquete):

```bash
git clone https://github.com/RemiH06/Fontificar.git
cd Fontificar
pip install -e .
```

3. Deja las fuentes (`.ttf`, `.otf` o `.zip`) en `fonts/in/` y corre:

```bash
fontificar --revisar   # qué falta y qué se puede derivar, sin escribir nada
fontificar             # genera las fuentes ampliadas en fonts/out/
```

Sin instalar, `python -I fontificar` desde la raíz hace lo mismo.

## Argumentos

- `entradas` `.ttf`, `.otf`, `.zip` (se lee en memoria, una salida por fuente) o carpeta. Una ruta que no existe tal cual se busca en `fonts/in/`. Sin argumentos se procesa el nivel superior de `fonts/in/`, no sus subcarpetas.
- `--idioma` Qué caracteres agregar: `es`, `latin1`, `latinext` o `fontificata` (por omisión, el más completo).
- `-o/--salida` Ruta de la fuente nueva, solo con una entrada. Por omisión, `fonts/out/<nombre>-<idioma>.<ext>`.
- `--revisar` Dice qué se agregaría y qué se omitiría, sin escribir nada.
- `--abrir` Abre en el navegador la muestra de cada fuente generada.

## Funciones

- Cuatro idiomas acumulativos: `es` (18 caracteres), `latin1` (66), `latinext` (195) y `fontificata` (239).
- TrueType (`glyf`) y OpenType CFF. Rechaza con un error claro CFF2 y CFF con CID.
- Acentos con cadena de respaldos: el de la fuente si tiene forma de acento, el modificador, el que viene en una letra acentuada (é menos e) o uno derivado (el agudo como espejo del grave, la tilde con la `s` acostada, el caron con el circunflejo volteado…).
- Letras especiales medidas en la fuente: ß como `B` volteada solo si su forma lo permite, Đ Ł tachadas del lado donde la letra tiene el asta, í sin el punto de la `i` cuando lo tiene.
- Símbolos armados con la puntuación, los dígitos y las letras de la fuente, con respaldos hechos con el guion cuando faltan `+ | < >`.
- Nombre de familia aumentado, no reemplazado (`!Y2KBUG Fontificata`), métricas ajustadas a los glifos nuevos y licencia copiada junto a la salida.
- Lotes: varias fuentes o zips en una corrida; una que falla no detiene a las demás y al final hay un resumen.
- Página HTML de muestra por cada salida, con la original contra la nueva.
- Sin dependencias fuera de `fontTools` y la biblioteca estándar.

## Autoría

por Hex ([@RemiH06](https://github.com/RemiH06))
