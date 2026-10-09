# Arquitectura y desacoplamiento — Certificado_operadores

Describe cómo está organizado el sistema y cómo se mantienen separadas sus
partes, para poder cambiarlas sin romper el resto.

## 1. Visión general

<!-- Diagrama de contexto. Puede ser ASCII, Mermaid o un enlace a un diagrama
     generado con la skill `archify` (HTML interactivo). -->

```text
[ Entrada / UI ] → [ Casos de uso ] → [ Dominio ] → [ Infraestructura ]
```

## 2. Capas y responsabilidades

| Capa / módulo | Responsabilidad única | Puede depender de |
|---------------|-----------------------|-------------------|
| Presentación / UI | Mostrar y capturar datos. | Casos de uso |
| Casos de uso / aplicación | Orquestar flujos. | Dominio |
| Dominio | Reglas de negocio. | Nada externo |
| Infraestructura | Persistencia, APIs, IO. | Dominio (implementa sus puertos) |

## 3. Dirección de dependencias (reglas duras)

- El **dominio no depende** de frameworks, base de datos ni UI.
- La **UI no accede** directamente a la base de datos.
- Las dependencias se **inyectan**, no se instancian dentro de la lógica.
- Los contratos entre capas son **interfaces / DTOs**, no tipos concretos de una
  tecnología.
- **Prohibido hardcodear ("quemar código"):** sin valores, rutas, credenciales,
  URLs, puertos ni parámetros incrustados. Todo sale de configuración, constantes
  con nombre, variables de entorno o se inyecta.

## 3bis. La UI no ejecuta tareas — patrón Facade

- La interfaz (incluida **Streamlit**) **no** contiene lógica de negocio ni ejecuta
  tareas; solo captura entrada, llama a la **fachada** y muestra el resultado.
- El **Facade** expone los casos de uso y orquesta dominio + infraestructura.

```text
UI / Streamlit  →  Facade (casos de uso)  →  Dominio  →  Infraestructura
```

## 4. Contratos entre módulos

| Contrato | Define | Implementa |
|----------|--------|------------|
| <!-- IPuerto --> | | |

## 5. Puntos de acoplamiento y su mitigación

| Acoplamiento | Riesgo | Mitigación |
|--------------|--------|------------|
| <!-- ... --> | | |

## 6. Decisiones de arquitectura

<!-- Enlaza a docs/adr/ o resume las decisiones clave. -->

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
