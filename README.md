# OmniFiles — explorador de archivos (prototipo 0.1)

Aplicación de escritorio para Windows escrita en Python y PySide6. Incorpora navegación por unidades y carpetas, favoritos, búsqueda local limitada y búsqueda global opcional mediante **Everything + ES**.

## Estado

**0.1: validación de uso inicial en Windows.** Se han superado 8 pruebas unitarias de lógica, pero la integración real con Everything todavía debe validarse.

- Navegar por carpetas y unidades C:, D:, E:, F: (y otras montadas)
- Consultar el espacio libre y ocupado de cada unidad lógica
- Abrir archivos y carpetas, copiar rutas, guardar favoritos
- Buscar con Everything estándar + `es.exe`, o usar búsqueda local acotada sin Everything

**No implementa:** copiar, mover, borrar ni renombrar archivos; no modifica particiones.

## Instalación

Desde PowerShell, en la raíz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m omnifiles
```

Para las pruebas:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Everything

Instalar [Everything estándar](https://www.voidtools.com/downloads/) y [ES](https://github.com/voidtools/ES/releases), mantener Everything abierto y seleccionar el ejecutable `es.exe` desde el botón **Configurar ES**.

La búsqueda local sin ES se limita a la carpeta actual y subcarpetas; no es una búsqueda global indexada.

## Desarrollo colaborativo

- `main`: versión estable confirmada mediante pruebas de uso.
- `develop`: integración y versiones en evaluación.
- `feature/*`: características independientes.
- No ejecutar GitHub Actions por ahora; las pruebas se realizan localmente.
- Registrar problemas y hallazgos en Issues, y las propuestas de cambios en Pull Requests.

Documentación: `docs/`. La aplicación no redistribuye binarios externos; la licencia del código propio está pendiente de selección.

> Prototipo experimental. Antes de publicar una versión estable es necesario verificar la integración en Windows, derechos de distribución y dependencias.
