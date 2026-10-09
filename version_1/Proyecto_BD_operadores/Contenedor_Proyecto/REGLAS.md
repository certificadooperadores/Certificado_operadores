# REGLAS DE TRABAJO — Proyecto BD Operadores

## 1. NUNCA borrar archivos
- Usar solo `edit` con oldString/newString puntuales
- Si hay que renombrar, usar `Move-Item`
- Si hay que crear, usar `write` solo para archivos NUEVOS

## 2. NUNCA reescribir archivos enteros
- No usar `write` para sobrescribir un archivo existente
- Solo modificar líneas específicas con `edit`

## 3. LEER antes de tocar
- Entender el contexto y el código existente antes de modificar
- Verificar imports, funciones, y estructura del archivo

## 4. UN cambio a la vez
- Hacer un cambio, probar, confirmar, luego el siguiente
- No encadenar múltiples modificaciones sin verificar

## 5. GIT para todo
- Commit después de cada cambio funcional
- Si algo falla: `git checkout -- archivo` para restaurar
- `git log` para ver historial
- `git diff` para ver qué cambió

## 6. Sobre el proyecto
- Los archivos de página están en `pages/` con prefijo numérico (1_ al 8_)
- `Inicio.py` es el entry point con login
- No usar `st.navigation()` — usar sistema nativo `pages/`
- Las credenciales van en `.env`, no en el código
- El contenedor se reconstruye solo si cambia el Dockerfile
