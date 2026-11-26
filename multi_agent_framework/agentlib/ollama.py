"""Ollama HTTP client adapted from agents_intro for ObsAgent's agent loop."""

import json
import os

import requests

TIMEOUT = 180  # un 9B compartido por el salon entero puede tardar


def ruta_env():
    """Dónde está el `.env` que manda. `None` si no hay ninguno."""
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for ruta in (os.path.join(raiz, ".env"), "/app/.env"):
        if os.path.exists(ruta):
            return ruta
    return None


def cargar_env():
    """
    Mete el `.env` de la raíz en `os.environ`, pisando lo que ya hubiera.

    Devuelve `(ruta, puestas, quitadas)`: el archivo que leyó, cuántas claves
    escribió y qué claves **borró** del entorno.

    `chat()` y `base_url()` no necesitan esto —leen el archivo en cada
    llamada—, pero los notebooks sí lo llaman, y por una razón concreta.

    **El entorno de un kernel de Jupyter puede contradecir al `.env` sin que
    nada lo diga.** La extensión de Python de VS Code inyecta el `.env` del
    workspace al *arrancar* el kernel: si el archivo cambió después, el kernel
    sigue con los valores viejos, y `importlib.reload` no limpia variables de
    entorno. El 2026-11-15 eso hizo que los notebooks 01 y 03 hablaran con
    `localhost` teniendo `OLLAMA_DESTINO=tec` en el archivo.

    De ahí lo de **borrar**: una clave nuestra que está en el entorno y ya no
    está en el `.env` se quita, porque si no, un valor que el archivo abandonó
    sigue mandando. Solo se tocan las claves del taller —las `OLLAMA_*`,
    `CHAT_MODEL` y `BACKEND_URL`—; el resto del entorno no se toca.
    """
    ruta = ruta_env()
    if ruta is None:
        return None, 0, []

    archivo = {}
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                archivo[k.strip()] = v.strip()

    nuestras = tuple(k for k in os.environ
                     if k.startswith("OLLAMA_") or k in ("CHAT_MODEL", "BACKEND_URL"))
    quitadas = sorted(k for k in nuestras if k not in archivo)
    for k in quitadas:
        del os.environ[k]
    for k, v in archivo.items():
        os.environ[k] = v
    return ruta, len(archivo), quitadas


