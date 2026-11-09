# 008-testing — Estrategia de pruebas

- **Estado:** PLANNED
- **Depende de:** 001-foundation, 002-provider-abstraction
- **Habilita:** 009-ci-cd, 010-integration-thehouse
- **Fecha de alta:** 2026-11-08

## Objetivo

Completar la estrategia de pruebas del servicio: unitarias, integración, contrato, seguridad y regresión, deterministas y sin red.

## Contexto

G01 cuenta con 21 pruebas de health, configuración, errores y límites. Las specs generativas requieren contratos estables, fake provider y pruebas de guardrails.

## Alcance

### Incluido

- Pirámide de pruebas y responsabilidades por capa.
- Fixtures canónicas de match y búsqueda.
- Contract tests de los endpoints futuros.
- Pruebas de seguridad y prompt injection.
- Cobertura mínima acordada para domain/application.
- Política de no-red, determinismo y control de flakiness.

### Excluido

- Load testing completo y caos.
- Pruebas E2E con Backend real (spec 010).
- Certificación externa.

## Requisitos

- **RF-01:** unitarias de domain/application sin FastAPI ni red.
- **RF-02:** integración de API con TestClient y settings de test.
- **RF-03:** contrato de request/response para endpoints generativos.
- **RF-04:** fake provider obligatorio; CI sin red.
- **RF-05:** pruebas de seguridad y prompt injection.
- **RF-06:** cobertura mínima acordada y reportada.
- **RF-07:** tests deterministas y con timeout.

## Criterios de aceptación

- [ ] Estrategia y fixtures documentadas.
- [ ] Contract tests de explain-match y parse-search.
- [ ] Suite sin red y reproducible.
- [ ] Cobertura mínima alcanzada.
- [ ] Pruebas de seguridad integradas.
- [ ] CI ejecuta todo de forma bloqueante.

## Seguridad y privacidad

- Fixtures sin PII ni secretos reales.
- Pruebas negativas de auth, PII y límites.
- No usar credenciales reales en tests.
- Registrar fallos sin volcar prompts sensibles.

## Fuera de esta spec

No se implementa nada de este documento en G01. La spec permanece PLANNED hasta que
el Backend, la seguridad y los contratos estén aprobados y sea su turno.
