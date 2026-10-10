---
title: "Spec 002: Modularización Arquitectónica del Facade"
status: borrador
---

| Campo     | Valor                                              |
|-----------|----------------------------------------------------|
| Estado    | borrador                                           |
| Autor     | Ing. Miguel Angel Ortiz Roldan                     |
| Fecha     | 2026-10-09                                         |
| Rama      | `main`                                             |

## 1. Objetivo
Refactorizar el módulo monolítico `src/certificado_operadores/facade.py` dividiéndolo en capas arquitectónicas definidas (Dominio e Infraestructura). El objetivo es separar responsabilidades: el Facade solo debe orquestar, no contener SQL duro ni definiciones de datos, adhiriendo a los principios de Clean Architecture.

## 2. Requerimientos

### 2.1. Capa de Dominio (`src/certificado_operadores/domain/models.py`)
1. Crear el paquete y módulo de dominio.
2. Extraer a este módulo todos los DTOs y _dataclasses_ (`OperadorInfo`, `EstadoCertificado`, `EstadisticasBasicas`).
3. Extraer a este módulo todas las constantes de negocio (`VIGENCIA_ACTIVA`, `ANIOS_VIGENCIA_CERTIFICADO`, `TIPOS_EVENTO_CERTIFICADO`, etc.).
4. Extraer las funciones puras de lógica de fechas y estados (por ejemplo `_sumar_anios`, `_clasificar_estado`).

### 2.2. Capa de Infraestructura (`src/certificado_operadores/infra/repository.py`)
1. Crear el paquete y módulo de infraestructura.
2. Mover todas las constantes de SQL (`_SQL_OPERADOR_BASE`, `_SQL_ULTIMO_CERTIFICADO`, etc.) a este archivo.
3. Crear una clase `OperadoresRepository` que reciba el motor de base de datos (`Engine`) y encapsule **toda** la ejecución de código SQLAlchemy y consultas directas.
4. Los métodos del repositorio deben devolver instancias de los modelos de Dominio.

### 2.3. Capa de Aplicación (`src/certificado_operadores/facade.py`)
1. `OperadoresFacade` debe dejar de ejecutar SQLAlchemy directamente.
2. `OperadoresFacade` debe delegar las consultas invocando a una instancia de `OperadoresRepository`.
3. Mantener la firma pública de los métodos del Facade intacta para no romper a sus consumidores.

### 2.4. Pruebas
1. Actualizar las importaciones en `tests/test_facade.py` para que importen los DTOs desde el nuevo módulo `domain.models`.
2. Las pruebas deben seguir pasando en verde (100% éxito) con el comando `make test`.

## 3. Criterios de Aceptación
- [ ] No existe ninguna línea de código SQL duro en `facade.py` ni en `domain/models.py`.
- [ ] `facade.py` importa y delega su trabajo a `infra.repository`.
- [ ] Ejecutar `make test` arroja un resultado exitoso sin errores de importación.
- [ ] Los DTOs viven exclusivamente en la capa de dominio.
