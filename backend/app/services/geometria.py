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

# Debajo de esta superficie el recorte es un punto, una línea o ruido numérico: se
# trata como vacío para no persistir polígonos inválidos ni áreas en cero.
AREA_MINIMA = 1e-4

# Iteraciones de la bisección que invierte el área acumulada. Con 60 la precisión
# es la de un ``float`` en metros, así que sobra para cualquier terreno real.
_ITERACIONES_AREA = 60

_EJE = {"x": 0, "y": 1}


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


# --------------------------------------------------------------------------- #
# Recorte contra semiplanos, franjas y rectángulos
# --------------------------------------------------------------------------- #

def _limpio(puntos: Iterable[Punto]) -> list[Punto]:
    """Anillo sin vértices repetidos ni cierre duplicado."""

    salida: list[Punto] = []
    for punto in puntos:
        if not salida or distancia(salida[-1], punto) > 1e-9:
            salida.append(punto)
    while len(salida) > 1 and distancia(salida[0], salida[-1]) <= 1e-9:
        salida.pop()
    return salida


def _recortar_eje(
    puntos: Sequence[Punto], indice: int, valor: float, mantener_mayor: bool
) -> list[Punto]:
    """Sutherland-Hodgman contra el semiplano ``coordenada >= valor`` (o ``<=``)."""

    def dentro(punto: Punto) -> bool:
        return (
            punto[indice] >= valor if mantener_mayor else punto[indice] <= valor
        )

    def corte(a: Punto, b: Punto) -> Punto | None:
        delta = b[indice] - a[indice]
        if abs(delta) <= 1e-12:
            return None  # el lado es paralelo al semiplano: no hay cruce real
        factor = (valor - a[indice]) / delta
        punto = [a[0] + (b[0] - a[0]) * factor, a[1] + (b[1] - a[1]) * factor]
        punto[indice] = valor
        return (punto[0], punto[1])

    if not puntos:
        return []

    salida: list[Punto] = []
    previo = puntos[-1]
    previo_dentro = dentro(previo)
    for actual in puntos:
        actual_dentro = dentro(actual)
        if actual_dentro:
            if not previo_dentro:
                borde = corte(previo, actual)
                if borde is not None:
                    salida.append(borde)
            salida.append(actual)
        elif previo_dentro:
            borde = corte(previo, actual)
            if borde is not None:
                salida.append(borde)
        previo = actual
        previo_dentro = actual_dentro
    return salida


def recortar_semiplano(
    puntos: Sequence[Punto],
    eje: str,
    valor: float,
    *,
    mantener_mayor: bool = True,
) -> list[Punto]:
    """Intersección con ``coordenada >= valor`` (o ``<=`` si ``mantener_mayor=False``).

    Devuelve ``[]`` cuando el resultado no es un polígono con superficie: un recorte
    que sólo toca un vértice o un lado es una línea (área 0) y no se devuelve.
    """

    indice = _EJE[eje]
    recorte = _limpio(_recortar_eje(puntos, indice, valor, mantener_mayor))
    if len(recorte) < 3 or area_poligono(recorte) <= AREA_MINIMA:
        return []
    return recorte


def recortar_poligono(
    puntos: Sequence[Punto],
    *,
    x_min: float | None = None,
    x_max: float | None = None,
    y_min: float | None = None,
    y_max: float | None = None,
) -> list[Punto]:
    """Intersección con el rectángulo dado (o con el terreno si no se acota)."""

    actual = list(puntos)
    for eje, valor, mantener_mayor in (
        ("x", x_min, True),
        ("x", x_max, False),
        ("y", y_min, True),
        ("y", y_max, False),
    ):
        if valor is None:
            continue
        actual = recortar_semiplano(actual, eje, valor, mantener_mayor=mantener_mayor)
        if not actual:
            return []
    return actual


def recortar_rectangulo(puntos: Sequence[Punto], caja_limite: Caja) -> list[Punto]:
    """Intersección con ``caja_limite`` (``x_min, y_min, x_max, y_max``)."""

    x_min, y_min, x_max, y_max = caja_limite
    return recortar_poligono(
        puntos, x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max
    )


