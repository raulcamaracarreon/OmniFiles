# 03 · Investigación dirigida con REA (plan, sin ejecución)

**Objetivo:** reservar la ingeniería inversa para preguntas que la documentación y el código fuente no resuelvan. Este documento NO representa resultados de una sesión REA real.

## Condiciones previas

- Tener legalmente instaladas o descargadas las versiones de Double Commander y Everything que se deseen examinar.
- Registrar ruta, arquitectura, hash SHA-256, versión y procedencia de cada binario **antes** del análisis.
- Configurar REA desde el repositorio oficial `https://github.com/morluto/rea`; revisar requisitos y plan de instalación de la versión realmente publicada.
- Definir una pregunta comprobable de ingeniería inversa, no una instrucción genérica de «clonar el programa».
- Preferir documentación y SDK de Everything; preferir código abierto y pruebas de comportamiento de Double Commander.
- Ejecutar análisis estático y de solo lectura inicialmente. Observar procesos o instrumentarlos solo con autorización y límites claros.

## Preguntas que sí podrían justificar REA

| Pregunta | Fuente primero | ¿Usar REA si no basta? | Evidencia esperada |
|---|---|---|---|
| ¿Cómo se comunican Everything y ES cuando falla IPC? | Docs SDK + logs ES | Sí, si hay una incompatibilidad concreta | Versiones, funciones llamadas, códigos de error |
| ¿Por qué un archivo con caracteres Unicode aparece incorrectamente? | CLI ES y pruebas de codificación | Sí, si hay comportamiento inexplicable | Bytes de salida, codificación, trazas |
| ¿Qué comportamiento tiene una cancelación en Double Commander? | Código fuente + prueba en carpeta temporal | Rara vez | Secuencia observable y protección ante fallo |
| ¿Qué estructura usa Double Commander para la cola de copias? | Código GPL disponible | No como primera opción | Archivos y funciones de código abierto |
| ¿Cómo recrear la velocidad de indexación de Everything? | SDK, requisitos y arquitectura conocida | **No** como tarea inicial | Usar IPC en vez de reconstruir motor propietario |

## Protocolo sugerido de evidencia

1. **Formular hipótesis:** por ejemplo «ES devuelve rutas UTF-8 en Windows 10 para nombres con acentos».
2. **Reproducir caso mínimo** en carpetas de prueba con archivos ficticios y salida guardada.
3. **Documentar observación:** comandos exactos, versión, entorno, salida, fecha.
4. **Contrastar con fuente pública:** documentación ES y código público del cliente ES.
5. **Usar REA si persiste una brecha real:** investigar solamente el binario y el punto de fallo autorizado.
6. **Implementar solución propia:** integrar API pública o adaptar el tratamiento de la salida.
7. **Agregar prueba automatizada:** no aceptar una conclusión sin verificación reproducible.

## Registro de investigaciones (al corte)

| ID | Pregunta | Estado | Resultado |
|---|---|---|---|
| REA-001 | ¿Se necesita decompilar Double Commander para seleccionar funciones? | Cerrada documentalmente | No: código disponible GPL-2.0 |
| REA-002 | ¿Se necesita decompilar Everything para hacer búsquedas? | Cerrada documentalmente | No: usar ES/SDK/IPC oficiales |
| REA-003 | ¿ES entrega rutas Unicode sin pérdida en Windows español? | Abierta | Requiere ejecución real |
| REA-004 | ¿Hay comportamiento de operaciones de archivos que no esté documentado? | Pendiente | Esperar diseño de operaciones |

## Límites de propiedad intelectual

- No usar REA para extraer y copiar una implementación propietaria de búsqueda/indexación cuando exista una API pública y suficiente.
- No mezclar código GPL de Double Commander dentro de una distribución cerrada o de licencia incompatible.
- No redistribuir `Everything.exe`, `es.exe` ni DLL de terceros sin revisar sus términos concretos.
- Conservar las fuentes, versiones y atribuciones de los hallazgos.

## Documentos de referencia

- https://github.com/morluto/rea
- https://github.com/morluto/rea/blob/main/.agents/skills/reverse-engineer-anything/SKILL.md
- https://github.com/morluto/rea/blob/main/docs/installation.md
- https://github.com/doublecmd/doublecmd
- https://www.voidtools.com/support/everything/sdk/
