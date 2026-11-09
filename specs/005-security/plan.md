# Plan — 005-security Seguridad de servicio e IA

- **Estado:** PLANNED
- **Depende de:** 001-foundation, 002-provider-abstraction, 003, 004

## Enfoque técnico

1. Partir de threat model y clasificar datos por sensibilidad.
2. Implementar un guard de autenticación de servicio reutilizable.
3. Centralizar filtros de PII y redacción en infraestructura.
4. Añadir pruebas negativas antes de habilitar endpoints.
5. Integrar escaneos de secretos/dependencias en CI sin bloquear por ruido.

## Pasos previstos

1. Documentar threat model y flujo de datos.
2. Definir e implementar autenticación de servicio.
3. Implementar allowlists y filtro de PII.
4. Implementar redacción y rate limiting.
5. Añadir corpus de prompt injection y pruebas.
6. Integrar escaneos de seguridad en CI.
7. Actualizar SDD y runbook.

## Archivos previstos

- `src/thehouse_genai/api/security.py`
- `src/thehouse_genai/infrastructure/redaction.py`
- `src/thehouse_genai/domain/pii.py`
- `tests/test_security.py`
- `docs/security-runbook.md (solo si se aprueba)`

## Estrategia de pruebas

- Acceso sin credencial → 401; credencial inválida → 401.
- Token de usuario no se acepta ni se propaga.
- PII no permitida se rechaza antes del proveedor.
- Logs no contienen secretos ni PII.
- Prompt injection no cambia hechos ni schema.
- Rate limit responde 429 con sobre estándar.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Confundir auth de usuario con auth de servicio | Contrato explícito y pruebas negativas. |
| PII en prompts o logs | Filtros y redacción con pruebas dedicadas. |
| Prompt injection | Datos delimitados, allowlist y validación de salida. |
| Abuso de coste | Rate limit y presupuesto de tokens/tiempo. |

## Puerta de salida

- Criterios de aceptación verificados y checklist completo.
- `ruff check .`, `mypy src` y `pytest` en verde.
- Evidencia registrada, sin secretos y con revisión de seguridad cuando aplique.
- Solo entonces se cambia el estado a IMPLEMENTED.