def recortar_franja(
    puntos: Sequence[Punto],
    eje: str,
    desde: float | None = None,
    hasta: float | None = None,
) -> list[Punto]:
    """Intersección con la franja ``desde <= coordenada <= hasta`` sobre ``eje``."""

    actual = list(puntos)
    if desde is not None:
        actual = recortar_semiplano(actual, eje, desde, mantener_mayor=True)
    if hasta is not None and actual:
        actual = recortar_semiplano(actual, eje, hasta, mantener_mayor=False)
    return actual


def _area_bajo(puntos: Sequence[Punto], indice: int, valor: float) -> float:
    recorte = _recortar_eje(puntos, indice, valor, mantener_mayor=False)
    return area_poligono(recorte) if len(recorte) >= 3 else 0.0


def _area_franja(puntos: Sequence[Punto], indice: int, desde: float, hasta: float) -> float:
    return _area_bajo(puntos, indice, hasta) - _area_bajo(puntos, indice, desde)


def corte_por_area(
    puntos: Sequence[Punto], eje: str, desde: float, objetivo: float
) -> float:
    """Coordenada sobre ``eje`` donde el área desde ``desde`` llega a ``objetivo``.

    El área acumulada crece siempre con la coordenada, así que la inversa se busca
    por bisección. Si el objetivo supera la superficie del polígono, devuelve el
    extremo (el recorte posterior queda vacío o al ras).
    """

    indice = _EJE[eje]
    limite_minimo, limite_maximo = caja(puntos)[indice], caja(puntos)[indice + 2]
    limite_inferior = min(desde, limite_minimo)
    limite_superior = max(desde, limite_maximo)
    if objetivo <= 0:
        return limite_inferior
    if _area_franja(puntos, indice, limite_inferior, limite_superior) <= objetivo:
        return limite_superior

    bajo, alto = limite_inferior, limite_superior
    for _ in range(_ITERACIONES_AREA):
        medio = (bajo + alto) / 2.0
        if _area_franja(puntos, indice, limite_inferior, medio) < objetivo:
            bajo = medio
        else:
            alto = medio
    return (bajo + alto) / 2.0


def banda_por_area(
    puntos: Sequence[Punto], indice: int, total: int, *, eje: str = "x"
) -> tuple[list[Punto], float]:
    """Franja ``indice`` de ``total`` franjas de área igual dentro del polígono.

    Con un terreno rectangular la banda es exactamente la fracción del ancho; con un
    trapecio, sus bordes se corren hasta que el área recortada coincide.
    """

    if total <= 0 or indice < 0 or indice >= total:
        return [], 0.0
    superficie = area_poligono(puntos)
    if superficie <= AREA_MINIMA:
        return [], 0.0

    minimo = caja(puntos)[0 if eje == "x" else 1]
    cuota = superficie / total
    desde = corte_por_area(puntos, eje, minimo, cuota * indice)
    hasta = corte_por_area(puntos, eje, minimo, cuota * (indice + 1))
    banda = recortar_franja(puntos, eje, desde, hasta)
    if not banda:
        return [], 0.0
    return banda, area_poligono(banda)


def bandas_por_area(
    puntos: Sequence[Punto], total: int, *, eje: str = "x"
) -> list[tuple[list[Punto], float]]:
    return [banda_por_area(puntos, indice, total, eje=eje) for indice in range(total)]


# --------------------------------------------------------------------------- #
# Puntos y segmentos dentro del polígono
# --------------------------------------------------------------------------- #

def _distancia_a_segmento(punto: Punto, a: Punto, b: Punto) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    largo = dx * dx + dy * dy
    if largo <= 1e-18:
        return distancia(punto, a)
    factor = ((punto[0] - a[0]) * dx + (punto[1] - a[1]) * dy) / largo
    factor = max(0.0, min(1.0, factor))
    return distancia(punto, (a[0] + dx * factor, a[1] + dy * factor))


