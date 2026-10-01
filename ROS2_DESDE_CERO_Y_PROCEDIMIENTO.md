# ROS 2 desde cero, y el procedimiento completo del Reto 2

Manual para quien viene de trabajar en Jupyter y ahora tiene que hacer correr seis
procesos que se hablan entre sí, en cinco máquinas distintas.

**No necesitas aprender ROS 2 entero.** Necesitas entender cuatro cosas (la
parte A) y después seguir un procedimiento (la parte B). La parte C es para
consultar cuando algo falla.

> **Antes de empezar, una nota sobre el dominio.** Este documento usa
> `ROS_DOMAIN_ID=47`, que es `42 + 5` (grupo 5). Si el docente te dio otro
> número, **cambia ese 47 en los 5 sitios donde aparece**.

---

## Índice

### Parte A · Entender (lo mínimo, para no perderte)

| # | Sección |
|---|---|
| A1 | Jupyter vs ROS 2: la tabla que te destraba |
| A2 | El vocabulario mínimo, con quién es en tu reto |
| A3 | Los seis procesos de tu reto |
| A4 | Qué es un workspace y por qué existe |

### Parte B · El procedimiento, paso a paso

| # | Paso | En qué máquina |
|---|---|---|
| B1 | Crear el repo en GitHub y subir el código | Tu PC (Windows) |
| B2 | Clonar y compilar en el Jetson | Jetson |
| B3 | Descubrir el nombre de la carpeta del driver | Jetson |
| B4 | Clonar y compilar en las 4 Raspberry | Raspberry × 4 |
| B5 | Configurar las variables de entorno | Las 5 |
| B6 | Las 5 comprobaciones, en orden | Las 5 |
| B7 | **Ítem 2**: correr el broker y probarlo | Las 5 |
| B8 | **Ítem 3**: las dos corridas medidas | Jetson + las 4 Pi |
| B9 | Los resultados finales: qué queda en tu disco | Jetson |

### Parte C · Referencia rápida

| # | Sección |
|---|---|
| C1 | En vez de `print`, usa esto |
| C2 | Cheat sheet de comandos |
| C3 | Errores frecuentes, explicados |

---

# PARTE A · Entender

## A1 · Jupyter vs ROS 2: la tabla que te destraba

Tu experiencia en el Reto 1 era esta:

```
┌──────────────────────────────────────────┐
│  Jupyter                                  │
│                                          │
│  [celda 1]  import numpy                 │
│  [celda 2]  q = calcular_efector(...)    │   ← las variables viven
│  [celda 3]  print(fk(q))                 │     en el kernel y
│                                          │     siguen vivas
│  Un solo proceso. Un solo "cerebro".     │
│  El ORDEN importa: de arriba abajo.      │
└──────────────────────────────────────────┘
```

En ROS 2 es distinto. Cada cosa que corre es **un programa independiente**, con
su memoria propia, y no pueden leer las variables del otro. Para comunicarse
tienen que **mandarse mensajes por canales con nombre**.

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ proceso  │  │ proceso  │  │ proceso  │  │ proceso  │  │ proceso  │  │ proceso  │
│  driver  │  │  broker  │  │ cliente1 │  │ cliente2 │  │ cliente3 │  │ cliente4 │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │            │            │            │            │            │
     └────────────┴──────┬─────┴────────────┴────────────┴────────────┘
                         │
              ¿cómo se habla esto?
              mensajes por canales con nombre:
              "tópicos" y "acciones"
