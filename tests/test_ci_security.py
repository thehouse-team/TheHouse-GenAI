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
    assert 'pip install "pip-audit==2.10.1"' in audit_steps[0]


@pytest.mark.parametrize("gate", ["Ruff", "Mypy", "Pytest"])
def test_quality_gates_remain_blocking(gate: str) -> None:
    matching = [
        step for step in _steps(_workflow()) if step.splitlines()[0].strip() == gate
    ]

    assert len(matching) == 1
    assert "continue-on-error" not in matching[0]


def test_quality_typechecks_the_deployment_parser() -> None:
    block = _job_block(_workflow(), "quality")
    matching = [
        step
        for step in _steps(block)
        if step.splitlines()[0].strip() == "Mypy strict (deployment parser)"
    ]

    assert len(matching) == 1
    assert "mypy --strict .github/ci/revision_status.py" in matching[0]
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


def _dependabot_ecosystem(name: str, text: str) -> str:
    """Return the config block of one ecosystem from dependabot.yml."""

    marker = f'package-ecosystem: "{name}"'
    start = text.index(marker)
    rest = text[start:]
    next_markers = [
        rest.find(f'package-ecosystem: "{other}"')
        for other in ("docker", "pip", "github-actions")
        if other != name
    ]
    ends = [position for position in next_markers if position >= 0]
    return rest[: min(ends)] if ends else rest


def test_dependabot_docker_ignores_python_version_bumps() -> None:
    text = DEPENDABOT.read_text(encoding="utf-8")
    docker = _dependabot_ecosystem("docker", text)
    assert 'dependency-name: "python"' in docker
    assert '"version-update:semver-major"' in docker
    assert '"version-update:semver-minor"' in docker


def test_dependabot_pip_ignores_major_and_documents_lock_regeneration() -> None:
    text = DEPENDABOT.read_text(encoding="utf-8")
    pip = _dependabot_ecosystem("pip", text)
    assert 'dependency-name: "*"' in pip
    assert '"version-update:semver-major"' in pip
    assert "Dependabot no regenera nuestros locks universales" in pip
    assert "lock-drift" in pip


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


def test_infra_job_validates_bicep_without_credentials() -> None:
    block = _job_block(_workflow(), "infra")
    assert "az bicep lint --file infra/genai.bicep" in block
    assert "az bicep build --file infra/genai.bicep --stdout" in block
    assert "az login" not in block
    assert "contents: read" in block


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
    assert block.count("create-storage-record: false") == 2


def _step_block(job: str, name: str) -> str:
    """Return one step block from a job, delimited by the next step."""

    marker = f"      - name: {name}\n"
    start = job.index(marker) + len(marker)
    collected: list[str] = []
    for line in job[start:].splitlines(keepends=True):
        if line.startswith("      - name:") or (line and not line.startswith(" ")):
            break
        collected.append(line)
    return "".join(collected)


def test_attestation_subjects_use_digest_without_at_in_name() -> None:
    block = _job_block(_workflow(), "publish")
    for name in ("Attest build provenance", "Attest SBOM"):
        step = _step_block(block, name)
        assert "subject-digest: ${{ steps.push.outputs.digest }}" in step, name
        match = re.search(r"subject-name:\s*(\S+)", step)
        assert match is not None, name
        assert "@" not in match.group(1), name


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


# --- B6: deployment with approval and rollback -------------------------------------


ROLLBACK_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "rollback.yml"
AZURE_LOGIN_PIN = "azure/login@a641126d1b8aa4d1fa005f4f92df94a3a4c4c906 # v3.1.0"
CHECKOUT_PIN = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1"


def test_deploy_runs_only_on_main_after_publish() -> None:
    block = _job_block(_workflow(), "deploy")
    assert "needs: publish" in block
    assert "if: github.event_name == 'push' && github.ref == 'refs/heads/main'" in block


def test_deploy_uses_the_production_environment() -> None:
    block = _job_block(_workflow(), "deploy")
    assert "environment: production" in block


def test_deploy_permissions_are_exact() -> None:
    block = _job_block(_workflow(), "deploy")
    match = re.search(r"    permissions:\n((?:      .*\n)+)", block)
    assert match is not None
    scope = match.group(1)
    assert "contents: read" in scope
    assert "id-token: write" in scope
    assert len([line for line in scope.splitlines() if line.strip()]) == 2


def test_deploy_logs_in_via_pinned_oidc_action_and_environment_vars() -> None:
    block = _job_block(_workflow(), "deploy")
    assert AZURE_LOGIN_PIN in block
    for name in (
        "AZURE_CLIENT_ID",
        "AZURE_TENANT_ID",
        "AZURE_SUBSCRIPTION_ID",
        "AZURE_RESOURCE_GROUP",
        "AZURE_CONTAINER_APP",
    ):
        assert f"vars.{name}" in block, name


def test_deploy_uses_the_exact_digest_not_a_tag() -> None:
    text = _workflow()
    block = _job_block(text, "deploy")
    assert "needs.publish.outputs.digest" in block
    assert "ghcr.io/thehouse-team/thehouse-genai@${DIGEST}" in block
    assert "az containerapp update" in block
    assert "--image \"$image\"" in block
    assert "^sha256:[0-9a-f]{64}$" in block
    assert "docker tag" not in block


