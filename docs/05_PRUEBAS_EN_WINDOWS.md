# 05 · Lista de verificación en Windows

No probar sobre archivos importantes. Si se necesitan casos de prueba, crear una carpeta temporal con archivos ficticios de texto.

## Instalación y arranque

- [ ] Abrir PowerShell en la carpeta descomprimida.
- [ ] Confirmar `python --version` y crear `.venv` con `python -m venv .venv`.
- [ ] Instalar `requirements.txt`.
- [ ] Ejecutar `python -m unittest discover -s tests -v`.
- [ ] Ejecutar `.\.venv\Scripts\python.exe -m omnifiles`.
- [x] Verificado por el usuario: OmniFiles abre y muestra unidades C:, D:, E:, F: y G: en Windows.

## Navegación

- [x] Aparecen las unidades lógicas esperadas, incluidas unidades adicionales montadas.
- [x] Se muestra el espacio libre y porcentaje ocupado de cada volumen.
- [ ] Navegar por E:, F: y G: y abrir una carpeta de prueba.
- [ ] Verificar Atrás / Adelante / Subir / Inicio.
- [ ] La ruta introducida es carpeta; una ruta inexistente muestra aviso.
- [ ] Doble clic abre un archivo de prueba con su aplicación.
- [ ] Menú contextual «Copiar ruta» copia texto, no el archivo.
- [ ] Añadir/quitar favorito y reabrir para verificar persistencia.

## Búsqueda sin ES

- [x] Se observó la advertencia de búsqueda local limitada al no detectar es.exe.
- [ ] Buscar un nombre dentro de una carpeta temporal.
- [ ] Confirmar nombres con espacios y tildes.
- [ ] Cancelar y cerrar sin bloqueo.

## Búsqueda con Everything

- [ ] Instalar/elegir Everything estándar (no Lite).
- [ ] Ejecutar Everything e indexar las unidades requeridas.
- [ ] Configurar es.exe desde OmniFiles.
- [ ] Buscar términos sencillos, rutas, `*.pdf` y nombres con acentos.
- [ ] Detener Everything y comprobar aviso adecuado.
- [ ] Probar un volumen alto de resultados (límite 400).

## Defectos

Registrar en GitHub Issues con versión, pasos para reproducir, resultado esperado/observado, traceback y captura si existe.

**Regla:** una prueba unitaria satisfactoria no equivale a una prueba de interfaz o integración. No crear instalador estable antes de validar navegación y Everything en Windows.
