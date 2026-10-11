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
4. Asegurar que ninguna página (incluidas la 2, 4 y 5) quede vacía o desalineada.
5. El gate de verificación debe ejecutar la suite de pruebas del proyecto (`make test`) asegurando que ningún cambio afecte el código fuente.
6. Limpiar scripts temporales al finalizar la generación.

## 3. Criterios de Aceptación
- El archivo `docs/README_Certificado_Operadores.pdf` existe y tiene tamaño superior a 500 KB con contenido en todas sus páginas.
- Los diagramas de arquitectura están dibujados con elementos legibles.
- `make test` pasa en verde con 402 casos aprobados.
