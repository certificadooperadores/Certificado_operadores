# GUIA DE TRABAJO — Proyecto BD Operadores

## DONDE ESTA TODO

```
Proyecto_BD_operadores/
├── BASE DE DATOS OPERADORESv4.xlsm    ← Excel fuente (no se toca)
├── Iniciar_App_Operadores.bat         ← Lanzador Windows
├── generar_modelo_estrella_maestro.py ← ETL (no se toca)
├── Backups/                           ← Copias de seguridad .sql
├── Modelo_Estrella_Final_CSVs/        ← Datos iniciales
├── Plantillas/                        ← Excel para carga masiva
│
└── Contenedor_Proyecto/               ← DONDE TRABAJAMOS
    ├── .git/                          ← REPO GIT (no tocar)
    ├── Inicio.py                      ← Login + redirige
    ├── db.py                          ← Conexion BD
    ├── utils.py                       ← Badge version
    ├── init_db.py                     ← Inicializa BD
    ├── docker-compose.yaml            ← Contenedores
    ├── Dockerfile                     ← Imagen
    │
    └── pages/                         ← LAS PAGINAS DE LA APP
        ├── 1_Gestion_Usuarios.py
        ├── 2_Administrar_Backups.py
        ├── 3_Modificacion_Tablas.py
        ├── 4_Administracion_Operadores.py
        └── 5_Registro_Eventos.py
```

## COMO NOMBRAR LOS COMMITS

```
tipo: descripción corta

Tipos:
  fix:    corregir un error
  feat:   nueva funcionalidad
  style:  cambio visual o de texto
  refactor: reorganizar sin cambiar logica

Ejemplos:
  fix: login no redirige al dashboard
  feat: badge de version en sidebar
  style: renombrar tabs en operadores
  refactor: mover catalogos a tab separado
```

## COMANDOS DIARIOS

```powershell
# 1. Entrar a la carpeta
cd "C:\Users\maortiz\OneDrive - metrocali.gov.co\Scripts\Proyecto_BD_operadores\Contenedor_Proyecto"

# 2. Ver que cambió
git status

# 3. Guardar cambios
git add .
git commit -m "fix: descripcion"

# 4. Si algo se rompe, volver atras
git checkout -- nombre_archivo
```

## REGLA DE ORO
Antes de tocar cualquier archivo: `git status`
Despues de cada cambio funcional: `git commit`
