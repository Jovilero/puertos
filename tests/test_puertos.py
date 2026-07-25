"""Tests de la librería `puertos`.

Deterministas y sin depender del entorno: se abre un socket listener real en un
puerto EFÍMERO (el SO elige uno libre con bind((host, 0))). Mientras ese socket
vive, su puerto está "ocupado"; al cerrarlo, vuelve a estar libre.
"""

from __future__ import annotations

import os
import socket
from collections.abc import Iterator

import pytest

from puertos import (
    buscar_puerto_libre,
    estado_puertos,
    proceso_en_puerto,
    puerto_libre,
)

HOST = "127.0.0.1"


@pytest.fixture
def puerto_ocupado() -> Iterator[int]:
    """Abre un listener en un puerto efímero y lo cede ocupado durante el test."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((HOST, 0))
    sock.listen(1)
    puerto = sock.getsockname()[1]
    try:
        yield puerto
    finally:
        sock.close()


def test_puerto_libre_detecta_ocupado(puerto_ocupado: int) -> None:
    assert puerto_libre(puerto_ocupado, HOST) is False


def test_puerto_libre_tras_cerrar() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((HOST, 0))
    sock.listen(1)
    puerto = sock.getsockname()[1]
    assert puerto_libre(puerto, HOST) is False
    sock.close()
    assert puerto_libre(puerto, HOST) is True


def test_buscar_salta_el_ocupado(puerto_ocupado: int) -> None:
    # El preferido está ocupado; debe devolver otro (>= preferido).
    libre = buscar_puerto_libre(puerto_ocupado, HOST, intentos=50)
    assert libre is not None
    assert libre != puerto_ocupado
    assert puerto_libre(libre, HOST) is True


def test_buscar_devuelve_el_preferido_si_libre() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((HOST, 0))
    puerto = sock.getsockname()[1]
    sock.close()  # queda libre
    assert buscar_puerto_libre(puerto, HOST, intentos=1) == puerto


def test_buscar_sin_libres_devuelve_none(puerto_ocupado: int) -> None:
    # intentos=1 sobre el puerto ocupado: no explora más -> None.
    assert buscar_puerto_libre(puerto_ocupado, HOST, intentos=1) is None


def test_estado_puertos_marca_libre_y_ocupado(puerto_ocupado: int) -> None:
    libre = buscar_puerto_libre(puerto_ocupado + 1, HOST, intentos=100)
    assert libre is not None
    estados = {e.puerto: e for e in estado_puertos([puerto_ocupado, libre], HOST)}
    assert estados[puerto_ocupado].libre is False
    assert estados[libre].libre is True


def test_proceso_en_puerto_identifica_el_propio(puerto_ocupado: int) -> None:
    info = proceso_en_puerto(puerto_ocupado)
    if info is None:
        pytest.skip("El entorno no permite identificar el proceso (psutil/netstat/ss).")
    pid, nombre = info
    assert pid == os.getpid()
    assert nombre