```

### La tabla de traducción

| En Jupyter | En ROS 2 | Qué debes hacer |
|---|---|---|
| Una celda que corres con "Run" | Un **nodo**: un programa aparte | Lo lanzas con `ros2 run <paquete> <nombre>` en su **propia terminal** |
| El kernel, donde viven las variables | Cada proceso tiene su memoria **propia** | **No se comparten variables.** Jamás. |
| `resultado = fk(q)` entre celdas | Un **tópico**: un canal con nombre | Mantas un mensaje, no una variable |
| `print(resultado)` para verlo | Escucharlo desde fuera | `ros2 topic echo /el_topico` **en otra terminal** |
| Correr las celdas **de arriba abajo, en orden** | El orden de lanzar **da igual** | Los nodos se buscan y se encuentran solos |
| `import fk` desde otro archivo | Un **paquete** de ROS 2 | `colcon build` lo instala y queda importable |
| El resultado se queda en una variable | El resultado hay que **guardarlo** | En un `.csv`, o grabado con `ros2 bag` |
| Un solo proceso | **Seis procesos** | Seis terminales (o seis sesiones SSH) |
| `Ctrl+C` para stopping | `Ctrl+C` para stopping | Igual. Pero el proceso muere y hay que volver a lanzarlo |

### El cambio de mentalidad, en dos frases

**En Jupyter tú mandas sobre el orden.** Corres la celda 2, produce un valor, la
celda 3 lo usa. Si no corres la 2 antes, la 3 falla.

**En ROS 2 el orden no importa.** Puedes lanzar el broker, esperar un minuto,
lanzar un cliente, y funciona. Y puedes lanzar los cuatro clientes a la vez, en
cuatro máquinas distintas, sin que ninguno sepa la IP de los demás. Cada nodo
anuncia "aquí estoy, hago esto" y los demás lo escuchan.

**Ese automatismo tiene un precio:** como nada te avisa de que te faltó algo, hay
que **comprobar a mano** que todo está donde debe estar. Por eso la parte B tiene
tantas comprobaciones.

### El otro cambio grande: en Jupyter tú eras el intermediario

En Jupyter eras tú quien llamaba a tus funciones, en orden, y veías el resultado
en la pantalla. En ROS 2 **nadie te llama**: tu nodo se lanza, anuncia lo que
hace, y espera a que le llegue trabajo. Por eso:

- Un nodo puede quedarse **corriendo en vacío** mucho rato sin que pase nada
  (el broker espera pedidos).
- Para ver qué hace, **tienes que mirar desde otro sitio** (`ros2 topic echo`).
- Para saber si está vivo, `ros2 node list`.

---

## A2 · El vocabulario mínimo

Solo siete palabras. Con la segunda columna te ubicas de inmediato.

| Palabra | Qué es, en una frase | En tu reto, quién es |
|---|---|---|
| **Nodo** (node) | Un programa de ROS 2 que hace una tarea. Corre como proceso aparte | El driver, el broker, y los 4 clientes: **6 nodos** |
| **Tópico** (topic) | Un canal de mensajes con nombre, de uno a muchos. Quien publica no sabe quién escucha | `/joint_states` (el broker publica, el driver escucha) y `/arm/queue_state` (el broker publica, todos escuchan) |
| **Acción** (action) | Un tipo de tarea larga: alguien pide, alguien ejecuta, y quien pidió recibe **progreso** y un **resultado** al final. Como una llamada a una función, pero asíncrona y con estado | `move_arm`. La pide `cliente.py` y la ejecuta el broker |
| **Servidor de acción** | El nodo que recibe las peticiones de una acción y hace el trabajo | El `arm_broker` |
| **Cliente de acción** | El nodo que pide la acción y espera el resultado | Cada `cliente.py` |
| **Mensaje** (msg) | El dato que viaja por un tópico. Su estructura está declarada en un archivo `.msg` o `.action` | `QueueState.msg` y `MoveArm.action`, ya están dados |
| **Parámetro** (parameter) | Un valor que se le pasa a un nodo al arrancarlo, con `--ros-args -p` | `politica`, `client_id`, `priority`, `traza` |

### La diferencia entre un tópico y una acción

Es la que más cuesta al principio, y es la que hace que tu reto esté bien diseñado:

| | **Tópico** | **Acción** |
|---|---|---|
| ¿Quién habla? | Uno publica, **cualquiera** escucha | Un cliente pregunta a **un** servidor concreto |
| ¿Hay respuesta? | No. Es un canal de una dirección | **Sí**: el resultado, y además progreso mientras tanto |
| ¿Sirve para...? | Datos que fluyen (sensores, estado) | Cosas que tardan y se pueden cancelar |
| En tu reto | `/joint_states` (órdenes al brazo) y `/arm/queue_state` (estado de la fila) | `move_arm` (mover el brazo) |

**Por qué el reto usa una acción para mover el brazo** y no un tópico: porque un
goal necesita tres cosas que un tópico no da: saber **quién** lo pidió, saber si
**lo aceptaron o lo rechazaron**, y poder **cancelarlo** si el cliente se arrepiente.
Y `MoveArm.action` además lleva `wait_time_s` y `exec_time_s`, que son
literalmente las métricas del ítem 3.

---

## A3 · Los seis procesos de tu reto

Esta es la tabla más importante del documento. Si entiendes esta tabla, entiendes
el reto.

| # | Proceso | Máquina | Se lanza con | Qué hace | Cómo sabes que está vivo |
|---|---|---|---|---|---|
| 1 | **Driver** | Jetson | `ros2 run jetcobot_driver sync_plan_nx` | Es el único que habla con `/dev/ttyUSB0`, el puerto del brazo. Escucha `/joint_states` y mueve el robot | `ros2 node list` muestra `/control_sync_plan` |
| 2 | **Broker** | Jetson | `ros2 run arm_broker broker` | Recibe los goals, **admite o rechaza** con la FK, los encola, y el worker mueve uno a uno. Publica `/arm/queue_state` a 5 Hz | `ros2 node list` muestra `/arm_broker`, y `ros2 action list` muestra `/move_arm` |
| 3 | **Cliente 1** | Raspberry 1 | `ros2 run arm_broker cliente --ros-args -p client_id:=uno` | Pide 40 poses, una a una, y espera el resultado de cada una | Su terminal imprime `pose 0: success=...` |
| 4 | **Cliente 2** | Raspberry 2 | `... -p client_id:=dos` | Ídem | Ídem |
| 5 | **Cliente 3** | Raspberry 3 | `... -p client_id:=tres` | Ídem | Ídem |
| 6 | **Cliente 4** | Raspberry 4 | `... -p client_id:=cuatro` | Ídem | Ídem |

Y un séptimo proceso, que solo existe mientras grabas:

| # | Proceso | Máquina | Se lanza con | Qué hace |
|---|---|---|---|---|
| 7 | **Grabadora** | Jetson | `ros2 bag record -o <carpeta> /arm/queue_state /joint_states` | Escribe todo en disco. No manda nada al brazo |

### Lo que espera cada proceso, y qué pasa si lo lanzas antes de tiempo

| Proceso | ¿Puede arrancar antes que los demás? | Qué pasa si lo lanzas pronto |
|---|---|---|
| Driver | **Sí**, cuando quieras | Se queda esperando órdenes |
| Broker | **Sí**, cuando quieras | Espera goals. Imprime `queue_length: 0` y `executing_goal_id: ''` |
| Grabadora | **Sí** | Se queda grabando una cola vacía. Solo gasta disco, nada más |
| Cliente | **No** | Espera hasta 15 s a que el broker aparezca, y si no aparece dice `El broker no aparece` y se sale |

**La secuencia cómoda:** driver → broker → grabadora → los 4 clientes. Pero solo
el cliente tiene una dependencia real. Los demás se pueden lanzar en cualquier orden.

### El error de concepto más común: "las cuatro Raspberry son cuatro copias de la misma máquina"

No. Cada Raspberry es **independiente**: tiene su propia copia del código, su
propio `colcon build`, su propio `ROS_DOMAIN_ID`. Lo único que comparten es:

1. La **red** del laboratorio.
2. El **mismo `ROS_DOMAIN_ID`** (47 en tu caso).
3. El **mismo archivo `carga.csv`**.

Y nada más. Si una Raspberry se apaga, las otras tres siguen funcionando. Si una
tiene el código viejo, solo ella corre el código viejo. Por eso hay que
**instalar y compilar en las cuatro**, no solo en una.

---

## A4 · Qué es un workspace y por qué existe

### La idea

Un workspace es una **carpeta de trabajo** donde metes tu código fuente y donde
`colcon` te deja una copia ya compilada e instalada.

```
~/rb2_ws/                      ← el workspace
│
├── src/                       ← AQUÍ va tu código. Es lo único que editas.
│   ├── arm_broker/
│   └── arm_broker_interfaces/
│
├── build/                     ← lo crea colcon. Scratch. No se edita.
├── install/                   ← lo crea colcon. El resultado final.
│   ├── setup.bash             ← ESTE es el que se sourcea
│   ├── local_setup.bash
│   └── arm_broker/
└── log/                       ← lo crea colcon. Errores de compilación.
```

### Por qué no se puede compilar en `src/` directamente

Porque `arm_broker_interfaces` no es Python: es un paquete C++ que tiene que
**generar código** a partir de la definición de la acción. Ese código generado
tiene que vivir en un paquete de Python, y Python no compila: se instala. Por eso
existe `install/`, y por eso el proceso se llama `colcon build` aunque uno de los
dos paquetes no se compile.

Además, `build/` e `install/` **se pueden borrar y regenerar**. Si algo sale mal,
`rm -rf build install log` y `colcon build` otra vez. Es la receta de limpieza
estándar.

### Qué hace `colcon build`

1. Lee todo lo que hay dentro de `src/`, y **detecta los paquetes** (por el
   `package.xml`).
2. Los ordena por dependencias: primero `arm_broker_interfaces` (que genera el
   código de la acción), después `arm_broker` (que la importa).
3. Compila el C++, copia el Python.
4. Deja el resultado en `install/`, y escribe las variables de entorno en
   `install/setup.bash`.

Y al terminar, en tu terminal verás algo así:

```
Starting >>> arm_broker_interfaces
Finished <<< arm_broker_interfaces [12.4s]      ← ESTA LÍNEA es la buena
Starting >>> arm_broker
Finished <<< arm_broker [0.8s]

Summary: 2 packages finished
```

`Finished <<<` es la palabra clave. Si ves `Failed <<<`, algo se rompió, y el
error está en `~/rb2_ws/log/latest_build/`.

### Qué hace `source`, y por qué se te olvida

`source install/setup.bash` **añade `install/` a tu PATH y a las variables de
Python**. Sin eso, cuando escribes `ros2 run arm_broker broker`, tu terminal busca
el programa `broker` en los caminos de siempre, no lo encuentra, y dice
`command not found`.

**Y las variables de `source` solo viven en la terminal donde las pones.** No
afectan a las demás. Por eso **cada terminal nueva** que abras tienes que
sourcear otra vez. Es la regla más molesta de ROS 2 y la que más Jupyter se parece:
en Jupyter también tenías que "activar" el kernel antes de poder hacer nada.

> **Atajo:** si quieres olvidarte de esto, agrega el `source` a tu `~/.bashrc`:
> ```bash
> echo 'source ~/rb2_ws/install/setup.bash' >> ~/.bashrc
> ```
> Con eso, cada terminal nueva ya nace con el entorno listo. **Hazlo.** Es lo que
> hacen todos.

---

# PARTE B · El procedimiento

Cada paso tiene el mismo formato: **qué haces**, **en qué máquina**, el
**comando exacto**, **qué debes ver**, y **qué significa si no lo ves**.

## B1 · Crear el repo en GitHub y subir el código

> **En tu PC con Windows.** Una sola vez.

### B1.1 · Crear el repositorio en GitHub

1. Entra a github.com y haz clic en **New repository**.
2. **Nombre sugerido:** `rb2-turno-del-brazo` (o el de tu equipo).
3. **Visibilidad:** Private, salvo que el profesor pida lo contrario.
4. **NO** marques "Add a README", ni `.gitignore`, ni licencia. Lo quieres vacío.
5. Clic en **Create repository**.

GitHub te mostrará una pantalla con dos URLs. **Copia la del botón verde "Code"**
(la que empieza con `https://github.com/TU_USUARIO/...`). La necesitas en unos
minutos.

### B1.2 · Subir el código desde tu PC

