#!/usr/bin/env python3
"""CLI de la utilidad de puertos: comprueba, busca y escanea puertos TCP locales.

Uso:
    puertos check 8000 8005 8501
    puertos find 8000            # imprime el primer 800X libre (stdout limpio)
    puertos scan 8000-8010
"""

from __future__ import annotations

import argparse
import sys

from .core import EstadoPuerto, buscar_puerto_libre, estado_puertos


def _imprimir_tabla(estados: list[EstadoPuerto]) -> None:
    for estado in estados:
        etiqueta = "LIBRE" if estado.libre else "OCUPADO"
        linea = f"{estado.puerto:<6} {etiqueta:<8}"
        if not estado.libre and estado.pid is not None:
            linea += f" PID {estado.pid}  {estado.proceso or '?'}"
        elif not estado.libre:
            linea += " (proceso desconocido)"
        print(linea)


def _rango(texto: str) -> range:
    """Convierte 'INICIO-FIN' en un range inclusivo."""
    try:
        inicio_txt, fin_txt = texto.split("-", 1)
        inicio, fin = int(inicio_txt), int(fin_txt)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"Rango inválido {texto!r}: usa INICIO-FIN, p.ej. 8000-8010"
        ) from error
    if fin < inicio:
        raise argparse.ArgumentTypeError(f"Rango vacío {texto!r}: FIN < INICIO")
    return range(inicio, fin + 1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Interfaz a comprobar (por defecto 127.0.0.1).",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p_check = sub.add_parser("check", help="Estado de puertos concretos.")
    p_check.add_argument("puertos", type=int, nargs="+")

    p_find = sub.add_parser("find", help="Primer puerto libre desde el preferido.")
    p_find.add_argument("preferido", type=int)
    p_find.add_argument("--intentos", type=int, default=20)

    p_scan = sub.add_parser("scan", help="Estado de un rango INICIO-FIN.")
    p_scan.add_argument("rango", type=_rango)

    args = parser.parse_args(argv)

    if args.comando == "check":
        _imprimir_tabla(estado_puertos(args.puertos, args.host))
        return 0

    if args.comando == "find":
        libre = buscar_puerto_libre(args.preferido, args.host, args.intentos)
        if libre is None:
            print(
                f"Sin puertos libres en {args.preferido}-"
                f"{args.preferido + args.intentos - 1}",
                file=sys.stderr,
            )
            return 1
        if libre != args.preferido:
            print(f"{args.preferido} ocupado -> uso {libre}", file=sys.stderr)
        print(libre)  # a stdout, limpio para PORT=$(...)
        return 0

    if args.comando == "scan":
        _imprimir_tabla(estado_puertos(list(args.rango), args.host))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
