"""Recorte de polígonos contra semiplanos, franjas y rectángulos (S1-S3).

El motor ya no puede trabajar con la caja envolvente del terreno: con un trapecio,
las franjas de sector y las zonas de cultivo tienen que seguir el contorno. Estas
pruebas cubren el recorte puro y su comportamiento en los casos degenerados.
"""

import pytest

from app.services import geometria

# Trapecio real del usuario: 2100 m², base 60 m, altura 40 m.
TRAPECIO = [(0.0, 40.0), (60.0, 40.0), (60.0, 20.0), (30.0, 0.0), (0.0, 0.0)]


def _area(puntos) -> float:
    return geometria.area_poligono(puntos)


# --------------------------------------------------------------------------- #
# Recorte contra un semiplano / una franja / un rectángulo
# --------------------------------------------------------------------------- #


def test_recortar_contra_un_semiplano_deja_la_mitad_del_trapecio() -> None:
    recorte = geometria.recortar_semiplano(TRAPECIO, "x", 30.0, mantener_mayor=False)

    assert _area(recorte) == pytest.approx(1200.0)
    assert all(x <= 30.0 for x, _ in recorte)


def test_recortar_una_franja_del_trapecio_no_inventa_area() -> None:
    franja = geometria.recortar_franja(TRAPECIO, "y", 0.0, 22.0)

    # De 0 a 20 el ancho crece de 30 a 60; de 20 a 22 hay 60 m de ancho.
    assert _area(franja) == pytest.approx(900.0 + 120.0)
    assert all(y <= 22.0 for _, y in franja)


def test_recortar_contra_la_caja_completa_no_cambia_el_area() -> None:
    caja = geometria.caja(TRAPECIO)
    recorte = geometria.recortar_rectangulo(TRAPECIO, caja)

    assert _area(recorte) == pytest.approx(_area(TRAPECIO))


def test_una_franja_que_no_toca_el_poligono_devuelve_vacio() -> None:
    assert geometria.recortar_franja(TRAPECIO, "x", 80.0, 90.0) == []
    assert geometria.recortar_semiplano(TRAPECIO, "y", -5.0, mantener_mayor=False) == []


def test_una_franja_que_solo_toca_un_vertice_devuelve_vacio() -> None:
    # y = 40 es el borde superior: el recorte es una línea, no un polígono.
    assert geometria.recortar_franja(TRAPECIO, "y", 40.0, 45.0) == []
    # x = 60 es el borde derecho: otra línea.
    assert geometria.recortar_franja(TRAPECIO, "x", 60.0, 61.0) == []


def test_una_franja_de_area_casi_cero_devuelve_vacio() -> None:
    assert geometria.recortar_franja(TRAPECIO, "x", 10.0, 10.0 + 1e-9) == []


def test_el_recorte_nunca_devuelve_un_poligono_invalido() -> None:
    for desde, hasta in ((-1.0, 0.0), (39.5, 40.0), (59.0, 60.0), (0.0, 40.0)):
        recorte = geometria.recortar_franja(TRAPECIO, "y", desde, hasta)
        assert len(recorte) in (0,) or len(recorte) >= 3
        if recorte:
            assert _area(recorte) > geometria.AREA_MINIMA


def test_un_poligono_degenerado_no_rompe_el_recorte() -> None:
    # Todos los vértices en una línea: el área es cero y no hay nada que repartir.
    linea = [(0.0, 0.0), (10.0, 0.0), (5.0, 0.0)]

    assert geometria.recortar_franja(linea, "x", 0.0, 10.0) == []
    assert geometria.banda_por_area(linea, 0, 4) == ([], 0.0)


# --------------------------------------------------------------------------- #
# Reparto por área igual
# --------------------------------------------------------------------------- #


