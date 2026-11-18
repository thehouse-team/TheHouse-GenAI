# Tareas — 005-security Seguridad de servicio e IA

- **Estado:** ACTIVE
- **Plan aprobado:** 2026-11-17
- **Rama:** `feature/security-hardening`

> Spec activa en G05. Ejecutar solo las tareas de los bloques B0–B8 del plan, dejando
> el repo verde después de cada bloque.

## Análisis

- [x] B0: threat model y data flow documentados como apéndice de `spec.md`.
- [x] B0: datos clasificados y decisiones D1–D12 registradas.
- [x] B0: mTLS fuera de alcance (D2); dependencias corregidas.

## Implementación

- [ ] B1: rotación de clave con `GENAI_SERVICE_KEY_PREVIOUS`, comparación contra todas
      con `|=` y fail closed si solo hay clave anterior.
- [ ] B2: allowlist explícita de campos del prompt y test de regresión del schema.
- [ ] B3: corpus JSON versionado y normalización de salida (NFKC + confusables + ancho
      cero); inyección en entrada solo escape y log.
- [ ] B4: rate limiting por fingerprint, 429 con sobre estándar y `Retry-After`.
- [ ] B5: headers de seguridad y re-verificación de OpenAPI.
- [ ] B6: logging de 401/429 con `request_id`, `reason` y fingerprint.
- [ ] B7: `pip-audit` en CI con `continue-on-error` y documentación del escaneo en
      GitHub Settings (secret scanning, push protection, Dependabot).

## Pruebas y cierre

- [ ] B1–B6: pruebas negativas de auth, rotación, PII, rate limit y logs, sin red.
- [ ] B3: corpus de prompt injection versionado y ejecutado sin red.
- [ ] B8: actualizar `checklist.md`, `evidence.md` y `memoria.md` con resultados reales.

## Cierre (B8)

- [ ] Actualizar `checklist.md` y `evidence.md` con resultados reales.
- [ ] Ejecutar `ruff check .`, `mypy src`, `pytest` y `git diff --check`.
- [ ] Revisar seguridad y ausencia de secretos/PII/CJK.
- [ ] Abrir PR a `main` con el checklist SDD y squash; cambiar el estado a
      `IMPLEMENTED` solo al cumplir todo.
