# Especificación 026: Exportación Premium del README a PDF con Diagramas

## 1. Contexto y Problema
El archivo `README.md` de la raíz del proyecto es la carta de presentación institucional para la Dirección de Operación de Metrocali S.A.
El usuario requiere disponer de este documento en formato PDF (`docs/README_Certificado_Operadores.pdf`) con los siguientes requisitos indispensables:
- Cero páginas o recuadros en blanco.
- Diagramas de arquitectura (Patrón Facade y Pipeline Operativo) completamente visibles con sus textos y cajas.
- Membrete institucional con logotipo oficial de Metrocali MIO.
- Pie de página institucional completo: "Metrocali S.A. — Dirección de Operación - Evaluación de la Operación | Página X".
- Formato limpio, legible y tipografía corporativa.

## 2. Requerimientos
1. Generar el archivo `docs/README_Certificado_Operadores.pdf` a partir de `README.md`.
2. Utilizar el logotipo de `assets/logo_metrocali.png`.
3. Asegurar que los bloques Mermaid se rendericen íntegramente sin cajas oscuras vacías ni diagramas cortados.
4. **CORRECCIONES CRÍTICAS DETECTADAS EN CICLO 1:**
   - La portada (sección 1) tiene `page-break-after: always;`, lo que causa que las páginas 2 y 3 tengan poco contenido o queden desbalanceadas/en blanco antes del contenido principal. Unificar el documento como flujo continuo natural sin forzar saltos huérfanos innecesarios.
   - En la página 7, el bloque de código de `Estructura del repositorio` genera un gran contenedor oscuro que sufre un salto de página defectuoso, dejando un bloque negro vacío o cortado, y enviando las últimas dos líneas de texto huérfanas a la página 8.
   - Aplicar `page-break-inside: auto;` o reducir el padding vertical de `pre` para que el texto de la estructura del repositorio se vea dentro de su contenedor de forma fluida.
   - Compactar el espaciado para que el documento no sobrepase 5 o 6 páginas completas y bien aprovechadas, sin hojas con solo 2 líneas ni bloques oscuros sin texto.
5. El gate de verificación debe ejecutar la suite de pruebas del proyecto (`make test`) asegurando que ningún cambio afecte el código fuente.
6. Limpiar scripts temporales al finalizar la generación.

## 3. Criterios de Aceptación
- El archivo `docs/README_Certificado_Operadores.pdf` no tiene ninguna página con bloques negros vacíos ni saltos huérfanos.
- Las páginas iniciales (2 y 3) y finales (7 y 8) tienen contenido equilibrado y continuo.
- Los diagramas de arquitectura están dibujados con elementos legibles.
- `make test` pasa en verde con 402 casos aprobados.

