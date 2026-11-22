"""Geometría plana mínima para derivar áreas, perímetros y centroides.

El backend nunca acepta áreas del cliente: las calcula a partir de los vértices.
Estas funciones trabajan en metros sobre el mismo sistema de coordenadas que usa
el terreno (``eje_y = "norte"``) y no dependen de librerías externas.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from math import hypot
from typing import Any

Punto = tuple[float, float]
Caja = tuple[float, float, float, float]  # x_min, y_min, x_max, y_max


def normalizar_vertices(vertices: Iterable[Any]) -> list[Punto]:
    """Convierte vértices (``{"x", "y"}`` o ``[x, y]``) en puntos únicos.

    Elimina duplicados consecutivos y el vértice de cierre repetido. Un polígono
    válido necesita al menos tres vértices distintos.
    """

    puntos: list[Punto] = []
    for vertice in vertices:
        if isinstance(vertice, dict):
            punto = (float(vertice["x"]), float(vertice["y"]))
        elif hasattr(vertice, "x") and hasattr(vertice, "y"):
            # Modelos Pydantic como ``Vertice``.
            punto = (float(vertice.x), float(vertice.y))
        else:
            punto = (float(vertice[0]), float(vertice[1]))
        if not puntos or punto != puntos[-1]:
            puntos.append(punto)

    if len(puntos) > 1 and puntos[0] == puntos[-1]:
        puntos.pop()

    if len(puntos) < 3:
        raise ValueError("El polígono necesita al menos 3 vértices distintos.")

    return puntos


def distancia(a: Punto, b: Punto) -> float:
    return hypot(b[0] - a[0], b[1] - a[1])


def area_firmada(puntos: Sequence[Punto]) -> float:
    """Área con signo por la fórmula del cordón (positiva si es antihoraria)."""

    total = 0.0
    for indice, (x1, y1) in enumerate(puntos):
        x2, y2 = puntos[(indice + 1) % len(puntos)]
        total += x1 * y2 - x2 * y1
    return total / 2.0


def area_poligono(puntos: Sequence[Punto]) -> float:
    return abs(area_firmada(puntos))


def perimetro_poligono(puntos: Sequence[Punto]) -> float:
    return sum(
        distancia(puntos[indice], puntos[(indice + 1) % len(puntos)])
        for indice in range(len(puntos))
    )


def centroide(puntos: Sequence[Punto]) -> Punto:
    """Centroide del polígono; promedio de vértices si el área es despreciable."""

    area = area_firmada(puntos)
    if abs(area) < 1e-9:
        return (
            sum(p[0] for p in puntos) / len(puntos),
            sum(p[1] for p in puntos) / len(puntos),
        )

    factor = 6.0 * area
    cx = 0.0
    cy = 0.0
    for indice, (x1, y1) in enumerate(puntos):
        x2, y2 = puntos[(indice + 1) % len(puntos)]
        cruz = x1 * y2 - x2 * y1
        cx += (x1 + x2) * cruz
        cy += (y1 + y2) * cruz
    return (cx / factor, cy / factor)


def caja(puntos: Sequence[Punto]) -> Caja:
    xs = [p[0] for p in puntos]
    ys = [p[1] for p in puntos]
    return (min(xs), min(ys), max(xs), max(ys))


def centro_caja(puntos: Sequence[Punto]) -> Punto:
    x_min, y_min, x_max, y_max = caja(puntos)
    return ((x_min + x_max) / 2.0, (y_min + y_max) / 2.0)


def rectangulo(x0: float, y0: float, x1: float, y1: float) -> list[Punto]:
    """Anillo rectangular en sentido antihorario."""

    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def poligono_dict(puntos: Sequence[Punto]) -> dict[str, list[list[float]]]:
    return {"anillo": [[round(x, 4), round(y, 4)] for x, y in puntos]}


def punto_dict(punto: Punto) -> dict[str, float]:
    return {"x": round(punto[0], 4), "y": round(punto[1], 4)}


def puntos_interpolados(a: Punto, b: Punto, paso: float) -> list[Punto]:
    """Puntos sobre el segmento ``a-b`` cada ``paso`` metros, incluido ``a``."""

    if paso <= 0:
        return [a]

    largo = distancia(a, b)
    if largo <= 1e-9:
        return [a]

    dx = (b[0] - a[0]) / largo
    dy = (b[1] - a[1]) / largo
    cantidad = int(largo / paso) + 1
    return [(a[0] + dx * paso * i, a[1] + dy * paso * i) for i in range(cantidad)]


def segmento_desplazado(a: Punto, b: Punto) -> tuple[Punto, Punto]:
    """Evita tramos de longitud cero que violan ``longitud_m > 0``."""

    if distancia(a, b) > 0.01:
        return a, b
    return a, (a[0] + 0.01, a[1])


__all__ = [
    "Caja",
    "Punto",
    "area_poligono",
    "caja",
    "centro_caja",
    "centroide",
    "distancia",
    "normalizar_vertices",
    "perimetro_poligono",
    "poligono_dict",
    "punto_dict",
    "puntos_interpolados",
    "rectangulo",
    "segmento_desplazado",
]
