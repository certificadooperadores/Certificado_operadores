# Requerimientos — Certificado_operadores

Este documento describe qué necesita el usuario y el sistema para ejecutar
`Certificado_operadores`, y qué debe hacer el sistema (requisitos funcionales y no
funcionales).

## 1. Requisitos de software

| Componente | Versión mínima | Notas |
|------------|----------------|-------|
| Sistema operativo | <!-- p. ej. Windows 10+, macOS 12+, Ubuntu 22.04+ --> | |
| Python | <!-- p. ej. 3.13 --> | Fijado en `.python-version`. |
| `uv` | Última estable | Gestor de entornos y dependencias. |
| Git | Última estable | Control de versiones. |
| <!-- otro runtime --> | | |
| Navegador | <!-- p. ej. Chrome/Edge/Firefox recientes --> | Solo si aplica. |

## 2. Requisitos de hardware mínimo

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| CPU | <!-- núcleos / arquitectura --> | |
| RAM | <!-- p. ej. 4 GB --> | |
| Disco | <!-- p. ej. 1 GB libres --> | |
| GPU | <!-- si aplica --> | |
| Red | <!-- p. ej. conexión para dependencias --> | |

## 3. Dependencias externas

| Servicio / API | Uso | Cómo obtenerlo |
|----------------|-----|----------------|
| <!-- p. ej. base de datos --> | | |

## 4. Requisitos funcionales

- **RF-01:** <!-- el sistema debe ... -->

## 5. Requisitos no funcionales

- **RNF-01 (rendimiento):** <!-- ... -->
- **RNF-02 (seguridad):** <!-- ... -->
- **RNF-03 (disponibilidad):** <!-- ... -->

## 6. Instalación y verificación

```bash
git clone certificadooperadores.git
cd certificado-operadores
uv sync
make check
```

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
