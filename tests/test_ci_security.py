"""CI security configuration tests.

The dependency audit is informative; the three quality gates stay blocking. The
workflow must never carry a provider credential, and every action must be pinned.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
DEPENDABOT = REPO_ROOT / ".github" / "dependabot.yml"
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


def _job_block(text: str, name: str) -> str:
    """Return the YAML block of one job, delimited by the next two-space key."""

    marker = f"  {name}:\n"
    start = text.index(marker) + len(marker)
    collected: list[str] = []
    for line in text[start:].splitlines(keepends=True):
        if line.startswith("  ") and not line.startswith("    "):
            break
        collected.append(line)
    return "".join(collected)


def test_every_action_is_pinned_to_a_full_sha() -> None:
    uses_lines = [
        line.strip()
        for line in _workflow().splitlines()
        if line.strip().startswith("uses:")
    ]
    assert uses_lines, "no actions found in the workflow"
    for line in uses_lines:
        parts = line.split()
        assert re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}", parts[1]
        ), line
        assert re.search(r"#\s*v\d", line), line


def test_quality_installs_from_the_dev_lock() -> None:
    block = _job_block(_workflow(), "quality")
    assert "pip install --require-hashes -r requirements-dev.lock" in block
    assert "pip install --no-deps -e ." in block
    assert 'pip install -e ".[dev]"' not in block


def test_lock_drift_job_regenerates_universal_locks() -> None:
    block = _job_block(_workflow(), "lock-drift")
    assert "uv==0.13.9" in block
    command = "uv pip compile pyproject.toml --universal --generate-hashes --python-version 3.12"
    assert command in block
    assert "--extra dev" in block
    assert "-o requirements.lock" in block
    assert "-o requirements-dev.lock" in block
    assert "git diff --exit-code -- requirements.lock requirements-dev.lock" in block


def test_image_job_builds_without_publishing() -> None:
    block = _job_block(_workflow(), "image")
    assert "push: false" in block
    assert "load: true" in block
    assert "tags: thehouse-genai:ci" in block
    assert "packages: write" not in block


def test_container_smoke_checks_are_present() -> None:
    block = _job_block(_workflow(), "image")
    for token in (
        "Container smoke",
        "docker run",
        "GENAI_PROVIDER=fake",
        "APP_ENV=production",
        "/health/ready",
        "id -u",
        "/docs",
        "/openapi.json",
        "write-probe",
        "if: always()",
        "docker rm -f genai-smoke",
        'echo "OK readiness payload exact"',
        'echo "OK no Server header"',
        'echo "OK uid 10001"',
        'echo "OK /docs returns 404"',
        'echo "OK /openapi.json returns 404"',
        'echo "OK write denied in /app/src"',
        'echo "OK write denied in /opt/venv"',
    ):
        assert token in block, token


def test_vulnerability_scan_is_blocking() -> None:
    block = _job_block(_workflow(), "image")
    assert 'exit-code: "1"' in block
    assert "severity: HIGH,CRITICAL" in block
    assert "ignore-unfixed: true" in block
    assert "trivyignores: .trivyignore" in block


def test_sbom_is_generated_and_uploaded() -> None:
    block = _job_block(_workflow(), "image")
    assert "spdx-json" in block
    assert "sbom.spdx.json" in block
    assert "upload-artifact" in block
    assert "if-no-files-found: error" in block


def test_dependabot_has_three_ecosystems_and_seven_day_cooldown() -> None:
    text = DEPENDABOT.read_text(encoding="utf-8")
    for ecosystem in ("docker", "pip", "github-actions"):
        assert f'package-ecosystem: "{ecosystem}"' in text
    assert text.count("cooldown:") == 3
    assert text.count("default-days: 7") == 3


def test_b3_jobs_use_minimal_permissions() -> None:
    text = _workflow()
    for name in ("quality", "lock-drift", "image"):
        block = _job_block(text, name)
        match = re.search(r"    permissions:\n((?:      .*\n)+)", block)
        assert match is not None, name
        scope = match.group(1)
        assert "contents: read" in scope
        assert "write" not in scope
        assert "id-token" not in scope


def test_publish_runs_only_on_main_after_image() -> None:
    text = _workflow()
    block = _job_block(text, "publish")
    assert "needs: image" in block
    assert "if: github.event_name == 'push' && github.ref == 'refs/heads/main'" in block
    assert "push: false" in _job_block(text, "image")


def test_publish_permissions_are_exact() -> None:
    block = _job_block(_workflow(), "publish")
    match = re.search(r"    permissions:\n((?:      .*\n)+)", block)
    assert match is not None
    scope = match.group(1)
    for entry in ("contents: read", "packages: write", "id-token: write", "attestations: write"):
        assert entry in scope, entry
    assert len([line for line in scope.splitlines() if line.strip()]) == 4


def test_publish_uses_immutable_sha_tag() -> None:
    block = _job_block(_workflow(), "publish")
    assert "ghcr.io/thehouse-team/thehouse-genai:sha-${{ github.sha }}" in block
    assert ":latest" not in _workflow()
    assert 'echo "digest=${digest}" >> "$GITHUB_OUTPUT"' in block
    assert 'echo "**Digest:**' in block
    assert "digest: ${{ steps.push.outputs.digest }}" in block


def test_attestations_are_present_and_pinned() -> None:
    block = _job_block(_workflow(), "publish")
    assert "attest-build-provenance@4d101475d8b20a2381f78447822ac1eab6504dd8 # v4.2.2" in block
    assert "attest@1e69f48acb82d1966a394da916b4c1698aa569d6 # v4.2.2" in block
    assert "subject-digest: ${{ steps.push.outputs.digest }}" in block
    assert "sbom-path: sbom.spdx.json" in block
    assert block.count("push-to-registry: true") == 2


def test_published_image_is_the_tested_one() -> None:
    text = _workflow()
    image = _job_block(text, "image")
    publish = _job_block(text, "publish")
    assert "docker save thehouse-genai:ci -o image.tar" in image
    assert "name: genai-image" in image
    assert "docker load -i image.tar" in publish
    assert "name: genai-image" in publish
    assert "docker tag thehouse-genai:ci" in publish
    assert "docker build-push-action" not in publish
