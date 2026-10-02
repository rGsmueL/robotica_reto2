"""arm_broker — el único nodo que publica en /joint_states.

Andamiaje entregado por el curso. Los bloques IMPLEMENTAR son lo que evalúa el
reto; el resto es instrumentación y se usa tal cual.

=========================== ORIGEN DE ESTE ARCHIVO ===========================
Copia del andamiaje `src/arm_broker/arm_broker/broker.py` del curso, sin
cambios en `__init__`, `cancel_callback`, `mover`, `publicar_estado_cola` ni
`destroy_node`. Solo se rellenaron los cuatro bloques `IMPLEMENTAR` del item 2
(`goal_callback`, `handle_accepted_callback`, `_worker`, `execute_callback`) y
se anadieron tres ayudantes privados que solo orchestran esos bloques:
`_admitir`, `_armar_resultado` y `_publicar_feedback`.

Ver `CAMBIOS.md` para el detalle linea por linea.
================================================================================
"""

import threading
import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import JointState

from arm_broker_interfaces.action import MoveArm
from arm_broker_interfaces.msg import QueueState

from arm_broker import fk
from arm_broker.politicas import POLITICAS, Pedido


class ArmBroker(Node):

    def __init__(self):
        super().__init__('arm_broker')

        self.declare_parameter('politica', 'fifo')
        self.declare_parameter('tau_envejecimiento_s', 8.0)
        self.declare_parameter('cola_max', 20)
        self.declare_parameter('paso_max_rad', 1.2)
        self.declare_parameter('duracion_movimiento_s', 3.0)
        self.declare_parameter('pasos_interpolacion', 10)

        nombre = self.get_parameter('politica').value
        if nombre not in POLITICAS:
            raise RuntimeError(f'política desconocida: {nombre}. Hay {list(POLITICAS)}')
        clase = POLITICAS[nombre]
        if nombre == 'prioridad':
            self.politica = clase(self.get_parameter('tau_envejecimiento_s').value)
        else:
            self.politica = clase()

        self.cola_max = int(self.get_parameter('cola_max').value)
        self.paso_max = float(self.get_parameter('paso_max_rad').value)
        self.duracion = float(self.get_parameter('duracion_movimiento_s').value)
        self.pasos = max(1, int(self.get_parameter('pasos_interpolacion').value))

        self.grupo_entrada = ReentrantCallbackGroup()
        self.grupo_worker = MutuallyExclusiveCallbackGroup()

        self.lock = threading.Lock()
        self.pendientes = []
        self.por_goal_id = {}
        self.ejecutando = None
        self.q_actual = [0.0] * 6
        self.n_aceptados = 0
        self.n_rechazados = 0
        self.n_completados = 0
        self._parar = threading.Event()

        self.pub_joint = self.create_publisher(JointState, '/joint_states', 10)
        self.pub_cola = self.create_publisher(QueueState, '/arm/queue_state', 10)

        self.servidor = ActionServer(
            self,
            MoveArm,
            'move_arm',
            goal_callback=self.goal_callback,
            handle_accepted_callback=self.handle_accepted_callback,
            cancel_callback=self.cancel_callback,
            execute_callback=self.execute_callback,
            callback_group=self.grupo_entrada,
        )

        self.create_timer(0.2, self.publicar_estado_cola,
                          callback_group=self.grupo_worker)

        self.worker = threading.Thread(target=self._worker, daemon=True)
        self.worker.start()

        self.get_logger().info(
            f'arm_broker listo · política={self.politica.nombre} · '
            f'cola_max={self.cola_max} · único publicador de /joint_states')

    # ========================= IMPLEMENTAR · ítem 2 ==========================
    def goal_callback(self, goal_request):
        """Admisión. Barata e inmediata: acepta o rechaza, nunca ejecuta.

        Rechacen con motivo explícito si el objetivo está fuera de límites
        articulares, fuera del workspace, o si el paso articular desde
        self.q_actual es mayor que self.paso_max. Usen fk.dentro_de_limites,
        fk.dentro_del_workspace y fk.paso_articular.

        Lleven la cuenta en self.n_aceptados y self.n_rechazados.
        Devuelve GoalResponse.ACCEPT o GoalResponse.REJECT.
        """
        q = list(goal_request.joint_positions)
        etiqueta = f'[{goal_request.client_id} p{int(goal_request.priority)}]'

        ok, motivo = self._admitir(q)
        if not ok:
            with self.lock:
                self.n_rechazados += 1
            # El motivo va al log del broker: es el "registro de rechazos con
            # motivo" que pide el enunciado. Para guardarlo en un archivo:
            #   ros2 run arm_broker broker 2>&1 | tee rechazos.log
            self.get_logger().warn(f'RECHAZADO {etiqueta} · {motivo}')
            return GoalResponse.REJECT

        with self.lock:
            self.n_aceptados += 1
            profundidad = len(self.pendientes)
        self.get_logger().info(
            f'ADMITIDO {etiqueta} · encolables en espera: {profundidad}')
        return GoalResponse.ACCEPT

    def handle_accepted_callback(self, goal_handle):
        """Encolar. AQUÍ NO SE EJECUTA NADA, y no se publica en /joint_states.

        Construyan un Pedido y guárdenlo en self.pendientes bajo self.lock.
        Indéxenlo también en self.por_goal_id, que el worker lo va a necesitar.
        """
        pedido_goal = goal_handle.request
        pedido = Pedido(
            goal_handle,
            pedido_goal.client_id,
            int(pedido_goal.priority),
            list(pedido_goal.joint_positions),
        )
        with self.lock:
            # self.pendientes es la fila en orden de llegada: se anade al
            # final y el worker solo saca por indice. FIFO no necesita ordenar.
            self.pendientes.append(pedido)
            self.por_goal_id[pedido.goal_id] = pedido
            profundidad = len(self.pendientes)
        self.get_logger().info(
            f'ENCOLADO {pedido} · {profundidad} en espera · no se ejecuta aquí')

    def _worker(self):
        """El único que decide a quién le toca. Corre en su propio hilo.

        En bucle, mientras no self._parar:
          - si no hay nada ejecutándose y hay pendientes, pregunten a
            self.politica.siguiente() cuál sigue y sáquenlo de la cola
          - si venía cancelado, descártenlo
          - si no, márquenlo en self.ejecutando, anoten t_inicio_ejec, y llamen
            a goal_handle.execute()
          - esperen a que termine con pedido.fin.wait() ANTES de sacar el
            siguiente: ahí está la exclusión mutua
          - al terminar, limpien self.ejecutando y avisen a la política con
            self.politica.atendido(pedido)

        Sobre la espera: goal_handle.execute() corre el execute_callback de
        forma SINCRONA en este hilo, así que la llamada ya bloquea hasta que
        el movimiento acaba. El bloqueo del worker no depende de eso: este
        while no vuelve a la cabeza del bucle hasta que execute() regresa, y
        solo entonces se saca el siguiente. pedido.fin.set() queda como la
        senal de "este pedido ya no esta en vuelo" para quien lo espere desde
        otro hilo; el execute_callback no lo pone, lo pone el finally de aqui.
        """
        while not self._parar.is_set():
            with self.lock:
                ocupada = self.ejecutando is not None
                hay = bool(self.pendientes)
            if ocupada or not hay:
                self._parar.wait(0.005)
                continue

            with self.lock:
                if self.ejecutando is not None or not self.pendientes:
                    continue
                indice = self.politica.siguiente(self.pendientes)
                if indice is None:
                    continue
                # La Exclusion mutua empieza aqui: a partir de este punto no
                # hay mas de un pedido en vuelo, porque el siguiente no se saca
                # hasta que este termine.
                pedido = self.pendientes.pop(indice)
                pedido.t_inicio_ejec = time.time()
                self.ejecutando = pedido

            if pedido.goal_handle.is_cancel_requested:
                self.get_logger().info(
                    f'DESCARTADO {pedido} · cancelado antes de ejecutar')
                with self.lock:
                    self.por_goal_id.pop(pedido.goal_id, None)
                self.politica.atendido(pedido)
                pedido.goal_handle.canceled()
                pedido.fin.set()
                continue

            try:
                # goal_handle.execute() corre execute_callback de forma
                # sincrona en ESTE hilo, que es el unico que publica en
                # /joint_states. Por eso el brazo no se solapa nunca.
                pedido.goal_handle.execute()
            except Exception as exc:                      # pragma: no cover
                self.get_logger().error(f'FALLO ejecutando {pedido} · {exc}')
            finally:
                with self.lock:
                    self.ejecutando = None
                    self.por_goal_id.pop(pedido.goal_id, None)
                self.politica.atendido(pedido)
                pedido.fin.set()

    def execute_callback(self, goal_handle):
        """Ejecutar UN pedido. Lo llama el worker, nunca handle_accepted.

        Busquen el Pedido en self.por_goal_id por el id del goal. Interpolen
        desde self.q_actual hasta el destino en self.pasos pasos, publicando
        con self.mover() y mandando feedback en cada uno. Comprueben
        goal_handle.is_cancel_requested en cada paso.

        Terminen con goal_handle.succeed() y devuelvan el Result con
        wait_time_s y exec_time_s. Pase lo que pase, pedido.fin.set() al final:
        si no, el worker se queda esperando para siempre.
        """
        clave = bytes(goal_handle.goal_id.uuid).hex()[:12]
        with self.lock:
            pedido = self.por_goal_id.get(clave)
            origen = list(self.q_actual)

        if pedido is None:
            # No deberia pasar: el worker solo llama a execute() con un pedido
            # que sigue en por_goal_id. Si pasa, no se publica nada.
            self.get_logger().error(f'goal {clave} no esta en la cola · abortado')
            resultado = MoveArm.Result()
            resultado.success = False
            resultado.message = 'pedido no encontrado en la cola'
            resultado.wait_time_s = 0.0
            resultado.exec_time_s = 0.0
            goal_handle.abort(resultado)
            return resultado

        destino = list(pedido.joint_positions)
        t0 = time.time()
        espera = (pedido.t_inicio_ejec or t0) - pedido.t_llegada
        dt_paso = self.duracion / self.pasos
        paso = 0
        cancelado = False

        for paso in range(1, self.pasos + 1):
            if goal_handle.is_cancel_requested:
                cancelado = True
                break
            # Interpolacion lineal en linea recta desde la pose de partida
            # hasta el destino. Se recalcula desde `origen` en cada paso, no
            # acumulando, para que no se arrastre error.
            alfa = paso / self.pasos
            q = [o + alfa * (d - o) for o, d in zip(origen, destino)]
            self.mover(q)
            self._publicar_feedback(goal_handle, 'EXECUTING', 0, time.time() - t0)
            time.sleep(dt_paso)

        resultado = MoveArm.Result()
        resultado.success = not cancelado
        resultado.wait_time_s = espera
        resultado.exec_time_s = time.time() - t0

        with self.lock:
            self.n_completados += 1

        if cancelado:
            resultado.message = f'cancelado en el paso {paso}/{self.pasos}'
            self.get_logger().info(f'{pedido} · {resultado.message}')
            goal_handle.canceled(resultado)
        else:
            resultado.message = f'pose alcanzada en {self.pasos} pasos'
            self.get_logger().info(f'{pedido} · {resultado.message}')
            goal_handle.succeed(resultado)
        return resultado
    # =========================================================================

    # -------------------------------------------------- ayudantes del ítem 2
    def _admitir(self, q):
        """Las tres validaciones del enunciado, en orden de coste creciente.

        Devuelve (True, '') o (False, motivo legible). Los tres motivos que
        exige la rubrica son: limites articulares, workspace y paso articular
        excesivo. Se agrega un cuarto, cola llena, que es para lo que existe el
        parametro `cola_max`: el andamiaje lo declara pero no lo usaba, y una
        fila sin tope bajo contencion no tiene ningun sentido.
        """
        ok, motivo = fk.dentro_de_limites(q)
        if not ok:
            return False, f'limites articulares: {motivo}'

        ok, motivo = fk.dentro_del_workspace(q)
        if not ok:
            return False, f'workspace: {motivo}'

        with self.lock:
            pose_actual = list(self.q_actual)
        salto = fk.paso_articular(pose_actual, q)
        if salto > self.paso_max:
            return False, (f'paso articular excesivo: {salto:.2f} rad desde la '
                           f'pose actual, maximo {self.paso_max:.2f} rad')

        with self.lock:
            if len(self.pendientes) >= self.cola_max:
                return False, (f'cola llena: {len(self.pendientes)} de '
                               f'{self.cola_max} pedidos')

        return True, ''

    def _publicar_feedback(self, goal_handle, estado, posicion, transcurrido):
        fb = MoveArm.Feedback()
        fb.state = estado
        fb.queue_position = posicion   # 0 = ya no esta en la cola
        fb.elapsed_s = transcurrido
        goal_handle.publish_feedback(fb)

    def cancel_callback(self, goal_handle):
        return CancelResponse.ACCEPT

    # ----------------------------------------------------------- publicar
    def mover(self, q):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        msg.name = fk.JOINT_NAMES
        msg.position = [float(v) for v in q]
        self.pub_joint.publish(msg)
        with self.lock:
            self.q_actual = list(q)

    def publicar_estado_cola(self):
        msg = QueueState()
        msg.stamp = self.get_clock().now().to_msg()
        with self.lock:
            ej = self.ejecutando
            msg.executing_client = ej.client_id if ej else ''
            msg.executing_goal_id = ej.goal_id if ej else ''
            msg.executing_elapsed_s = (time.time() - ej.t_inicio_ejec) if ej and ej.t_inicio_ejec else 0.0
            msg.queue_length = len(self.pendientes)
            msg.queued_goal_ids = [p.goal_id for p in self.pendientes]
            msg.queued_clients = [p.client_id for p in self.pendientes]
            msg.queued_priorities = [min(255, max(0, p.priority)) for p in self.pendientes]
            msg.queued_wait_s = [p.espera_s for p in self.pendientes]
            msg.total_accepted = self.n_aceptados
            msg.total_rejected = self.n_rechazados
            msg.total_completed = self.n_completados
            cola = list(self.pendientes)
        self.pub_cola.publish(msg)

        for posicion, p in enumerate(cola, start=1):
            try:
                fb = MoveArm.Feedback()
                fb.state = 'QUEUED'
                fb.queue_position = posicion
                fb.elapsed_s = p.espera_s
                p.goal_handle.publish_feedback(fb)
            except Exception:
                pass

    def destroy_node(self):
        self._parar.set()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    nodo = ArmBroker()
    executor = MultiThreadedExecutor()
    executor.add_node(nodo)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        nodo.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