Abre **PowerShell** en la carpeta `solucionOO+` (la que tiene `src/`,
`herramientas/`, `analisis/`, `docs/`, `README.md`). Puedes llegar ahí desde el
Explorador: clic derecho en la carpeta → *Abrir en Terminal*.

Si nunca has configurado git, hazlo **una vez** (si ya lo tienes, sáltate esto):

```powershell
git config --global user.name "Tu Nombre"
git config --global user.email "tu.correo@esan.edu.pe"
```

Ahora los cuatro comandos que hacen todo el trabajo:

```powershell
git init
git add .
git commit -m "Reto 2: broker con cola FIFO y round-robin"
git remote add origin https://github.com/TU_USUARIO/rb2-turno-del-brazo.git
git push -u origin main
```

| Comando | Qué hace |
|---|---|
| `git init` | Crea la carpeta `.git`, que guarda el historial |
| `git add .` | Marca **todos** los archivos de esta carpeta para el próximo commit |
| `git commit -m "..."` | Guarda una versión, con un mensaje que dice qué cambió |
| `git remote add origin ...` | Apunta a tu repo de GitHub |
| `git push -u origin main` | Sube esa versión a GitHub |

**Qué debes ver:** `main` con una flecha, y en GitHub tus archivos.

### B1.3 · Qué **no** subir

No subas `__pycache__`, ni `install/`, ni `build/`, ni `log/`. Esos están en
Windows si compilaste ahí, pero si no, no existen. Si aun así aparecen, crea un
`.gitignore`:

```
__pycache__/
build/
install/
log/
carga.csv
```

**Sobre `carga.csv`:** no lo subas **todavía**. Se genera después de verificar la
tabla DH (paso B8.1), y tiene que ser **la misma copia** en las cinco máquinas. Lo
subir al repo es la forma más limpia de garantizarlo, pero solo cuando ya exista
definitivo.

### B1.4 · Si cambias algo en Windows después

```powershell
git add .
git commit -m "qué cambié"
git push
```

Y después, **en cada una de las 5 máquinas**: `git pull` + recompilar. Ese paso
extra es el que más olvida la gente; está en el paso B4.4.

---

## B2 · Clonar y compilar en el Jetson

> **En el Jetson**, por SSH desde tu PC o con monitor y teclado. Una sola vez.

### B2.1 · Entrar al Jetson

```bash
ssh jetson@172.51.9.5
```

*(La IP es la que te dio tu profesor. Si no la tienes, este es el momento de
preguntarla.)*

### B2.2 · Traer el código

```bash
cd ~
git clone https://github.com/TU_USUARIO/rb2-turno-del-brazo.git rb2
cd rb2
ls
```

**Qué debes ver** en el `ls`: `README.md`, `src`, `herramientas`, `analisis`,
`docs`, `CAMBIOS.md`. Si solo ves `src`, el clon se hizo a medias: bórralo y
vuelve a hacerlo.

### B2.3 · Copiar `src/` al workspace

```bash
mkdir -p ~/rb2_ws/src
cp -r src/* ~/rb2_ws/src/
ls ~/rb2_ws/src
```

**Qué debes ver:** `arm_broker` y `arm_broker_interfaces`.

> **Por qué copiar y no trabajar directamente en `~/rb2_ws/src/`:** si compilaras
> dentro del repo, los archivos generados (`build/`, `install/`) ensuciarían tu
> GitHub. Con la copia, el repo queda limpio y el código compilado se tira sin
> miedo. Es un poco más de trabajo, pero evita subir basura.

### B2.4 · Compilar

```bash
cd ~/rb2_ws
colcon build
```

Tarda **entre 2 y 15 minutos**. El primer build es el lento.

**Qué debes ver:**

```
Starting >>> arm_broker_interfaces
Finished <<< arm_broker_interfaces [12.4s]
Starting >>> arm_broker
Finished <<< arm_broker [0.8s]

Summary: 2 packages finished
```

Si ves `Failed <<<`:

```bash
cat ~/rb2_ws/log/latest_build/*/stderr.log | tail -40
```

### B2.5 · Comprobar que compiló

```bash
source ~/rb2_ws/install/setup.bash
ros2 pkg list | grep arm_broker
ros2 interface show arm_broker_interfaces/action/MoveArm
```

**Qué debes ver:**

```
arm_broker
arm_broker_interfaces
```

Y la definición de la acción, que es la que tu broker y tus clientes comparten:

```
float64[] joint_positions
string    client_id
uint8     priority
---
bool     success
...
```

**Esa última parte del paso es importante:** si `ros2 interface show` imprime
algo, es que la acción se **generó y registró** en ROS 2. Es el puente entre el
broker y los clientes. Sin eso, el cliente no encuentra la acción y dice
`El broker no aparece`.

### B2.6 · El atajo que te va a ahorrar tiempo

```bash
echo 'source ~/rb2_ws/install/setup.bash' >> ~/.bashrc
exec bash
```

A partir de ahora, **ninguna terminal nueva del Jetson necesita sourcear tu
reto**.

---

## B3 · Descubrir el nombre de la carpeta del driver

> **En el Jetson.** Una sola vez.

El material del curso menciona dos nombres distintos para la misma cosa
(`ros2_ws_brazo` y `jetcobot_colcon_ws`). No adivines: **pregunta a la máquina.**

```bash
ls -d ~/ros2_ws_brazo ~/jetcobot_colcon_ws 2>/dev/null
```

**Qué debes ver:** exactamente uno de los dos.

Si no sale ninguno, busca el driver por ahí:

```bash
find ~ -maxdepth 4 -name "install" -path "*brazo*" -o -maxdepth 4 -name "install" -path "*jetcobot*" 2>/dev/null
ls -d ~/ros2_ws* ~/jetcobot* 2>/dev/null
```

**Lo que hagas con el resultado, en los dos casos:**

| Si encontraste | Sustituye en todo el documento | Cómo sourcear |
|---|---|---|
| `~/ros2_ws_brazo` | Usa ese nombre | `source ~/ros2_ws_brazo/install/setup.bash` |
| `~/jetcobot_colcon_ws` | Usa ese nombre | `source ~/jetcobot_colcon_ws/install/setup.bash` |

> **No compiles el driver.** Ese workspace es del curso y ya está compilado.
> **Nunca** corras `colcon build` ahí: si algo está mal, rompes el driver de tu
> equipo y la siguiente clase empieza con un problema que no es tuyo.

**Comprueba que el driver está disponible** (sin lanzarlo todavía):

```bash
source <la-carpeta-del-driver>/install/setup.bash
ros2 pkg list | grep jetcobot
```

**Qué debes ver:** algo con `jetcobot` en el nombre. Ya está.

---

## B4 · Clonar y compilar en las 4 Raspberry

> **En cada Raspberry**, una por integrante. Es lo mismo en las cuatro.

### B4.1 · Repetir B2.2, B2.3, B2.4, B2.5, B2.6

Exactamente los mismos comandos, en cada Raspberry:

```bash
cd ~
git clone https://github.com/TU_USUARIO/rb2-turno-del-brazo.git rb2
cd rb2
mkdir -p ~/rb2_ws/src
cp -r src/* ~/rb2_ws/src/
cd ~/rb2_ws && colcon build
source ~/rb2_ws/install/setup.bash
ros2 interface show arm_broker_interfaces/action/MoveArm
```

**La Raspberry NO tiene el driver, y no lo necesita.** El driver vive en el
Jetson. Lo que la Raspberry necesita es su propio `rb2_ws`, para tener el
ejecutable `cliente`.

**Sobre la Raspberry:** es el mismo sistema operativo, así que `colcon build` ahí
tarda bastante menos: unos segundos. No esperes los 15 minutos del Jetson.

### B4.2 · Comprobar que las dos cosas conviven

En una Raspberry, en una terminal nueva:

```bash
ros2 pkg list | grep -E 'arm_broker|jetcobot'
```

**Qué debes ver:**

```
arm_broker
arm_broker_interfaces
```

Si también ves `jetcobot_driver`, es porque el driver está instalado en la Pi
también. No es un problema, pero recuerda: **quien lo lanza es el Jetson.**

### B4.3 · Poner un nombre reconocible a cada Raspberry

