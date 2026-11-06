# 06 · Flujo de trabajo de GitHub (OmniFiles)

Repositorio: https://github.com/raulcamaracarreon/OmniFiles

## Ramas

- `main`: contiene versión base 0.1 del proyecto. Los cambios que se consideren estables se integran solo tras pruebas.
- `develop`: rama de integración para prototipos/validaciones.
- `feature/<funcion>`: ramas específicas para cada mejora; se propone un pull request a `develop`.

## Ciclo por cambio

1. Revisar README, continuidad y estado actual del repositorio.
2. Acordar alcance: un problema o funcionalidad a la vez.
3. Implementar cambio en rama de trabajo, con pruebas automatizadas locales.
4. Publicar PR con objetivo, cambios, criterios de aceptación y riesgos.
5. El usuario actualiza su repositorio local y ejecuta pruebas de uso en Windows.
6. Registrar hallazgos en el PR o Issues; corregir en la misma rama.
7. Tras validación explícita, integrar a `main` cuando corresponda.

## Comandos básicos de Windows (PowerShell)

Clonar por primera vez:

```powershell
git clone https://github.com/raulcamaracarreon/OmniFiles.git
cd OmniFiles
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m omnifiles
```

Para actualizar en una carpeta clonada **sin descartar cambios locales**:

```powershell
git status --short
git pull --ff-only
```

Si existen cambios locales, revisar el estado y decidir qué conservar antes de hacer pull. No utilizar `git reset --hard` por defecto.

## Política de pruebas y seguridad

- **No usar GitHub Actions**, a menos que el usuario cambie la decisión.
- Las pruebas unitarias se ejecutan localmente; no implican validación visual.
- No ejecutar copias, movimientos, borrados, formateos ni cambios de particiones automáticamente.
- El usuario valida nuevas funciones con archivos desechables en Windows antes de pasar a estable.
- Al cerrar una sesión, actualizar `docs/04_CONTINUIDAD_PROYECTO.md` con decisiones, problemas, versiones y pendientes.