def test_las_bandas_por_area_reparten_todo_el_trapecio() -> None:
    bandas = [geometria.banda_por_area(TRAPECIO, indice, 8) for indice in range(8)]

    assert all(poligono for poligono, _ in bandas)
    assert sum(area for _, area in bandas) == pytest.approx(2100.0)
    for poligono, area in bandas:
        assert area == pytest.approx(2100.0 / 8)
        assert _area(poligono) == pytest.approx(area)
        assert all(geometria.punto_en_poligono(p, TRAPECIO) for p in poligono)


def test_las_bandas_por_area_dejan_las_franjas_del_trapecio_inclinadas() -> None:
    ultima, _ = geometria.banda_por_area(TRAPECIO, 7, 8)

    # La última franja arranca en el borde inclinado: no es un rectángulo.
    assert min(y for _, y in ultima) > 1.0
    assert len({round(y, 6) for _, y in ultima}) >= 3


def test_corte_por_area_devuelve_la_coordenada_del_area_pedida() -> None:
    # Bajo y = 20 hay 900 m²; los 150 restantes hasta la mitad salen de 2,5 m más.
    assert geometria.corte_por_area(TRAPECIO, "y", 0.0, 1050.0) == pytest.approx(22.5)


def test_banda_por_area_fuera_de_rango_no_explota() -> None:
    assert geometria.banda_por_area(TRAPECIO, 20, 8) == ([], 0.0)
    assert geometria.banda_por_area(TRAPECIO, 0, 0) == ([], 0.0)


# --------------------------------------------------------------------------- #
# Punto dentro del polígono y segmentos sobre una recta
# --------------------------------------------------------------------------- #


def test_punto_en_poligono_acepta_borde_y_rechaza_el_exterior() -> None:
    assert geometria.punto_en_poligono((30.0, 20.0), TRAPECIO)
    assert geometria.punto_en_poligono((45.0, 10.0), TRAPECIO)  # sobre el borde inclinado
    assert geometria.punto_en_poligono((0.0, 0.0), TRAPECIO)  # vértice
    assert not geometria.punto_en_poligono((55.0, 5.0), TRAPECIO)  # fuera, bajo la diagonal
    assert not geometria.punto_en_poligono((30.0, 45.0), TRAPECIO)


def test_punto_en_poligono_ve_el_hueco_de_un_poligono_concavo() -> None:
    ele = [
        (0.0, 0.0),
        (10.0, 0.0),
        (10.0, 4.0),
        (4.0, 4.0),
        (4.0, 10.0),
        (0.0, 10.0),
    ]

    assert geometria.punto_en_poligono((2.0, 8.0), ele)
    assert not geometria.punto_en_poligono((8.0, 8.0), ele)


def test_los_segmentos_sobre_una_recta_quedan_dentro_del_trapecio() -> None:
    tramos = geometria.segmentos_horizontales(TRAPECIO, 10.0)
    assert tramos == [((0.0, 10.0), (45.0, 10.0))]

    verticales = geometria.segmentos_verticales(TRAPECIO, 45.0)
    assert verticales == [((45.0, 10.0), (45.0, 40.0))]

    assert geometria.segmentos_horizontales(TRAPECIO, 39.5) == [
        ((0.0, 39.5), (60.0, 39.5))
    ]
    # Por debajo de la diagonal no hay polígono.
    assert geometria.segmentos_horizontales(TRAPECIO, 2.0) == [
        ((0.0, 2.0), (33.0, 2.0))
    ]


def test_punto_interior_de_un_poligono_concavo_queda_adentro() -> None:
    # U abierta hacia arriba: ni el centro de la caja ni el centroide caen adentro.
    u = [
        (0.0, 0.0),
        (10.0, 0.0),
        (10.0, 10.0),
        (7.0, 10.0),
        (7.0, 3.0),
        (3.0, 3.0),
        (3.0, 10.0),
        (0.0, 10.0),
    ]
    assert not geometria.punto_en_poligono(geometria.centroide(u), u)
    assert not geometria.punto_en_poligono(geometria.centro_caja(u), u)

    punto = geometria.punto_interior(u)
    assert geometria.punto_en_poligono(punto, u)