Para que en la sustentación puedas decir "este cliente corre en esta máquina":

```bash
hostname
```

Si sale algo como `raspberrypi`, cámbialo:

```bash
sudo hostnamectl set-hostname pi-uno    # uno, dos, tres, cuatro
```

Y anota en tu README la tabla: qué IP tiene cada Pi, qué `client_id` usa, y qué
`priority`.

### B4.4 · Atención: el paso que más se olvida

Cuando hagas `git pull` en una máquina para actualizar el código, **`git pull` no
actualiza el workspace**. El broker y el cliente se ejecutan desde
`~/rb2_ws/`, que es una **copia**, no desde el repo.

Después de cada `git pull`, repite:

```bash
cp -r ~/rb2/src/* ~/rb2_ws/src/
cd ~/rb2_ws && colcon build
```

Si no lo haces, **corres el código viejo y no te enteras**, porque el broker
arranca igual y todo parece funcionar. Es el error más silencioso de todo el
procedimiento.

> **Atajo opcional:** si en el paso B2.4 en lugar de `colcon build` usaras
> `colcon build --symlink-install`, los archivos Python del repo se enlazan en
> vez de copiarse, y las ediciones de `.py` se ven sin recompilar. Es lo más
> parecido a la comodidad de Jupyter. **El precio:** si borras un archivo, el
> enlace se rompe y hay que volver a compilar. Si vas a estar editando mucho,
> úsalo; si vas a lanzar y ya, quédate con el normal.

---

## B5 · Configurar las variables de entorno

> **En las 5 máquinas.** El mismo dominio en todas, o nada funciona.

### B5.1 · Los valores

| Variable | Valor en tu equipo | Para qué |
|---|---|---|
| `ROS_DOMAIN_ID` | **47** (= 42 + 5) | Aísla tu equipo de los otros 9 brazos de la red |
| `ROS_LOCALHOST_ONLY` | `0` | Permite que tus nodos se comuniquen con otras máquinas |
| `RMW_IMPLEMENTATION` | `rmw_fastrtps_cpp` | El conector de DDS que usa el curso |
| `JETSON` | La IP de tu Jetson | Para los scripts de `herramientas/` |
| `source` del driver | Ruta de tu carpeta del driver (paso B3) | Para que exista el driver |

### B5.2 · Escribirlas en `.bashrc`

En **cada** máquina, Jetson y las 4 Raspberry:

```bash
echo 'source /opt/ros/humble/setup.bash' >> ~/.bashrc
echo 'export ROS_DOMAIN_ID=47'            >> ~/.bashrc
echo 'export ROS_LOCALHOST_ONLY=0'        >> ~/.bashrc
echo 'export RMW_IMPLEMENTATION=rmw_fastrtps_cpp' >> ~/.bashrc
echo 'export JETSON=172.51.9.5'           >> ~/.bashrc
echo 'source ~/rb2_ws/install/setup.bash' >> ~/.bashrc
echo 'source <TU-CARPETA-DRIVER>/install/setup.bash' >> ~/.bashrc
exec bash
```

> La del driver **solo en el Jetson**. En las Raspberry no hace falta (y si no
> existe la carpeta, no la agregues).

**Qué debes ver, en cualquier terminal nueva:**

```bash
echo "$ROS_DISTRO · dominio $ROS_DOMAIN_ID · localhost $ROS_LOCALHOST_ONLY"
```

```
humble · dominio 47 · localhost 0
```

### B5.3 · Reiniciar el demonio

```bash
ros2 daemon stop
ros2 daemon start
```

**Cada vez que cambies una variable.** El demonio de ROS guarda en memoria la
configuración con la que arrancó, y si no lo reinicias te sigue enseñando la
información vieja. Es la causa número uno de "lo configuré y no funciona".

### B5.4 · El cortafuegos

ROS 2 usa puertos UDP que dependen del dominio: `7400 + 250 × dominio`. Con 47,
el rango es **19150–19250**.

```bash
sudo ufw status
```

Si dice `Status: active`:

```bash
sudo ufw allow from 172.51.0.0/16 to any proto udp port 19150:19250
```

**Qué debes ver:** `Status: inactive`, o el `ufw status` mostrando la regla.

---

## B6 · Las cinco comprobaciones, en orden

> **En cada máquina.** Hazlas en este orden: cada una descarta una causa.

Cada línea es un filtro. Si la primera pasa, pasa a la siguiente. La primera que
falle es la causa del problema, y las de después no importan todavía.

### Comprobación 1 · ¿Hay red?

```bash
ping -c 3 $JETSON
```

**Debes ver:** tres respuestas con tiempo. **Si falla: es la red, no ROS 2.**
Avisa al profesor; nada de lo que viene va a funcionar.

### Comprobación 2 · ¿Tienen el mismo dominio?

En las 5 máquinas, una por una:

```bash
echo $ROS_DOMAIN_ID
```

**Debes ver:** `47` en las cinco. Si una dice otra cosa, esa máquina no ve a las
demás. Arréglalo ahí y repite desde esta línea.

### Comprobación 3 · ¿Está el código compilado?

```bash
ros2 pkg list | grep arm_broker
```

**Debes ver:** `arm_broker` y `arm_broker_interfaces`.

Si no sale nada, se te olvidó sourcear o no compilaste: vuelve a B2.5 o B4.1.

### Comprobación 4 · ¿Alguien levantó el driver?

Primero, **dentro del Jetson**:

```bash
ros2 node list
```

**Debes ver, como mínimo:**
```
/control_sync_plan
```

**Si aquí sale vacío, el problema NO es tu Raspberry.** Nadie levantó el driver.
Esto desconcierta a todo el equipo, y por eso lo digo dos veces: es el
diagnóstico más confuso que existe, porque parece un problema tuyo y es del
Jetson.

### Comprobación 5 · ¿Te ven los clientes y el broker?

Con el driver levantado, desde **cada Raspberry**:

```bash
ros2 node list
ros2 topic list
```

**Debes ver** (desde una Raspberry, con el driver arriba):

```
/control_sync_plan
/joint_states
/parameter_events
/rosout
```

Y en `ros2 topic list` debe estar `/joint_states`. La presencia de `/joint_states`
es la prueba de que **el driver está escuchando órdenes**.

Cuando lances el broker (paso B7), en la Raspberry aparecerán dos nodos más:

```
/arm_broker
/arm_client
```

**Y cuando lances los cuatro clientes, verás cuatro líneas iguales de
`/arm_client`.** Es lo correcto: los cuatro nodos se llaman igual, y están en
cuatro máquinas distintas. Si ves cuatro líneas, **los cuatro están vivos.**

### La comprobación que no es una lista: el descubrimiento

Si `ros2 node list` sale vacío pero hiciste todo lo de más, el problema es de
**descubrimiento**: las máquinas no se están encontrando por la red. Las dos
causas más comunes:

1. **Cortafuegos.** Vuelve a B5.4.
2. **El laboratorio usa Discovery Server.** Pregunta al profesor. Si es así,
   hacen falta dos variables más:

   ```bash
   sudo apt install -y ros-humble-rmw-fastrtps-cpp
   scp jetson@$JETSON:~/super_client_configuration_file.xml ~/
   echo 'export ROS_DISCOVERY_SERVER='"$JETSON"':11811' >> ~/.bashrc
   echo 'export FASTRTPS_DEFAULT_PROFILES_FILE=$HOME/super_client_configuration_file.xml' >> ~/.bashrc
   ros2 daemon stop; ros2 daemon start
   ```

   **El archivo XML es obligatorio** en esa modalidad. Sin él verás solo
   `/parameter_events` y `/rosout` (tus propios tópicos) y nada del robot.

---

## B7 · Ítem 2: correr el broker y probarlo

> **5 o 6 terminales.** Todas en el Jetson salvo los clientes.

### B7.0 · Abrir las terminales

En el Jetson, con HDMI o por SSH. La forma más cómoda es abrir **varias sesiones
SSH** desde tu PC:

```bash
# Desde tu PC, abre 3-4 terminales y en cada una:
ssh jetson@172.51.9.5
```

