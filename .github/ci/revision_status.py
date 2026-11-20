"""Parse and validate `az containerapp revision show -o json` (spec 009, B6).

Standard library only. No network, no secrets. Used by the deploy and rollback workflows.

Exit codes: 0 = verified, 1 = not ready yet (retry), 2 = fatal. Fatal is reserved for
explicit documented failures and missing/invalid structural data (name, image) or invalid
JSON. Everything else -- including a null healthState while starting up and unknown enum
values -- is a normal transition and only prints a warning.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Exact swagger 2025-01-01 enums (Microsoft.App/ContainerAppsRevisions.json), plus the
# values the service actually emits ("ScaledToZero" / "RunningAtMaxScale" on 2026-11-19).
PROVISIONING_READY = frozenset({"Provisioned"})
PROVISIONING_WAIT = frozenset({"Provisioning"})
PROVISIONING_FATAL = frozenset({"Failed", "Deprovisioning", "Deprovisioned"})

RUNNING_READY_ZERO = frozenset({"ScaledToZero", "Stopped"})
RUNNING_READY_REPLICAS = frozenset({"Running", "RunningAtMaxScale"})
RUNNING_WAIT = frozenset({"Provisioning", "Activating", "Processing", "Scaling", "Unknown"})
RUNNING_FATAL = frozenset({"Failed", "Degraded", "ActivationFailed"})

HEALTH_READY = frozenset({"Healthy", "None"})
HEALTH_FATAL = frozenset({"Unhealthy"})

KNOWN_PROVISIONING = PROVISIONING_READY | PROVISIONING_WAIT | PROVISIONING_FATAL
KNOWN_RUNNING = (
    RUNNING_READY_ZERO | RUNNING_READY_REPLICAS | RUNNING_WAIT | RUNNING_FATAL
)
KNOWN_HEALTH = HEALTH_READY | HEALTH_FATAL


class RevisionParseError(ValueError):
    """Structural data is missing or invalid; this is always fatal."""


@dataclass(frozen=True)
class RevisionStatus:
    """Validated fields used by the deployment gate, plus non-secret warnings."""

    revision: str
    active: bool | None
    provisioning_state: str
    running_state: str
    health_state: str
    replicas: int | None
    image: str
    warnings: tuple[str, ...] = ()

    def describe(self) -> str:
        """One stable, log-friendly line with the complete parsed state."""

        active = "unknown" if self.active is None else str(self.active).lower()
        replicas = "unknown" if self.replicas is None else str(self.replicas)
        return (
            f"revision={self.revision} active={active} "
            f"provisioning={self.provisioning_state or '<empty>'} "
            f"running={self.running_state or '<empty>'} "
            f"health={self.health_state or '<empty>'} "
            f"replicas={replicas} image={self.image}"
        )


def _as_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RevisionParseError(f"{path} must be an object, got {type(value).__name__}")
    return value


def _required_text(mapping: dict[str, Any], key: str, path: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RevisionParseError(f"{path}.{key} must be a non-empty string, got {value!r}")
    return value


def _state_text(
    mapping: dict[str, Any], key: str, known: frozenset[str], warnings: list[str]
) -> str:
    """Read a possibly empty or unknown state value: warn, never abort."""

    value = mapping.get(key)
    if value is None:
        warnings.append(f"empty {key}")
        return ""
    text = value if isinstance(value, str) else str(value)
    if not text.strip():
        warnings.append(f"empty {key}")
    elif text not in known:
        warnings.append(f"unknown {key}={text!r}")
    return text


def parse_revision(payload: Any) -> RevisionStatus:
    """Extract gate fields, aborting only on missing/invalid structural data."""

    root = _as_mapping(payload, "$")
    revision = _required_text(root, "name", "$")
    props = _as_mapping(root.get("properties"), "$.properties")
    warnings: list[str] = []

    active_value = props.get("active")
    if isinstance(active_value, bool):
        active: bool | None = active_value
    elif isinstance(active_value, str) and active_value.lower() in {"true", "false"}:
        active = active_value.lower() == "true"
    else:
        active = None
        warnings.append(f"unexpected active={active_value!r}")

    provisioning = _state_text(props, "provisioningState", KNOWN_PROVISIONING, warnings)
    running = _state_text(props, "runningState", KNOWN_RUNNING, warnings)

    health_value = props.get("healthState")
    if health_value is None:
        health = "None"
    elif isinstance(health_value, str) and health_value.strip():
        health = health_value
        if health not in KNOWN_HEALTH:
            warnings.append(f"unknown healthState={health!r}")
    else:
        health = ""
        warnings.append("empty healthState")

    replicas_value = props.get("replicas")
    replicas: int | None
    if isinstance(replicas_value, bool) or not isinstance(replicas_value, (int, str)):
        replicas = None
        warnings.append(f"unexpected replicas={replicas_value!r}")
    else:
        try:
            parsed = int(replicas_value)
        except ValueError:
            replicas = None
            warnings.append(f"unexpected replicas={replicas_value!r}")
        else:
            replicas = parsed if parsed >= 0 else None
            if replicas is None:
                warnings.append(f"negative replicas={parsed}")

    template = _as_mapping(props.get("template"), "$.properties.template")
    containers = template.get("containers")
    if not isinstance(containers, list) or not containers:
        raise RevisionParseError("$.properties.template.containers must be a non-empty array")
    container = _as_mapping(containers[0], "$.properties.template.containers[0]")
    image = _required_text(container, "image", "$.properties.template.containers[0]")

    return RevisionStatus(
        revision=revision,
        active=active,
        provisioning_state=provisioning,
        running_state=running,
        health_state=health,
        replicas=replicas,
        image=image,
        warnings=tuple(warnings),
    )


def is_failed(status: RevisionStatus, expected_image: str) -> bool:
    """Only explicit failures and a wrong image after provisioning are fatal."""

    return (
        status.provisioning_state in PROVISIONING_FATAL
        or status.running_state in RUNNING_FATAL
        or status.health_state in HEALTH_FATAL
        or (status.provisioning_state in PROVISIONING_READY and status.image != expected_image)
    )


def is_ready(status: RevisionStatus, expected_image: str) -> bool:
    """Return True only with the verified exact image and consistent healthy states."""

    if not (
        status.active is True
        and status.provisioning_state in PROVISIONING_READY
        and status.image == expected_image
    ):
        return False
    if status.replicas == 0:
        return status.running_state in RUNNING_READY_ZERO
    if status.replicas is None or status.replicas < 1:
        return False
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
    if is_failed(status, args.expected):
        print(
            "FATAL: explicit failure state or wrong image after provisioning",
            file=sys.stderr,
        )
        return 2
    if is_ready(status, args.expected):
        print("VERIFIED")
        return 0
    for warning in status.warnings:
        print(f"WARNING: {warning}")
    print("NOT_READY")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
