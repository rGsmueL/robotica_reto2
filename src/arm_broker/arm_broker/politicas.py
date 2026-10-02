"""Políticas de cola — ítems 2 y 3.

=========================== ORIGEN DE ESTE ARCHIVO ===========================
`Pedido` y la clase base `Politica` son del andamiaje del curso, sin cambios.
Se IMPLEMENTAN los dos `siguiente()` que el andamiaje dejo como
`NotImplementedError`:

  · FIFO .............. obligatoria por el enunciado.
  · SegundaPolitica ... round-robin entre clientes.

Restricciones del andamiaje que la eleccion tiene que respetar
----------------------------------------------------------------
1. `broker.py` linea 40 hace:
       if nombre == 'prioridad':
           self.politica = clase(self.get_parameter('tau_envejecimiento_s').value)
       else:
           self.politica = clase()
   O sea: si la politica se llama 'prioridad' RECIBE un tau. Round-robin no
   usa envejecimiento, pero su `__init__` tiene que aceptar el argumento
   igual, o el broker no arranca con `-p politica:=prioridad`.

2. `POLITICAS` no puede tener mas de dos entradas sin tocar `broker.py`, que
   solo distingue el caso 'prioridad'. Por eso la segunda politica conserva la
   clave 'prioridad' aunque por dentro sea round-robin.
================================================================================
"""

import threading
import time


class Pedido:
    def __init__(self, goal_handle, client_id, priority, joint_positions):
        self.goal_handle = goal_handle
        self.goal_id = bytes(goal_handle.goal_id.uuid).hex()[:12]
        self.client_id = client_id
        self.priority = int(priority)
        self.joint_positions = list(joint_positions)
        self.t_llegada = time.time()
        self.t_inicio_ejec = None
        self.fin = threading.Event()
        self.resultado = None

    @property
    def espera_s(self):
        fin = self.t_inicio_ejec if self.t_inicio_ejec else time.time()
        return fin - self.t_llegada

    def __repr__(self):
        return f'<{self.client_id} p{self.priority} {self.goal_id}>'


class Politica:
    nombre = 'base'

    def siguiente(self, pendientes):
        raise NotImplementedError

    def atendido(self, pedido):
        pass


# ============================== IMPLEMENTAR · ítems 2 y 3 =========================
# FIFO es obligatoria. La segunda la eligen ustedes y la justifican en el README:
# prioridad estática, prioridad con envejecimiento, o round-robin entre clientes.
#
# siguiente(pendientes) devuelve el ÍNDICE del pedido a atender, o None.
# Cada Pedido trae: client_id, priority, t_llegada y espera_s.


class FIFO(Politica):
    """Primero que llega, primero sale. El indice 0 es el mas antiguo.

    `pendientes` es `self.pendientes` del broker, que se mantiene siempre en
    orden de llegada porque solo se le anade al final y solo se le saca por
    indice. Por eso basta con devolver 0: no hace falta ordenar nada.
    """
    nombre = 'fifo'

    def siguiente(self, pendientes):
        if not pendientes:
            return None
        return 0


class SegundaPolitica(Politica):
    """Round-robin entre clientes: el turno pasa al cliente mas antiguo que no
    sea el ultimo servido.

    Como elegir entre las tres opciones
    -----------------------------------
    · Genera equidad de Jain ~= 1.0 por construccion: el cliente que acaba de
      ser atendido no vuelve a salir hasta que todos los demas hayan elusive.
    · Con aging el indice de inanicion baja, pero la equidad depende de que
      las prioridades de los clientes esten bien elegidas.
    · Con prioridad estatica la equidad y el p95 los decide quien tenga el
      numero mas alto, lo cual no es una decision del equipo sino del
      docente. Ademas, cuanto mas grande es la diferencia de prioridad, peor
      es el p95 agregado.

    Mecanica
    ---------
    Se guarda `_ultimo`: el `client_id` al que se le dio el turno en la ultima
    atencion. En cada llamada se busca el primer pedido, EN ORDEN DE LLEGADA,
    cuyo `client_id` sea distinto de `_ultimo`. Ese es el cliente mas antiguo
    que lleva mas rato sin turno, que es lo que round-robin quiere decir.

    En la practica `cliente.py` espera el resultado antes de enviar la pose
    siguiente, asi que cada cliente tiene como mucho un pedido en la cola: el
    reparto round-robin sale practicamente perfecto.
    """
    nombre = 'prioridad'

    def __init__(self, tau=0.0):
        # Acepta tau porque `broker.py` lo pasa cuando nombre == 'prioridad'.
        # Round-robin no envejece prioridades, asi que el valor no se usa.
        self.tau = float(tau)
        self._ultimo = None

    def siguiente(self, pendientes):
        if not pendientes:
            return None
        for i, pedido in enumerate(pendientes):
            if pedido.client_id != self._ultimo:
                return i
        # Todos los pendientes son del mismo cliente que acaba de ser atendido:
        # no hay a quien alternar, se sirve el mas antiguo.
        return 0

    def atendido(self, pedido):
        self._ultimo = pedido.client_id
# =================================================================================


POLITICAS = {
    'fifo': FIFO,
    'prioridad': SegundaPolitica,
}
