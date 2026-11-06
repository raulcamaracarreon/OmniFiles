# CONTINUIDAD DE PROYECTO · OmniFiles (síntesis Double Commander + Everything)

**Versión del registro:** 1.0  
**Fecha de corte:** 2026-11-05 (hora CDMX)  
**Proyecto:** OmniFiles (nombre de trabajo, no definitivo)  
**Entregable de esta sesión:** investigación documental, especificación de arquitectura y prototipo Python/PySide6 0.1.

> **Instrucción para retomar:** leer este archivo junto con `README.md`, `docs/01_AUDITORIA_COMPARATIVA.md`, `docs/02_ARQUITECTURA_Y_ALCANCE.md` y la salida de pruebas más reciente. **No afirmar que se ha ejecutado REA, que la interfaz funciona en Windows o que el producto está terminado sin pruebas adicionales.**

## 1. Origen y alcance acordados

El usuario buscaba inicialmente software para administrar varias unidades en una PC Windows. Mostró capturas de **cuatro volúmenes lógicos**:

- C: 953 GB, 406 GB libres (captura).
- D: 111 GB, 10.2 GB libres (unidad con mayor presión de espacio).
- E: 953 GB, 408 GB libres.
- F: 931 GB, 601 GB libres.

Las letras visibles no confirman la cantidad de **discos físicos**. Se planteó inicialmente un administrador integral (salud, RAID, particiones, respaldos), pero el usuario **redefinió el objetivo**: un explorador de archivos práctico, búsqueda rápida, gestión simple, funciones básicas, preferentemente freeware o desarrollado de forma propia.

Se evaluaron **Double Commander** como referente para administrar archivos y **Everything** como referente de búsqueda. El usuario preguntó si podía utilizarse **REA (Reverse Engineer Anything)** para analizarlos y sintetizar una aplicación. Se aceptó realizar una auditoría, diseño y prototipo, más este documento de continuidad.

## 2. Decisiones tomadas

1. **No construir una «navaja suiza»:** concentrarse en navegación, búsqueda, organización básica y uso diario.
2. **No empezar con descompilación:** Double Commander tiene código abierto GPL-2.0; Everything ofrece SDK/IPC y cliente ES.
3. **REA condicionado:** utilizarlo solo ante preguntas del binario/comportamiento no resueltas por fuentes públicas. El plan está en `03_REA_PLAN_DE_VERIFICACION.md`.
4. **Prototipo PySide6:** interfaz local Windows 10/11, adaptable a otras plataformas donde Qt funcione.
5. **Búsqueda:** Everything estándar + ES cuando están disponibles; respaldo local *acotado a la carpeta activa*.
6. **Seguridad:** versión 0.1 solo lectura respecto a archivos del usuario; nada de borrar, mover, renombrar, particionar o formatear.
7. **Independencia del software de terceros:** no se han copiado ni distribuido códigos/binarios de Double Commander/Everything.
8. **Configuración propia:** archivo JSON de favoritos y ubicación de ES en `%LOCALAPPDATA%\OmniFiles\settings.json`.
9. **Sin publicación ni deploy:** no se creó repositorio GitHub, Release ni instalador por cuenta del usuario.

## 3. Estructura del proyecto

```text
Explorador_Sintesis_v0.1/
├─ README.md
├─ requirements.txt
├─ run_windows.bat
├─ .gitignore
├─ omnifiles/
│  ├─ __init__.py
│  ├─ __main__.py
│  ├─ core.py
│  ├─ search.py
│  └─ app.py
├─ tests/
│  ├─ test_core.py
│  └─ test_search.py
└─ docs/
   ├─ 01_AUDITORIA_COMPARATIVA.md
   ├─ 02_ARQUITECTURA_Y_ALCANCE.md
   ├─ 03_REA_PLAN_DE_VERIFICACION.md
   ├─ 04_CONTINUIDAD_PROYECTO.md
   └─ 05_PRUEBAS_EN_WINDOWS.md
```

## 4. Estado funcional al corte

### Escrito e implementado

- Tarjetas de volúmenes montados con barra de ocupación (Qt `QStorageInfo`).
- Explorador de una sola vista con rutas, historial, botón subir, inicio, actualización y apertura de archivos (Qt `QFileSystemModel`).
- Marcadores/favoritos persistidos en JSON.
- Búsqueda ES mediante `subprocess` (sin shell) con resultados y timeout; requiere Everything ejecutándose e `es.exe` independiente.
- Búsqueda local por nombre, limitada en duración y directorios; no sigue enlaces de directorios.
- Worker Qt para búsquedas y botón de cancelación; resultados en vista separada.
- Menú contextual para abrir o **copiar ruta**, no copiar archivo.

### Deliberadamente ausente

- Copiar, mover, borrar, renombrar, crear carpetas, sobrescribir, duplicados, previews, treemaps, S.M.A.R.T., particiones, RAID, pestañas, installer/EXE.
- Registro/historial de operaciones: reservado para cuando existan operaciones mutables.
- Integración directa al DLL SDK: en 0.1 se usa ES CLI.

### Verificación realizada

- **Revisión documental:** fuentes oficiales de Double Commander, voidtools ES/SDK, REA, Qt.
- **Pruebas unitarias Python:** 8 de 8 pruebas OK con `python -m unittest discover -s tests -v` (lógica de rutas, buscador local y adaptador ES simulado).
- **Compilación sintáctica:** `python -m compileall -q .`.
- **GUI:** no validada en Windows durante esta sesión porque la ejecución se creó en un entorno sin PySide6 y sin las unidades de destino. Se intentó instalar PySide6 en el entorno de generación, pero el índice disponible no ofreció el paquete; **no hubo prueba visual**.
- **Everything real:** no probado en el equipo del usuario.
- **REA real:** no ejecutado. La auditoría fue documental, no análisis binario.