Si solo tienes una consola física, **conéctate por SSH y usa multiplexores**
(`tmux`, `screen`) para no perder la sesión al desconectarte:

```bash
# Instalar (una vez)
sudo apt install -y tmux

# En el Jetson
tmux new -s rb2          # creas una sesión con 6 ventanas
#   Ctrl+B  luego  %   → divide verticalmente (otra terminal)
#   Ctrl+B  luego  "   → divide horizontalmente
#   Ctrl+B  luego  flecha → te mueves entre ventanas
```

Con `tmux`, si se te cae el WiFi, **el broker sigue corriendo** y no pierdes nada.
Para el ítem 3 es casi obligatorio, porque las corridas duran 8 minutos.

**Reparto de terminales:**

| Terminal | Máquina | Qué va a correr |
|---|---|---|
| T1 | Jetson | El driver |
| T2 | Jetson | El broker (con `tee`) |
| T3 | Jetson | La telemetría (`ros2 topic echo`) |
| T4 | Jetson | La grabadora (solo en el ítem 3) |
| T5, T6, T7, T8 | Una Raspberry cada una | Un cliente cada una |

### B7.1 · Terminal 1 — el driver

```bash
source ~/rb2_ws/install/setup.bash
ros2 run jetcobot_driver sync_plan_nx
```

**Qué debes ver:** nada, o escasas líneas de log. **Eso es normal**: el driver
está esperando órdenes. Se queda **corriendo** y no vuelve al prompt. Eso es lo
correcto.

> **Solo una persona levanta el driver.** El puerto serial es único. Si dos lo
> abren, el segundo recibe un error.

### B7.2 · Terminal 2 — el broker

```bash
source ~/rb2_ws/install/setup.bash
ros2 run arm_broker broker --ros-args -p politica:=fifo 2>&1 | tee rechazos.log
```

**Qué debes ver:**

```
[INFO] [arm_broker]: arm_broker listo · política=fifo · cola_max=20 · único publicador de /joint_states
```

Y **se queda corriendo**, sin volver al prompt.

> **Por qué el `2>&1 | tee rechazos.log`:** ese pipe captura en un archivo todo lo
> que el broker escribe, incluidos los avisos de rechazo. El log **es** el
> entregable "registro de rechazos con motivo" del ítem 2. Sin el `tee` se
> pierde al cerrar la terminal.

### B7.3 · Terminal 3 — mirar la telemetría

```bash
ros2 topic echo /arm/queue_state
```

**Qué debes ver, ahora mismo:**

```
stamp: ...
executing_client: ''
executing_goal_id: ''
executing_elapsed_s: 0.0
queue_length: 0
...
total_accepted: 0
total_rejected: 0
total_completed: 0
```

**Es normal que esté vacía.** El broker está vivo y publica cada 0.2 segundos,
pero nadie ha pedido nada todavía. Si no sale nada, mira la terminal T2: si el
broker no arrancó, no hay telemetría.

### B7.4 · Probar los tres rechazos (3 de los 8 puntos)

**Hazlo ahora, con el broker recién arrancado.** Los rechazos por paso articular
y por workspace dependen de la pose actual del brazo, y al arrancar es
`q = 0,0,0,0,0,0`. Si lo pruebas después de que se mueva, el motivo puede ser otro.

En la **terminal 3** (deja de ver el `echo` con `Ctrl+C` primero), manda los
tres goals:

**a) Fuera de límites articulares** (pide 3.5 rad, el tope es 2.93):

```bash
ros2 action send_goal /move_arm arm_broker_interfaces/action/MoveArm \
  "{joint_positions: [3.5, 0.0, 0.0, 0.0, 0.0, 0.0], client_id: 'prueba', priority: 1}"
```

**En la terminal 2 (`rechazos.log`):**
```
[INFO] [arm_broker]: RECHAZADO [prueba p1] · limites articulares: 1_Joint fuera de rango: 3.500 rad, límite [-2.93, 2.93]
```

**b) Paso articular excesivo** (desde la pose actual, pide 1.3 rad, el tope es 1.2):

```bash
ros2 action send_goal /move_arm arm_broker_interfaces/action/MoveArm \
  "{joint_positions: [1.3, 0.0, 0.0, 0.0, 0.0, 0.0], client_id: 'prueba', priority: 1}"
```

**En `rechazos.log`:**
```
RECHAZADO [prueba p1] · paso articular excesivo: 1.30 rad desde la pose actual, maximo 1.20 rad
```

**c) Fuera del workspace** (el efector cae a 71 mm, el mínimo es 80):

```bash
ros2 action send_goal /move_arm arm_broker_interfaces/action/MoveArm \
  "{joint_positions: [0.0, 1.5, 2.4, 0.0, 0.0, 0.0], client_id: 'prueba', priority: 1}"
```

**En `rechazos.log`:**
```
RECHAZADO [prueba p1] · workspace: efector a 71 mm de la base, demasiado cerca
```

> Estos tres motivos están verificados contra tu `fk.py`, así que el texto es el
> exacto. **Si al probarlos no sale ese texto, el brazo ya se movió**: reinicia
> el broker (Ctrl+C y vuélvelo a lanzar) y prueba otra vez.

> **`ros2 action send_goal` es para pruebas.** No lo uses con los clientes reales
> del ítem 3: no pasa por `cliente.py` y no llena las métricas por cliente.

### B7.5 · Terminals 5 a 8 — lanzar los cuatro clientes

En **cada Raspberry**, una terminal, con su propio `client_id`:

```bash
source ~/rb2_ws/install/setup.bash
ros2 run arm_broker cliente --ros-args -p client_id:=uno -p priority:=3
```

Los otros tres, con `client_id` y `priority` distintos. **Lánzalos a la vez**, en
las cuatro máquinas, dentro de un margen de unos segundos. Esa simultaneidad es
justo lo que genera la contención que mide el ítem 3.

| Parámetro | Qué es | Consejo |
|---|---|---|
| `client_id` | Tu nombre en la telemetría y en el log | Todos distintos: `uno`, `dos`, `tres`, `cuatro` |
| `priority` | 0–255, **mayor = más urgente** | Elegid cuatro distintos si queréis que la prioridad importe |
| `traza` | Ruta al CSV de `generar_carga.py` | Vacío = 2 poses por defecto, para una prueba rápida |
| `repeticiones` | Cuántas veces repite la traza | `1` |
| `pausa_s` | Pausa entre poses, en el cliente | `0.5` por defecto |

> **Sobre el `priority` y round-robin:** tu `politicas.py` implementa **round-robin**,
> que reparte por cliente y **ignora el número de prioridad**. Si queréis que la
> prioridad tenga efecto visible en la comparación, usad prioridades iguales, o
> el resultado medido va a ser round-robin igual.

**Qué debes ver en cada Raspberry:**

```
[uno] esperando al broker...
[uno] QUEUED pos=2 t=0.3s
[uno] pose 0: success=True espera=4.2s ejec=3.0s total=7.4s — pose alcanzada en 10 pasos
```

| Parte del mensaje | Qué significa |
|---|---|
| `QUEUED pos=2` | Este pedido está en la posición 2 de la fila |
| `success=True` | Se ejecutó bien |
| `espera=4.2s` | Lo que estuvo **en la fila**. Esta es la métrica del ítem 3 |
| `ejec=3.0s` | Lo que tardó **moviéndose**. Debería ser siempre ~3.0 |
| `total=7.4s` | La espera + la ejecución + la pausa |

**Si `ejec` no es ~3.0, algo se movió dos veces.** Avisa.

### B7.6 · Los tres chequeos que valen los 8 puntos

#### Chequeo 1 · Un solo publicador (5 puntos)

```bash
ros2 topic info /joint_states -v
```

**Debes ver:**
```
Publisher count: 1
Subscription count: 1
```

**Si dice más de uno, se anulan 5 puntos.** No es un bug de tu código: es que
alguien levantó el driver a mano, o hizo un `ros2 topic pub`, o hay un test
corriendo. La rúbrica es literal:

