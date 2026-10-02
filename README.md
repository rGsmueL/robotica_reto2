# Reto 2 · Comandos por dispositivo — Equipo 1

**Curso de Robótica · Reto 2 · Broker de acceso exclusivo al JetCobot**

Este documento es la lista de comandos **por dispositivo**. Cada sección dice
exactamente qué máquina es y qué pegar. No hay que leerlo entero: ve a la sección
de tu máquina.

| Documento | Para qué |
|---|---|
| **`comandos_final.md`** (este) | Los comandos, separados por Jetson / Raspberry 1–4 |
| `explicacion_comandos.md` | Qué hace cada comando y por qué |
| `errores_y_soluciones.md` | Qué falla, por qué y cómo se arregla |
| `cambios_angulos.md` | Cómo pasar de radianes a grados, y cómo mandar ángulos como parámetros |
| `archivos_a_modificar.md` | Qué archivo tocar para cambiar cada cosa, y quién lo toca |

## Convenciones

| Símbolo | Significado |
|---|---|
| `<IP_JETSON>` | La IP del Jetson de tu equipo. **No está escrita en ningún sitio de este repo a propósito**: cambia de un equipo a otro y de un día a otro. |
| `<USUARIO_PI>` | Tu usuario en la Raspberry (`pi`, `asan`, el que sea). Se ve con `whoami`. |
| `<CARPETA_DRIVER>` | El workspace del driver en el Jetson: `~/jetcobot_colcon_ws` o `~/ros2_ws_brazo`. Lo descubres en §1.3. |
| `#` al principio | Un comentario. No lo escribas. |

**Una regla de este equipo:** el dominio de ROS es el **43**.

```
42 + 1 = 43        (42 es la base del curso, +1 es el número de equipo)
```

Tiene que ser **43 en las cinco máquinas**: Jetson y las cuatro Raspberry. Con dos
dominios distintos, las máquinas se hacen `ping` igual pero no se ven entre sí.

---

# §0 · Lo primero: qué se configura, dónde y quién

Esta es la tabla que hay que leer antes de la primera sesión. Responde a las tres
preguntas que siempre generan confusión: **qué**, **dónde**, **quién**.

| Qué | Valor | Dónde vive | Qué máquina | Quién lo configura |
|---|---|---|---|---|
| `ROS_DOMAIN_ID` | `43` | `~/rb2/entorno.sh` | Las 5 | **Cada integrante**, pero el número te lo da el profesor. Nadie lo escribe en el `.bashrc`. |
| `ROS_LOCALHOST_ONLY` | `0` | `~/rb2/entorno.sh` | Las 5 | Cada integrante |
| `RMW_IMPLEMENTATION` | `rmw_fastrtps_cpp` | `~/rb2/entorno.sh` | Las 5 | Cada integrante |
| `source` de ROS 2 | `/opt/ros/humble/setup.bash` | `~/rb2/entorno.sh` | Las 5 | **El profesor**, al instalar. Tú solo lo verificas. |
| `source` del driver | `<CARPETA_DRIVER>/install/setup.bash` | `~/rb2/entorno.sh` (con guarda) | **Solo Jetson** | **El profesor / dueño del Jetson.** Ya suele estar hecho. |
| `source` del reto | `~/rb2_ws/install/setup.bash` | `~/rb2/entorno.sh` | Las 5 | Cada integrante (tú) |
| `JETSON` | `<IP_JETSON>` | `~/rb2/entorno.sh` | Las 4 Raspberry | El profesor te dice la IP; tú la escribes |
| `hostnamectl set-hostname` | `pi-equipo1`, … | `/etc/hostname` | Cada Raspberry | Cada integrante |
| Cortafuegos (UDP) | `18150:18250` | `ufw` | Las 5 | Cada integrante, con permisos de `sudo` |
| Compilación del reto | `colcon build` en `~/rb2_ws` | `~/rb2_ws/` | Las 5 | Cada integrante |
| Repositorio de Git | `robotica_reto2` | `~/rb2/` | Las 5 | Una persona del equipo lo sube; los demás clonan |

### 0.1 · Por qué **nunca** escribimos en `~/.bashrc`

El Jetson del laboratorio tiene archivos que se ejecutan **automáticamente al
iniciar sesión** — scripts del curso que sourcean su propio workspace y fijan sus
variables. Por eso este equipo decidió:

1. **No tocar `~/.bashrc` en ninguna máquina.** Nada de `echo ... >> ~/.bashrc`,
   nada de `exec bash`.
2. El entorno se carga **a mano** en cada terminal con `source ~/rb2/entorno.sh`.
3. El driver y el kit del curso se dejan como los dejó el profesor.

**El único coste** es escribir `source ~/rb2/entorno.sh` al abrir cada terminal. Es
un `source` de 4 segundos. A cambio: si algo se rompe, no rompiste la sesión de
nadie, y puedes ver exactamente qué se cargó.

### 0.2 · Verificar qué ya se carga solo (Jetson, una vez)

Antes de escribir nada, mira qué hay puesto. Esto **no modifica** nada:

```bash
grep -nE 'source|export|exec' ~/.bashrc
```

```bash
# ¿Qué ve ROS 2 al entrar, sin que yo sourcee nada?
echo "dominio=$ROS_DOMAIN_ID  localhost=$ROS_LOCALHOST_ONLY  rwm=$RMW_IMPLEMENTATION"
ros2 pkg list | grep jetcobot
```

Qué hacer con lo que salga:

