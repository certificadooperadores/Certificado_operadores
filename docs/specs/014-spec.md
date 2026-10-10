# Spec 014 — Restauración de Backups con Comparación Preventiva de Registros

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Estado  | aprobada                                           |
| Autor   | Ing. Miguel Angel Ortiz Roldan                     |
| Fecha   | 2026-10-10                                         |
| Rama    | `feat/restauracion-backups-comparacion`            |
| Relaciona | `005-spec.md` (Administrar Backups)                |

## 1. Contexto y problema

El módulo actual de `Administrar Backups` permite crear, listar, proteger y eliminar copias de respaldo de SQLite, pero **carece de la funcionalidad de restauración**.
Restaurar una base de datos directamente sin advertencia previa es peligroso, ya que sobrescribe los datos actuales de producción/SharePoint.
Por tanto, el usuario requiere:
1. Una herramienta de **comparación previa** que analice el backup contra la base activa antes de restaurar, mostrando cuántos registros se perderían o modificarían en las tablas clave.
2. Un **respaldo preventivo de rescate automático** antes de aplicar la restauración.
3. Actualización del origen en `dim_version_bd` para reflejar la versión restaurada en el indicador lateral.

## 2. Objetivos

1. **En `BackupService` (`infra/backup_service.py`):**
   - Implementar `comparar_backup(nombre_backup: str) -> list[dict[str, object]]`:
     - Inspecciona la base actual y el archivo de respaldo seleccionado.
     - Compara conteos de filas para las tablas maestras (`dim_persona`, `dim_codigo`, `fact_licencias`, `fact_eventos_operador`, `fact_comportamiento`, `dim_usuarios`).
     - Devuelve filas con: `tabla`, `actual`, `backup`, `diferencia`.
   - Implementar `restaurar_backup(nombre_backup: str, crear_respaldo_seguridad: bool = True) -> tuple[bool, str]`:
     - Genera un respaldo automático preventivo (`pre_restauracion_<fecha>.db`).
     - Sobrescribe la base de datos de origen con la API atómica de `sqlite3.backup`.
     - Inserta registro en `dim_version_bd` con el nombre del backup restaurado.
2. **En la Interfaz UI (`modulos/administrar_backups/ui.py`):**
   - Incorporar la sección **"Restaurar Respaldo en la Base de Datos Activa"**.
   - Selector desplegable de backups existentes.
   - Tabla comparativa con semáforo de impacto (diferencia de registros).
   - Botón de confirmación explícito para ejecutar la restauración.
3. **Pruebas unitarias (`tests/test_backups.py`):**
   - Validar comparación de registros y cálculo de diferencias.
   - Validar restauración atómica y creación de copia preventiva.

## 3. Criterios de aceptación

- [ ] **CA-01:** `BackupService.comparar_backup` calcula diferencias de registros por tabla entre la BD actual y el backup.
- [ ] **CA-02:** `BackupService.restaurar_backup` crea backup preventivo y sobrescribe la BD de forma consistente.
- [ ] **CA-03:** La UI de backups muestra la tabla comparativa y requiere confirmación.
- [ ] **CA-04:** Las pruebas unitarias pasan 100% en verde con `uv run pytest`.

## 10. Enlaces

- Plan: [`014-plan.md`](./014-plan.md)
- Tareas: [`014-tareas.md`](./014-tareas.md)

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