> *"cualquier cliente que publique directamente en `/joint_states` anula el
> puntaje del criterio de exclusión mutua."*

**Haz esta comprobación antes de cada corrida y antes de grabar el video.**

#### Chequeo 2 · Nunca dos goals ejecutándose (5 puntos)

Mira el `executing_goal_id` en la terminal 3:

```
executing_client: uno
executing_goal_id: a1b2c3d4e5f6
queue_length: 3
queued_goal_ids: [b2c3d4e5f6a7, c3d4e5f6a7b8, d4e5f6a7b8c9]
```

Cuatro cosas que deben ser verdad:

1. `executing_goal_id` **nunca está vacío** mientras haya trabajo.
2. **Solo hay un goal ejecutándose.** Nunca dos a la vez.
3. `executing_goal_id` **no aparece** dentro de `queued_goal_ids`. Si aparece, ese
   goal está en la fila **y** ejecutándose: la exclusión mutua se rompió.
4. Cuando `queue_length` baja, `executing_goal_id` **cambia**.

> **La línea que nunca debe aparecer:**
> ```
> executing_goal_id: a1b2c3d4e5f6
> queued_goal_ids: [a1b2c3d4e5f6, b2c3d4e5f6a7]
> ```
> El mismo ID en los dos sitios. Si la ves, para la corrida y depura.

Este chequeo **sustituye** a "no vi dos publicadores", y es más sólido: un bag de
`/joint_states` solo no registra quién publicó cada mensaje; correlacionado contra
`/arm/queue_state` sí lo demuestra.

#### Chequeo 3 · Cada rechazo dice por qué (3 puntos)

Ya lo hiciste en B7.4. Deja la **captura** (foto o el `rechazos.log` copiado) en
el repositorio, porque es entregable.

---

## B8 · Ítem 3: las dos corridas medidas

> **Jetson + las 4 Raspberry.** Dos corridas idénticas, cambiando una sola cosa.

### B8.1 · Congelar la tabla DH (antes de nada)

`generar_carga.py` llama a `fk`, y `fk.py` usa la tabla DH. **Si cambias la
tabla, cambia la carga, y las dos corridas dejan de ser comparables.**

El orden obligatorio:

```
  verificar la FK contra el robot  →  congelar la tabla  →  generar carga.csv
         (ítem 1)                      (escribirlo)          (B8.2)
```

**Concreto:** en tu README, escribe *"La tabla DH verificada es la del commit
`XXXXXXX` y no se modifica después de esa fecha."* Y no toques `fk.py` a partir de
ahí.

### B8.2 · Generar `carga.csv`, una sola vez

> **En el Jetson**, desde la raíz del repo.

```bash
cd ~/rb2
source ~/rb2_ws/install/setup.bash
python3 herramientas/generar_carga.py --n 40 --semilla 7 --salida carga.csv
```

**Qué debes ver:**
```
40 poses alcanzables en carga.csv (semilla 7)
```

> **¿Por qué desde la raíz del repo?** Porque `generar_carga.py` busca tu código
> con una ruta **relativa a su propia ubicación**:
> ```python
> sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
>                                 '..', 'src', 'arm_broker'))
> ```
> O sea, calcula `../src/arm_broker` a partir de donde está el script. Si lo
> corres desde otro lado, no encuentra tu `fk.py` y falla.

### B8.3 · Llevar la carga a las 4 Raspberry

Como usas Git, la forma más limpia es subirla al repo:

```bash
# En el Jetson, desde ~/rb2
git add carga.csv
git commit -m "carga oficial: 40 poses, semilla 7"
git push
```

Y en cada Raspberry:

```bash
cd ~/rb2
git pull carga.csv
```

**Verifica que las 4 copias son idénticas** (si no, la comparación se rompe):

```bash
md5sum carga.csv
```

Los cuatro hashes tienen que salir iguales.

### B8.4 · Corrida 1 — FIFO

**Terminal 1 (Jetson)** — el driver, si no lo tienes corriendo:

```bash
ros2 run jetcobot_driver sync_plan_nx
```

**Terminal 4 (Jetson)** — la grabadora, **antes** de que arranque nadie:

```bash
source ~/rb2_ws/install/setup.bash
ros2 bag record -o ~/rb2/corrida_fifo /arm/queue_state /joint_states
```

> **Graba los dos tópicos.** Grabando solo `/joint_states` no hay métricas:
> `exportar_csv.py` te avisa con un aviso si le falta `/arm/queue_state`. Y
> `/arm/queue_state` es el que dice **quién esperó cuánto**, que es justo lo que
> mides.

**Terminal 2 (Jetson)** — el broker:

```bash
ros2 run arm_broker broker --ros-args -p politica:=fifo
```

**Terminals 5 a 8 (las 4 Raspberry)** — los cuatro clientes, **con la carga**:

```bash
ros2 run arm_broker cliente --ros-args \
  -p client_id:=uno -p priority:=3 -p traza:=/home/TU_USUARIO/rb2/carga.csv
```

*(`/home/TU_USUARIO` es tu usuario en la Raspberry. Usa la ruta real, y con
`~` expandido: `traza:=~/rb2/carga.csv`.)*

**Los cuatro a la vez**, en un margen de unos segundos.

### B8.5 · Qué esperar durante la corrida

| Tiempo | Qué pasa |
|---|---|
| 0 s | Los cuatro envían su primer goal casi al mismo tiempo |
| ~1 s | Uno está ejecutando, tres en la fila. **Este es el momento del reto** |
| 0–8 min | 160 goals en total, uno cada 3 segundos |
| ~8 min | El último cliente termina |

**Los números de una corrida completa:**

| Dato | Valor |
|---|---|
| Goals totales | **160** (40 poses × 4 clientes) |
| Duración | **~8 minutos** (160 × 3 s) |
| Mensajes de `/arm/queue_state` | ~2400 |
| Mensajes de `/joint_states` | ~1600 |
| Tamaño del bag | Pocos MB |

**Lo que debe verse en la terminal 3 (telemetría):**

```
executing_client: uno
executing_goal_id: a1b2c3d4e5f6
queue_length: 3
queued_clients: [dos, tres, cuatro]
queued_wait_s: [2.1, 4.5, 6.8]
total_accepted: 47
total_rejected: 2
total_completed: 44
```

`queued_wait_s` **va creciendo** en cada elemento mientras esperan. Eso es
correcto. Si no crece, el broker no está midiendo el tiempo bien.

**Cuando el último cliente termine**, corta la grabadora con `Ctrl+C` (terminal 4).
Corta también el broker y el driver.

### B8.6 · Corrida 2 — round-robin

**Exactamente lo mismo, cambiando una sola cosa:**

| | Corrida 1 | Corrida 2 |
|---|---|---|
| Parámetro | `-p politica:=fifo` | `-p politica:=prioridad` |
| Carpeta del bag | `~/rb2/corrida_fifo` | `~/rb2/corrida_rr` |
| La carga | `carga.csv` | **la misma** `carga.csv` |
| Los 4 clientes | iguales | **exactamente iguales** |

> **Sobre el nombre del parámetro:** tu `politicas.py` es round-robin, pero la
> **clave en el diccionario se llama `prioridad`**, porque el `broker.py` del
> andamiaje solo distingue ese caso y le pasa el parámetro `tau`. Es lo que está
> implementado y funciona. No lo cambies ahora, y si te preguntan, la respuesta
> es esa.

### B8.7 · Exportar a CSV

> **En el Jetson**, desde la raíz del repo.

```bash
cd ~/rb2
source ~/rb2_ws/install/setup.bash
python3 analisis/exportar_csv.py corrida_fifo --salida fifo/
python3 analisis/exportar_csv.py corrida_rr  --salida roundrobin/
```

**Qué debes ver**, para cada una:

```
Tópicos en el bag:
  /arm/queue_state  (arm_broker_interfaces/msg/QueueState)
  /joint_states  (sensor_msgs/msg/JointState)

queue_state.csv   2400 filas
joint_states.csv  1600 filas
```