| Lo que ves | Qué haces |
|---|---|
| El dominio ya es `43` y el driver ya aparece | Perfecto. No toques nada del `.bashrc`. Solo crea `entorno.sh` (§A.1). |
| El dominio es `47` u otro número | El `.bashrc` trae el valor de otro equipo. **No lo borres**: tu `entorno.sh` lo pisa a `43` al hacer `source`. |
| `ros2 pkg list \| grep jetcobot` no da nada | El driver no está sourceado al entrar. Añade la línea del driver a `entorno.sh` (§A.1, paso 6). |
| `ros2: command not found` | ROS 2 no está sourceado. Añade su `source` a `entorno.sh` (§A.1, paso 5). |

---

# §1 · Las tres carpetas del Jetson (y por qué tu `src` va en una nueva)

Esta es la duda que más tiempo cuesta. En el Jetson conviven **tres** workspaces y
son cosas distintas.

```
/home/jetson/
├── jetcobot_colcon_ws/      ← EL DRIVER.  Del curso. NO se compila. NO se toca.
├── ros2_ws_brazo/           ← EL KIT.    Del curso. Compilado. Se sourcea, no se rebuilda.
└── rb2_ws/                  ← TU RETO.   Este. Tú lo creas y tú lo compilas.
    ├── src/
    │   ├── arm_broker_interfaces/   ← genera la acción MoveArm y el msg QueueState
    │   └── arm_broker/              ← el broker y el cliente (Python)
    ├── build/     ← generado por colcon, se puede borrar
    └── install/   ← generado por colcon, es lo que se sourcea
```

Y tu código fuente vive **fuera**, en un repo de Git:

```
/home/jetson/rb2/          ← el repo (clonado de GitHub)
├── src/                    ← el código que escribiste tú
├── herramientas/
├── analisis/
└── carga.csv
```

### 1.1 · Las reglas, sin excepciones

| Carpeta | ¿Se compila? | ¿Se toca? | Por qué |
|---|---|---|---|
| `jetcobot_colcon_ws` | **NUNCA** | **NUNCA** | Es el driver de tu equipo. Si rompes el build, la siguiente clase empieza con un problema que no es tuyo y no lo arregla nadie en el laboratorio. |
| `ros2_ws_brazo` | **NUNCA** | **NUNCA** | Mismo motivo: es el material del curso. |
| `rb2_ws` | **Sí, cada vez que cambies código** | Sí | Es tuyo. Aquí corre todo lo del reto. |
| `rb2` (el repo) | **NUNCA** | Sí | Es la fuente. Si compilas aquí, `build/` e `install/` ensucian el repo de GitHub. |

> **`colcon build` en `~/jetcobot_colcon_ws` es el error más caro del reto.**
> Si algo está mal, rompiste el driver. No hay vuelta atrás rápida.

### 1.2 · ¿Por qué copiar `src/` y no trabajar dentro del repo?

Porque `colcon build` ** siempre genera `build/` e `install/` en el workspace donde
lo ejecutas**. Si ejecutaras `colcon build` en `~/rb2`, esos dos folders aparecerían
dentro de tu repo de GitHub, y tendrías que acordarte de no subirlos cada vez que
haces `git add`.

La alternativa es copiar:

```bash
cp -r ~/rb2/src/* ~/rb2_ws/src/
```

El repo queda limpio y el workspace se puede tirar con `rm -rf ~/rb2_ws` sin miedo
a perder nada.

**El precio de esa comodidad** es un error silencioso, y por eso tiene su propia
sección: ver `errores_y_soluciones.md` §9 *"Corrés el código viejo y no te enterás"*.

### 1.3 · Descubrir cómo se llama la carpeta del driver

> Solo en el Jetson. Una vez.

```bash
ls -d ~/jetcobot_colcon_ws ~/ros2_ws_brazo 2>/dev/null
```

| Si aparece | Usa este nombre en todos los comandos |
|---|---|
| `jetcobot_colcon_ws` | `~/jetcobot_colcon_ws` |
| `ros2_ws_brazo` | `~/ros2_ws_brazo` |

Si no aparece ninguno:

```bash
ls -d ~/*ws* ~/*colcon* ~/*jetcobot* ~/*brazo* 2>/dev/null
```

Comprobación de que el driver está disponible **sin lanzarlo**:

```bash
source <CARPETA_DRIVER>/install/setup.bash
ros2 pkg list | grep jetcobot
```

Debe salir algo con `jetcobot` en el nombre. Si no sale, es del material del curso
y hay que hablar con el profesor.

---

# §A · Configuración (una sola vez por máquina)

## ▸ Orden

```
1. Jetson       → A.1     ┐
2. Raspberry 1  → A.2     │  Las cinco, en cualquier orden.
3. Raspberry 2  → A.3     │  Si ya están hechas, sáltatelas.
4. Raspberry 3  → A.4     │
5. Raspberry 4  → A.5     ┘
6. Las cinco comprobaciones → A.6
```

## ▸ Cuánto tarda

| Máquina | Tiempo aproximado |
|---|---|
| Jetson | 5–20 min. El `colcon build` inicial es el lento. |
| Raspberry 1–4 | 1–3 min cada una. Es el mismo CPU, pero sin el driver: compila en segundos. |

---

## A.1 · Jetson

> Once pasos. Repítelos **una sola vez**. Si ya lo hiciste, ve a §B.

**1. Entrar**

```bash
ssh jetson@<IP_JETSON>
```

**2. Traer el código**

```bash
cd ~
git clone https://github.com/rGsmueL/robotica_reto2.git rb2
cd rb2
ls
```

> **Qué debes ver:** `src`, `analisis`, `herramientas`. Si solo ves `src`, el clon
> se hizo a medias: `rm -rf ~/rb2` y vuelve a intentarlo.

**3. Crear el workspace del reto y copiar `src/`**

```bash
mkdir -p ~/rb2_ws/src
cp -r ~/rb2/src/* ~/rb2_ws/src/
ls ~/rb2_ws/src
```

> **Qué debes ver:** `arm_broker` y `arm_broker_interfaces`.
> Lo que **no** debe aparecer: `__pycache__` ni `.pyc`. Si aparecen, son basura de
> Windows versionada en el repo (ver `archivos_a_modificar.md` §7).

