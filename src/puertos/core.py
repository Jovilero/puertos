"""Núcleo de la utilidad de puertos: funciones puras, sin CLI.

Método: para saber si un puerto está libre se intenta hacer bind(); si el SO lo
rechaza con OSError (EADDRINUSE), está ocupado. Es más fiable que "conectar y ver
si algo responde" y detecta también los listeners en 0.0.0.0 (como Docker),
porque 0.0.0.0:P reclama todas las interfaces y el bind a 127.0.0.1:P falla igual.
"""

from __future__ import annotations

import socket
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass


def puerto_libre(puerto: int, host: str = "127.0.0.1") -> bool:
    """True si se puede escuchar en (host, puerto).

    Se comprueba intentando el bind, no conectando: es la pregunta real que nos
    importa ("¿puedo yo abrir aquí un servidor?"). NO se activa SO_REUSEADDR a
    propósito: en Windows permitiría bindear sobre un listener ya activo y
    daríamos por libre un puerto ocupado.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, puerto))
            return True
        except OSError:
            return False


def buscar_puerto_libre(
    preferido: int, host: str = "127.0.0.1", intentos: int = 20
) -> int | None:
    """Devuelve `preferido` si está libre; si no, el siguiente libre hacia arriba.

    Explora preferido, preferido+1, ... hasta `intentos` puertos (el patrón
    800X). Devuelve None si ninguno está libre en ese rango.
    """
    for puerto in range(preferido, preferido + intentos):
        if puerto > 65535:
            break
        if puerto_libre(puerto, host):
            return puerto
    return None


def proceso_en_puerto(puerto: int) -> tuple[int, str] | None:
    """(pid, nombre) del proceso que escucha en `puerto`, o None si no se sabe.

    Cascada sin dependencias obligatorias: psutil si está instalado (limpio y
    portable), y si no, las herramientas del sistema (netstat/tasklist en
    Windows, ss en Linux). Nunca usa shell=True.
    """
    return _proceso_psutil(puerto) or _proceso_windows(puerto) or _proceso_linux(puerto)


def _proceso_psutil(puerto: int) -> tuple[int, str] | None:
    try:
        import psutil  # type: ignore[import-untyped]
    except ImportError:
        return None
    try:
        for conexion in psutil.net_connections(kind="inet"):
            if (
                conexion.laddr
                and conexion.laddr.port == puerto
                and conexion.status == psutil.CONN_LISTEN
                and conexion.pid
            ):
                try:
                    nombre = psutil.Process(conexion.pid).name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    nombre = "?"
                return conexion.pid, nombre
    except (psutil.AccessDenied, PermissionError):
        return None
    return None


def _ejecutar(comando: list[str]) -> str:
    """Ejecuta un comando del sistema y devuelve su stdout (vacío si falla)."""
    try:
        completado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            check=False,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, ValueError):
        return ""
    return completado.stdout or ""


def _proceso_windows(puerto: int) -> tuple[int, str] | None:
    if not sys.platform.startswith("win"):
        return None
    salida = _ejecutar(["netstat", "-ano", "-p", "TCP"])
    pid: int | None = None
    for linea in salida.splitlines():
        partes = linea.split()
        # 0=proto 1=local 2=remoto 3=estado 4=pid
        if len(partes) >= 5 and partes[3] == "LISTENING":
            direccion = partes[1]
            if direccion.rsplit(":", 1)[-1] == str(puerto):
                try:
                    pid = int(partes[4])
                except ValueError:
                    continue
                break
    if pid is None:
        return None
    nombre = _nombre_proceso_windows(pid) or "?"
    return pid, nombre


def _nombre_proceso_windows(pid: int) -> str | None:
    salida = _ejecutar(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"])
    for linea in salida.splitlines():
        if linea.startswith('"'):
            # "imagen.exe","PID","sesión",...
            return linea.split('","')[0].strip('"')
    return None


def _proceso_linux(puerto: int) -> tuple[int, str] | None:
    if sys.platform.startswith("win"):
        return None
    salida = _ejecutar(["ss", "-ltnHp"])
    for linea in salida.splitlines():
        # ...  127.0.0.1:8000  ...  users:(("python",pid=1234,fd=3))
        campos = linea.split()
        if len(campos) < 4:
            continue
        direccion = campos[3]
        if direccion.rsplit(":", 1)[-1] != str(puerto):
            continue
        marca = "pid="
        if marca in linea:
            resto = linea.split(marca, 1)[1]
            digitos = ""
            for caracter in resto:
                if caracter.isdigit():
                    digitos += caracter
                else:
                    break
            nombre = "?"
            if 'users:(("' in linea:
                nombre = linea.split('users:(("', 1)[1].split('"', 1)[0]
            if digitos:
                return int(digitos), nombre
    return None


@dataclass
class EstadoPuerto:
    puerto: int
    libre: bool
    pid: int | None = None
    proceso: str | None = None


def estado_puertos(
    puertos: Iterable[int], host: str = "127.0.0.1"
) -> list[EstadoPuerto]:
    """Estado de cada puerto: libre/ocupado y, si está ocupado, el proceso."""
    estados: list[EstadoPuerto] = []
    for puerto in puertos:
        libre = puerto_libre(puerto, host)
        pid, proceso = None, None
        if not libre:
            info = proceso_en_puerto(puerto)
            if info is not None:
                pid, proceso = info
        estados.append(EstadoPuerto(puerto, libre, pid, proceso))
    return estados
