"""CI security configuration tests.

The dependency audit is informative; the three quality gates stay blocking. The
workflow must never carry a provider credential.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PYPROJECT = REPO_ROOT / "pyproject.toml"


def _workflow() -> str:
    return CI_WORKFLOW.read_text(encoding="utf-8")


def _steps(text: str) -> list[str]:
    """Split the job into its named steps using the workflow indentation."""

    return [step.strip() for step in text.split("      - name:")[1:]]


def test_pip_audit_step_is_present_and_non_blocking() -> None:
    audit_steps = [
        step
        for step in _steps(_workflow())
        if step.startswith("Dependency audit") and "pip-audit" in step
    ]

    assert len(audit_steps) == 1
    assert "continue-on-error: true" in audit_steps[0]
    assert "pip install pip-audit" in audit_steps[0]


@pytest.mark.parametrize("gate", ["Ruff", "Mypy", "Pytest"])
def test_quality_gates_remain_blocking(gate: str) -> None:
    matching = [step for step in _steps(_workflow()) if step.startswith(gate)]

    assert len(matching) == 1
    assert "continue-on-error" not in matching[0]


def test_workflow_does_not_reference_provider_secrets() -> None:
    text = _workflow()

    assert "GENAI_API_KEY" not in text
    assert "GENAI_SERVICE_KEY" not in text
    assert "API_KEY" not in text
    assert "secrets." not in text


def test_pip_audit_is_not_a_project_dependency() -> None:
    assert "pip-audit" not in PYPROJECT.read_text(encoding="utf-8")