**4. Compilar**

```bash
cd ~/rb2_ws
colcon build
```

> **Qué debes ver:**
> ```
> Starting >>> arm_broker_interfaces
> Finished <<< arm_broker_interfaces [12.4s]
> Starting >>> arm_broker
> Finished <<< arm_broker [0.8s]
>
> Summary: 2 packages finished
> ```

Si ves `Failed <<<`:

```bash
cat ~/rb2_ws/log/latest_build/*/stderr.log | tail -40
```

**5. Verificar que compiló**

```bash
source ~/rb2_ws/install/setup.bash
ros2 pkg list | grep arm_broker
ros2 interface show arm_broker_interfaces/action/MoveArm
```

> **Qué debes ver:** los dos paquetes, y la definición de la acción:
> ```
> float64[] joint_positions
> string    client_id
> uint8     priority
> ---
> bool     success
> string   message
> float64  wait_time_s
> float64  exec_time_s
> ---
> string   state
> int32    queue_position
> float64  elapsed_s
> ```

> **Este paso es el más importante de la configuración.** Si `ros2 interface show`
> imprime algo, la acción se generó y se registró en ROS 2. Ese es el puente entre
> el broker y los clientes. Sin esto, el cliente arranca y dice
> `El broker no aparece. ¿Está corriendo?` — aunque el broker esté corriendo y
> perfecto. Explicación en `errores_y_soluciones.md` §6.

**6. Crear tu archivo de entorno**

Este es el archivo que reemplaza al `.bashrc`. En el Jetson:

```bash
cat > ~/rb2/entorno.sh <<'FIN'
# Entorno del Reto 2 - Equipo 1.  Se carga a mano:  source ~/rb2/entorno.sh
# NO va en .bashrc: en el Jetson hay archivos que se ejecutan al iniciar sesion.
export ROS_DOMAIN_ID=43
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export JETSON=<IP_JETSON>

source /opt/ros/humble/setup.bash
source ~/rb2_ws/install/setup.bash

# El driver. Solo existe en el Jetson; si la carpeta no esta, esta linea
# no hace nada. En las Raspberry este bloque tambien es inofensivo.
for d in ~/jetcobot_colcon_ws ~/ros2_ws_brazo; do
  if [ -f "$d/install/setup.bash" ]; then
    source "$d/install/setup.bash"
  fi
done
FIN
```

> **Ojo:** `<IP_JETSON>` es texto literal. Reemplázalo por la IP real de tu equipo
> antes de dar `Enter`. La línea `export JETSON=<IP_JETSON>` solo la usan
> `herramientas/verificar_fk.py` y los scripts del curso.

**7. Probar el entorno**

```bash
source ~/rb2/entorno.sh
echo "dominio=$ROS_DOMAIN_ID  localhost=$ROS_LOCALHOST_ONLY  rwm=$RMW_IMPLEMENTATION"
ros2 pkg list | grep -E 'arm_broker|jetcobot'
```

> **Qué debes ver:** `dominio=43  localhost=0  rwm=rmw_fastrtps_cpp`, y al menos
> `arm_broker`. Si el driver no sale, avisaste: el bloque del `for` lo sourcea
> solo.

**8. Reiniciar el demonio de ROS**

```bash
ros2 daemon stop
ros2 daemon start
```

> El demonio guarda en memoria la configuración con la que arrancó. Si cambiaste
> el dominio y no lo reinicias, `ros2 node list` te sigue enseñando la lista
> vieja. Es la causa número uno de "lo configuré y no funciona".

**9. Poner nombre a la máquina** *(opcional pero recomendado)*

```bash
hostnamectl set-hostname jetson-equipo1
hostname
```

**10. Verificar la FK contra el brazo** *(solo cuando el driver esté apagado)*

```bash
pip install pymycobot
cd ~/rb2
source ~/rb2/entorno.sh
python3 herramientas/verificar_fk.py
```

> **Qué debes ver:** una tabla `pose | FK (x,y,z) | robot (x,y,z) | error`, y
> **error ≤ 10 mm**. Ese es el criterio del ítem 1.
>
> **No lo corras con el driver andando:** los dos abrirían `/dev/ttyUSB0` y el
> segundo recibe un error. Apaga el driver primero (Ctrl+C en T1).

**11. Congelar la tabla DH**

Anota en tu README: *"La tabla DH verificada es la del commit `XXXX` y no se
modifica después de esa fecha."* A partir de ahí no toques `src/arm_broker/arm_broker/fk.py`.

> **Por qué antes de generar la carga:** `generar_carga.py` llama a `fk`, y `fk` usa
> la tabla DH. Si cambias la tabla después, cambian las poses de `carga.csv`, y las
> dos corridas del ítem 3 dejan de ser comparables.

---

## A.2 · Raspberry 1

> Mismos 8 pasos que A.1, **menos** el driver. Es exactamente lo mismo en las
> cuatro Raspberry; aquí está la Raspberry 1.

**1. Entrar**

```bash
ssh <USUARIO_PI>@<IP_RASPBERRY_1>
```

**2. Comprobar que tienes IP del laboratorio**

```bash
ip -4 addr show scope global
```

> **Qué debes ver:** una dirección tipo `172.51.9.30`. Si empieza por `169.254`, no
> recibió dirección: revisa el cable o la WiFi antes de seguir.

**3. Traer el código**

```bash
cd ~
git clone https://github.com/rGsmueL/robotica_reto2.git rb2
cd rb2
ls
```

**4. Crear el workspace y copiar `src/`**

```bash
mkdir -p ~/rb2_ws/src
cp -r ~/rb2/src/* ~/rb2_ws/src/
ls ~/rb2_ws/src
```

