"""Permite `python -I fontificar ...` desde la raíz del proyecto (se corre la carpeta)."""
import sys
from pathlib import Path

if not __package__:
    # Al correr la carpeta, sys.path[0] es la carpeta misma; se cambia por la raíz
    # del proyecto para importar `fontificar` como paquete.
    sys.path[0] = str(Path(__file__).resolve().parent.parent)

from fontificar.cli import principal  # noqa: E402

sys.exit(principal())