## 5. Riesgos y preguntas abiertas

**Prioridad alta:**

- Validar apertura de interfaz, navegación, tarjetas, Unicode y búsqueda ES en Windows real.
- Corroborar si Everything estándar y ES ya están instalados; si no, instalarlos desde sitios oficiales solo tras decisión del usuario.
- Revisar que `es.exe` entregue rutas completas por cada línea y en codificación correcta.
- Verificar permisos/rutas largas/unidades no disponibles y que cancelar búsqueda no deje hilos activos.

**Prioridad media:**

- Refinar UX según preferencias reales: una columna vs doble panel, pestañas, controles compactos, estilo oscuro/claro.
- Definir acciones del primer gestor de archivos seguro: copiar, mover, renombrar con confirmaciones y sin sobreescritura automática.
- Diseño de índice/tabla de resultados para búsquedas grandes y filtros visuales.

**Antes de distribuir:**

- Seleccionar licencia del código propio.
- Cumplir licencias de Qt/PySide6 y de cualquier componente externo redistribuido.
- Empaquetar con PyInstaller o equivalente **solo tras** pruebas en el equipo real.

## 6. Próximos pasos concretos, en orden

1. En Windows, descomprimir el ZIP en una carpeta elegida por el usuario.
2. Abrir PowerShell en esa carpeta y preparar entorno: `python -m venv .venv`; instalar dependencias según README.
3. Ejecutar las pruebas unitarias; conservar el resultado.
4. Lanzar `python -m omnifiles`, comprobar unidades reales y navegación; no manipular archivos importantes.
5. Probar fallback local en carpeta temporal con nombres acentuados.
6. Configurar Everything estándar + ES; probar búsqueda `informe`, `*.pdf` y nombres Unicode. Registrar versiones y resultado.
7. Corregir cualquier defecto observado **solicitando los archivos pertinentes del proyecto antes de proponer modificaciones al código**. Proponer instrucciones de cambios localizables para principiantes.
8. Seleccionar y planificar fase 0.2 de operaciones seguras. REA solo si aparece un problema específico no resuelto por fuentes públicas.

## 7. Criterios mínimos para dar 0.1 por validada

- La ventana abre y cierra sin errores ni hilos colgantes.
- Se reconocen exactamente los volúmenes montados por Windows, con capacidades razonables.
- Se puede entrar en una carpeta, regresar, abrir archivo y copiar ruta.
- Favoritos persisten y no afectan a Windows Explorer.
- Sin Everything se ve confirmación previa a la búsqueda local y se informa que es parcial.
- Con Everything estándar en marcha se devuelven rutas correctas, incluidas tildes y espacios.
- Ninguna operación altera archivos del usuario (excepto configuración propia).

## 8. Fuentes primarias

- https://doublecmd.github.io/doc/en/about.html
- https://github.com/doublecmd/doublecmd
- https://www.voidtools.com/support/everything/sdk/
- https://www.voidtools.com/support/everything/command_line_interface/
- https://www.voidtools.com/support/everything/installing_everything/
- https://github.com/voidtools/ES
- https://github.com/morluto/rea
- https://github.com/morluto/rea/blob/main/.agents/skills/reverse-engineer-anything/SKILL.md

## 9. SOTA (resumen para el siguiente agente/sesión)

**SOTA 2026-11-05:** el usuario decidió reducir el alcance de un administrador general de discos a un **gestor cotidiano de archivos con búsqueda global**, inspirado en Double Commander y Everything. El trabajo entregado consiste en **auditoría documental**, arquitectura y prototipo 0.1 PySide6 con exploración de volúmenes, carpetas, favoritos y búsqueda ES/fallback. **REA todavía no se ejecutó**, porque no es necesario para estudiar código abierto o usar el SDK, y falta un caso concreto de comportamiento binario. **Ninguna función de copia/movimiento/borrado está activa en 0.1.** Pendiente crucial: validación de GUI y búsqueda ES en Windows real, antes de ampliar el alcance.


## 10. Actualización de continuidad (2026-11-05/06)

- Repositorio GitHub confirmado: https://github.com/raulcamaracarreon/OmniFiles
- Se decidió usar GitHub como fuente de verdad para permitir desarrollo y pruebas de uso en paralelo.
- Rama \`main\`: base de trabajo 0.1 con navegación validada visualmente por el usuario en Windows. Rama \`develop\`: cambios posteriores en integración. Ramas \`feature/*\` para funcionalidades aisladas, PR para revisión.
- Primera prueba de usuario: la aplicación abre, muestra C:, D:, E:, F: y G: y permite navegación. En una búsqueda sin \`es.exe\`, muestra correctamente advertencia de búsqueda local limitada. Esta observación **no equivale a haber validado** Everything/ES.
- Las 8 pruebas unitarias locales de Python siguen pasando en el entorno de preparación.
- No usar GitHub Actions por el momento. Las pruebas automáticas se ejecutan localmente y las pruebas de uso en Windows las realiza el usuario, registrando resultados.
- Prioridad siguiente: comprobar búsqueda real con Everything estándar + ES; después diseñar acciones seguras de gestión de archivos.
- Evitar modificaciones destructivas, automatismos de movimiento y alteraciones de particiones sin plan de pruebas y confirmación.
- Al reanudar, revisar \`docs/06_FLUJO_GITHUB.md\` y Issues/PR activos antes de modificar código.
