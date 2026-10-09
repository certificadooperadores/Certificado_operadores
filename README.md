<div align="center">

# Certificado_operadores

**Aplicación para la gestión del certificado de ideoneida de los operadores del sistema masivo mio, desde su vinculación, formación, supensión, retiro. el objetivo es poder gestionar la información de una manera ordenada y versionada de facil acceso y manipulación**

[![License: Privado](https://img.shields.io/badge/License-Privado-yellow.svg)](./LICENSE)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-fe5196.svg)](https://conventionalcommits.org)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./CONTRIBUTING.md)

</div>

---

## 📖 Descripción general

<!-- Explica qué es el proyecto y para qué sirve. Una o dos secciones breves. -->

> 📘 La verdad técnica central —stack, decisiones, convenciones y flujo— vive en
> [`CONSTITUTION.md`](./CONSTITUTION.md). De lectura obligatoria antes de contribuir.

## 📑 Tabla de contenidos

- [Descripción general](#-descripción-general)
- [Estado del proyecto](#-estado-del-proyecto)
- [Stack tecnológico](#-stack-tecnológico)
- [Primeros pasos](#-primeros-pasos)
- [Calidad y automatización](#-calidad-y-automatización)
- [Estructura del repositorio](#-estructura-del-repositorio)
- [Documentación](#-documentación)
- [Flujo de trabajo y contribución](#-flujo-de-trabajo-y-contribución)
- [Licencia](#-licencia)

## 🚧 Estado del proyecto

| Área                              | Estado |
|-----------------------------------|:------:|
| Estructura del repositorio y entorno (`uv`) | ✅ |
| Constitución y gobernanza         | ✅     |
| Primera funcionalidad             | ⏳     |
| Suite de pruebas                  | ⏳     |

## 🛠️ Stack tecnológico

| Categoría         | Tecnología |
|-------------------|------------|
| **Lenguaje**      | Python 3.13+ |
| **Entorno/deps**  | [`uv`](https://docs.astral.sh/uv/) |
| **Testing**       | [`pytest`](https://docs.pytest.org/) |
| **Lint / formato**| [Ruff](https://docs.astral.sh/ruff/) |
| **Pre-commit**    | [pre-commit](https://pre-commit.com) |
| **CI/CD**         | [GitHub Actions](.github/workflows/ci.yml) |

## 🚀 Primeros pasos

### Requisitos previos

- [Python 3.13+](https://www.python.org/downloads/)
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
- [Git](https://git-scm.com/)

### Instalación

```bash
git clone certificadooperadores.git
cd certificado-operadores

uv sync
uv run pre-commit install   # equivalente a: make dev
```

### Verificación

```bash
make check   # lint + formato + pruebas
```

> ⚠️ **Regla del proyecto:** toda gestión de dependencias y entornos pasa por `uv`.
> Está **prohibido** `pip` y `requirements.txt`.

## ✅ Calidad y automatización

| Herramienta   | Rol |
|---------------|-----|
| [`uv`](https://docs.astral.sh/uv/) | Entornos, dependencias y lockfile determinista. |
| [Ruff](https://docs.astral.sh/ruff/) | Lint y formato. |
| [pre-commit](https://pre-commit.com) | Hooks antes de cada commit. |
| [pytest](https://docs.pytest.org/) | Pruebas unitarias. |

| Comando | Descripción |
|---------|-------------|
| `make help` | Lista los objetivos disponibles. |
| `make dev` | `uv sync` + instala los hooks de pre-commit. |
| `make check` | Verificación completa (lint + formato + pruebas). |
| `make lint` / `make format` | Ruff. |
| `make test` | `pytest`. |

## 📂 Estructura del repositorio

```text
certificado-operadores/
├── src/certificado_operadores/    # código del paquete (src-layout)
├── tests/                   # pruebas
├── docs/                    # documentación detallada
├── CONSTITUTION.md          # verdad central del proyecto
├── README.md                # este archivo
└── CONTRIBUTING.md          # guía de contribución
```

## 📚 Documentación

La documentación detallada vive en [`docs/`](./docs/README.md):

| Documento | Contenido |
|-----------|-----------|
| [docs/requerimientos.md](./docs/requerimientos.md) | Requisitos de software y hardware mínimo. |
| [docs/desacople.md](./docs/desacople.md) | Arquitectura, capas y desacoplamiento. |
| [docs/manual-usuario.md](./docs/manual-usuario.md) | Guía de uso: qué hace cada botón/elemento. |
| [docs/referencia-funciones.md](./docs/referencia-funciones.md) | Todas las funciones, su ubicación y descripción. |

## 🤝 Flujo de trabajo y contribución

> 📘 La guía completa está en [`CONTRIBUTING.md`](./CONTRIBUTING.md). Resumen:

1. Crea una rama: `git checkout -b feat/nombre-corto`.
2. Desarrolla y verifica localmente.
3. Commitea con [Conventional Commits](https://www.conventionalcommits.org/): `git commit -m "feat: ..."`.
4. Abre un Pull Request con la plantilla oficial.
5. Mantén `CONSTITUTION.md` actualizado ante cambios arquitectónicos o tecnológicos.

## 📄 Licencia

Distribuido bajo la licencia Privado. Ver [`LICENSE`](./LICENSE).

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