**Si `queue_state.csv` tiene 0 filas**, no se grabó `/arm/queue_state`. Repite la
corrida grabando los dos tópicos.

**Dos paquetes que hacen falta en el Jetson** y que el enunciado no pide instalar,
pero sin ellos no hay ítem 3:

```bash
sudo apt install -y ros-humble-rosbag2 ros-humble-rosbag2-storage-default-plugins python3-matplotlib
```

### B8.8 · Calcular las métricas y la figura

```bash
python3 analisis/metricas.py fifo/queue_state.csv roundrobin/queue_state.csv
```

**Qué debes ver**, para cada política:

```
=== fifo
  pedidos observados : 160
  completados        : 158
  espera media       : 7.45 s
  espera p95         : 11.20 s
  espera máxima      : 12.90 s
  por prioridad:
    prioridad 0: n=40  media= 9.10s  p95=12.90s  máx=12.90s
    ...
  índice de inanición: 12.90 s  (espera máxima de prioridad 0, la menos urgente)
  goals por cliente  : {'cuatro': 40, 'dos': 40, 'tres': 40, 'uno': 40}
  equidad de Jain    : 1.000
```

Y al final:

```
Figura: comparacion_politicas.png
```

Los números **no van a ser esos** (son un ejemplo de formato), pero la
**estructura** sí tiene que ser esa: los 160 pedidos, las 4 prioridades, el
índice de inanición, los goals por cliente y el Jain.

> **Detalle que no es obvio: el nombre de la carpeta es la etiqueta de la
> figura.** `metricas.py` saca el nombre de la gráfica del nombre de la carpeta
> donde está el CSV. Si exportas a `prioridad/`, la figura va a decir "prioridad"
> y nadie sabrá que mediste round-robin. **Por eso en B8.7 usé `--salida
> roundrobin/`.** Así la figura dice `fifo` y `roundrobin`.

> **Si dice "Sin matplotlib":** `sudo apt install -y python3-matplotlib`.

### B8.9 · La conclusión (esto lo escribes tú)

Ningún script redacta esto, y es lo que la rúbrica pide: *"figura que sustenta
una conclusión"*.

| # | Qué escribir |
|---|---|
| 1 | Los números de las dos corridas, de lo que imprimió `metricas.py` |
| 2 | **Cuál gana en qué métrica**: p95, inanición, Jain |
| 3 | **Por qué** |
| 4 | El matiz honesto: cuándo gana round-robin y cuándo no |

**El "por qué" ya está desarrollado** en
[`docs/03_item2_como_se_resuelve.md`](docs/03_item2_como_se_resuelve.md) §5. El
punto central, y es lo que el docente busca:

> Round-robin **garantiza alternancia, no conteo igual**. Con servicios parecidos
> el Jain sube; con servicios muy desiguales, el cliente rápido acumula turnos
> legítimamente y el Jain **puede bajar**.

Presentar round-robin como mejor en todo es un error. Explica **cuándo** gana y
**cuándo** empata o pierde.

---

## B9 · Los resultados finales: qué queda en tu disco

### En el Jetson

```
~/rb2/                              ← tu repo (el código)
├── carga.csv                       ← la carga oficial, 40 poses, semilla 7
├── corrida_fifo/                  ← el bag de la corrida 1
│   ├── metadata.yaml
│   ├── corrida_fifo_0.db3
│   └── corrida_fifo_0.db3.metadata.yaml
├── corrida_rr/                    ← el bag de la corrida 2
├── fifo/                           ← el CSV de la corrida 1
│   ├── queue_state.csv             ← las esperas. LA fuente de las métricas
│   └── joint_states.csv            ← las poses que pasaron
├── roundrobin/                     ← el CSV de la corrida 2
│   ├── queue_state.csv
│   └── joint_states.csv
├── comparacion_politicas.png       ← LA FIGURA del ítem 3
├── rechazos.log                    ← el entregable del ítem 2
└── src/ herramientas/ analisis/     ← el código
```

### Qué es cada archivo, y para qué sirve

| Archivo | Qué es | Para qué ítem |
|---|---|---|
| `carga.csv` | Las 40 poses que los cuatro clientes repitieron | 3 — la evidencia de que la carga fue la misma |
| `corrida_fifo/`, `corrida_rr/` | Los bags: todo lo que pasó, con marca de tiempo | 3 — la evidencia bruta |
| `fifo/queue_state.csv` | La telemetría de la corrida 1, fila por fila | 3 — **de aquí salen todas las métricas** |
| `roundrobin/queue_state.csv` | Ídem para la corrida 2 | 3 |
| `fifo/joint_states.csv` | Las poses que se publicaron | 3 — la prueba de la exclusión mutua |
| `comparacion_politicas.png` | La figura con las dos políticas | 3 — **es el entregable** |
| `rechazos.log` | El log del broker con los rechazos y su motivo | 2 — **es el entregable** |

### Los cinco entregables, y de dónde sale cada uno

| # | Entregable | De dónde sale | Estado |
|---|---|---|---|
| 1 | **Repo GitHub** con los dos paquetes, README e instrucciones | Tu repo | `git push` |
| 2 | **Diseño previo firmado**: tabla DH, diagrama de secuencia y **predicción del p95 por política**, **antes de medir** | El diagrama está en `docs/03` §3; la predicción en `docs/03` §5. Pásalos a un documento, fíjalo y **fírmalo** | **Falta redactarlo y firmarlo** |
| 3 | **Bag + CSV + la figura comparativa** | Los archivos de arriba | Los produce B8 |
| 4 | **Video de 3 minutos** con los 4 clientes en disputa y `/arm/queue_state` en pantalla | Grabar durante B8.4 | **Falta grabar** |
| 5 | **Cierre reflexivo**, máximo una página: *¿qué política llevarían a CapyTown y por qué?* | Escribirlo, con las métricas de B8.8 | **Falta escribir** |

**Sobre el video:** grábalo en una pantalla donde se vean **a la vez** la
telemetría (terminal 3) y las terminales de los clientes. Lo que tiene que verse
en 3 minutos:

1. Los cuatro clientes pidiendo poses al mismo tiempo.
2. `/arm/queue_state` con `queue_length: 3` y **un solo** `executing_goal_id`.
3. La rotación de los turnos en la corrida de round-robin.
4. **Opcional pero recomendado:** una línea de `rechazos.log` con su motivo.

### Lo que falta de los ítems 1 y 4 (para que no se te pase)

| Ítem | Qué falta | Dónde está el material |
|---|---|---|
| **1** (4 pts) | Firmar la predicción, medir con el robot, reportar el error | `herramientas/verificar_fk.py`; la predicción ya está calculada en [`PLAN_DE_TRABAJO.md`](PLAN_DE_TRABAJO.md) |
| **4** (2 pts) | Escribir el script de `send_coords` + `get_angles` + `fk(q)` | El código literal está en [`PLAN_DE_TRABAJO.md`](PLAN_DE_TRABAJO.md), paso 7 |

### El paso final: subir los resultados a GitHub

```powershell
# En tu PC con Windows
git add carga.csv rechazos.log comparacion_politicas.png fifo/ roundrobin/
git commit -m "Resultados del item 3: dos corridas, CSV, figura comparativa"
git push
```

Sube también los CSV (son pocos KB). **Los bags no los subas**: pesan mucho y
GitHub no es un sitio para bags.

---

# PARTE C · Referencia rápida

## C1 · En vez de `print`, usa esto

| En Jupyter harías | En ROS 2 haces esto | En qué terminal |
|---|---|---|
| `print(fk(q))` | `ros2 topic echo /arm/queue_state` | Cualquiera |
| `print("el broker arrancó")` | `ros2 node list` | Cualquiera |
| `print(len(nodos))` | `ros2 node list \| wc -l` | Cualquiera |
| Ver quién publica en un tópico | `ros2 topic info /joint_states -v` | Cualquiera |
| Ver qué mensajes hay | `ros2 topic list` | Cualquiera |
| Ver las acciones disponibles | `ros2 action list` | Cualquiera |
| Ver el detalle de una acción | `ros2 action info /move_arm` | Cualquiera |
| Ver los parámetros de un nodo | `ros2 param list /arm_broker` | Cualquiera |
| Cambiar un parámetro en caliente | `ros2 param set /arm_broker politica fifo` | Cualquiera |
| Ver la definición de un mensaje | `ros2 interface show arm_broker_interfaces/msg/QueueState` | Cualquiera |
| `time.sleep(5)` para esperar | `Ctrl+C` y relanzar, o `ros2 param` | — |
| Guardar el resultado en un `.csv` | `ros2 bag record` + `exportar_csv.py` | Jetson |
| Ver los logs de un nodo | Ya los tienes: la salida de su terminal | La del nodo |