def _config():
    """
    Lee el .env de la raíz del repo. Las variables del entorno pisan al archivo.

    Dos detalles que parecen de más y no lo son, los dos aprendidos rompiendo
    el backend:

    **Se busca el `.env` en dos lugares.** Dentro del contenedor este archivo
    vive en `/agentlib/`, así que subir tres directorios da `/` y ahí no hay
    `.env`. El Dockerfile lo deja en `/app/.env`.

    **Y se leen del entorno TODAS las claves `OLLAMA_*`, estén o no en el
    archivo.** `env_file` de Docker Compose inyecta el `.env` como variables de
    entorno, y si solo se miraran las claves que ya estaban en el diccionario,
    `OLLAMA_DESTINO` y las `OLLAMA_URL_*` se perderían dentro del contenedor.
    El síntoma era que el backend hablaba con `localhost` mientras el `.env`
    decía otra cosa.
    """
    valores = {
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "qwen3.5:9b",
    }
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for ruta in (os.path.join(raiz, ".env"), "/app/.env"):
        if not os.path.exists(ruta):
            continue
        with open(ruta, encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith("#") and "=" in linea:
                    k, v = linea.split("=", 1)
                    valores[k.strip()] = v.strip()
        break
    for k in list(valores):
        if os.getenv(k):
            valores[k] = os.getenv(k)
    for k, v in os.environ.items():
        if k == "CHAT_MODEL" or k.startswith("OLLAMA_"):
            valores.setdefault(k, v)
    valores["OLLAMA_MODEL"] = _modelo(valores)
    return valores


def _modelo(valores):
    """
    Qué modelo se le pide a Ollama. Una sola perilla, no dos.

    El `.env` tiene dos variables que nombran modelo, y es una trampa: la
    página y el backend leen `CHAT_MODEL` —con la convención
    `proveedor:modelo`— y este archivo leía `OLLAMA_MODEL`. Cambiar una sola
    dejaba a los notebooks pidiendo un modelo distinto del que usa la página,
    y el síntoma es "a mí me funciona y a ti no" entre dos pestañas de la misma
    máquina.

    Así que `CHAT_MODEL` manda cuando nombra un modelo de Ollama. Si apunta a
    otro proveedor —azure, foundry, mistral— ese no lo puede servir Ollama, y
    entonces vale `OLLAMA_MODEL`.

        1. `CHAT_MODEL`, cuando empieza con `ollama:`.
        2. `OLLAMA_MODEL`, del entorno o del archivo, para un `.env` viejo que
           no tenga `CHAT_MODEL`.

    **`CHAT_MODEL` va primero a propósito.** `env_file` de Docker Compose
    convierte cada línea del `.env` en una variable de entorno dentro del
    contenedor, así que darle prioridad al entorno hacía que un
    `OLLAMA_MODEL` heredado le ganara al modelo que el `.env` declara dos
    líneas más arriba. El síntoma era el peor posible: la página pedía un
    modelo y los notebooks otro.
    """
    chat_model = (valores.get("CHAT_MODEL") or "").strip()
    if chat_model.startswith("ollama:"):
        return chat_model.split(":", 1)[1]
    return valores.get("OLLAMA_MODEL", "qwen3.5:9b")


def origen_url(cfg=None):
    """
    Cuál de las direcciones del `.env` se usa, y **quién lo decidió**.

    Devuelve `(url, motivo)`. El motivo es la mitad útil: cuando un proceso
    habla con el Ollama equivocado, lo que falta no es la dirección —esa sale
    en el error— sino saber qué la puso ahí.

    El `.env` declara las tres de una vez —`OLLAMA_URL_LOCALHOST`,
    `OLLAMA_URL_AULA`, `OLLAMA_URL_TEC`— y `OLLAMA_DESTINO` dice cuál está
    activa. Moverse entre ellas es cambiar una palabra, y las otras dos no se
    pierden ni hay que recordarlas.

    El orden de precedencia, de mayor a menor:

        1. `OLLAMA_DESTINO` más la `OLLAMA_URL_<DESTINO>` que le corresponda.
           Es el punto único de configuración y gana.
        2. La variable de entorno `OLLAMA_BASE_URL`, si no hay destino. Es el
           escape para un caso suelto sin editar el archivo.
        3. `OLLAMA_BASE_URL` del `.env`, que es como funcionaba antes y sigue
           funcionando.
        4. localhost.

    **El orden está así por una falla medida el 2026-11-15.** El kernel de
    Jupyter traía `OLLAMA_BASE_URL=http://localhost:11434` inyectada al
    arrancar, de un `.env` anterior, y le ganaba a `OLLAMA_DESTINO=tec` en los
    notebooks 01 y 03 mientras el `.env` decía otra cosa. `importlib.reload` no
    limpia variables de entorno, así que no había forma de corregirlo desde el
    notebook. **Un punto único de configuración que pierde contra una variable
    que nadie puso no es un punto único**, así que ahora el destino manda y,
    cuando hay una `OLLAMA_BASE_URL` que se ignora, el motivo lo dice.
    """
    cfg = cfg if cfg is not None else _config()

    suelta = os.getenv("OLLAMA_BASE_URL")
    destino = (cfg.get("OLLAMA_DESTINO") or "").strip().lower()

    if destino:
        url = cfg.get(f"OLLAMA_URL_{destino.upper()}")
        if url:
            url = url.rstrip("/")
            motivo = f"OLLAMA_DESTINO={destino}, en el .env de la raíz"
            if suelta and suelta.rstrip("/") != url:
                motivo += (f"; se ignora OLLAMA_BASE_URL={suelta.rstrip('/')}, "
                           f"que viene del entorno")
            return url, motivo
        # Que la clave exista vacia no es lo mismo que no existir, y el
        # .env.example las trae vacias a proposito. Decir "no hay una
        # OLLAMA_URL_TEC" y listar 'tec' como declarado se contradice.
        clave = f"OLLAMA_URL_{destino.upper()}"
        con_valor = sorted(k[len("OLLAMA_URL_"):].lower()
                           for k, v in cfg.items()
                           if k.startswith("OLLAMA_URL_") and (v or "").strip())
        falta = ("está vacía" if clave in cfg else "no está")
        raise RuntimeError(
            f"OLLAMA_DESTINO dice '{destino}' y {clave} {falta} en el .env de "
            f"la raíz.\n"
            f"Ponle la dirección, con el formato  http://<ip>:11434\n"
            f"Destinos con dirección ahora mismo: "
            f"{', '.join(con_valor) or 'ninguno'}")

    if suelta:
        return (suelta.rstrip("/"),
                "la variable de entorno OLLAMA_BASE_URL, porque no hay OLLAMA_DESTINO")

    url = cfg.get("OLLAMA_BASE_URL") or "http://localhost:11434"
    return url.rstrip("/"), "OLLAMA_BASE_URL del .env, porque no hay OLLAMA_DESTINO"


def _elegida(cfg):
    """La URL sola. El motivo lo da `origen_url`."""
    return origen_url(cfg)[0]


def base_url(cfg=None):
    """
    La URL de Ollama, corregida si estamos dentro de un contenedor.

    `localhost` significa cosas distintas según dónde corra el código: en la
    laptop es la máquina, y dentro de un contenedor es el contenedor mismo. Sin
    esta corrección, un `.env` con `localhost` funciona para los pasos en
    Python y rompe el backend — con un error que no explica por qué uno sí y el
    otro no.

    `host.docker.internal` es el alias que Docker da al host. En Linux hace
    falta declararlo, y el compose del taller lo hace con
    `extra_hosts: host-gateway`.

    Cuál de las direcciones del `.env` se usa lo decide `_elegida`.
    """
    cfg = cfg or _config()
    url = _elegida(cfg).rstrip("/")
    en_contenedor = os.path.exists("/.dockerenv")
    if en_contenedor:
        for local in ("localhost", "127.0.0.1"):
            if f"//{local}" in url:
                return url.replace(f"//{local}", "//host.docker.internal")
    return url


def modelo_configurado():
    """
    El modelo que dice el `.env`, para quien necesite el nombre.

    `chat()` ya lo usa solo, así que esto hace falta únicamente cuando se
    escribe la petición a mano —el notebook 01 lo hace a propósito, para que se
    vea el JSON entero— o cuando hay que consultar `/api/show`.

    Existe para que nadie vuelva a escribir el nombre del modelo en una celda:
    un notebook con `"qwen3.5:9b"` adentro pide ese modelo aunque el `.env`
    diga otro, y falla contra un servidor que no lo tenga.
    """
    return _config()["OLLAMA_MODEL"]


def chat(mensajes, herramientas=None, temperatura=0.0, pensar=False, modelo=None,
         top_k=None, top_p=None, num_ctx=None):
    """
    Una llamada a /api/chat de Ollama. Devuelve el `message` de la respuesta.

        mensajes     lista de {"role": ..., "content": ...}
                     Los roles son: system, user, assistant, tool.
        herramientas lista de esquemas JSON, o None. El modelo NO las ejecuta:
                     devuelve message["tool_calls"] pidiendo que lo hagas tú.
        temperatura  0 para que el taller sea reproducible. Súbela para ver el
                     no determinismo en acción (bloque 1).
        pensar       False apaga el modo de razonamiento. Importa: qwen3.5:9b
                     puede gastar miles de tokens pensando y devolver una
                     respuesta vacía. Está en las notas del .env de itzae.
        top_k        Cuantos tokens candidatos considerar, y que fraccion de
        top_p        probabilidad acumulada. None deja los del modelo, que en
                     qwen3.5:9b son top_k 20 y top_p 0.95: recortan la lista
                     ANTES de que la temperatura elija entre lo que quedo.
                     Su efecto se nota poco; lo que de verdad hace visible el
                     no determinismo es pedir una respuesta LARGA, porque las
                     divergencias se acumulan token a token. Medido en
                     planeacion/hallazgos.md

    El valor de retorno es un dict con, según el caso:
        content      el texto de la respuesta
        tool_calls   lo que el modelo quiere que ejecutes
        thinking     el razonamiento, si `pensar=True`
    """
    cfg = _config()
    cuerpo = {
        "model": modelo or cfg["OLLAMA_MODEL"],
        "messages": mensajes,
        "stream": False,
        "think": pensar,
        "options": {"temperature": temperatura},
    }
    # Solo los mandamos si el llamador los pidio: asi el modelo conserva sus
    # propios valores por omision cuando nadie los toca.
    if top_k is not None:
        cuerpo["options"]["top_k"] = top_k
    if top_p is not None:
        cuerpo["options"]["top_p"] = top_p
    # La ventana de contexto. None deja la del servidor, que es lo normal; se
    # fija cuando un experimento tiene que dar lo mismo en cualquier maquina.
    # Un Ollama con 4096 por omision y otro con 262144 no demuestran lo mismo.
    if num_ctx is not None:
        cuerpo["options"]["num_ctx"] = num_ctx
    if herramientas:
        cuerpo["tools"] = herramientas

    url = base_url(cfg)

    # Ollama habla HTTP plano, sin TLS. Un `https://` en el .env produce un
    # error de SSL que manda a cualquiera a investigar certificados durante
    # veinte minutos, cuando lo que sobra es una letra. Lo atajamos antes de
    # que `requests` llegue al handshake.
    if url.startswith("https://"):
        raise RuntimeError(
            f"La dirección de Ollama dice https:// y Ollama no hace TLS.\n"
            f"La decidió: {origen_url(cfg)[1]}\n"
            f"Cambiala a:  {url.replace('https://', 'http://', 1)}"
        )

    try:
        r = requests.post(f"{url}/api/chat", json=cuerpo, timeout=TIMEOUT)
    except requests.exceptions.SSLError as e:
        # Por si el https llega por la variable de entorno en vez del .env.
        raise RuntimeError(
            f"Error de TLS contra {url}. Ollama habla HTTP plano: el esquema "
            f"tiene que ser http://, no https://.\n{e}"
        ) from e
    except requests.exceptions.ConnectionError as e:
        _, motivo = origen_url(cfg)
        pista = ("Si no es la que esperabas, revisa OLLAMA_DESTINO en el .env "
                 "de la raíz: es la única palabra que elige el destino."
                 if "OLLAMA_DESTINO=" in motivo
                 else "No hay OLLAMA_DESTINO en el .env de la raíz, así que "
                      "manda OLLAMA_BASE_URL. Pon OLLAMA_DESTINO y gana el .env.")
        raise RuntimeError(
            f"No pude conectarme a Ollama en {url}\n"
            f"Esa dirección la decidió: {motivo}\n"
            f"{pista}\n{e}"
        ) from e
    r.raise_for_status()
    datos = r.json()

    # Ollama devuelve, junto al message, los contadores REALES de tokens de
    # esta llamada. Hasta aqui los tirabamos. No cambian el valor de retorno
    # -chat() sigue devolviendo el message y nada mas-, pero quedan a mano
    # para quien quiera ver como crece el contexto vuelta a vuelta, que es la
    # unica forma honesta de verlo: estimar tokens contando caracteres falla
    # distinto en cada idioma.
    ULTIMA_LLAMADA.clear()
    ULTIMA_LLAMADA.update({k: v for k, v in datos.items() if k != "message"})
    CONTADOR["llamadas"] += 1
    return datos["message"]


# La respuesta cruda de la ultima llamada a chat(), sin el message.
ULTIMA_LLAMADA = {}

# Cuantas veces se ha llamado a chat() desde el ultimo reinicio del contador.
CONTADOR = {"llamadas": 0}


def llamadas_al_modelo(reiniciar=False):
    """
    Cuantas veces se llamo a `chat()`. Con `reiniciar=True` pone el contador en
    cero **despues** de leerlo.

    Existe porque calcular las llamadas con una formula sale mal, y salio mal:
    el notebook 05 afirmaba "dos llamadas por par, una para pedir la evidencia y
    otra para dictaminar", y medido el 2026-11-16 son **tres**. La tercera es la
    vuelta en la que el modelo redacta su respuesta despues de recibir el
    resultado de la ultima tool, y es facil de olvidar porque no pide nada.

    El bloque 5 cuenta llamadas para hablar de costo. Un numero deducido no
    sirve para eso.
    """
    n = CONTADOR["llamadas"]
    if reiniciar:
        CONTADOR["llamadas"] = 0
    return n


def ultima_medicion():
    """
    Tokens y tiempo de la última llamada a `chat()`. {} si todavía no hubo.

        tokens_enviados   el prompt COMPLETO de esa vuelta: system + toda la
                          conversación acumulada + los esquemas de las tools.
                          Es el número que hay que vigilar: el contexto real
                          de qwen3.5:9b en el aula son 4096 tokens.
        tokens_generados  lo que escribió el modelo.
    """
    return {
        "tokens_enviados": ULTIMA_LLAMADA.get("prompt_eval_count"),
        "tokens_generados": ULTIMA_LLAMADA.get("eval_count"),
        "segundos": round(ULTIMA_LLAMADA.get("total_duration", 0) / 1e9, 2),
    }


def normalizar_argumentos(tool_call):
    """
    Devuelve los argumentos de un tool_call como dict.

    Existe porque Ollama no es consistente: según el modelo, `arguments` viene
    como dict o como string con JSON dentro. Descubrirlo en vivo durante el
    paso 2 descarrila la explicación justo en el momento donde hay que estar
    mirando el bucle, no el parseo.
    """
    argumentos = tool_call["function"].get("arguments", {})
    if isinstance(argumentos, str):
        try:
            argumentos = json.loads(argumentos)
        except json.JSONDecodeError:
            # Un argumento ilegible NO es una excepcion: es informacion que le
            # devolvemos al modelo para que se corrija. Esa idea es el paso 3.
            return {"__error__": f"argumentos ilegibles: {argumentos!r}"}
    return argumentos


def streaming(mensajes, temperatura=0.0, modelo=None):
    """
    Igual que `chat`, pero devolviendo el texto token por token.

    Solo para el paso 1: ver los tokens caer de a uno es lo que hace concreta la
    idea de que un LLM predice el siguiente token y nada más. No se usa en los
    pasos 2 al 5 — con tools, el streaming complica el bucle sin aportar
    a lo que se está enseñando.
    """
    cfg = _config()
    cuerpo = {
        "model": modelo or cfg["OLLAMA_MODEL"],
        "messages": mensajes,
        "stream": True,
        "think": False,
        "options": {"temperature": temperatura},
    }
    url = base_url(cfg)
    with requests.post(f"{url}/api/chat", json=cuerpo, stream=True, timeout=TIMEOUT) as r:
        r.raise_for_status()
        for linea in r.iter_lines():
            if not linea:
                continue
            dato = json.loads(linea)
            pedazo = dato.get("message", {}).get("content", "")
            if pedazo:
                yield pedazo
            if dato.get("done"):
                break
