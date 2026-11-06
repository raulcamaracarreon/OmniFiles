# OmniFiles 0.2 (desarrollo) — buscador autónomo para Windows

Proyecto Python + PySide6; interfaz de exploración y volúmenes heredada de la versión 0.1, con **indexación y búsqueda SQLite propias**. No requiere Everything ni es.exe.

> Esta versión está en la rama de desarrollo feature/indexador-sqlite; **main conserva la 0.1** hasta que el usuario valide el cambio en Windows. No se modifican archivos originales; la aplicación crea una base de datos en %LOCALAPPDATA%\OmniFiles\index.sqlite3.

## Ejecutar y probar en Windows

En PowerShell, tras clonar, cambiar a la rama de prueba:

```powershell
git fetch origin
git switch feature/indexador-sqlite
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m omnifiles
```

Si ya existe .venv, reutilizarlo sin recrearlo. No modificar ni eliminar otros archivos locales con git reset --hard.

## Prueba de uso segura (primera validación)

1. Crear dos carpetas de prueba en una ubicación conocida y agregar archivos ficticios con nombres como informe_UNRC.txt y vacaciones.jpg (no necesitan datos reales).
2. Abrir OmniFiles, pulsar **Indexar carpeta**, elegir la primera y aceptar. Repetir para la segunda.
3. Escribir informe y pulsar **Buscar**: aparecen resultados procedentes de todas las carpetas indexadas.
4. Cerrar OmniFiles y abrirlo nuevamente: la búsqueda debe seguir funcionando sin reindexar.
5. Crear un nuevo archivo en una carpeta indexada. Comprobar que **no** aparece hasta volver a indexar esa carpeta (limitación documentada).
6. Probar **Cancelar índice** sobre una carpeta con varios cientos de elementos: si ya existía un índice anterior, debe conservarse.

**Importante:** la versión 0.2 inicial no actualiza el índice en tiempo real ni indexa automáticamente unidades completas; cada carpeta se selecciona explícitamente. No muestra resultados de archivos nuevos ni eliminados hasta reindexar. El escaneo de una unidad grande puede tardar y consumir E/S. Se omiten enlaces/junctions y algunos elementos no accesibles por permisos.

## Desarrollo

- main: 0.1 sin cambios.
- develop: integración de funciones probadas.
- feature/indexador-sqlite: implementación aislada de la búsqueda independiente.
- Pruebas locales, sin GitHub Actions.
- Seguimiento: [Issue #2](https://github.com/raulcamaracarreon/OmniFiles/issues/2).
- Documentación: docs/ (continuidad en docs/04_CONTINUIDAD_PROYECTO.md).

Licencia del código propio pendiente de selección. No se redistribuyen dependencias externas.
