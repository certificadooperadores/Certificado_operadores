# Spec 003 — Refactorización UI: Administración de Operadores

| Campo   | Valor                                              |
|---------|----------------------------------------------------|
| Estado  | aprobada                                           |
| Autor   | Ing. Miguel Angel Ortiz Roldan                     |
| Fecha   | 2026-10-09                                         |
| Rama    | `feat/refactor-ui-admin-operadores`                |
| Relaciona | `002-spec.md` (Facade Arquitectura)              |

## 1. Contexto y problema

El archivo heredado `src/certificado_operadores/modulos/5_Administracion_Operadores.py` viola los principios de Clean Architecture al mezclar la interfaz visual de Streamlit con consultas directas a la base de datos (usando `run_query` y `run_transaction` de `db.py`). Esto produce acoplamiento fuerte y código difícil de mantener.

## 2. Objetivos

- Mover la administración de operadores a una estructura modular estricta: **una carpeta exclusiva para el módulo** (ej. `src/certificado_operadores/modulos/admin_operadores/`), que contenga sus archivos con funciones únicas (ej. `ui.py` para las vistas de Streamlit, separadas del punto de entrada en `pages/`).
- Eliminar por completo las sentencias SQL y las importaciones directas de la base de datos en la UI.
- Hacer que la UI consuma exclusivamente la capa `OperadoresFacade`.

## 3. No-objetivos

- Refactorizar otros módulos como `10_Reportes.py` o `6_Gestion_Certificados.py` (quedan para futuras specs).
- Cambiar la paleta de colores de Streamlit o agregar nuevas funcionalidades de negocio.

## 4. Requisitos funcionales

- **RF-01:** La UI debe permitir buscar un operador por cédula, delegando la búsqueda a `OperadoresFacade.obtener_operador_por_cedula`.
- **RF-02:** Los datos devueltos por el Facade (`OperadorInfo`) deben utilizarse para autocompletar el formulario visual de Streamlit.

## 5. Requisitos no funcionales

- **RNF-01 (Mantenibilidad):** El archivo de interfaz no debe contener la palabra `SELECT`, `UPDATE` o `INSERT`. Toda interacción con datos debe pasar por el Facade.
- **RNF-02 (Desacople):** Si la tabla `dim_persona` cambia de nombre mañana, la UI no debe verse afectada.

## 6. Criterios de aceptación (verificables)

- [ ] **CA-01:** El archivo refactorizado `Administracion_Operadores.py` importa y utiliza `OperadoresFacade`.
- [ ] **CA-02:** La búsqueda por cédula en la UI no ejecuta `run_query` desde el archivo visual.
- [ ] **CA-03:** La aplicación Streamlit carga sin errores de sintaxis tras la refactorización.

## 7. Casos de borde

- Manejo de operadores no encontrados (el Facade devuelve `None`, la UI debe mostrar estado de "Creación").

## 8. Dependencias

- Depende del `OperadoresFacade` construido en el Ciclo 2.

## 9. Fuera de alcance (por ahora)

- La refactorización del módulo de "Carga Masiva (Excel)" dentro de esa misma pestaña, que quizás requiera su propio Facade futuro.

## 10. Enlaces

- Plan: [`003-plan.md`](./003-plan.md)
- Tareas: [`003-tareas.md`](./003-tareas.md)

---

**Autor:** Ing. Miguel Angel Ortiz Roldan

## Instrucciones Especiales

**Agente OpenCode:** Por favor, inicia tu primera respuesta generando una confirmación explícita que diga 'Recibido, iniciando refactorización de la UI' antes de empezar a programar. Esto es para confirmar que estás vivo y leyendo esto.
