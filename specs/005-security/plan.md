# Plan — 005-security Seguridad de servicio e IA

- **Estado:** ACTIVE
- **Depende de:** 001-foundation, 002-provider-abstraction, 003-smart-match-explanation,
  011-llm-provider
- **Plan aprobado:** 2026-11-17
- **Rama:** `feature/security-hardening`

## Enfoque técnico

1. Partir del threat model y clasificar datos por sensibilidad (apéndice de la spec).
2. Extender el guard de autenticación de 003 con rotación de dos claves y comparación
   contra todas, sin mTLS (D2).
3. Fijar la allowlist de campos del prompt con un test de regresión del schema.
4. Añadir el corpus versionado y la normalización de salida contra homoglifos.
5. Añadir rate limiting por fingerprint del cliente en memoria, con 429 y `Retry-After`.
6. Añadir headers de seguridad y logging de 401/429 con metadatos acotados.
7. Documentar secret scanning, push protection y Dependabot; ejecutar `pip-audit` en CI
   con `continue-on-error` (D8).

## Pasos previstos (bloques)

1. **B0 (docs):** activar 005, corregir lo desactualizado y registrar D1–D12.
2. **B1:** rotación de clave (`GENAI_SERVICE_KEY_PREVIOUS`, fail closed).
3. **B2:** allowlist de PII y test del schema.
4. **B3:** corpus de inyección y normalización de salida.
5. **B4:** rate limiting, 429 y `Retry-After`.
6. **B5:** headers de seguridad y verificación de OpenAPI.
7. **B6:** logging de seguridad (401/429 con request_id, reason y fingerprint).
8. **B7:** `pip-audit` en CI y documentación del escaneo en GitHub.
9. **B8:** cierre SDD, evidencia y PR.

## Archivos previstos

- `src/thehouse_genai/api/auth.py` (rotación; comparación contra todas las claves).
- `src/thehouse_genai/api/rate_limit.py` (nuevo; fixed window en memoria).
- `src/thehouse_genai/api/middleware.py` (headers de seguridad).
- `src/thehouse_genai/api/errors.py` (propagación de `Retry-After`).
- `src/thehouse_genai/infrastructure/config.py` (clave anterior y ajustes de rate limit).
- `src/thehouse_genai/infrastructure/redaction.py` (nuevo; fingerprint de la clave).
- `src/thehouse_genai/infrastructure/logging.py` (allowlist de campos de log).
- `src/thehouse_genai/domain/match_explanation.py` (allowlist de campos del prompt).
- `src/thehouse_genai/application/explain_match.py` (NFKC + confusables + ancho cero).
- `tests/fixtures/prompt_injection_corpus.json` (nuevo; corpus versionado).
- `tests/test_key_rotation.py`, `tests/test_pii_allowlist.py`,
  `tests/test_prompt_injection_corpus.py`, `tests/test_rate_limit.py`,
  `tests/test_security_headers.py`, `tests/test_security_logging.py`,
  `tests/test_ci_security.py` (nuevos), además de ampliaciones de `test_config.py`,
  `test_errors.py`, `test_generative_api.py`, `.env.example` y `README.md`.
- `.github/workflows/ci.yml` (`pip-audit` con `continue-on-error`).
- Runbook: apéndice de `spec.md` (D7); no se crea `docs/`.

## Estrategia de pruebas

- Clave actual y anterior aceptadas; solo anterior → 401; `SERVICE_KEY_PREVIOUS`
  genérica ignorada; ambas claves comparadas incluso cuando la actual coincide.
- Acceso sin credencial → 401; todos los rechazos comparten el mismo sobre.
- Token de usuario no se acepta ni se propaga; allowlist del schema exacta.
- Logs de 401/429 con `request_id`, `reason` y fingerprint; sin clave ni body.
- Corpus de inyección sin red: hechos y schema inalterados; salida normalizada.
- Rate limit: 429 con sobre estándar y `Retry-After`; sin clave no se consume cupo.
- Headers presentes en éxito, 401, 413, 422 y 429; OpenAPI apagada en producción.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Confundir auth de usuario con auth de servicio | Contrato explícito y pruebas negativas. |
| PII en prompts o logs | Allowlist de campos y tests de regresión del schema. |
| Prompt injection | Datos delimitados, validación de salida y normalización de homoglifos. |
| Filtrar qué clave rotada coincidió | Comparar siempre todas con `|=`. |
| Agotar el bucket de Backend sin clave | Auth antes del rate limit. |
| Abuso de coste | Rate limit por fingerprint antes del proveedor; fallback en 429 del vendor. |
| Límite no global con varias réplicas | Documentado; trasladar al gateway en G09/G10. |
| Ruido del escaneo de dependencias | `pip-audit` con `continue-on-error`. |

## Puerta de salida

- Criterios de aceptación verificados y checklist completo.
- `ruff check .`, `mypy src` y `pytest` en verde.
- Evidencia registrada, sin secretos y con revisión de seguridad cuando aplique.
- Solo entonces se cambia el estado a IMPLEMENTED.
