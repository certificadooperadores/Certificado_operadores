# Plan 011 — Refactorización UI: Reporte Comportamientos

| Campo  | Valor                          |
|--------|--------------------------------|
| Spec   | [`011-spec.md`](./011-spec.md) |
| Autor  | Ing. Miguel Angel Ortiz Roldan |
| Fecha  | 2026-10-09                       |

## 1. Enfoque

Desacoplar la autenticación del usuario en el punto de entrada principal `src/certificado_operadores/Inicio.py`, delegando la validación en `UsuariosFacade.autenticar()` y eliminando cualquier sentencia SQL o uso de bibliotecas criptográficas directas en la interfaz.

## 2. Arquitectura y capas

```text
UI (Streamlit `Inicio.py`)  →  UsuariosFacade  →  Domain (ResultadoAutenticacion)  →  Infra (UsuariosRepository + Seguridad)  →  SQLite
```

El punto de entrada `Inicio.py` queda 100% libre de SQL y consultas a base de datos.

## 3. Archivos afectados

| Archivo | Acción (crear/modificar) | Nota |
|---------|--------------------------|------|
| `src/certificado_operadores/domain/usuarios.py` | modificar | DTO `ResultadoAutenticacion` y constantes de login |
| `src/certificado_operadores/infra/usuarios_repository.py` | modificar | Método `obtener_para_autenticacion()` |
| `src/certificado_operadores/facade_usuarios.py` | modificar | Método `autenticar(usuario, contrasena)` |
| `src/certificado_operadores/Inicio.py` | modificar | Delegación de login a `UsuariosFacade` |
| `tests/test_autenticacion.py` | crear | Pruebas unitarias de casos de autenticación |

## 4. Orden de implementación

1. Extender `domain/usuarios.py` con DTO y mensajes de autenticación.
2. Añadir método en `infra/usuarios_repository.py` para obtener credenciales seguras.
3. Implementar `autenticar()` en `facade_usuarios.py` usando `verificar_contrasena`.
4. Refactorizar `Inicio.py` reemplazando `run_query` y `bcrypt`.
5. Crear pruebas unitarias en `tests/test_autenticacion.py`.
6. Validar con `uv run pytest` y `make test`.

---

**Autor:** Ing. Miguel Angel Ortiz Roldan
