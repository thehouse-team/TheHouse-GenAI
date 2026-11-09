# Plan — 009-ci-cd CI/CD

- **Estado:** PLANNED
- **Depende de:** 001-foundation, 005-security, 008-testing

## Enfoque técnico

1. Conservar el workflow actual y añadir jobs independientes.
2. Separar CI (siempre) de CD (solo entornos protegidos).
3. Gestionar secretos con el gestor del repositorio, nunca en YAML.
4. Documentar promoción y rollback antes de habilitar staging.

## Pasos previstos

1. Revisar y mantener gates actuales.
2. Añadir escaneos de secretos y dependencias.
3. Generar artefacto y SBOM.
4. Configurar staging con aprobación.
5. Documentar y probar rollback.
6. Actualizar SDD y evidencia.

## Archivos previstos

- `.github/workflows/ci.yml`
- `.github/workflows/cd.yml (futuro)`
- `docs/rollback.md (solo si se aprueba)`

## Estrategia de pruebas

- Workflow válido y gates bloqueantes.
- Build reproducible.
- Escaneos detectan un secreto de prueba.
- Rollback simulado en staging.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Pipeline lento | Caché y paralelización moderada. |
| Supply chain | Acciones fijadas y SBOM. |
| Despliegue accidental | Aprobación manual y entornos protegidos. |
| Rollback no probado | Simulación obligatoria antes de habilitar CD. |

## Puerta de salida

- Criterios de aceptación verificados y checklist completo.
- `ruff check .`, `mypy src` y `pytest` en verde.
- Evidencia registrada, sin secretos y con revisión de seguridad cuando aplique.
- Solo entonces se cambia el estado a IMPLEMENTED.