def punto_en_poligono(
    punto: Punto, puntos: Sequence[Punto], tolerancia: float = 1e-6
) -> bool:
    """True si el punto está dentro o sobre el borde del polígono (par-impar)."""

    if len(puntos) < 3:
        return False

    dentro = False
    x, y = punto
    for indice, a in enumerate(puntos):
        b = puntos[(indice + 1) % len(puntos)]
        if _distancia_a_segmento(punto, a, b) <= tolerancia:
            return True
        if (a[1] > y) != (b[1] > y):
            cruce = a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
            if cruce > x:
                dentro = not dentro
    return dentro


def _distancia_al_contorno(punto: Punto, puntos: Sequence[Punto]) -> float:
    return min(
        _distancia_a_segmento(punto, a, puntos[(indice + 1) % len(puntos)])
        for indice, a in enumerate(puntos)
    )


def _estrictamente_dentro(
    punto: Punto, puntos: Sequence[Punto], margen: float = 1e-6
) -> bool:
    """Dentro del polígono y a más de ``margen`` del borde (no sobre una arista)."""

    return punto_en_poligono(punto, puntos, tolerancia=0.0) and (
        _distancia_al_contorno(punto, puntos) > margen
    )


def _alturas_candidatas(puntos: Sequence[Punto]) -> list[float]:
    """Alturas donde buscar un tramo horizontal interior, en orden de preferencia."""

    alturas = [centroide(puntos)[1]]
    alturas.extend(punto[1] for punto in puntos)
    alturas.extend(
        (puntos[indice][1] + puntos[(indice + 1) % len(puntos)][1]) / 2.0
        for indice in range(len(puntos))
    )
    vistas: list[float] = []
    for altura in alturas:
        if not any(abs(altura - vista) <= 1e-12 for vista in vistas):
            vistas.append(altura)
    return vistas


def _punto_por_alturas(puntos: Sequence[Punto]) -> Punto | None:
    """Punto medio del tramo horizontal interior más ancho de alguna altura."""

    for altura in _alturas_candidatas(puntos):
        tramos = segmentos_horizontales(puntos, altura)
        if not tramos:
            continue
        inicio, fin = max(tramos, key=lambda tramo: distancia(tramo[0], tramo[1]))
        medio = ((inicio[0] + fin[0]) / 2.0, altura)
        if _estrictamente_dentro(medio, puntos):
            return medio
    return None


def _punto_por_subdivision(puntos: Sequence[Punto]) -> Punto | None:
    """Centroide del recorte de mayor área al subdividir la caja del polígono."""

    x_min, y_min, x_max, y_max = caja(puntos)
    for divisiones in (4, 8, 16, 32):
        ancho = (x_max - x_min) / divisiones
        alto = (y_max - y_min) / divisiones
        if ancho <= 0 or alto <= 0:
            continue
        mejor: tuple[float, Punto] | None = None
        for fila in range(divisiones):
            for columna in range(divisiones):
                celda = (
                    x_min + columna * ancho,
                    y_min + fila * alto,
                    x_min + (columna + 1) * ancho,
                    y_min + (fila + 1) * alto,
                )
                recorte = recortar_rectangulo(puntos, celda)
                if not recorte:
                    continue
                superficie = area_poligono(recorte)
                if superficie <= AREA_MINIMA:
                    continue
                centro = centroide(recorte)
                if not _estrictamente_dentro(centro, puntos):
                    continue
                if mejor is None or superficie > mejor[0]:
                    mejor = (superficie, centro)
        if mejor is not None:
            return mejor[1]
    return None


def _punto_desde_arista(puntos: Sequence[Punto]) -> Punto:
    """Último recurso: punto medio de una arista desplazado hacia adentro."""

    orientacion = 1.0 if area_firmada(puntos) > 0 else -1.0
    x_min, y_min, x_max, y_max = caja(puntos)
    escala = max(hypot(x_max - x_min, y_max - y_min), 1e-6)
    respaldo: Punto | None = None
    for indice, a in enumerate(puntos):
        b = puntos[(indice + 1) % len(puntos)]
        largo = distancia(a, b)
        if largo <= 1e-12:
            continue
        medio = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        # Normal interior: a la izquierda del recorrido si el anillo es antihorario.
        normal_x = -(b[1] - a[1]) / largo * orientacion
        normal_y = (b[0] - a[0]) / largo * orientacion
        for fraccion in (1e-3, 1e-2, 0.05, 0.1, 0.25):
            paso = min(largo, escala) * fraccion
            candidato = (medio[0] + normal_x * paso, medio[1] + normal_y * paso)
            if _estrictamente_dentro(candidato, puntos):
                return candidato
        if respaldo is None:
            respaldo = medio
    return respaldo if respaldo is not None else centroide(puntos)