> **Qué debes ver:** `arm_broker` y `arm_broker_interfaces`.
> La Raspberry **no necesita** el driver. El driver vive en el Jetson.

**5. Compilar**

```bash
cd ~/rb2_ws
colcon build
```

> **Qué debes ver:** `Summary: 2 packages finished`. Tarda **segundos**, no los 20
> minutos del Jetson.

**6. Verificar**

```bash
source ~/rb2_ws/install/setup.bash
ros2 pkg list | grep arm_broker
ros2 interface show arm_broker_interfaces/action/MoveArm
```

**7. Crear tu archivo de entorno**

Idéntico al del Jetson (paso 6 de A.1), y funciona igual aunque no tengas driver:

```bash
cat > ~/rb2/entorno.sh <<'FIN'
# Entorno del Reto 2 - Equipo 1.  Se carga a mano:  source ~/rb2/entorno.sh
# NO va en .bashrc: hay archivos que se ejecutan al iniciar sesion.
export ROS_DOMAIN_ID=43
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export JETSON=<IP_JETSON>

source /opt/ros/humble/setup.bash
source ~/rb2_ws/install/setup.bash

for d in ~/jetcobot_colcon_ws ~/ros2_ws_brazo; do
  if [ -f "$d/install/setup.bash" ]; then
    source "$d/install/setup.bash"
  fi
done
FIN
```

**8. Probarlo y reiniciar el demonio**

```bash
source ~/rb2/entorno.sh
echo "dominio=$ROS_DOMAIN_ID  localhost=$ROS_LOCALHOST_ONLY"
ros2 daemon stop
ros2 daemon start
```

**9. Poner nombre a la máquina**

```bash
sudo hostnamectl set-hostname pi-equipo1-uno
hostname
```

**10. Cortafuegos**

```bash
sudo ufw status
```

> Si dice `Status: active`, hay que abrir los puertos del dominio 43
> (18150–18250). Ver `errores_y_soluciones.md` §3.

---

## A.3 · Raspberry 2

Idéntico a A.2. Lo único que cambia:

**1. Entrar**

```bash
ssh <USUARIO_PI>@<IP_RASPBERRY_2>
```

**2. Los mismos pasos 2 a 8** — clonar, crear `~/rb2_ws`, copiar, compilar,
verificar, crear `entorno.sh`, probarlo, reiniciar el demonio. Sin cambios.

**3. Nombre de la máquina**

```bash
sudo hostnamectl set-hostname pi-equipo1-dos
hostname
```

**4. Lo que va a ser distinto en §B**

Este equipo se identifica en la telemetría como `equipo1-pi2`, con prioridad `3`.

---

## A.4 · Raspberry 3

Idéntico a A.2. Lo único que cambia:

**1. Entrar**

```bash
ssh <USUARIO_PI>@<IP_RASPBERRY_3>
```

**2. Los mismos pasos 2 a 8.** Sin cambios.

**3. Nombre de la máquina**

```bash
sudo hostnamectl set-hostname pi-equipo1-tres
hostname
```

**4. Lo que va a ser distinto en §B**

`client_id:=equipo1-pi3`, con prioridad `2`.

---

## A.5 · Raspberry 4

Idéntico a A.2. Lo único que cambia:

**1. Entrar**

```bash
ssh <USUARIO_PI>@<IP_RASPBERRY_4>
```

**2. Los mismos pasos 2 a 8.** Sin cambios.

**3. Nombre de la máquina**

```bash
sudo hostnamectl set-hostname pi-equipo1-cuatro
hostname
```

**4. Lo que va a ser distinto en §B**

`client_id:=equipo1-pi4`, con prioridad `1`.

---

## A.6 · Las cinco comprobaciones, en las cinco máquinas

> Cuando las cinco estén configuradas, hacé estas cinco comprobaciones **en las
> cinco**. Todas tienen que dar lo mismo. Es el momento de descubrir un problema,
> no en plena sustentación.

| # | En qué máquina | Comando | Qué debe salir |
|---|---|---|---|
| 1 | Las 5 | `echo $ROS_DOMAIN_ID` | `43` en todas |
| 2 | Las 5 | `ros2 pkg list \| grep arm_broker` | `arm_broker` y `arm_broker_interfaces` |
| 3 | Las 4 Raspberry | `ping -c 3 <IP_JETSON>` | `3 packets transmitted, 3 received` |
| 4 | Jetson | `ros2 node list` | `/rosout` y `/parameter_events` (los propios) |
| 5 | Jetson, driver andando | `ros2 topic info /joint_states -v` | `Publisher count: 1`, `Subscription count: 1` |

La comprobación 5 es la que importa: **un publicador, un suscriptor**. El broker
publica, el driver se suscribe. Si hay más de un publicador, se anulan 5 puntos del
ítem 2.

---

# §B · Comandos para hacer los retos

## B.0 · Mapa de terminales

> **La corrección más importante de este documento:** los cuatro procesos pesados
> —driver, broker, grabadora y post-proceso— **corren todos en el Jetson**. No es
> que "una Raspberry abra cuatro terminales": es que **el Jetson** tiene cuatro
> terminales, y **cada Raspberry tiene una sola**, con su cliente.

| Terminal | ¿En qué máquina? | ¿Qué corre? | ¿Cuándo? |
|---|---|---|---|
| **T1** | Jetson | El driver `sync_plan_nx` | Siempre |
| **T2** | Jetson | El broker, con `tee` al log | Siempre |
| **T3** | Jetson | Telemetría (`ros2 topic echo`) | Siempre |
| **T4** | Jetson | La grabadora (`ros2 bag record`) | Solo ítem 3 |
| **T5** | Raspberry 1 | El cliente `equipo1-pi1` | Pruebas e ítem 3 |
| **T6** | Raspberry 2 | El cliente `equipo1-pi2` | Pruebas e ítem 3 |
| **T7** | Raspberry 3 | El cliente `equipo1-pi3` | Pruebas e ítem 3 |
| **T8** | Raspberry 4 | El cliente `equipo1-pi4` | Pruebas e ítem 3 |

