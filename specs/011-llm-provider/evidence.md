# Evidencia — 011-llm-provider Proveedor LLM real

- **Estado:** ACTIVE
- **Fecha:** 2026-11-16
- **Implementación:** completa (bloques B1 a B8)

## Resultado

Spec activada el 2026-11-15 con el plan aprobado y cerrada el 2026-11-16 tras el
smoke test manual. Existen `evaluation.md` con la matriz de los seis criterios y sus
fuentes, `decision.md` con el proveedor elegido, las alternativas descartadas, las
decisiones de integración D-1 a D-20 y las condiciones de revisión, el adaptador
`GeminiProvider` detrás del puerto, su registro en la factory y el script de smoke
test manual.

## Smoke test manual (B8)

- **Fecha:** 2026-11-16
- **Modelo:** `gemini-3.5-flash-lite` (familia Flash Lite)
- **Capa:** gratuita, proyecto `thehouse-genai` en Google AI Studio
- **Ejecución:** manual y opt-in, fuera de CI, con confirmación explícita
- **Datos:** prompts sintéticos de una vivienda ficticia; sin datos reales ni PII

| Caso | Iteraciones | Latencia min (ms) | Latencia mediana (ms) | Latencia max (ms) | Tokens entrada | Tokens salida | finish_reason | Aviso de deprecación | Errores |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A · texto en español | 3 | 1309.2 | 1445.0 | 1461.3 | 97 | 63 | STOP | no | - |
| B · salida JSON | 3 | 817.0 | 1047.4 | 1171.6 | 99 | 59 | STOP | no | - |

### Observaciones

- El español es natural y usa solo los datos del prompt, sin inventar hechos. Único
  defecto detectado: un espacio faltante ("conuna").
- El JSON devuelto fue válido y con los cinco campos pedidos.
- Ninguna llamada falló: las seis respostas con `finish_reason` `STOP`.
- La credencial no aparece en la salida del script.
- `.env` confirmado como ignorado por git: `git check-ignore -v .env` →
  `.gitignore:2:.env`.
- Ninguna llamada devolvió aviso de deprecación, con lo que `temperature` se aplicó
  sin observancia en este modelo.

### Límites observados del modelo (capa gratuita, vistos en AI Studio)

| Métrica | Valor |
| --- | --- |
| Requests por minuto (RPM) | ~15 |
| Tokens por minuto (TPM) | 250K |
| Requests por día (RPD) | 500 |

### Observación menor

- La confirmación interactiva del script acepta «si» en minúsculas, porque la
  comparación normaliza a mayúsculas. Queda anotado como deuda menor y no se corrige
  en esta spec.

## Evidencia requerida al cerrar

- [x] Matriz de evaluación con los seis criterios y fuentes citadas.
- [x] Documento de decisión aprobado.
- [x] Adaptador implementando `GenerativeAiProvider` y registrado en la factory.
- [x] Test de contrato del adaptador en verde, sin red.
- [x] Errores del vendor mapeados a la taxonomía propia.
- [x] La credencial no aparece en logs, `repr` ni respuestas.
- [x] Timeout y límite de entrada verificados.
- [x] El modelo y su versión aparecen en logs internos y en ninguna respuesta de la API.
- [x] Script de smoke test manual documentado y no ejecutado por CI.
- [ ] Resultados de `ruff check .`, `mypy src` y `pytest`.
- [ ] Revisión de seguridad y confirmación de ausencia de secretos/PII.
- [ ] Referencia al commit que implementa la spec.
