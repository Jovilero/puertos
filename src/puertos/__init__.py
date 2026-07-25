"""puertos — utilidad de puertos TCP locales.

API pública:
    puerto_libre(puerto, host="127.0.0.1") -> bool
    buscar_puerto_libre(preferido, host="127.0.0.1", intentos=20) -> int | None
    proceso_en_puerto(puerto) -> (pid, nombre) | None
    estado_puertos(puertos, host="127.0.0.1") -> list[EstadoPuerto]

CLI equivalente: `puertos check|find|scan` (ver puertos.cli).
"""

from __future__ import annotations

from .core import (
    EstadoPuerto,
    buscar_puerto_libre,
    estado_puertos,
    proceso_en_puerto,
    puerto_libre,
)

__all__ = [
    "EstadoPuerto",
    "buscar_puerto_libre",
    "estado_puertos",
    "proceso_en_puerto",
    "puerto_libre",
]

__version__ = "0.1.0"
