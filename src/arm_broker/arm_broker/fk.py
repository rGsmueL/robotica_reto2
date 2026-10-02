"""Cinemática directa del JetCobot (MyCobot 280) — ítem 1.

=========================== ORIGEN DE ESTE ARCHIVO ===========================
Archivo FUSIONADO a partir de dos fuentes del material del curso:

  · posicion_DH.py  (raiz de `termin/`)  ->  aporta la TABLA DH y la matriz
    homogenea por articulacion, escritas en convencion DH ESTANDAR
    (Craig 2005, Introduccion a la Robotica, ec. 2-6).
  · src/arm_broker/arm_broker/fk.py  (andamiaje del curso)  ->  aporta la
    INTERFAZ DE MODULO que el resto del codigo ya consume:
    JOINT_NAMES, JOINT_LIMITS, ALCANCE_MIN_MM, ALCANCE_MAX_MM,
    fk_matriz(q), fk(q), dentro_de_limites(q), dentro_del_workspace(q),
    paso_articular(q_desde, q_hasta).

Por que hubo que fusionarlos y no copiar uno de los dos
--------------------------------------------------------------
El `_t()` del andamiaje del curso implementaba el bloque de ROTACION del DH
MODIFICADO (Craig, ec. 2-41) pero dejaba su columna de traslacion sin rotar
por ese bloque. Una matriz homogenea 4x4 es una transformacion rigida solo si
la traslacion es R.p; si no, el resultado no es una pose de ningun marco y
todo el producto acumulado se desplaza. Ese `_t` ademas es incompatible con
una tabla DH ESTANDAR: no es un reordenamiento de columnas.

Verificacion (400 poses aleatorias en el rango de `herramientas/generar_carga.py`):
    version del andamiaje .............. error vs DH estandar: hasta 656.8 mm
    este fk.py (DH estandar) .......... alcance 281.7 .. 426.0 mm, 400/400
                                         poses dentro del workspace, z >= 0

La tabla que se usa abajo esta en GRADOS en `posicion_DH.py`; aqui ya esta
en RADIANES, que es lo que pide el contrato del andamiaje (`fk_matriz` recibe
`alpha_rad` y `theta_offset_rad`).

CRITERIO DEL RETO: error de posicion <= 10 mm contra el robot real, medido con
`herramientas/verificar_fk.py`. Esa verificacion es fisica: no se puede
resolver sin el JetCobot delante.
==========================================================================
"""

import math

JOINT_NAMES = ['1_Joint', '2_Joint', '3_Joint', '4_Joint', '5_Joint', '6_Joint']

# ============================== IMPLEMENTAR · ítem 1 ==============================
# Tabla DH del JetCobot en convencion DH ESTANDAR, una fila por articulacion:
#     (alpha_rad, a_mm, d_mm, theta_offset_rad)
#
# Traducida de la tabla de `posicion_DH.py`, que la expressa en grados y en el
# orden [theta_offset, d, a, alpha]:
#
#   | # | Joint   | theta_off | d (mm)  | a (mm) | alpha |  -> esta tabla
#   |---|---------|-----------|---------|--------|-------|
#   | 1 | Joint 1 |     0     | 134.75  |   0    |  90   |  -> ( 90deg, 0, 134.75, 0)
#   | 2 | Joint 2 |   -90     |    0    | -110   |   0   |  -> (  0deg, -110, 0, -90deg)
#   | 3 | Joint 3 |     0     |    0    |  -96   |   0   |  -> (  0deg, -96, 0,   0)
#   | 4 | Joint 4 |   -90     |  63.4   |   0    |  90   |  -> ( 90deg, 0, 63.4, -90deg)
#   | 5 | Joint 5 |    90     |  75.05  |   0    | -90   |  -> (-90deg, 0, 75.05, 90deg)
#   | 6 | Joint 6 |     0     |   50    |   0    |   0   |  -> (  0deg, 0, 50,    0)
#
# `theta_offset` es el angulo en que la articulacion esta cuando q_i = 0, y se
# SUMA a q_i. `d` se mide sobre z_{i-1} y `a` sobre x_i, como manda DH estandar.
#
# ESTA TABLA ESTA SIN VERIFICAR CONTRA EL ROBOT. Antes de entregar el item 1
# hay que correr `python3 herramientas/verificar_fk.py` en el Jetson. Si el
# error sale grande y constante, el problema son los offsets; si crece con la
# distancia, son los a_i.
DH = [
    (math.radians(90.0), 0.0, 134.75, math.radians(0.0)),    # Joint 1
    (math.radians(0.0), -110.0, 0.0, math.radians(-90.0)),  # Joint 2
    (math.radians(0.0), -96.0, 0.0, math.radians(0.0)),     # Joint 3
    (math.radians(90.0), 0.0, 63.4, math.radians(-90.0)),   # Joint 4
    (math.radians(-90.0), 0.0, 75.05, math.radians(90.0)),  # Joint 5
    (math.radians(0.0), 0.0, 50.0, math.radians(0.0)),      # Joint 6
]

