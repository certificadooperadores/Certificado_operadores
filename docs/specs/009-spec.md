# Spec 009 — Refactorización UI: Reportes Bitacora

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Estado  | aprobada                                           |
| Autor   | Ing. Miguel Angel Ortiz Roldan                     |
| Fecha   | 2026-10-09                                         |
| Rama    | `feat/refactor-ui-reportes-bitacora`                        |
| Relaciona | `002-spec.md` (Facade Arquitectura)              |

## 1. Contexto y problema

El archivo heredado `src/certificado_operadores/modulos/7_Reportes_Bitacora.py` viola los principios de Clean Architecture al mezclar la interfaz visual de Streamlit con consultas directas a la base de datos. Esto produce acoplamiento fuerte y código difícil de mantener.

## 2. Objetivos

- Mover el módulo a una estructura modular estricta: **una carpeta exclusiva para el módulo** (ej. `src/certificado_operadores/modulos/reportes_bitacora/`), que contenga sus archivos con funciones únicas (ej. `ui.py` para las vistas de Streamlit, separadas del punto de entrada en `pages/`).
- Eliminar por completo las sentencias SQL y las importaciones directas de la base de datos en la UI.
- Aislar el acceso a datos en la capa Facade/Infraestructura que corresponda.

## 3. No-objetivos

- Cambiar la paleta de colores de Streamlit o agregar nuevas funcionalidades de negocio.

## 4. Requisitos funcionales

- **RF-01:** La funcionalidad visual actual del módulo reportes_bitacora debe mantenerse intacta, delegando el manejo de datos a la capa inferior.

## 5. Requisitos no funcionales

- **RNF-01 (Mantenibilidad):** El archivo de interfaz no debe contener la palabra `SELECT`, `UPDATE` o `INSERT`.
- **RNF-02 (Desacople):** Si la base de datos cambia, la UI no debe verse afectada.

## 6. Criterios de aceptación (verificables)

- [ ] **CA-01:** El archivo refactorizado interactúa exclusivamente a través de la capa de aplicación (Facade).
- [ ] **CA-02:** No existen consultas SQL en la vista visual.
- [ ] **CA-03:** La aplicación Streamlit carga sin errores de sintaxis tras la refactorización.

## 10. Enlaces

- Plan: [`009-plan.md`](./009-plan.md)
- Tareas: [`009-tareas.md`](./009-tareas.md)

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
