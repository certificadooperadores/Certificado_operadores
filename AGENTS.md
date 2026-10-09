# AGENTS — Certificado_operadores

> Contexto del proyecto para sesiones con asistentes LLM (OpenCode, Gemini CLI,
> Copilot, Claude Code, etc.). Versionado en el repositorio.

## Proyecto

Aplicación para la gestión del certificado de ideoneida de los operadores del sistema masivo mio, desde su vinculación, formación, supensión, retiro. el objetivo es poder gestionar la información de una manera ordenada y versionada de facil acceso y manipulación

> 📘 La verdad técnica central —propósito, stack, estructura, convenciones,
> decisiones y flujo de trabajo— vive en [`CONSTITUTION.md`](./CONSTITUTION.md).
> **Léela antes de operar.** Ante cualquier cambio arquitectónico, tecnológico o de
> proceso, actualízala en el mismo commit.

---

## Reglas obligatorias

- **Repositorio obligatorio:** pide al usuario el repositorio antes de crear o
  modificar archivos; no trabajes sin respaldo.
- **No borrar sin autorización expresa** de archivos, carpetas o bases de datos.
- **Modificar solo con respaldo previo:** commit/stash/rama antes de editar.
- **Una función por ciclo:** implementar → probar → corregir → documentar → commit.
- **Pruebas obligatorias:** ninguna tarea termina hasta que las pruebas pasan (verde).
- **Todo en español** (documentación, comentarios, docstrings, commits); solo los
  identificadores de código en inglés.
- **Prohibido hardcodear:** nada de valores, rutas, credenciales, URLs o puertos
  incrustados; usa configuración, constantes, entorno o inyección.
- **La UI no ejecuta tareas (patrón Facade):** la interfaz (incl. Streamlit) solo
  llama al Facade y muestra resultados; `UI → Facade → Dominio → Infraestructura`.
- **Orden de carpetas:** una carpeta = una responsabilidad; nada suelto en la raíz.
- **Código temporal del agente:** los `fix`, `repair`, parches y diagnósticos que
  no forman parte del proyecto van en `temp_agent/` (ignorado en Git); nunca en la
  raíz, `src/`, `tests/`, `docs/` ni `scripts/`.

---

## Flujo diario (commit + push)

```bash
# 1. Ver cambios
git status

# 2. Verificación completa (lint + formato + pruebas)
make check

# 3. Agregar y commitear (los hooks se ejecutan solos)
git add -A
git commit -m "tipo: mensaje descriptivo"

# 4. Subir
git push
```

**Convención de commits:** [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — nueva funcionalidad
- `fix:` — corrección de bug
- `docs:` — documentación
- `refactor:` — refactorización
- `style:` — formato, linting (sin cambio de lógica)
- `test:` — pruebas
- `chore:` — mantenimiento o configuración

---

## Comandos del proyecto (`make`)

```bash
make help      # lista los objetivos disponibles
make dev       # entorno + hooks de pre-commit
make check     # lint + formato + pruebas
make lint      # Ruff (lint)
make format    # Ruff (formato)
make test      # pytest
```

---

## Reglas de estilo

Respeta [`docs/rules/python-style.md`](./docs/rules/python-style.md) **mientras
escribes**: Ruff + ty, responsabilidad única, docstrings en español, sin
hardcodear y sin lógica en la UI. (Para Gemini CLI existe el equivalente
[`GEMINI.md`](./GEMINI.md).)

## Estructura y convenciones

- `src/certificado_operadores/` — código del paquete (src-layout).
- `tests/` — pruebas con `pytest` (patrón AAA).
- `docs/` — documentación detallada (requerimientos, desacople, manual, funciones).
- `CONSTITUTION.md` — fuente única de verdad.
- Docstrings **en español**; responsabilidad única por archivo y función.
- Mantén `docs/referencia-funciones.md` al día con cada función que añadas o cambies.
