# Tareas — 002-provider-abstraction Abstracción de proveedor LLM

- **Estado:** PLANNED

> No iniciar hasta que la spec sea la activa y su plan esté aprobado.

## Diseño

- [ ] Aprobar DTOs y firma del puerto.
- [ ] Definir taxonomía de errores y política de timeout.
- [ ] Definir estrategia de inyección y configuración.

## Implementación

- [ ] Crear `providers/base.py` con puerto y DTOs.
- [ ] Implementar adaptador httpx.
- [ ] Implementar `FakeLLMProvider`.
- [ ] Validar proveedor/modelo/timeout en `Settings`.

## Pruebas y cierre

- [ ] Añadir tests de contrato, timeout y errores.
- [ ] Añadir test de frontera de imports.
- [ ] Ejecutar ruff, mypy y pytest.
- [ ] Actualizar checklist, evidence y memoria.

## Cierre

- [ ] Actualizar `checklist.md` y `evidence.md` con resultados reales.
- [ ] Ejecutar `ruff check .`, `mypy src` y `pytest`.
- [ ] Revisar seguridad y ausencia de secretos/PII.
- [ ] Cambiar el estado a IMPLEMENTED solo al cumplir todo.
