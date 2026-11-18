# Tareas — 005-security Seguridad de servicio e IA

- **Estado:** IMPLEMENTED
- **Plan aprobado:** 2026-11-17
- **Cierre:** 2026-11-17
- **Rama:** `feature/security-hardening`

> Spec cerrada en G05. Bloques B0–B8 ejecutados dejando el repo verde después de cada
> uno; resultados reales en `evidence.md`.

## Análisis

- [x] B0: threat model y data flow documentados como apéndice de `spec.md`.
- [x] B0: datos clasificados y decisiones D1–D12 registradas.
- [x] B0: mTLS fuera de alcance (D2); dependencias corregidas.

## Implementación

- [x] B1: rotación de clave con `GENAI_SERVICE_KEY_PREVIOUS`, comparación contra todas
      con `|=` y fail closed si solo hay clave anterior.
- [x] B2: allowlist explícita de campos del prompt y test de regresión del schema.
- [x] B3: corpus JSON versionado y normalización de salida (NFKC + confusables + ancho
      cero); inyección en entrada solo escape y log.
- [x] B4: rate limiting por fingerprint, 429 con sobre estándar y `Retry-After`.
- [x] B5: headers de seguridad y re-verificación de OpenAPI.
- [x] B6: logging de 401/429 con `request_id`, `reason` y fingerprint.
- [x] B7: `pip-audit` en CI con `continue-on-error` y documentación del escaneo en
      GitHub Settings (secret scanning, push protection, Dependabot).

## Pruebas y cierre

- [x] B1–B6: pruebas negativas de auth, rotación, PII, rate limit y logs, sin red.
- [x] B3: corpus de prompt injection versionado y ejecutado sin red.
- [x] B8: actualizar `checklist.md`, `evidence.md` y `memoria.md` con resultados reales.

## Cierre (B8)

- [x] Actualizar `checklist.md` y `evidence.md` con resultados reales.
- [x] Ejecutar `ruff check .`, `mypy src`, `pytest` y `git diff --check`.
- [x] Revisar seguridad y ausencia de secretos/PII/CJK.
- [ ] Abrir PR a `main` con el checklist SDD y squash (pendiente; el usuario abre el PR).