REVISION_PARSER = REPO_ROOT / ".github" / "ci" / "revision_status.py"


def test_deploy_waits_and_verifies_the_active_revision() -> None:
    block = _job_block(_workflow(), "deploy")
    for token in (
        "attempts=24",
        "sleep_seconds=10",
        "properties.latestRevisionName",
        "az containerapp revision show",
        "-o json > revision.json",
        "revision_status.py revision.json --expected",
        '"$rc" -eq 0',
        '"$rc" -eq 2',
        "Fatal revision state or invalid payload",
        "Last parsed state:",
        "**Revision:**",
        "**Digest:**",
        "**Previous image (for rollback):**",
    ):
        assert token in block, token


def test_verification_never_parses_a_multi_select_tsv_row() -> None:
    for path in (CI_WORKFLOW, ROLLBACK_WORKFLOW):
        text = path.read_text(encoding="utf-8")
        assert "IFS=" not in text, path
        assert "--query '[" not in text, path
        assert "revision_status.py" in text, path
        assert "-o json > revision.json" in text, path

    parser = REVISION_PARSER.read_text(encoding="utf-8")
    assert '"$replicas" == "1"' not in parser
    assert '"$health" == "Healthy"' not in parser
    assert "status.replicas == 0" in parser
    assert "status.health_state == \"Healthy\"" in parser


def test_fatal_parse_errors_abort_without_retrying() -> None:
    for path in (CI_WORKFLOW, ROLLBACK_WORKFLOW):
        block = path.read_text(encoding="utf-8")
        assert 'python3 .github/ci/revision_status.py revision.json --expected' in block
        assert '|| rc=$?' in block
        assert 'if [[ "$rc" -eq 2 ]]' in block
        assert "exit 1" in block


def _rollback_workflow() -> str:
    return ROLLBACK_WORKFLOW.read_text(encoding="utf-8")


def test_rollback_is_a_dispatch_workflow_in_production() -> None:
    text = _rollback_workflow()
    assert "workflow_dispatch:" in text
    assert "image_digest:" in text
    assert "environment: production" in text
    assert "needs:" not in text
    assert AZURE_LOGIN_PIN in text


def test_rollback_permissions_are_exact() -> None:
    match = re.search(r"    permissions:\n((?:      .*\n)+)", _rollback_workflow())
    assert match is not None
    scope = match.group(1)
    assert "contents: read" in scope
    assert "id-token: write" in scope
    assert len([line for line in scope.splitlines() if line.strip()]) == 2


def test_rollback_validates_the_full_image_reference() -> None:
    block = _rollback_workflow()
    assert (
        r"^ghcr\.io/thehouse-team/thehouse-genai@sha256:[0-9a-f]{64}$" in block
    )
    assert "az containerapp update" in block
    assert "--image \"$IMAGE_REF\"" in block
    assert '"$previous" == "$IMAGE_REF"' in block


def test_rollback_uses_the_same_verification() -> None:
    block = _rollback_workflow()
    for token in (
        "attempts=24",
        "properties.latestRevisionName",
        "az containerapp revision show",
        "-o json > revision.json",
        "revision_status.py revision.json --expected \"$IMAGE_REF\"",
        '"$rc" -eq 0',
        '"$rc" -eq 2',
        "Last parsed state:",
        "**Revision:**",
    ):
        assert token in block, token


def test_all_actions_in_both_workflows_are_pinned() -> None:
    for path in (CI_WORKFLOW, ROLLBACK_WORKFLOW):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped.startswith("uses:"):
                continue
            parts = stripped.split()
            assert re.fullmatch(
                r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}", parts[1]
            ), line
            assert re.search(r"#\s*v\d", line), line


def test_every_job_using_the_revision_parser_checks_out_first() -> None:
    cases = ((CI_WORKFLOW, "deploy"), (ROLLBACK_WORKFLOW, "rollback"))
    for path, job_name in cases:
        steps = _steps(_job_block(path.read_text(encoding="utf-8"), job_name))
        parser_steps = [i for i, step in enumerate(steps) if "revision_status.py" in step]
        checkout_steps = [i for i, step in enumerate(steps) if CHECKOUT_PIN in step]

        assert parser_steps, f"{job_name}: no parser step"
        assert checkout_steps, f"{job_name}: no checkout step"
        assert min(checkout_steps) < min(parser_steps), f"{job_name}: checkout too late"
        assert "persist-credentials: false" in steps[min(checkout_steps)]


def test_deploy_checks_out_the_triggering_commit() -> None:
    steps = _steps(_job_block(_workflow(), "deploy"))
    checkout = next(step for step in steps if CHECKOUT_PIN in step)

    assert "ref: ${{ github.sha }}" in checkout
    assert "persist-credentials: false" in checkout


def test_every_job_that_reads_repo_files_checks_out() -> None:
    cases = (
        (CI_WORKFLOW, ("quality", "lock-drift", "infra", "image", "deploy")),
        (ROLLBACK_WORKFLOW, ("rollback",)),
    )
    for path, job_names in cases:
        text = path.read_text(encoding="utf-8")
        for name in job_names:
            assert CHECKOUT_PIN in _job_block(text, name), f"{name} needs a checkout"

    # publish only consumes uploaded artifacts, so it does not need a checkout.
    assert CHECKOUT_PIN not in _job_block(_workflow(), "publish")