**Por qué el broker va en el Jetson y no en una Raspberry:** el broker publica en
`/joint_states` **diez veces por movimiento** (10 pasos de interpolación). Si el
broker estuviera en una Raspberry, cada uno de esos mensajes cruzaría la red antes
de llegar al driver. El driver está a un centímetro del cable del brazo; el broker
tiene que estarlo también.

### Las cuatro terminales del Jetson

Abrí **cuatro sesiones SSH** desde tu PC, todas a `<IP_JETSON>`. Cada una es una
terminal. En todas:

```bash
source ~/rb2/entorno.sh
```

Si preferís una sola sesión física, usá `tmux` (B.10).

### En cada Raspberry

Una sola terminal. En ella:

```bash
source ~/rb2/entorno.sh
```

---

## B.1 · Jetson · T1 — el driver

```bash
source ~/rb2/entorno.sh
ros2 run jetcobot_driver sync_plan_nx
```

> **Qué debes ver:** nada, o escasas líneas de log. **Eso es normal.** El driver
> está esperando órdenes y **no vuelve al prompt**. Lo correcto es eso.

> **Solo una persona levanta el driver.** El puerto serie es único: si dos lo
> abren, el segundo recibe un error.

> **Antes de la primera pose: despeja el espacio alrededor del brazo y avisa en voz
> alta.** El driver no avisa.

---

## B.2 · Jetson · T2 — el broker

**Prueba rápida** (política por defecto, FIFO):

```bash
source ~/rb2/entorno.sh
ros2 run arm_broker broker --ros-args -p politica:=fifo 2>&1 | tee ~/rb2/rechazos_fifo.log
```

**Para la corrida del ítem 3** (la otra política, round-robin):

```bash
source ~/rb2/entorno.sh
ros2 run arm_broker broker --ros-args -p politica:=prioridad 2>&1 | tee ~/rb2/rechazos_rr.log
```

> **Qué debes ver:**
> ```
> [INFO] [arm_broker]: arm_broker listo · política=fifo · cola_max=20 · único publicador de /joint_states
> ```
> Y se queda corriendo, sin volver al prompt.

**Sobre `2>&1 | tee ~/rb2/rechazos_*.log`:** ese pipe guarda en un archivo todo lo
que el broker escribe, **incluidos los rechazos con su motivo**. Ese log **es** un
entregable del ítem 2. Sin el `tee`, al cerrar la terminal lo perdés.

**Sobre `-p politica:=prioridad`:** el nombre dice "prioridad" pero por dentro es
**round-robin**. No es un error de nombre: el `broker.py` del andamiaje solo
distingue ese caso y le pasa el parámetro `tau` de envejecimiento. Está
implementado así y funciona. Si te preguntan en la sustentación, esa es la
respuesta. Ver `src/arm_broker/arm_broker/politicas.py:112`.

### Los parámetros del broker

Cambiables sin tocar código:

```bash
# Cola de 30 en vez de 20, movimientos de 5 segundos, 20 pasos de interpolación
ros2 run arm_broker broker --ros-args \
  -p politica:=fifo -p cola_max:=30 -p duracion_movimiento_s:=5.0 -p pasos_interpolacion:=20
```

| Parámetro | Por defecto | Qué hace |
|---|---|---|
| `politica` | `fifo` | `fifo` o `prioridad` (= round-robin) |
| `tau_envejecimiento_s` | `8.0` | Solo lo recibe `prioridad`; round-robin no lo usa |
| `cola_max` | `20` | Máximo de pedidos esperando. Llenarse **rechaza** |
| `paso_max_rad` | `1.2` | Máximo salto articular desde la pose actual. Excederlo **rechaza** |
| `duracion_movimiento_s` | `3.0` | Duración de cada movimiento |
| `pasos_interpolacion` | `10` | Puntos por los que se publica `/joint_states` |

---

## B.3 · Jetson · T3 — la telemetría

```bash
source ~/rb2/entorno.sh
ros2 topic echo /arm/queue_state
```

> **Qué debes ver ahora mismo, con el broker recién arrancado:**
> ```
> stamp: ...
> executing_client: ''
> executing_goal_id: ''
> executing_elapsed_s: 0.0
> queue_length: 0
> queued_goal_ids: []
> total_accepted: 0
> total_rejected: 0
> total_completed: 0
> ```

**Es normal que esté vacía.** El broker publica cada 0.2 s, pero nadie pidió nada
todavía. Si no sale nada, el problema está en T2: el broker no arrancó.

Una sola línea, para mirar sin inundar la pantalla:

```bash
ros2 topic echo /arm/queue_state --once
```

---

## B.4 · Jetson · T4 — la grabadora (solo ítem 3)

```bash
source ~/rb2/entorno.sh
ros2 bag record -o ~/rb2/bag_fifo /arm/queue_state /joint_states
```

> **Grabá los dos tópicos.** Con solo `/joint_states` no hay métricas:
> `exportar_csv.py` te avisa. Y `/arm/queue_state` es el que dice **quién esperó
> cuánto**, que es justo lo que se mide.

> **La carpeta del bag no importa para el nombre de la figura.** Ese nombre sale de
> la carpeta de `--salida` del export, no del bag. Ver `cambios_angulos.md` §B.6.

Se corta con `Ctrl+C`. **Esperá a que el último cliente termine** antes de cortar.

---

## B.5 · Jetson — post-proceso y entregables

> Todas estas van **después** de la corrida, con el broker y el driver parados.
> Desde `~/rb2`, el repo.

**Verificar que solo hay un publicador:**

