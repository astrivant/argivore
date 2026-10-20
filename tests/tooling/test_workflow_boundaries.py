"""
Keep privileged CI jobs separate from candidate code and verification-only events.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def mapping(value: object) -> dict[str, object]:
    """
    Validate a parsed workflow mapping before inspecting its security contract.

    Args:
        value (object): Parsed YAML node.

    Returns:
        dict[str, object]: Mapping with validated string keys.
    """
    assert isinstance(value, dict)
    result: dict[str, object] = {}
    for key, item in value.items():
        assert isinstance(key, str)
        result[key] = item
    return result


def workflow(name: str) -> dict[str, object]:
    """
    Load one maintained workflow without YAML boolean coercion of event names.

    Args:
        name (str): Workflow basename, without its YAML suffix.

    Returns:
        dict[str, object]: Validated workflow root.
    """
    value: object = yaml.load((ROOT / ".github/workflows" / f"{name}.yml").read_text(), Loader=yaml.BaseLoader)
    return mapping(value)


def test_only_declared_jobs_can_write() -> None:
    """
    Reject added write permissions unless their specific job is reviewed here.

    Returns:
        None: Only the documented coverage, repair and release jobs can write.
    """
    expected = {
        "ci/coverage": {"contents": "write"},
        "ci/release": {"contents": "write", "pull-requests": "write"},
        "ci/generated-repair": {"contents": "write", "pull-requests": "read"},
        "stage-coverage/publish": {"contents": "write"},
        "stage-repair/repair": {"contents": "write", "pull-requests": "read"},
        "stage-release/publish": {"contents": "write", "pull-requests": "read"},
        "stage-release/feedback": {"contents": "read", "pull-requests": "write"},
    }
    observed: dict[str, dict[str, object]] = {}
    for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
        document = workflow(path.stem)
        default = mapping(document["permissions"])
        for name, value in mapping(document["jobs"]).items():
            permissions = mapping(mapping(value).get("permissions", default))
            assert set(permissions.values()) <= {"read", "write", "none"}
            if "write" in permissions.values():
                observed[f"{path.stem}/{name}"] = permissions
    assert observed == expected


def test_required_gate_covers_all_verification_producers() -> None:
    """
    Prevent optional publishers or untrusted target events from replacing validation.

    Returns:
        None: Source checks, tests and the build are parallel required producers.
    """
    document = workflow("ci")
    assert document["permissions"] == {"contents": "read"}
    jobs = mapping(document["jobs"])
    required = mapping(jobs["required"])
    producers = {"checks", "tests", "build"}
    needs = required["needs"]
    assert isinstance(needs, list) and set(needs) == producers | {"registry-preview"}
    assert required["if"] == "always() && github.event_name != 'pull_request_target' && github.event_name != 'schedule'"
    for name in producers:
        job = mapping(jobs[name])
        assert "needs" not in job
        assert job["if"] == "github.event_name != 'pull_request_target' && github.event_name != 'schedule'"
        assert "secrets" not in job


def test_repair_executes_only_trusted_default_branch_code() -> None:
    """
    Preserve arbitrary PR targets without trusting their executable source.

    Returns:
        None: Repair checks out trusted source and receives no inherited secrets.
    """
    caller = mapping(mapping(workflow("ci")["jobs"])["generated-repair"])
    assert " ".join(str(caller["if"]).split()) == (
        "github.event_name == 'pull_request_target' || github.event_name == 'schedule' "
        "|| (github.event_name == 'push' && github.ref == 'refs/heads/main')"
    )
    assert "secrets" not in caller
    job = mapping(mapping(workflow("stage-repair")["jobs"])["repair"])
    steps = job["steps"]
    assert isinstance(steps, list) and len(steps) == 3
    checkout, setup, dispatch = (mapping(step) for step in steps)
    assert str(checkout["uses"]).startswith("actions/checkout@")
    assert mapping(checkout["with"]) == {
        "ref": "${{ github.event.repository.default_branch }}",
        "persist-credentials": "false",
        "fetch-depth": "0",
    }
    assert str(setup["uses"]).startswith("actions/setup-python@")
    assert str(dispatch["uses"]).startswith("actions/github-script@")
    source = (ROOT / ".github/workflows/stage-repair.yml").read_text()
    assert "secrets." not in source and "github.event.pull_request.head" not in source


def test_release_and_feedback_wait_for_their_actual_producers() -> None:
    """
    Prevent green tag runs without publication and premature contributor notifications.

    Returns:
        None: Release admission, acceptance and feedback retain their dependencies.
    """
    jobs = mapping(workflow("ci")["jobs"])
    release = mapping(jobs["release"])
    assert release["needs"] == ["required"]
    assert release["if"] == (
        "!cancelled() && needs.required.result == 'success' && github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')"
    )
    terminal = mapping(jobs["release-complete"])
    assert terminal["needs"] == ["required", "release"]
    assert terminal["if"] == "!cancelled() && github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')"
    stages = mapping(workflow("stage-release")["jobs"])
    acceptance = mapping(stages["acceptance"])
    assert acceptance["needs"] == "publish" and acceptance["if"] == "!cancelled()"
    assert mapping(stages["feedback"])["needs"] == ["publish", "acceptance"]
    coverage = mapping(jobs["coverage"])
    assert coverage["needs"] == ["tests"]
    assert coverage["if"] == "github.event_name == 'push' && github.ref == 'refs/heads/main'"


def test_release_verifier_requires_provider_immutability() -> None:
    """
    Keep hosted immutability distinct from local signature and checksum validation.

    Returns:
        None: Acceptance checks public visibility and the provider lock before downloading.
    """
    source = (ROOT / "scripts/release/verify-published.sh").read_text()
    assert ".draft == false and .immutable == true" in source
    assert source.index(".immutable == true") < source.index("gh release download")


@pytest.mark.parametrize("result", ["success", "failure", "cancelled", "skipped"])
@pytest.mark.parametrize("enabled", [True, False])
def test_registry_preview_is_required_only_for_eligible_events(result: str, enabled: bool) -> None:
    """
    Exercise the actual terminal shell with every preview publication outcome.

    Args:
        result (str): Registry publisher conclusion reported by the provider.
        enabled (bool): Whether this trusted event requires preview publication.

    Returns:
        None: Eligible previews require success and other events require an intended skip.
    """
    jobs = mapping(workflow("ci")["jobs"])
    publisher = mapping(jobs["registry-preview"])
    needs = publisher["needs"]
    assert isinstance(needs, list) and set(needs) == {"checks", "tests", "build"}
    assert publisher["secrets"] == {"ARTIFACT_REGISTRY_CREDENTIALS": "${{ secrets.ARTIFACT_REGISTRY_CREDENTIALS }}"}
    condition = str(publisher["if"])
    assert "github.event_name == 'pull_request'" in condition
    assert "github.event.pull_request.head.repo.full_name == github.repository" in condition
    assert "github.ref == 'refs/heads/main'" in condition
    steps = mapping(jobs["required"])["steps"]
    assert isinstance(steps, list)
    gate = mapping(steps[0])
    completed = subprocess.run(
        ["bash", "-e", "-c", str(gate["run"])],
        check=False,
        capture_output=True,
        env={
            **os.environ,
            "CHECKS": "success",
            "TESTS": "success",
            "BUILD": "success",
            "READINESS_REQUIRED": "false",
            "READINESS": "skipped",
            "REGISTRY": result,
            "REGISTRY_REQUIRED": str(enabled).lower(),
        },
    )
    assert (completed.returncode == 0) == (result == ("success" if enabled else "skipped"))