**La regla de oro:** en Jupyter mirabas la pantalla donde estaba el kernel. En
ROS 2 **miras desde otra terminal, preguntándole a la red.**

---

## C2 · Cheat sheet de comandos

### Instalar y configurar (una vez)

| Comando | Qué hace | Dónde |
|---|---|---|
| `git clone <url> rb2` | Baja el código | Las 5 |
| `mkdir -p ~/rb2_ws/src && cp -r src/* ~/rb2_ws/src/` | Pasa el código al workspace | Las 5 |
| `colcon build` | Compila | Las 5 |
| `source ~/rb2_ws/install/setup.bash` | Activa el resultado | Cada terminal |
| `ros2 interface show arm_broker_interfaces/action/MoveArm` | Verifica que la acción existe | Las 5 |
| `ros2 daemon stop && ros2 daemon start` | Reinicia el índice de ROS | Las 5 |

### Correr (ítem 2 y 3)

| Comando | Qué hace | Dónde |
|---|---|---|
| `ros2 run jetcobot_driver sync_plan_nx` | Levanta el driver | Jetson |
| `ros2 run arm_broker broker --ros-args -p politica:=fifo` | Levanta el broker | Jetson |
| `ros2 run arm_broker cliente --ros-args -p client_id:=uno` | Levanta un cliente | Cada Pi |
| `ros2 bag record -o <carpeta> /arm/queue_state /joint_states` | Graba | Jetson |

### Mirar

| Comando | Qué te dice |
|---|---|
| `ros2 node list` | Qué nodos ve esta máquina |
| `ros2 topic list` | Qué tópicos hay |
| `ros2 topic echo /arm/queue_state` | La fila en tiempo real |
| `ros2 topic info /joint_states -v` | **Cuántos publican. Debe ser 1** |
| `ros2 action list` | Qué acciones hay. Debe estar `/move_arm` |
| `ros2 param list /arm_broker` | Los parámetros del broker |

### Medir

| Comando | Qué hace |
|---|---|
| `python3 herramientas/generar_carga.py --n 40 --semilla 7 --salida carga.csv` | Crea la carga |
| `python3 herramientas/verificar_fk.py` | Mide el error de la FK (ítem 1) |
| `python3 analisis/exportar_csv.py <bag> --salida <carpeta>` | Bag → CSV |
| `python3 analisis/metricas.py a/queue_state.csv b/queue_state.csv` | CSV → números + figura |

---

## C3 · Errores frecuentes, explicados

### Los de "no veo nada", en orden de probabilidad

| Síntoma | Qué pasa de verdad | Qué hacer |
|---|---|---|
| `ros2 node list` vacío | **Casi nunca es el robot.** Es descubrimiento: no se ven por la red | `ros2 daemon stop && ros2 daemon start`. Si sigue vacío, el driver no está corriendo (pregunta en el Jetson, no en tu Pi) |
| Veo mis tópicos pero no los del robot | `ROS_LOCALHOST_ONLY=1` | `export ROS_LOCALHOST_ONLY=0` y reinicia el demonio |
| No veo a los otros integrantes | `ROS_DOMAIN_ID` distinto | `echo $ROS_DOMAIN_ID` en **cada** máquina y iguálos a 47 |
| Ping funciona pero no hay nodos | Cortafuegos | B5.4 |
| Ping no funciona | **Es la red** | Avisa al profesor. Nada de lo que viene va a funcionar |
| Veo `/parameter_events` y `/rosout`, nada más | Falta el XML del Discovery Server | B6, última opción |

### Los de ROS 2 específicamente

| Síntoma | Por qué | Solución |
|---|---|---|
| `ros2 run arm_broker broker: command not found` | No sourceaste tu reto | `source ~/rb2_ws/install/setup.bash` |
| `ros2 run jetcobot_driver ...: not found` | No sourceaste el kit | `source <TU-CARPETA-DRIVER>/install/setup.bash` |
| `El broker no aparece. ¿Está corriendo?` | El cliente no encuentra la acción `/move_arm` | El broker no arrancó, o no estás sourceando el mismo workspace en las dos máquinas |
| `Failed <<< arm_broker_interfaces` | Error de compilación | `cat ~/rb2_ws/log/latest_build/*/stderr.log \| tail -40` |
| `ModuleNotFoundError: arm_broker_interfaces` | Compilaste solo `arm_broker` | `rm -rf ~/rb2_ws/build ~/rb2_ws/install && colcon build` |
| Modifiqué un `.py` y no cambia nada | No recompilaste tras el `git pull` | B4.4: re-copiar y recompilar |
| `Publisher count: 2` en `/joint_states` | **Alguien más publica** | Busca el segundo: driver duplicado, un `ros2 topic pub`, un test. **5 puntos en juego** |
| `Permission denied` en `/dev/ttyUSB0` | El driver ya tiene el puerto | Solo el driver toca el brazo. No pelees por el puerto |
| El broker se cuelga y no atiende más | Bug en el `finally` del worker | Debería estar resuelto. Si pasa, alguien editó `_worker` |
| Rechazos que no reproducen el motivo esperado | El brazo ya se movió, y el rechazo depende de la pose actual | Reinicia el broker y prueba con la pose en cero |
| `exportar_csv.py`: "Falta ROS 2" | Sin sourcear, o falta `rosbag2` | `source` + `sudo apt install -y ros-humble-rosbag2` |
| `exportar_csv.py`: "no se grabó /arm/queue_state" | Grabaste solo un tópico | Repite la corrida con los dos tópicos |
| `metricas.py`: "Sin matplotlib" | Falta la librería | `sudo apt install -y python3-matplotlib` |
| `metricas.py`: "Con un solo CSV no hay comparación" | Solo le diste un CSV | Pásale los dos |

### Dos cosas que parecen errores y no lo son

1. **`queue_length: 0` y `executing_goal_id: ''` al arrancar.** El broker acaba
   de publicar y nadie ha pedido nada. Es lo correcto.
2. **Los clientes dicen "pose N: RECHAZADA".** Con contención, es esperado. De
   hecho los rechazos son un ítem que se reporta. Pero **mira `rechazos.log`**: si
   todos son por paso articular, es que el servicio es más rápido que el intervalo
   de llegada, y eso es un **resultado**, no un bug.

### La limpieza de último recurso

Si nada funciona y no sabes por dónde empezar:

```bash
# En el Jetson y en cada Pi
rm -rf ~/rb2_ws/build ~/rb2_ws/install ~/rb2_ws/log
cd ~/rb2_ws && colcon build
source install/setup.bash
```

Y si aun así:

```bash
ros2 daemon stop
rm -rf ~/.ros
ros2 daemon start
```

`~/.ros` es la caché de descubrimiento de ROS 2. Borrarla es seguro: solo pierde
el índice de lo que vio, que se reconstruye.

---

## Lo que no puedes hacer en ningún orden

Tres cosas, y romperlas cuesta puntos:

1. **Que aparezca un segundo publicador en `/joint_states`.** Anula 5 puntos. No
   es un bug: es que alguien levantó el driver a mano, o hizo un `ros2 topic pub`,
   "para comprobar algo". Compruébalo antes de cada corrida y del video.
2. **Regenerar `carga.csv` entre las dos corridas**, o cambiar la tabla DH
   después. Rompe la comparabilidad del ítem 3 completo.
3. **Medir el ítem 1 antes de escribir la predicción.** Con el número bueno igual,
   el ítem no vale.
