# Tareas — 003-smart-match-explanation Explicación de Smart Match

- **Estado:** ACTIVE

> Spec activa en G04 sobre `feature/smart-match-explanation`. Ejecutar solo las tareas
> de este archivo, por bloques, dejando los gates en verde en cada uno.

## Contrato y diseño

- [ ] Aprobar schemas de entrada y salida.
- [ ] Definir allowlist de hechos y límite de palabras.
- [ ] Definir política de errores y PII.
- [ ] Definir la autenticación mínima de servicio (header, credencial, comparación y
      respuesta 401).

## Implementación

- [ ] Implementar validaciones de dominio.
- [ ] Implementar prompt y caso de uso.
- [ ] Implementar la dependencia de autenticación con `X-Service-Key`, `SecretStr` y
      comparación en tiempo constante.
- [ ] Implementar endpoint protegido por esa dependencia.
- [ ] Implementar validador de fidelidad de salida.

## Pruebas y cierre

- [ ] Añadir pruebas de fidelidad e inyección.
- [ ] Añadir pruebas de error y timeout.
- [ ] Añadir pruebas de 401 (sin credencial y con credencial incorrecta).
- [ ] Ejecutar gates y actualizar evidencia.

## Cierre

- [ ] Actualizar `checklist.md` y `evidence.md` con resultados reales.
- [ ] Ejecutar `ruff check .`, `mypy src` y `pytest`.
- [ ] Revisar seguridad y ausencia de secretos/PII.
- [ ] Cambiar el estado a IMPLEMENTED solo al cumplir todo.
