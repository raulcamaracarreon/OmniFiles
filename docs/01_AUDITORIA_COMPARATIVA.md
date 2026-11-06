# 01 · Auditoría comparativa: Double Commander + Everything

**Fecha de corte:** 2026-11-05  
**Propósito:** seleccionar capacidades para un explorador ligero de archivos para Windows 10/11.  
**Tipo de evidencia:** documentación oficial y repositorios públicos. **No se ejecutó REA sobre binarios ni se realizaron pruebas de esas aplicaciones en el equipo del usuario.**

## 1. Contexto y necesidad real

El caso tiene cuatro **letras de unidad visibles**, de las cuales D: mostraba ~111 GB de capacidad y ~10.2 GB disponibles, mientras que C:, E: y F: conservaban más espacio. Estas letras no equivalen necesariamente a cuatro discos físicos; el software debe mostrar «unidades/volúmenes» y no «discos físicos» hasta tener un inventario de dispositivos.

El objetivo es **encontrar y organizar archivos fácilmente**, no construir una suite de particiones, RAID, S.M.A.R.T. o administración de sistemas. Prioridades: búsqueda global por nombre, navegación clara, operaciones seguras, favoritos y visibilidad básica del espacio.

## 2. Matriz funcional verificada

**Leyenda:** ● disponible según documentación; ◐ disponible o posible con limitaciones; — no es función central corroborada; **MVP**: implementado en el prototipo; **Posterior**: propuesto, no implementado.

| Necesidad | Double Commander | Everything estándar + ES | OmniFiles 0.1 | Prioridad siguiente |
|---|---|---|---|---|
| Navegar carpetas | ● Dos paneles y pestañas | ◐ Lista de resultados, no gestor de doble panel | **MVP:** lista por carpeta | Mejorar navegación |
| Ver unidades y espacio | ◐ Paneles de unidades | ◐ Filtros por volumen | **MVP:** unidades y barras | Mejorar interpretación física/lógica |
| Búsqueda por nombre | ● Búsqueda avanzada | ● Indexada, muy rápida | **MVP:** ES opcional | Verificar Unicode/volúmenes |
| Filtros por tipo/tamaño/fecha | ● Búsqueda avanzada | ● Sintaxis de búsqueda | **MVP**: se pasan consultas a ES | UI de filtros |
| Búsqueda dentro del contenido | ● | ◐ Depende de configuración/funcionalidad | **No** | Posterior |
| Copiar y mover | ● | ◐ Acciones de archivos, no su foco | **No** | Alta: cola segura |
| Renombrado individual/masivo | ● | ◐ No constituye herramienta de renombrado masivo comparable | **No** | Alta |
| Sincronizar directorios | ● | — | **No** | Baja |
| Previsualizar archivos | ● Visor integrado | ◐ Vista previa | **No** | Media |
| Favoritos / accesos rápidos | ● Hotlist | ◐ Marcadores de búsqueda | **MVP:** favoritos de carpetas | Mejorar UX |
| Pestañas | ● | ◐ Ventanas/búsquedas | **No** | Media |
| Historial de operaciones | ● | — | **No** | Alta para cambios |
| Mapas de espacio | — No se confirma treemap nativo | — | **No** | Media, módulo independiente |
| Buscar duplicados | — No se confirma función integrada como módulo principal | — | **No** | Media, fase posterior |
| S.M.A.R.T. | — | — | **No** | Fuera de alcance por ahora |
| Integración con otras apps | ● Extensiones/plugins | ● IPC/SDK y CLI ES | **MVP:** ES por CLI | SDK si hace falta |
| Código fuente accesible | ● GPL-2.0 | **ES** tiene repositorio público bajo MIT; **Everything** no debe asumirse abierto | ● Código propio | Mantener procedencia |

Notas: los grados de disponibilidad de Everything dependen de la versión; la versión **Lite de Everything 1.4 no permite IPC**, por lo que no sirve para consultar ES. ES requiere Everything ejecutándose. Algunas funciones están sujetas a configuración y permisos.

