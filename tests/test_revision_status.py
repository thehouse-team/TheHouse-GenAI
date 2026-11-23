"""Offline tests for the deployment gate's revision JSON parser (spec 009, B6).

The example payload has the ARM/CLI shape returned by `az containerapp revision show -o
json`: the revision fields live under `properties` and the image under
`properties.template.containers[0].image`. No network, no credentials, no secrets.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[1] / ".github" / "ci" / "revision_status.py"
)
_SPEC = importlib.util.spec_from_file_location("revision_status", MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

parse_revision = _MODULE.parse_revision
is_failed = _MODULE.is_failed
is_ready = _MODULE.is_ready
traffic_is_settled = _MODULE.traffic_is_settled
main = _MODULE.main
RevisionParseError = _MODULE.RevisionParseError

IMAGE = "ghcr.io/thehouse-team/thehouse-genai@sha256:" + "a" * 64
REVISION_NAME = "ca-thehouse-genai-u2--0000002"
REAL_IMAGE = (
    "ghcr.io/thehouse-team/thehouse-genai@sha256:"
    "bb106ef6ad5db6e460f88f7f004c7cfb4844034e8c1e5547a80366da60c64447"
)


def _revision(**overrides: Any) -> dict[str, Any]:
    """Return a fresh, realistic revision payload with optional field overrides."""

    properties: dict[str, Any] = {
        "active": True,
        "createdTime": "2026-11-19T20:00:00.0000000Z",
        "fqdn": "ca-thehouse-genai-u2--0000002.internal.example",
        "healthState": "Healthy",
        "lastActiveTime": "2026-11-19T20:00:00.0000000Z",
        "provisioningState": "Provisioned",
        "replicas": 1,
        "runningState": "Running",
        "template": {
            "containers": [
                {
                    "image": IMAGE,
                    "name": "thehouse-genai",
                    "resources": {"cpu": 0.25, "memory": "0.5Gi"},
                }
            ],
            "scale": {
                "minReplicas": 0,
                "maxReplicas": 1,
                "cooldownPeriod": 300,
                "pollingInterval": 30,
            },
        },
        "trafficWeight": 100,
    }
    for key, value in overrides.items():
        if key == "properties":
            properties.update(value)
        elif key == "image":
            properties["template"]["containers"][0]["image"] = value
        elif key == "name":
            continue
        else:
            properties[key] = value
    payload: dict[str, Any] = {
        "id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/"
        "rg-thehouse-u2/providers/Microsoft.App/containerApps/ca-thehouse-genai-u2/"
        "revisions/" + REVISION_NAME,
        "name": overrides.get("name", REVISION_NAME),
        "type": "Microsoft.App/containerApps/revisions",
        "properties": properties,
    }
    return payload


def _write(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "revision.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _revision_entry(name: str, active: bool, traffic: int) -> dict[str, Any]:
    """One entry of `az containerapp revision list -o json` (no secrets)."""

    return {
        "name": name,
        "properties": {"active": active, "trafficWeight": traffic},
    }


def _write_list(tmp_path: Path, entries: list[dict[str, Any]]) -> Path:
    path = tmp_path / "revisions.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


def test_parse_revision_extracts_every_gated_field() -> None:
    status = parse_revision(_revision())

    assert status.revision == REVISION_NAME
    assert status.active is True
    assert status.provisioning_state == "Provisioned"
    assert status.running_state == "Running"
    assert status.health_state == "Healthy"
    assert status.replicas == 1
    assert status.traffic_weight == 100
    assert status.image == IMAGE
    assert REVISION_NAME in status.describe()
    assert "traffic=100" in status.describe()
    assert IMAGE in status.describe()


@pytest.mark.parametrize("health", ["Healthy", None])
def test_parse_revision_accepts_a_scaled_to_zero_revision(health: str | None) -> None:
    payload = _revision(
        properties={"healthState": health, "replicas": 0, "runningState": "ScaledToZero"}
    )

    status = parse_revision(payload)

    assert status.replicas == 0
    assert status.health_state == ("None" if health is None else health)
    assert status.running_state == "ScaledToZero"
    assert is_ready(status, IMAGE) is True
    assert is_failed(status, IMAGE) is False


def test_real_deployed_revision_is_verified(tmp_path: Path) -> None:
    """The exact revision and states reported by the operator after the first deploy."""

    payload = _revision(
        name=REVISION_NAME,
        image=REAL_IMAGE,
        properties={
            "active": True,
            "provisioningState": "Provisioned",
            "runningState": "ScaledToZero",
            "healthState": "Healthy",
            "replicas": 0,
        },
    )
    path = _write(tmp_path, payload)

    assert main([str(path), "--expected", REAL_IMAGE]) == 0


def test_second_real_revision_running_at_max_scale_is_verified(tmp_path: Path) -> None:
    """RunningAtMaxScale with one replica is a healthy state, never a fatal one."""

    payload = _revision(
        name="ca-thehouse-genai-u2--okuxih9",
        image=REAL_IMAGE,
        properties={
            "active": True,
            "provisioningState": "Provisioned",
            "runningState": "RunningAtMaxScale",
            "healthState": "Healthy",
            "replicas": 1,
        },
    )
    path = _write(tmp_path, payload)

    assert main([str(path), "--expected", REAL_IMAGE]) == 0


@pytest.mark.parametrize(
    ("running", "replicas", "ready", "failed"),
    [
        ("ScaledToZero", 0, True, False),
        ("Stopped", 0, True, False),
        ("Running", 1, True, False),
        ("RunningAtMaxScale", 1, True, False),
        ("Provisioning", 1, False, False),
        ("Activating", 0, False, False),
        ("Processing", 1, False, False),
        ("Scaling", 1, False, False),
        ("Unknown", 0, False, False),
        ("Failed", 1, False, True),
        ("Degraded", 1, False, True),
        ("ActivationFailed", 0, False, True),
    ],
)
def test_running_state_classification(
    running: str, replicas: int, ready: bool, failed: bool
) -> None:
    overrides: dict[str, Any] = {"runningState": running, "replicas": replicas}
    if replicas == 0:
        overrides["healthState"] = "Healthy"
    status = parse_revision(_revision(properties=overrides))

    assert is_ready(status, IMAGE) is ready
    assert is_failed(status, IMAGE) is failed


def test_main_waits_and_warns_on_an_unknown_running_state(
    tmp_path: Path, capsys: Any
) -> None:
    path = _write(tmp_path, _revision(properties={"runningState": "UnexpectedState"}))

    assert main([str(path), "--expected", IMAGE]) == 1
    output = capsys.readouterr().out
    assert "WARNING: unknown runningState='UnexpectedState'" in output
    assert "NOT_READY" in output


def test_third_real_case_starting_replica_with_null_health_waits(tmp_path: Path) -> None:
    """Right after the update Azure has a replica but has not evaluated health yet."""

    payload = _revision(
        name="ca-thehouse-genai-u2--0000003",
        image=REAL_IMAGE,
        properties={
            "active": True,
            "provisioningState": "Provisioned",
            "runningState": "Processing",
            "healthState": None,
            "replicas": 1,
        },
    )
    path = _write(tmp_path, payload)

    assert main([str(path), "--expected", REAL_IMAGE]) == 1


def test_main_warns_on_empty_state_values(tmp_path: Path, capsys: Any) -> None:
    path = _write(tmp_path, _revision(properties={"provisioningState": ""}))

    assert main([str(path), "--expected", IMAGE]) == 1
    assert "WARNING: empty provisioningState" in capsys.readouterr().out


def test_main_verifies_the_exact_image(tmp_path: Path) -> None:
    path = _write(tmp_path, _revision())

    assert main([str(path), "--expected", IMAGE]) == 0


def test_main_retries_only_on_not_ready(tmp_path: Path) -> None:
    path = _write(tmp_path, _revision(properties={"provisioningState": "Provisioning"}))

    assert main([str(path), "--expected", IMAGE]) == 1


def test_main_fails_immediately_on_an_empty_image(tmp_path: Path, capsys: Any) -> None:
    path = _write(tmp_path, _revision(image=""))

    assert main([str(path), "--expected", IMAGE]) == 2
    errors = capsys.readouterr().err
    assert "FATAL" in errors
    assert "containers[0].image must be a non-empty string" in errors


def test_main_fails_immediately_on_a_failed_state(tmp_path: Path) -> None:
    path = _write(tmp_path, _revision(properties={"runningState": "Failed"}))

    assert main([str(path), "--expected", IMAGE]) == 2


def test_main_rejects_mismatched_image_after_provisioning(tmp_path: Path) -> None:
    other = "ghcr.io/thehouse-team/thehouse-genai@sha256:" + "b" * 64
    path = _write(tmp_path, _revision())

    assert main([str(path), "--expected", other]) == 2


def test_null_health_with_replicas_is_only_a_wait(tmp_path: Path) -> None:
    path = _write(tmp_path, _revision(properties={"healthState": None}))

    assert main([str(path), "--expected", IMAGE]) == 1


def test_unhealthy_is_fatal(tmp_path: Path) -> None:
    path = _write(tmp_path, _revision(properties={"healthState": "Unhealthy"}))

    assert main([str(path), "--expected", IMAGE]) == 2


def test_parse_revision_rejects_missing_template() -> None:
    payload = _revision()
    del payload["properties"]["template"]

    with pytest.raises(RevisionParseError, match=r"\$\.properties\.template must be an object"):
        parse_revision(payload)


# --- B7/B8: traffic cutover gate ------------------------------------------------------


@pytest.mark.parametrize("traffic", [0, 50, 99, None, "many", 101, True])
def test_partial_or_missing_traffic_is_only_a_wait(traffic: Any, tmp_path: Path) -> None:
    path = _write(tmp_path, _revision(properties={"trafficWeight": traffic}))

    assert main([str(path), "--expected", IMAGE]) == 1


def test_list_with_another_active_revision_with_traffic_waits(
    tmp_path: Path, capsys: Any
) -> None:
    """The real transition window: 0000006 and 0000007 both active with traffic."""

    path = _write(tmp_path, _revision())
    revisions = _write_list(
        tmp_path,
        [
            _revision_entry("ca-thehouse-genai-u2--0000006", True, 100),
            _revision_entry(REVISION_NAME, True, 100),
        ],
    )

    assert main([str(path), "--expected", IMAGE, "--revisions-json", str(revisions)]) == 1
    output = capsys.readouterr().out
    assert "WARNING: other active revision(s) still carry traffic" in output
    assert "0000006" in output
    assert "NOT_READY" in output


def test_list_after_cutover_verifies_when_others_are_stopped(tmp_path: Path) -> None:
    """The real settled state: 0000005/0000006 stopped at 0%, new revision at 100%."""

    path = _write(tmp_path, _revision())
    revisions = _write_list(
        tmp_path,
        [
            _revision_entry("ca-thehouse-genai-u2--0000005", False, 0),
            _revision_entry("ca-thehouse-genai-u2--0000006", False, 0),
            _revision_entry(REVISION_NAME, True, 100),
        ],
    )

    assert main([str(path), "--expected", IMAGE, "--revisions-json", str(revisions)]) == 0


@pytest.mark.parametrize("payload", [{}, "not-a-list", [42]])
def test_unexpected_revision_list_waits_instead_of_failing(
    payload: Any, tmp_path: Path
) -> None:
    path = _write(tmp_path, _revision())
    revisions = tmp_path / "revisions.json"
    revisions.write_text(json.dumps(payload), encoding="utf-8")

    assert main([str(path), "--expected", IMAGE, "--revisions-json", str(revisions)]) == 1


def test_unreadable_revision_list_waits_instead_of_failing(tmp_path: Path) -> None:
    path = _write(tmp_path, _revision())

    assert (
        main(
            [
                str(path),
                "--expected",
                IMAGE,
                "--revisions-json",
                str(tmp_path / "missing.json"),
            ]
        )
        == 1
    )


def test_traffic_is_settled_accepts_string_boolean_and_weight() -> None:
    entries = [
        _revision_entry(REVISION_NAME, True, 100),
        {
            "name": "ca-thehouse-genai-u2--0000004",
            "properties": {"active": "false", "trafficWeight": "0"},
        },
    ]

    assert traffic_is_settled(entries, REVISION_NAME) == (True, ())