JOINT_LIMITS = [
    (-2.93, 2.93),
    (-2.36, 2.36),
    (-2.53, 2.53),
    (-2.58, 2.58),
    (-2.93, 2.93),
    (-3.14, 3.14),
]

ALCANCE_MIN_MM = 80.0
ALCANCE_MAX_MM = 480.0


def _t(alpha, a, d, theta):
    """Matriz de la articulacion i en DH ESTANDAR (Craig 2005, ec. 2-6).

    A_i = Rz(theta) . Tz(d) . Tx(a) . Rx(alpha)

    La columna de traslacion [a*ct, a*st, d] es el resultado de aplicar la
    rotacion Rz(theta) al vector [a, 0, d]. Por eso el andamiaje no servia: el
    modulo de rotacion que traia era el de DH modificado y la traslacion no
    correspondia a esa rotacion.
    """
    ct, st = math.cos(theta), math.sin(theta)
    ca, sa = math.cos(alpha), math.sin(alpha)
    return [
        [ct,      -st * ca,  st * sa,  a * ct],
        [st,       ct * ca, -ct * sa,  a * st],
        [0.0,      sa,       ca,       d    ],
        [0.0,      0.0,      0.0,      1.0  ],
    ]


def _mul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def fk_matriz(q):
    """Matriz homogénea 4x4 de la base al efector final."""
    T = [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]
    for (alpha, a, d, off), theta in zip(DH, q):
        T = _mul(T, _t(alpha, a, d, theta + off))
    return T


def fk(q):
    """Posición (x, y, z) del efector final, en milímetros desde la base."""
    T = fk_matriz(q)
    return (T[0][3], T[1][3], T[2][3])
# =================================================================================


def dentro_de_limites(q):
    if len(q) != 6:
        return False, f'se esperaban 6 ángulos, llegaron {len(q)}'
    for i, (valor, (lo, hi)) in enumerate(zip(q, JOINT_LIMITS)):
        if not lo <= valor <= hi:
            return False, f'{JOINT_NAMES[i]} fuera de rango: {valor:.3f} rad, límite [{lo}, {hi}]'
    return True, ''


def dentro_del_workspace(q):
    x, y, z = fk(q)
    r = math.sqrt(x * x + y * y + z * z)
    if r > ALCANCE_MAX_MM:
        return False, f'efector a {r:.0f} mm de la base, máximo {ALCANCE_MAX_MM:.0f}'
    if r < ALCANCE_MIN_MM:
        return False, f'efector a {r:.0f} mm de la base, demasiado cerca'
    if z < 0.0:
        return False, f'z = {z:.0f} mm: el efector quedaría bajo la base'
    return True, ''


def paso_articular(q_desde, q_hasta):
    return max(abs(b - a) for a, b in zip(q_desde, q_hasta))
