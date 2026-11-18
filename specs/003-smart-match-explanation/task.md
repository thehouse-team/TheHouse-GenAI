# Tareas — 003-smart-match-explanation Explicación de Smart Match

- **Estado:** IMPLEMENTED

> Spec cerrada en G04 sobre `feature/smart-match-explanation`. Las tareas se ejecutaron
> por bloques B1–B7b, con los gates en verde en cada uno.

## Contrato y diseño

- [x] Aprobar schemas de entrada y salida.
- [x] Definir allowlist de hechos y límite de palabras.
- [x] Definir política de errores y PII.
- [x] Definir la autenticación mínima de servicio (header, credencial, comparación y
      respuesta 401).

## Implementación

- [x] Implementar validaciones de dominio.
- [x] Implementar prompt y caso de uso.
- [x] Implementar la dependencia de autenticación con `X-Service-Key`, `SecretStr` y
      comparación en tiempo constante.
- [x] Implementar endpoint protegido por esa dependencia.
- [x] Implementar validador de fidelidad de salida.

## Pruebas y cierre

- [x] Añadir pruebas de fidelidad e inyección.
- [x] Añadir pruebas de error y timeout.
- [x] Añadir pruebas de 401 (sin credencial y con credencial incorrecta).
- [x] Ejecutar gates y actualizar evidencia.

## Cierre

- [x] Actualizar `checklist.md` y `evidence.md` con resultados reales.
- [x] Ejecutar `ruff check .`, `mypy src` y `pytest`.
- [x] Revisar seguridad y ausencia de secretos/PII.
- [x] Cambiar el estado a IMPLEMENTED solo al cumplir todo.
