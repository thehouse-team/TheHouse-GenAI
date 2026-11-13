# Pull Request — TheHouse GenAI

## Spec y fase

- [ ] La PR corresponde a una única spec de `specs/` y a una fase del mapeo de
      `memoria.md`.
- [ ] La spec afectada está `ACTIVE` en `memoria.md`, o la PR es de gobernanza
      (constitución, plantillas, tooling).
- [ ] No se implementa trabajo de specs en estado `PLANNED`.

## Alcance

- [ ] Las tareas implementadas son exactamente las de `task.md` de la spec.
- [ ] No hay cambios fuera del alcance de la spec, salvo `.gitignore`, CI o plantillas.

## Gates

- [ ] `ruff check .` en verde, sin hallazgos.
- [ ] `mypy src` en verde, en modo estricto.
- [ ] `pytest` en verde.
- [ ] `git diff --check` limpio, sin errores de whitespace.

## SDD

- [ ] `checklist.md` actualizado con los criterios verificados.
- [ ] `evidence.md` actualizado con salidas reales (comandos, resultados y commit).
- [ ] `memoria.md` actualizado: estado de specs, decisiones y deuda.

## Seguridad

- [ ] Sin secretos, API keys, tokens ni PII en código, tests, fixtures, logs o
      documentación.
- [ ] Sin `.env` ni credenciales reales versionados.
- [ ] Los logs no incluyen prompts, respuestas, cuerpos ni cabeceras sensibles.

## Proceso

- [ ] La rama no es `main`: se usa `feature/<spec>` o `chore/<tema>`.
- [ ] El merge se hace por pull request y con squash.

## Notas

<!-- Cambios relevantes, decisiones tomadas y riesgos conocidos. -->
