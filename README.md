# puertos

Utilidad de puertos TCP locales: comprueba si están **libres u ocupados**, busca
el **primer puerto libre** de un rango (el patrón `800X`) e identifica **qué
proceso** ocupa cada puerto. Nació de un problema real: un servidor local que
chocaba una y otra vez con el `8000`, ocupado por Docker.

## Por qué el método es fiable

Para saber si un puerto está libre se intenta hacer `bind()`, **no** conectar y
ver si algo responde. Es la pregunta que de verdad importa —"¿puedo abrir aquí un
servidor?"— y además detecta los listeners en `0.0.0.0` (como Docker), porque
`0.0.0.0:P` reclama todas las interfaces y el `bind` a `127.0.0.1:P` falla igual.
No se activa `SO_REUSEADDR` en el sondeo: en Windows daría falsos "libre".

## Instalación

```bash
uv pip install -e .            # editable, desde la carpeta del proyecto
uv pip install -e .[proceso]   # + psutil (identificación de proceso más robusta)
```

`psutil` es **opcional**: sin él, el nombre del proceso se obtiene de
`netstat`/`tasklist` (Windows) o `ss` (Linux/Steam Deck). Cero dependencias
obligatorias.

## Uso — línea de comandos

```bash
puertos check 8000 8005 8501     # tabla libre/ocupado + PID y nombre del proceso
puertos find 8000                # primer puerto libre desde 8000 (stdout limpio)
puertos scan 8000-8010           # estado de un rango
puertos --host 0.0.0.0 check 80  # otra interfaz
```

`find` imprime **solo el número** a stdout (los avisos van a stderr), pensado para
scripts:

```bash
PORT=$(puertos find 8000)
python -m http.server "$PORT" --bind 127.0.0.1
```

Ejemplo de salida de `check`:

```
8000   LIBRE
8005   OCUPADO  PID 36580  python.exe
8501   LIBRE
```

## Uso — como librería

```python
from puertos import puerto_libre, buscar_puerto_libre, estado_puertos

if not puerto_libre(8000):
    puerto = buscar_puerto_libre(8000)   # 8001, 8002, ... el primero libre
    print(f"Usaré el {puerto}")

for e in estado_puertos([8000, 8005, 8501]):
    print(e.puerto, "libre" if e.libre else f"ocupado por {e.proceso}")
```

## Desarrollo

```bash
uv pip install -e .[dev]
pytest -q          # 7 tests deterministas (listener en puerto efímero)
ruff check . && black --check . && mypy src/puertos
```

## Licencia

MIT.