def punto_interior(puntos: Sequence[Punto]) -> Punto:
    """Punto estrictamente dentro del polígono para colgar el cabezal o una válvula.

    El centroide sirve para formas convexas; en una cóncava puede caer en el hueco y
    en una franja partida puede quedar sobre la costura. Por eso se prueban primero
    el centroide y el centro de la caja, después el tramo horizontal interior más
    ancho a la altura del centroide, de los vértices y de los puntos medios, luego el
    centroide del recorte de mayor área de una subdivisión de la caja y, por último,
    el punto medio de una arista desplazado hacia adentro. Con área despreciable no
    hay interior: se devuelve un punto finito de la huella para no romper el motor.
    """

    if area_poligono(puntos) <= AREA_MINIMA:
        return centroide(puntos)

    for candidato in (centroide(puntos), centro_caja(puntos)):
        if _estrictamente_dentro(candidato, puntos):
            return candidato

    punto = _punto_por_alturas(puntos)
    if punto is not None:
        return punto

    punto = _punto_por_subdivision(puntos)
    if punto is not None:
        return punto

    return _punto_desde_arista(puntos)


def _cortes(puntos: Sequence[Punto], indice: int, valor: float) -> list[float]:
    """Coordenadas del otro eje donde la recta corta el contorno, ordenadas."""

    otro = 1 - indice
    cortes: list[float] = []
    for posicion, a in enumerate(puntos):
        b = puntos[(posicion + 1) % len(puntos)]
        # Intervalo semiabierto: un vértice justo sobre la recta cuenta una vez.
        if (a[indice] > valor) != (b[indice] > valor):
            factor = (valor - a[indice]) / (b[indice] - a[indice])
            cortes.append(a[otro] + (b[otro] - a[otro]) * factor)
    cortes.sort()
    return cortes


def _segmentos(
    puntos: Sequence[Punto], indice: int, valor: float
) -> list[tuple[Punto, Punto]]:
    cortes = _cortes(puntos, indice, valor)
    salida: list[tuple[Punto, Punto]] = []
    for inicio, fin in zip(cortes[::2], cortes[1::2]):
        if fin - inicio <= 1e-9:
            continue
        if indice == 1:  # recta horizontal y = valor
            salida.append(((inicio, valor), (fin, valor)))
        else:  # recta vertical x = valor
            salida.append(((valor, inicio), (valor, fin)))
    return salida


def segmentos_horizontales(
    puntos: Sequence[Punto], y: float
) -> list[tuple[Punto, Punto]]:
    """Tramos de la recta ``y`` que quedan dentro del polígono, de oeste a este."""

    return _segmentos(puntos, 1, y)


def segmentos_verticales(
    puntos: Sequence[Punto], x: float
) -> list[tuple[Punto, Punto]]:
    """Tramos de la recta ``x`` que quedan dentro del polígono, de sur a norte."""

    return _segmentos(puntos, 0, x)


__all__ = [
    "AREA_MINIMA",
    "Caja",
    "Punto",
    "area_poligono",
    "banda_por_area",
    "bandas_por_area",
    "caja",
    "centro_caja",
    "centroide",
    "corte_por_area",
    "distancia",
    "normalizar_vertices",
    "perimetro_poligono",
    "poligono_dict",
    "punto_dict",
    "punto_en_poligono",
    "punto_interior",
    "puntos_interpolados",
    "recortar_franja",
    "recortar_poligono",
    "recortar_rectangulo",
    "recortar_semiplano",
    "rectangulo",
    "segmento_desplazado",
    "segmentos_horizontales",
    "segmentos_verticales",
]