```bash
source ~/rb2/entorno.sh
ros2 topic info /joint_states -v
```

> **Qué debes ver:** `Publisher count: 1`, `Subscription count: 1`.
> Si dice más de uno, se anulan 5 puntos del ítem 2.

**Exportar los bags a CSV:**

```bash
cd ~/rb2
source ~/rb2/entorno.sh
python3 analisis/exportar_csv.py bag_fifo --salida fifo/
python3 analisis/exportar_csv.py bag_rr  --salida roundrobin/
```

> **Qué debes ver**, para cada bag:
> ```
> Tópicos en el bag:
>   /arm/queue_state  (arm_broker_interfaces/msg/QueueState)
>   /joint_states  (sensor_msgs/msg/JointState)
>
> queue_state.csv   2400 filas
> joint_states.csv  1600 filas
> ```
>
> **El nombre de la carpeta de `--salida` es el nombre de la figura.** Sacada a
> `prioridad/`, la figura diría "prioridad" y nadie sabría que mediste round-robin.
> Por eso `fifo/` y `roundrobin/`.

**Calcular las métricas y la figura:**

```bash
python3 analisis/metricas.py fifo/queue_state.csv roundrobin/queue_state.csv
```

> **Qué debes ver:** los dos bloques con `espera media`, `espera p95`, `espera
> máxima`, el desglose `por prioridad`, el `índice de inanición`, `goals por
> cliente` y la `equidad de Jain`. Y al final:
> ```
> Figura: comparacion_politicas.png
> ```
> Los números **no van a ser esos** (son un ejemplo de formato). La estructura sí.

**Si dice "Sin matplotlib":**

```bash
sudo apt install -y python3-matplotlib
```

**Verificar la FK** (de nuevo, con el driver apagado y el puerto libre):

```bash
python3 herramientas/verificar_fk.py
```

---

## B.6 · Raspberry 1 — el cliente

```bash
source ~/rb2/entorno.sh
ros2 run arm_broker cliente --ros-args \
  -p client_id:=equipo1-pi1 -p priority:=4
```

> **Qué debes ver:**
> ```
> [equipo1-pi1] esperando al broker...
> [equipo1-pi1] QUEUED pos=2 t=0.3s
> [equipo1-pi1] pose 0: success=True espera=4.2s ejec=3.0s total=7.4s — pose alcanzada en 10 pasos
> ```

**Qué significa cada parte:**

| Parte | Qué es |
|---|---|
| `QUEUED pos=2` | Este pedido está en la posición 2 de la fila |
| `success=True` | Se ejecutó bien |
| `espera=4.2s` | Lo que estuvo **en la fila**. **Esta es la métrica del ítem 3** |
| `ejec=3.0s` | Lo que tardó **moviéndose**. Debería ser siempre ~3.0 |
| `total=7.4s` | Espera + ejecución + pausa |

> **Si `ejec` no es ~3.0, algo se movió dos veces.** Avisa al equipo.

Con la carga completa del ítem 3:

```bash
ros2 run arm_broker cliente --ros-args \
  -p client_id:=equipo1-pi1 -p priority:=4 \
  -p traza:=~/rb2/carga.csv -p repeticiones:=1 -p pausa_s:=0.5
```

---

## B.7 · Raspberry 2 — el cliente

```bash
source ~/rb2/entorno.sh
ros2 run arm_broker cliente --ros-args \
  -p client_id:=equipo1-pi2 -p priority:=3
```

Con la carga:

```bash
ros2 run arm_broker cliente --ros-args \
  -p client_id:=equipo1-pi2 -p priority:=3 \
  -p traza:=~/rb2/carga.csv -p repeticiones:=1 -p pausa_s:=0.5
```

---

## B.8 · Raspberry 3 — el cliente

```bash
source ~/rb2/entorno.sh
ros2 run arm_broker cliente --ros-args \
  -p client_id:=equipo1-pi3 -p priority:=2
```

Con la carga:

```bash
ros2 run arm_broker cliente --ros-args \
  -p client_id:=equipo1-pi3 -p priority:=2 \
  -p traza:=~/rb2/carga.csv -p repeticiones:=1 -p pausa_s:=0.5
```

---

## B.9 · Raspberry 4 — el cliente

```bash
source ~/rb2/entorno.sh
ros2 run arm_broker cliente --ros-args \
  -p client_id:=equipo1-pi4 -p priority:=1
```

Con la carga:

```bash
ros2 run arm_broker cliente --ros-args \
  -p client_id:=equipo1-pi4 -p priority:=1 \
  -p traza:=~/rb2/carga.csv -p repeticiones:=1 -p pausa_s:=0.5
```

### Los cuatro a la vez

Lanzá los cuatro **dentro de un margen de unos segundos**, en las cuatro máquinas a
la vez. Esa simultaneidad es justo lo que genera la contención que mide el ítem 3.
Si los lanzás de a uno, no hay cola y no hay nada que medir.

### Tabla de los cuatro clientes

| Raspberry | `client_id` | `priority` | `hostnamectl` |
|---|---|---|---|
| 1 | `equipo1-pi1` | `4` | `pi-equipo1-uno` |
| 2 | `equipo1-pi2` | `3` | `pi-equipo1-dos` |
| 3 | `equipo1-pi3` | `2` | `pi-equipo1-tres` |
| 4 | `equipo1-pi4` | `1` | `pi-equipo1-cuatro` |

Todos los `client_id` distintos: si dos coinciden, la telemetría no los
distingue. **Prioridades distintas** (mayor = más urgente) para que la comparación
de políticas tenga contenido.

### Los parámetros del cliente

