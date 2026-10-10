# Plan 002 — Modularización Arquitectónica del Facade

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`002-spec.md`](./002-spec.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |
| Fecha  | 2026-10-09                       |

## 1. Enfoque

Refactorizar el archivo monolítico `facade.py` que contiene tanto las entidades (dataclasses) como las consultas SQL crudas. Se separarán responsabilidades usando principios de Arquitectura Limpia (Clean Architecture) para aislar las reglas de negocio del acceso a la base de datos.

## 2. Arquitectura y capas

```text
UI / Streamlit  →  Facade (casos de uso)  →  Dominio  →  Infraestructura
```

- **Dominio:** Contiene lógica pura sin dependencias externas (`dataclasses` y constantes).
- **Infraestructura:** Contiene acceso a la DB mediante `SQLAlchemy`.
- **Facade:** Solo coordina el flujo.

## 3. Archivos afectados

| Archivo | Acción (crear/modificar) | Nota |
|---------|--------------------------|------|
| `src/certificado_operadores/domain/models.py` | crear | DTOs y constantes de negocio |
| `src/certificado_operadores/infra/repository.py` | crear | Acceso a DB y constantes SQL |
| `src/certificado_operadores/facade.py` | modificar | Limpiar y delegar llamadas |
| `tests/test_facade.py` | modificar | Actualizar imports |

## 4. Orden de implementación

1. Crear el módulo `domain/models.py` y extraer los DTOs.
2. Crear el módulo `infra/repository.py` y aislar SQLAlchemy.
3. Refactorizar `facade.py` para usar el repositorio.
4. Ajustar los tests para reflejar la nueva ubicación de los modelos.

## 5. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|-----------|
| Ruptura de imports en tests | Usar IDE tools para refactorización automática y correr `make test` exhaustivamente. |
| Inyección de dependencias rota | Mantener el inicializador por defecto en `OperadoresFacade` con carga perezosa (lazy load) hacia el engine local. |

## 6. Pruebas previstas

- `test_facade.py` debe seguir pasando sin alteraciones funcionales (15 pruebas en verde).

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
