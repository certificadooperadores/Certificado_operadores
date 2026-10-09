# GEMINI — Certificado_operadores

> Contexto del proyecto para **Gemini CLI**. Equivalente a `AGENTS.md`.

## Proyecto

Aplicación para la gestión del certificado de ideoneida de los operadores del sistema masivo mio, desde su vinculación, formación, supensión, retiro. el objetivo es poder gestionar la información de una manera ordenada y versionada de facil acceso y manipulación

> 📘 La verdad central vive en [`CONSTITUTION.md`](./CONSTITUTION.md). **Léela
> antes de operar.** La documentación detallada está en [`docs/`](./docs/README.md).

## Reglas obligatorias

- **Repositorio obligatorio:** pide al usuario el repositorio antes de crear o
  modificar archivos; no trabajes sin respaldo.
- **No borrar** archivos, carpetas ni bases de datos sin autorización expresa.
- **Modificar solo con respaldo previo:** commit/stash/rama antes de editar.
- **Una función por ciclo:** implementar → probar → corregir → documentar → commit.
- **Pruebas obligatorias:** ninguna tarea termina sin pruebas verdes.
- **Todo en español** (documentación, comentarios, docstrings, commits); solo los
  identificadores de código en inglés.
- **Prohibido hardcodear:** usa configuración, constantes, entorno o inyección.
- **La UI no ejecuta tareas (Facade):** `UI → Facade → Dominio → Infraestructura`.
- **Orden de carpetas**; código temporal del agente (`fix`, `repair`, parches) en
  `temp_agent/`.

## Reglas de estilo

Consulta y respeta [`docs/rules/python-style.md`](./docs/rules/python-style.md):
Ruff + ty, responsabilidad única, docstrings en español, sin hardcodear, sin
lógica en la UI.

## Comandos

```bash
make check     # lint + formato + pruebas
make test      # pytest
make lint      # Ruff
```

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
