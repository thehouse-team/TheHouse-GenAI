# AGENTS.md — Reglas de trabajo

## Lectura obligatoria

Antes de cambiar código, leer `constitution.md`, `memoria.md` y la spec activa completa
(`spec.md`, `plan.md`, `task.md`, `checklist.md`, `evidence.md`). No explorar ni modificar
otros repositorios de TheHouse; este contexto es el contrato de integración inicial.

## Límites duros

- Implementar únicamente la spec activa. En G01 solo `001-foundation` está habilitada.
- No implementar endpoints futuros (`explain-match`, `parse-search`) ni proveedores LLM.
- No calcular Smart Match, consultar propiedades ni duplicar lógica del Backend.
- No incluir Mobile, autenticación de usuarios ni secretos reales.
- No añadir Docker, bases de datos ni servicios externos sin una spec aprobada.
- No registrar tokens, API keys, passwords, cuerpos de request ni PII en logs.
- No devolver stack traces ni mensajes internos al cliente.

## Flujo SDD

1. Confirmar que la spec es la activa y que su plan está aprobado.
2. Implementar solo las tareas de `task.md`.
3. Ejecutar `ruff check .`, `mypy src` y `pytest`.
4. Actualizar `checklist.md` y `evidence.md` con resultados reales.
5. Si la spec se completa, cambiar su estado a `IMPLEMENTED`; el resto sigue `PLANNED`.
6. Registrar decisiones y deuda en `memoria.md`.

## Comandos

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
ruff check .
mypy src
pytest
uvicorn thehouse_genai.main:app --reload
```

## Estructura

```text
src/thehouse_genai/
  api/            HTTP, middleware, errores, health
  application/    casos de uso (futuro)
  domain/         contratos e invariantes (futuro)
  providers/      interfaz LLM y adaptadores (futuro, spec 002)
  infrastructure/ configuración, logging
tests/            unitarias e integración con TestClient
specs/            SDD por incremento
```

## Convenciones

- Código y comentarios en inglés; documentación SDD en español.
- Tipado estricto (`mypy --strict`) y funciones pequeñas.
- Errores de API mediante el sobre único de `api/errors.py`.
- Configuración solo a través de `Settings`; nunca leer `os.environ` disperso.
- Secretos como `SecretStr` y nunca serializados.
- IDs de correlación saneados; no confiar en cabeceras del cliente.

## Definición de terminado

- Criterios de aceptación de la spec verificados.
- Gates en verde y evidencia registrada.
- Sin secretos ni `.env` versionados.
- `git diff --check` limpio.
- Documentación de la spec actualizada.

## Prohibiciones de proceso

- No hacer commit sin tests verdes.
- No marcar specs futuras como implementadas.
- No generar documentación redundante fuera del SDD.
- No desplegar ni configurar un proveedor real.