| Parámetro | Por defecto | Qué hace |
|---|---|---|
| `client_id` | `alumno` | Tu nombre en la telemetría y en el log |
| `priority` | `1` | 0–255, **mayor = más urgente** |
| `traza` | `''` | Ruta al CSV de poses. Vacío = 2 poses por defecto |
| `repeticiones` | `1` | Cuántas veces repite la traza |
| `pausa_s` | `0.5` | Pausa entre poses |

> **Sobre `priority` y round-robin:** tu `politicas.py` implementa round-robin, que
> reparte **por cliente** e **ignora el número de prioridad**. Con prioridades
> distintas el resultado medido va a ser round-robin igual. No pasa nada: solo
> tené que saberlo cuando lo expliques.

---

## B.10 · tmux en el Jetson (recomendado para el ítem 3)

> Las corridas duran ~8 minutos. Si se cae el WiFi con el broker en una SSH normal,
> perdiste todo. Con `tmux` no.

```bash
# Instalar (una vez)
sudo apt install -y tmux
```

```bash
# En el Jetson
tmux new -s rb2          # creas una sesión con 4 ventanas
```

| Atajo | Qué hace |
|---|---|
| `Ctrl+B` y después `%` | Divide verticalmente (otra ventana al lado) |
| `Ctrl+B` y después `"` | Divide horizontalmente (otra ventana arriba) |
| `Ctrl+B` y después flecha | Te movés entre ventanas |
| `Ctrl+B` y después `d` | Salís de tmux sin detener nada |
| `tmux attach -t rb2` | Volvés a entrar |

Creá 4 ventanas con `Ctrl+B %` tres veces, y en cada una `source ~/rb2/entorno.sh`.

---

## B.11 · Probar los tres rechazos (3 de los 8 puntos del ítem 2)

> **Hacé esto con el broker recién arrancado.** Los rechazos por paso articular y
> por workspace dependen de la pose actual del brazo, y al arrancar es
> `q = 0,0,0,0,0,0`. Si lo probás después de que se mueva, el motivo puede ser otro.

En **T3**, cortá el `echo` con `Ctrl+C` primero. Después mandá los tres goals, uno
por uno.

**a) Fuera de límites articulares** — pedís 3.5, el tope es 2.93:

```bash
ros2 action send_goal /move_arm arm_broker_interfaces/action/MoveArm \
  "{joint_positions: [3.5, 0.0, 0.0, 0.0, 0.0, 0.0], client_id: 'prueba', priority: 1}"
```

> **En `~/rb2/rechazos_fifo.log` (T2):**
> ```
> RECHAZADO [prueba p1] · limites articulares: 1_Joint fuera de rango: 3.500 rad, límite [-2.93, 2.93]
> ```

**b) Paso articular excesivo** — pedís 1.3, el tope es 1.2:

```bash
ros2 action send_goal /move_arm arm_broker_interfaces/action/MoveArm \
  "{joint_positions: [1.3, 0.0, 0.0, 0.0, 0.0, 0.0], client_id: 'prueba', priority: 1}"
```

> **En el log:**
> ```
> RECHAZADO [prueba p1] · paso articular excesivo: 1.30 rad desde la pose actual, maximo 1.20 rad
> ```

**c) Fuera del workspace** — el efector cae a 71 mm, el mínimo es 80:

```bash
ros2 action send_goal /move_arm arm_broker_interfaces/action/MoveArm \
  "{joint_positions: [0.0, 1.5, 2.4, 0.0, 0.0, 0.0], client_id: 'prueba', priority: 1}"
```

> **En el log:**
> ```
> RECHAZADO [prueba p1] · workspace: efector a 71 mm de la base, demasiado cerca
> ```

Esos tres textos están **verificados contra tu `fk.py`**. Si al probarlos no sale
exactamente eso, el brazo ya se movió: reiniciá el broker y probá de nuevo.

**Una pose que sí tiene que ser aceptada** (para ver el camino feliz):

```bash
ros2 action send_goal /move_arm arm_broker_interfaces/action/MoveArm \
  "{joint_positions: [0.0, -0.5, 0.5, 0.0, 0.5, 0.0], client_id: 'prueba', priority: 1}"
```

> **Qué debes ver:** el log dice `pose alcanzada en 10 pasos` y, en T3,
> `total_completed` sube a 1.

> **`ros2 action send_goal` es para pruebas de rechazo.** Para las corridas medidas
> usá los clientes de B.6–B.9: son los que llenan las métricas por cliente con
> nombres reconocibles.

---

## B.12 · Las dos corridas del ítem 3

### Paso 0 · Generar la carga (una sola vez, en el Jetson)

**Antes:** la tabla DH tiene que estar congelada (A.1, paso 11).

```bash
cd ~/rb2
source ~/rb2/entorno.sh
python3 herramientas/generar_carga.py --n 40 --semilla 7 --salida carga.csv
```

> **Qué debes ver:** `40 poses alcanzables en carga.csv (semilla 7)`
>
> **La semilla es lo importante.** La misma semilla = el mismo archivo. Sin eso, las
> dos corridas no son comparables.

### Paso 1 · Llevar la carga a las cuatro Raspberry

```bash
# En el Jetson, desde ~/rb2
git add carga.csv
git commit -m "carga oficial: 40 poses, semilla 7"
git push
```

```bash
# En cada Raspberry
cd ~/rb2
git pull
ls -l carga.csv
md5sum carga.csv
```

> **Los cuatro `md5sum` tienen que dar el mismo hash.** Si no, cada cliente está
> mandando poses distintas y la comparación de métricas es basura.

### Paso 2 · Corrida 1 — FIFO

Lanzá en este orden:

