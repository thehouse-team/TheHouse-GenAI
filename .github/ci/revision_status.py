"""Parse and validate `az containerapp revision show -o json` (spec 009, B6).

Standard library only. No network, no secrets. Used by the deploy and rollback workflows.

Exit codes: 0 = verified, 1 = not ready yet (retry), 2 = fatal (invalid payload or a
failed revision state). A missing or empty field such as the image is always fatal: a
broken script must never look like a slow deployment.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Value sets, classified explicitly. Exact swagger 2025-01-01 enums:
#   RevisionHealthState      = Healthy | Unhealthy | None
#   RevisionProvisioningState = Provisioning | Provisioned | Failed | Deprovisioning |
#                               Deprovisioned
#   RevisionRunningState     = Running | Processing | Stopped | Degraded | Failed | Unknown
# The service actually emits "ScaledToZero" and "RunningAtMaxScale" (the guide's
# "Scale to 0" / "Running (at max)"); both were observed in production on 2026-11-19,
# so they are accepted as ready values too. Source:
# https://github.com/Azure/azure-rest-api-specs/blob/main/specification/app/resource-manager/Microsoft.App/ContainerApps/stable/2025-01-01/ContainerAppsRevisions.json
# Anything not listed here is unexpected and aborts immediately.
PROVISIONING_READY = frozenset({"Provisioned"})
PROVISIONING_WAIT = frozenset({"Provisioning"})
PROVISIONING_FATAL = frozenset({"Failed", "Deprovisioning", "Deprovisioned"})

RUNNING_READY_ZERO = frozenset({"ScaledToZero", "Stopped"})
RUNNING_READY_REPLICAS = frozenset({"Running", "RunningAtMaxScale"})
RUNNING_WAIT = frozenset({"Provisioning", "Activating", "Processing", "Scaling", "Unknown"})
RUNNING_FATAL = frozenset({"Failed", "Degraded", "ActivationFailed"})

HEALTH_OK = frozenset({"Healthy", "None"})
HEALTH_FATAL = frozenset({"Unhealthy"})


class RevisionParseError(ValueError):
    """A required field is missing, empty or of an unexpected type."""


@dataclass(frozen=True)
class RevisionStatus:
    """The validated fields used by the deployment gate."""

    revision: str
    active: bool
    provisioning_state: str
    running_state: str
    health_state: str
    replicas: int
    image: str

    def describe(self) -> str:
        """One stable, log-friendly line with every gated field."""

        return (
            f"revision={self.revision} active={str(self.active).lower()} "
            f"provisioning={self.provisioning_state} running={self.running_state} "
            f"health={self.health_state} replicas={self.replicas} image={self.image}"
        )


def _as_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RevisionParseError(f"{path} must be an object, got {type(value).__name__}")
    return value


def _text(mapping: dict[str, Any], key: str, path: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RevisionParseError(f"{path}.{key} must be a non-empty string, got {value!r}")
    return value


def parse_revision(payload: Any) -> RevisionStatus:
    """Extract the gate fields, failing loudly on any unexpected shape or value."""

    root = _as_mapping(payload, "$")
    revision = _text(root, "name", "$")
    props = _as_mapping(root.get("properties"), "$.properties")

    active_value = props.get("active")
    if isinstance(active_value, bool):
        active = active_value
    elif isinstance(active_value, str) and active_value.lower() in {"true", "false"}:
        active = active_value.lower() == "true"
    else:
        raise RevisionParseError(
            f"$.properties.active must be a boolean, got {active_value!r}"
        )

    provisioning = _text(props, "provisioningState", "$.properties")
    if provisioning not in PROVISIONING_READY | PROVISIONING_WAIT | PROVISIONING_FATAL:
        raise RevisionParseError(f"unexpected provisioningState {provisioning!r}")

    running = _text(props, "runningState", "$.properties")
    known_running = (
        RUNNING_READY_ZERO | RUNNING_READY_REPLICAS | RUNNING_WAIT | RUNNING_FATAL
    )
    if running not in known_running:
        raise RevisionParseError(f"unexpected runningState {running!r}")

    health_value = props.get("healthState")
    if health_value is None:
        # A scaled-to-zero revision legitimately reports no health state.
        health = "None"
    elif isinstance(health_value, str) and health_value.strip():
        health = health_value
    else:
        raise RevisionParseError(
            f"$.properties.healthState must be a string or null, got {health_value!r}"
        )
    if health not in HEALTH_OK | HEALTH_FATAL:
        raise RevisionParseError(f"unexpected healthState {health!r}")

    replicas_value = props.get("replicas")
    if isinstance(replicas_value, bool) or not isinstance(replicas_value, (int, str)):
        raise RevisionParseError(
            f"$.properties.replicas must be a non-negative integer, got {replicas_value!r}"
        )
    try:
        replicas = int(replicas_value)
    except ValueError as exc:
        raise RevisionParseError(
            f"$.properties.replicas must be a non-negative integer, got {replicas_value!r}"
        ) from exc
    if replicas < 0:
        raise RevisionParseError(f"$.properties.replicas must not be negative: {replicas}")

    template = _as_mapping(props.get("template"), "$.properties.template")
    containers = template.get("containers")
    if not isinstance(containers, list) or not containers:
        raise RevisionParseError("$.properties.template.containers must be a non-empty array")
    container = _as_mapping(containers[0], "$.properties.template.containers[0]")
    image = _text(container, "image", "$.properties.template.containers[0]")

    if health == "None" and replicas > 0:
        raise RevisionParseError("healthState is null but replicas > 0: unexpected state")

    return RevisionStatus(
        revision=revision,
        active=active,
        provisioning_state=provisioning,
        running_state=running,
        health_state=health,
        replicas=replicas,
        image=image,
    )


def is_failed(status: RevisionStatus) -> bool:
    """Return True for terminal failure states, which must abort the job."""

    return (
        status.provisioning_state in PROVISIONING_FATAL
        or status.running_state in RUNNING_FATAL
        or status.health_state in HEALTH_FATAL
    )


def is_ready(status: RevisionStatus, expected_image: str) -> bool:
    """Return True only for the exact image with a state consistent with its replicas.

    With 0 replicas the verified production state is ``ScaledToZero`` (swagger:
    ``Stopped``) and health may be ``Healthy`` or null. With replicas, both the running
    state and the health state must be the healthy ones.
    """

    if not (
        status.active
        and status.provisioning_state in PROVISIONING_READY
        and status.image == expected_image
    ):
        return False
    if status.replicas == 0:
        return status.running_state in RUNNING_READY_ZERO
    return (
        status.running_state in RUNNING_READY_REPLICAS
        and status.health_state == "Healthy"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("revision_json", type=Path, help="az revision show -o json output")
    parser.add_argument("--expected", required=True, help="exact ghcr.io/... @sha256 image")
    args = parser.parse_args(argv)

    try:
        payload = json.loads(args.revision_json.read_text(encoding="utf-8"))
        status = parse_revision(payload)
    except (OSError, UnicodeError, json.JSONDecodeError, RevisionParseError) as exc:
        print(f"FATAL: cannot parse revision JSON: {exc}", file=sys.stderr)
        return 2

    print(status.describe())
    if is_failed(status):
        print(f"FATAL: revision {status.revision} is in a failed state", file=sys.stderr)
        return 2
    if is_ready(status, args.expected):
        print("VERIFIED")
        return 0
    print("NOT_READY")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
