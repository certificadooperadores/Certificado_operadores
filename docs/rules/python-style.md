# Regla: estilo Python (Ruff + ty)

> Regla que el agente debe asumir **mientras escribe código**, no solo al final.

Todo el código Python del proyecto **debe** cumplir lo siguiente:

## 1. Pasa Ruff y ty antes de cada commit

```bash
uv run ruff check --fix .
uv run ruff format .
uv run ty check
```

- **Ruff** — lint + formato (reemplaza flake8/isort/black).
- **ty** (Astral) — tipado estático. Si el proyecto usa `mypy`, sustituir aquí.
- Config en `pyproject.toml`: `line-length = 100`, comillas dobles.

## 2. Responsabilidad única

- Una función = una cosa. Un archivo/módulo = una responsabilidad.
- Divide funciones largas o con varias responsabilidades.

## 3. Docstrings en español (PEP 257)

- Todo módulo, clase y función pública lleva docstring en español.
- Identificadores de código en inglés; la prosa en español.

## 4. Prohibido hardcodear

- Nada de valores, rutas, credenciales, URLs, puertos ni parámetros incrustados.
- Todo sale de configuración, constantes con nombre, variables de entorno o se
  inyecta.

## 5. Sin lógica en la UI

- La UI (incl. Streamlit) solo llama al **Facade** y muestra resultados.
- `UI → Facade → Dominio → Infraestructura`.

## 6. Antes de dar por terminada una función

- [ ] `uv run ruff check .` sin errores.
- [ ] `uv run ruff format --check .` sin cambios pendientes.
- [ ] `uv run ty check` sin errores.
- [ ] Pruebas de la función en verde.

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