| Orden | Máquina | Comando |
|---|---|---|
| 1º | Jetson T1 | `ros2 run jetcobot_driver sync_plan_nx` |
| 2º | Jetson T4 | `ros2 bag record -o ~/rb2/bag_fifo /arm/queue_state /joint_states` |
| 3º | Jetson T2 | `ros2 run arm_broker broker --ros-args -p politica:=fifo 2>&1 \| tee ~/rb2/rechazos_fifo.log` |
| 4º | Jetson T3 | `ros2 topic echo /arm/queue_state` |
| 5º | Las 4 Raspberry | Los cuatro clientes de B.6–B.9, **con `-p traza:=~/rb2/carga.csv`** |

> **El grabador va antes que el broker.** Si lo levantás después, te perdés los
> primeros mensajes.

### Paso 3 · Qué esperar durante la corrida

| Tiempo | Qué pasa |
|---|---|
| 0 s | Los cuatro mandan su primer goal casi al mismo tiempo |
| ~1 s | Uno ejecutando, tres en la fila. **Este es el momento del reto** |
| 0–8 min | 160 goals en total, uno cada 3 segundos |
| ~8 min | El último cliente termina |

| Dato | Valor esperado |
|---|---|
| Goals totales | 160 (40 poses × 4 clientes) |
| Duración | ~8 minutos |
| Mensajes de `/arm/queue_state` | ~2400 |
| Tamaño del bag | Pocos MB |

Lo que tiene que verse en T3:

```
executing_client: equipo1-pi1
executing_goal_id: a1b2c3d4e5f6
queue_length: 3
queued_clients: [equipo1-pi2, equipo1-pi3, equipo1-pi4]
queued_wait_s: [2.1, 4.5, 6.8]
total_accepted: 47
total_rejected: 2
total_completed: 44
```

`queued_wait_s` **va creciendo** en cada elemento mientras esperan. Si no crece, el
broker no está midiendo el tiempo.

Cuando termine el último cliente: `Ctrl+C` en T4 (grabadora), después en T2
(broker), después en T1 (driver).

### Paso 4 · Corrida 2 — round-robin

**Exactamente lo mismo, cambiando una sola cosa:**

| | Corrida 1 | Corrida 2 |
|---|---|---|
| Parámetro | `-p politica:=fifo` | `-p politica:=prioridad` |
| Carpeta del bag | `~/rb2/bag_fifo` | `~/rb2/bag_rr` |
| Log de rechazos | `rechazos_fifo.log` | `rechazos_rr.log` |
| La carga | `carga.csv` | **La misma** `carga.csv` |
| Los 4 clientes | iguales | **Exactamente iguales** |

### Paso 5 · Exportar y medir

```bash
cd ~/rb2
source ~/rb2/entorno.sh
python3 analisis/exportar_csv.py bag_fifo --salida fifo/
python3 analisis/exportar_csv.py bag_rr  --salida roundrobin/
python3 analisis/metricas.py fifo/queue_state.csv roundrobin/queue_state.csv
```

### Paso 6 · Lo que queda en el disco

```
~/rb2/
├── carga.csv
├── rechazos_fifo.log          ← registro de rechazos con motivo (ítem 2)
├── rechazos_rr.log
├── bag_fifo/                  ← bag crudo (súbelo a GitHub)
├── bag_rr/
├── fifo/
│   ├── queue_state.csv        ← las métricas del ítem 3
│   └── joint_states.csv
├── roundrobin/
│   ├── queue_state.csv
│   └── joint_states.csv
└── comparacion_politicas.png  ← la figura del ítem 3
```

```bash
# Subir los resultados al repo
cd ~/rb2
git add carga.csv rechazos_fifo.log rechazos_rr.log fifo/ roundrobin/ comparacion_politicas.png
git commit -m "resultados: corrida FIFO y round-robin, equipo 1"
git push
```

### Paso 7 · La conclusión (esto lo escribís vos)

Ningún script redacta esto, y es lo que pide la rúbrica. Cuatro cosas:

| # | Qué escribir |
|---|---|
| 1 | Los números de las dos corridas, tal como los imprimió `metricas.py` |
| 2 | **Cuál gana en qué métrica**: p95, inanición, Jain |
| 3 | **Por qué** |
| 4 | El matiz honesto: cuándo gana round-robin y cuándo no |

El punto central, que es lo que busca el docente:

> Round-robin **garantiza alternancia, no conteo igual**. Con servicios parecidos el
> Jain sube; con servicios muy desiguales el cliente rápido acumula turnos
> legítimamente y el Jain **puede bajar**.

Presentar round-robin como mejor en todo es un error. Explicá **cuándo** gana y
**cuándo** empata o pierde.

---

# §C · Resumen de una pantalla

**En cada terminal nueva, en cualquier máquina:**

```bash
source ~/rb2/entorno.sh
```

**Jetson:**

| Terminal | Comando |
|---|---|
| T1 driver | `ros2 run jetcobot_driver sync_plan_nx` |
| T2 broker | `ros2 run arm_broker broker --ros-args -p politica:=fifo 2>&1 \| tee ~/rb2/rechazos_fifo.log` |
| T3 telemetría | `ros2 topic echo /arm/queue_state` |
| T4 bag | `ros2 bag record -o ~/rb2/bag_fifo /arm/queue_state /joint_states` |

**Cada Raspberry, una terminal:**

```bash
ros2 run arm_broker cliente --ros-args \
  -p client_id:=equipo1-pi<N> -p priority:=<PRIORIDAD> -p traza:=~/rb2/carga.csv
```

**Después de la corrida, en el Jetson:**

```bash
cd ~/rb2
python3 analisis/exportar_csv.py bag_fifo --salida fifo/
python3 analisis/metricas.py fifo/queue_state.csv roundrobin/queue_state.csv
```

**Nunca:**

```bash
colcon build  ~/jetcobot_colcon_ws    # rompe el driver
colcon build  ~/ros2_ws_brazo         # rompe el kit del curso
colcon build  ~/rb2                   # ensucia el repo
echo '...' >> ~/.bashrc               # hay archivos que se ejecutan al entrar
```
