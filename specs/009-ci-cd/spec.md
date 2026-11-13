# 009-ci-cd — CI/CD

- **Estado:** PLANNED
- **Depende de:** 001-foundation, 005-security, 008-testing
- **Habilita:** 010-integration-thehouse
- **Fecha de alta:** 2026-11-08

## Objetivo

Evolucionar el pipeline bloqueante actual hacia entrega segura: escaneos, artefacto, SBOM, despliegue a staging con aprobación y rollback. Sin CD en G01.

## Contexto

G01 ya incluye CI con checkout, Python 3.12, instalación, ruff, mypy y pytest. La entrega continua requiere controles adicionales y no forma parte de foundation.

## Alcance

### Incluido

- Mantener gates actuales como obligatorios.
- Escaneo de secretos y dependencias.
- Build reproducible de artefacto y SBOM.
- Despliegue a staging con aprobación manual.
- Rollback documentado.
- Protección de rama y permisos mínimos.

### Excluido

- Desplegar en G01.
- Elegir infraestructura definitiva sin aprobación.
- Pipeline de Mobile o Backend.

## Requisitos

- **RF-01:** PR y push a main ejecutan ruff, mypy y pytest.
- **RF-02:** los gates son bloqueantes y no se saltan con secretos.
- **RF-03:** escaneo de secretos y dependencias integrado.
- **RF-04:** build de artefacto reproducible con SBOM.
- **RF-05:** staging requiere aprobación y usa secretos gestionados.
- **RF-06:** rollback probado y documentado.
- **RF-07:** permisos mínimos y acciones fijadas.

## Criterios de aceptación

- [ ] CI actual se mantiene en verde y bloqueante.
- [ ] Escaneos integrados sin filtrar secretos.
- [ ] Artefacto y SBOM generados.
- [ ] Staging con aprobación manual.
- [ ] Rollback documentado y probado.
- [ ] Protección de rama activa.

## Seguridad y privacidad

- Secretos solo en el gestor de CI, nunca en logs.
- Acciones de terceros fijadas por versión/commit.
- Permisos mínimos (`contents: read` por defecto).
- Artefacto firmado o verificable cuando aplique.

## Fuera de esta spec

Esta spec permanece `PLANNED` hasta que sea su turno. No se activa hasta que su plan
esté aprobado.