## 3. Hallazgos de arquitectura

### Double Commander

- Aplicación de dos paneles con operaciones asíncronas, pestañas, búsqueda de contenido, renombrado múltiple, sincronización, visor y registro de operaciones.
- Código fuente público, distribuido bajo **GPL-2.0**. La documentación y el repositorio son la primera fuente de estudio. No es razonable decompilar para descubrir funciones visibles en el código.
- Diseño a rescatar: operaciones desacopladas de la vista, comandos previsibles, retroalimentación, atajos y trazabilidad.
- No se copiará código GPL a una aplicación que pretenda distribuirse bajo licencia incompatible. Inspirarse en patrones de interacción no equivale a copiar implementación.

### Everything y ES

- Everything es un **motor externo de indexación y búsqueda por nombres y rutas** con un SDK de consultas IPC y un cliente de línea de comandos llamado ES.
- El SDK necesita que Everything esté ejecutándose. ES es la primera integración recomendada: contrato pequeño, fácil de observar y revertir.
- El prototipo 0.1 usa `subprocess` con lista de argumentos (`shell=False`), límite de resultados y tiempo de espera. No descarga ni instala Everything, ni necesita privilegios de administrador.
- El uso del SDK/DLL directamente puede evaluarse después, si ES introduce problemas de latencia, salida Unicode o despliegue.
- La cobertura real depende de qué volúmenes indexa Everything; no prometer búsqueda global en unidades no indexadas.

### REA (Reverse Engineer Anything)

- Herramienta local de investigación por CLI/MCP para inspeccionar binarios y comportamiento con evidencia.
- Su guía oficial indica **evitar REA para análisis ordinario de repositorios con código disponible** y usarlo cuando una pregunta dependa de un binario distribuido, trazas reales o comportamiento que la fuente no explica.
- **No se ha ejecutado REA en este trabajo.** No se cuenta aquí con los binarios instalados en el equipo del usuario ni con trazas de ejecución de ambos programas. El plan de investigación se documenta en `03_REA_PLAN_DE_VERIFICACION.md`.

## 4. Recomendación de producto

**No combinar dos productos completos.** Construir una interfaz propia con:

1. Exploración de carpetas y unidades con Qt `QFileSystemModel`.
2. Motor de búsqueda por adaptador: Everything ES opcional; modo local acotado como respaldo.
3. Barra de acciones seguras y verificación previa cuando lleguemos a copiar/mover/renombrar.
4. Favoritos, historial y filtros de búsqueda útiles, sin complejidad de administración de particiones.

## 5. Lo que sigue sin comprobarse

- Comportamiento real de Everything ES en un Windows 10 en español, especialmente Unicode y la compatibilidad de todas las opciones elegidas.
- Cantidad de volúmenes que Everything indexa en esa computadora y si existe ya una instalación.
- Distribución física de C:, D:, E: y F:; no inferir de las letras.
- Reacción de Qt ante discos desconectados, rutas protegidas y archivos en uso.
- Efectividad relativa en velocidad; **no se realizaron benchmarks**.

## 6. Fuentes de evidencia (consultadas 2026-11-05)

1. Double Commander, descripción de capacidades y licencia: https://doublecmd.github.io/doc/en/about.html
2. Documentación completa y funciones: https://doublecmd.github.io/doc/en/
3. Repositorio y licencia: https://github.com/doublecmd/doublecmd
4. Everything SDK IPC: https://www.voidtools.com/support/everything/sdk/
5. Everything ES, opciones/errores: https://www.voidtools.com/support/everything/command_line_interface/
6. Descargas oficiales de Everything/ES: https://www.voidtools.com/downloads/
7. Diferencias instalador/Lite: https://www.voidtools.com/support/everything/installing_everything/
8. Repositorio de ES: https://github.com/voidtools/ES
9. REA oficial: https://github.com/morluto/rea
10. Guía REA de uso condicionado: https://github.com/morluto/rea/blob/main/.agents/skills/reverse-engineer-anything/SKILL.md
