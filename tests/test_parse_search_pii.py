"""End-to-end PII checks for parse-search: redaction before prompt and logs.

The provider double records the exact port request, so the absence of raw PII in the
prompt is asserted against `fake.calls`. All content is synthetic; no test opens a socket.
"""

from __future__ import annotations

import asyncio
import json
import logging

import pytest

from thehouse_genai.application.parse_search import ParseSearch
from thehouse_genai.domain.search_filters import (
    ParseSearchRequest,
    SearchConfidence,
    empty_filters,
)
from thehouse_genai.providers.fake import FakeProvider

_EMAIL = "estudiante@ejemplo.mx"
_PHONE_WITH_PREFIX = "+52 55 1234 5678"
_PHONE_PLAIN = "33 1234 5678"
_URL = "https://ejemplo.mx/cuarto"
_KEPT_TEXT = "busco cuarto de 3 mil con internet"
_RAW_PII = (_EMAIL, _PHONE_WITH_PREFIX, _PHONE_PLAIN, _URL)


def _request(query: str) -> ParseSearchRequest:
    return ParseSearchRequest.model_validate({"query": query})


def _completion() -> str:
    """A grounded completion so the test isolates PII handling."""

    return json.dumps(
        {
            "filters": {
                "maxBudget": 3000,
                "currency": "MXN",
                "essentialServices": ["internet"],
            }
        },
        ensure_ascii=False,
    )


def _logged_text(caplog: pytest.LogCaptureFixture) -> str:
    return "\n".join(
        str(value) for record in caplog.records for value in record.__dict__.values()
    )


def test_combined_pii_is_redacted_from_prompt_and_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Every raw PII value is absent from the prompt and the logs; placeholders remain."""

    caplog.set_level(logging.DEBUG)
    query = (
        f"Correo {_EMAIL}, tel {_PHONE_WITH_PREFIX} o {_PHONE_PLAIN}, "
        f"web {_URL}; {_KEPT_TEXT}"
    )
    provider = FakeProvider(text=_completion())

    response = asyncio.run(ParseSearch(provider).execute(_request(query)))

    assert len(provider.calls) == 1
    prompt = provider.calls[0].prompt
    for placeholder in ("[EMAIL]", "[TELEFONO]", "[URL]"):
        assert placeholder in prompt
    assert prompt.count("[TELEFONO]") == 2
    for secret in _RAW_PII:
        assert secret not in prompt, secret
        assert secret not in _logged_text(caplog), secret
        assert secret not in str(response.model_dump(by_alias=True)), secret
    assert _KEPT_TEXT in prompt
    assert response.generated is True


@pytest.mark.parametrize(
    "query",
    [
        _PHONE_WITH_PREFIX,
        _PHONE_PLAIN,
        "https://ejemplo.mx/cuarto",
        "www.ejemplo.mx",
    ],
)
def test_pii_only_query_of_each_kind_skips_the_provider(query: str) -> None:
    """A query left empty by redaction degrades without any provider call.

    B3 covers the email-only case; these are the remaining PII shapes.
    """

    provider = FakeProvider(text=_completion())

    response = asyncio.run(ParseSearch(provider).execute(_request(query)))

    assert provider.calls == []
    assert response.filters == empty_filters()
    assert response.confidence is SearchConfidence.LOW
    assert response.generated is False
