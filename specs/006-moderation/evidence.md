# Evidencia — 006-moderation Moderación de contenido

- **Estado:** IMPLEMENTED
- **Fecha:** 2026-11-18
- **Alcance:** A (salida generativa + `safetySettings`)
- **Implementación:** B1–B6 completados sobre la rama `feature/moderation`

## Gates

Salida real de los tres gates al cerrar la spec:

```text
$ .venv\Scripts\python.exe -m ruff check .
All checks passed!

$ .venv\Scripts\python.exe -m mypy src
Success: no issues found in 27 source files

$ .venv\Scripts\python.exe -m pytest
688 passed, 1 warning in 3.99s
```

El warning es el `StarletteDeprecationWarning` heredado de `TestClient` (deuda (e),
registrada para 008). `git diff --check` sin salida: sin errores de whitespace. El
barrido de caracteres CJK/fullwidth y de secretos no produjo coincidencias.

## Commits

```text
$ git log --oneline main..HEAD
357adf7 feat: send gemini safety settings
18b4430 feat: moderate explain-match output with local rules
47980b9 feat: add moderation provider port and local moderator
8078049 feat: add initial moderation lexicon
4c954d6 feat: add moderation policy and local detectors
392b937 docs: activate spec 006 moderation
```

## Verificación manual real (2026-11-18)

Servidor local con Gemini `gemini-3.5-flash-lite`, `safetySettings`
`BLOCK_MEDIUM_AND_ABOVE` y moderación local activos. Petición válida estándar:
`matchScore` 91, UTTT, `$2,800 MXN`, `1.3 km` y servicio `internet`.

Respuesta real:

```json
{
  "explanation": "Habitacion cerca de UTTT tiene una coincidencia de 91% porque cuesta $2,800 MXN, se ubica a 1.3 kilómetros de la universidad y cuenta con internet.",
  "generated": true,
  "promptVersion": "explain_match_v3"
}
```

La salida cita solo hechos del input, `generated=true` y el contrato es el previsto; ni la
moderación local ni los filtros del proveedor bloquearon la respuesta.

**Observación:** en PowerShell 5 los acentos se vieron mal (`kilÃ³metros`) porque
`Invoke-RestMethod` no decodifica la respuesta como UTF-8. Es un problema del cliente de
prueba, no del servicio: la API devuelve JSON UTF-8 válido. Se documenta para la prueba
de integración de G09.

El resto de la suite sigue siendo 100% offline, con el guard `block_network` activo y el
adaptador probado con `MockTransport`.

## Mapeo criterio → tests

| Criterio | Tests |
| --- | --- |
| Política `moderation_v1` aprobada, versionada y probada | `tests/test_moderation_policy.py::test_policy_version_and_priority`, `::test_shipped_lexicon_is_well_formed` |
| Puerto, fake y moderador local probados sin red | `tests/test_moderation_provider.py` (67 tests), `tests/test_import_boundaries.py` |
| Correo, teléfono y URL en la salida degradan a fallback | `tests/test_moderation_output.py::test_pii_and_url_in_the_output_degrade`, `::test_phone_in_the_output_degrades` |
| Léxico ofensivo por palabra completa y allowlist | `::test_fictitious_block_term_blocks`, `::test_fictitious_review_term_reviews`, `::test_offensive_terms_match_only_whole_words`, `::test_allowlist_suppresses_a_lexicon_match` |
| Corpus benigno versionado nunca se bloquea | `::test_benign_corpus_is_versioned_and_complete`, `::test_benign_corpus_is_never_flagged`, `::test_benign_corpus_is_not_flagged_by_a_custom_lexicon` |
| Salida adversa o error del moderador respeta fail-closed | `::test_each_adverse_decision_uses_its_own_reason`, `::test_moderator_errors_degrade_to_unavailable` |
| Logs solo metadatos, nunca contenido | `::test_moderation_logs_are_metadata_only`, `::test_moderation_metadata_is_logged_on_success`, `tests/test_security_logging.py::test_json_formatter_emits_only_allowlisted_extra_fields` |
| `safetySettings` con `BLOCK_MEDIUM_AND_ABOVE`, sin llamada extra | `tests/test_gemini_safety.py` (5 tests), `tests/test_provider_adapter.py` |
| Plantilla de fallback sin título ni presupuesto | `tests/test_moderation_output.py::test_fallback_never_echoes_a_hostile_title`, `tests/test_explain_match.py::test_fallback_has_only_input_numbers_and_mentions_preferences` |
| Contrato `{explanation, generated, promptVersion}` intacto | `::test_benign_output_is_returned_with_the_exact_contract`, `::test_endpoint_keeps_the_contract_when_output_is_blocked`, `tests/test_generative_api.py::test_success_has_the_exact_response_shape` |

## Desviaciones y decisiones registradas

1. **Léxico como archivo de datos.** Las listas versionadas se cargan con
   `load_lexicon()` desde un JSON junto a `domain/moderation.py`. El contenido real lo
   llena y mantiene el equipo a mano; G06 no escribió términos ofensivos en código,
   tests ni documentación, fuera de ese archivo de datos. Los tests inyectan solo
   términos ficticios y `test_shipped_lexicon_is_well_formed` valida el formato.
2. **Moderación sobre la completion cruda.** La normalización tipográfica de 003
   inserta un espacio tras el punto interior de un dominio (`ejemplo.mx` →
   `ejemplo. mx`), lo que ocultaba correos y URLs. La moderación se aplica a la
   completion original, después de la validación y antes de responder.
3. **Plantilla sin título ni presupuesto (A6, D19 de 003).** El título es texto libre
   del arrendador y puede traer PII, ofensas o inyección; el presupuesto es una
   preferencia del estudiante. La plantilla queda reducida a score, precio con moneda,
   distancia, universidad y servicios.
4. **`safetySettings` como refuerzo, no como mecanismo.** La capa determinista local
   es el mecanismo de moderación; los filtros de Gemini viajan en la misma petición.
5. **Sin modo híbrido ni opción B.** Cero llamadas extra a Gemini y sin endpoint de
   contenido de usuarios (deuda (a) en `memoria.md`).
6. **Warning heredado de `TestClient`**, documentado para 008.

## Seguridad y privacidad

- No se escribieron términos ofensivos reales en código, tests ni documentación fuera
  del archivo de datos del léxico; los tests usan únicamente términos ficticios.
- No hay secretos, API keys, tokens ni PII en el repositorio: los barridos del prefijo
  de credencial del proveedor y de la clave local de prueba no produjeron coincidencias.
- Los logs de moderación contienen solo `moderation_decision`, `moderation_category` y
  `policy_version`; nunca el texto moderado, el prompt ni la completion.
- Sin red en la suite: el guard `block_network` sigue activo y el adaptador se prueba
  con `httpx.MockTransport`.
