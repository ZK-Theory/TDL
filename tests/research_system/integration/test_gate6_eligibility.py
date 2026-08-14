from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from research_system.canonical import canonical_bytes
import research_system.discovery.dossier as dossier_module
from research_system.errors import IntegrityError
from research_system.gate6_eligibility import certify_scale01_eligibility, create_scale01_root_grant
from research_system.cli import main


REPO = Path(__file__).resolve().parents[3]
RUNTIME_ROOT = Path(os.environ.get("TDL_REPOSITORY_ROOT", Path.home() / "TDL"))
CONTRACT_ROOT = RUNTIME_ROOT / ".research-system" / "contracts" / "wp6-4"
VAULT_ROOT = Path(os.environ.get("TDA_VAULT_ROOT", RUNTIME_ROOT / "vault"))
AUTHORITY_PATH = REPO / ".research-system" / "contracts" / "wp6-6" / "tda-scale-dossier-expected-set-authority.json"
NOW = datetime(2026, 8, 14, tzinfo=UTC)
EXPIRY = datetime(2026, 9, 30, tzinfo=UTC)


def _real_roots_or_skip() -> dict[str, Path]:
    if not CONTRACT_ROOT.is_dir() or not VAULT_ROOT.is_dir():
        pytest.skip("real TDA-scale dossier roots are not configured")
    return {"repo": CONTRACT_ROOT, "vault": VAULT_ROOT}


def _member_bytes() -> dict[str, bytes]:
    authority = json.loads(AUTHORITY_PATH.read_bytes())
    roots = _real_roots_or_skip()
    return {
        member["member_key"]: (roots[member["root_id"]] / member["relative_path"]).read_bytes()
        for member in authority["expected_set"]["members"]
    }


def _rewrite_grant(grant_path: Path, mutate) -> None:
    grant = json.loads(grant_path.read_bytes())
    mutate(grant)
    preimage = {key: value for key, value in grant.items() if key != "grant_id"}
    grant["grant_id"] = f"g6rg_{hashlib.sha256(canonical_bytes(preimage)).hexdigest()}"
    grant_path.write_bytes(canonical_bytes(grant))


@pytest.mark.integration
def test_real_dossier_capability_grant_produces_one_immutable_provider_free_envelope(tmp_path: Path) -> None:
    """The real public eligibility seam consumes canonical WP6.6 evidence without writing inputs."""

    roots = _real_roots_or_skip()
    before = _member_bytes()
    grant_path = tmp_path / "scale01-root-grant.json"
    output_path = tmp_path / "scale01-eligibility-envelope.json"

    grant = create_scale01_root_grant(
        repository_root=REPO,
        roots=roots,
        output_path=grant_path,
        expires_at=EXPIRY,
    )
    envelope = certify_scale01_eligibility(
        repository_root=REPO,
        roots=roots,
        root_grant_path=grant_path,
        output_path=output_path,
        now=NOW,
    )

    assert grant["enforcement"] == "capability_read_only"
    assert envelope["eligibility_verdict"] == "eligible"
    assert envelope["dispatchable"] is True
    assert envelope["execution_authorized"] is False
    assert envelope["provider_execution"] == "forbidden"
    assert envelope["dossier_admission"]["event_type"] == "ResearchDossierAdmitted"
    assert envelope["dossier_admission"]["event_count"] == 35
    assert output_path.read_bytes() == json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
    assert {key: hashlib.sha256(value).hexdigest() for key, value in _member_bytes().items()} == {
        key: hashlib.sha256(value).hexdigest() for key, value in before.items()
    }


@pytest.mark.integration
def test_public_gate6_cli_runs_the_real_positive_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    roots = _real_roots_or_skip()
    grant_path = tmp_path / "scale01-root-grant.json"
    output_path = tmp_path / "scale01-eligibility-envelope.json"
    expiry = (datetime.now(UTC) + timedelta(days=1)).isoformat().replace("+00:00", "Z")

    assert (
        main(
            [
                "gate6",
                "root-grant",
                "--repository-root",
                str(REPO),
                "--repository-contract-root",
                str(roots["repo"]),
                "--vault-root",
                str(roots["vault"]),
                "--expires-at",
                expiry,
                "--output",
                str(grant_path),
            ]
        )
        == 0
    )
    grant_stdout = json.loads(capsys.readouterr().out)
    assert grant_stdout["grant_id"].startswith("g6rg_")

    assert (
        main(
            [
                "gate6",
                "certify",
                "--repository-root",
                str(REPO),
                "--repository-contract-root",
                str(roots["repo"]),
                "--vault-root",
                str(roots["vault"]),
                "--root-grant",
                str(grant_path),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )
    envelope_stdout = json.loads(capsys.readouterr().out)
    assert envelope_stdout == json.loads(output_path.read_bytes())
    assert envelope_stdout["execution_authorized"] is False


@pytest.mark.integration
@pytest.mark.parametrize("failure", ["missing", "write_capable", "substituted", "expired", "tampered"])
def test_invalid_root_grants_fail_closed_without_an_envelope(tmp_path: Path, failure: str) -> None:
    roots = _real_roots_or_skip()
    grant_path = tmp_path / "scale01-root-grant.json"
    create_scale01_root_grant(
        repository_root=REPO,
        roots=roots,
        output_path=grant_path,
        expires_at=EXPIRY,
        now=NOW,
    )
    if failure == "missing":
        grant_path = tmp_path / "missing-root-grant.json"
    elif failure == "write_capable":
        _rewrite_grant(grant_path, lambda grant: grant.__setitem__("enforcement", "read_write"))
    elif failure == "substituted":
        _rewrite_grant(grant_path, lambda grant: grant["roots"][0].__setitem__("root_identity_hash", "0" * 64))
    elif failure == "expired":
        _rewrite_grant(grant_path, lambda grant: grant.__setitem__("expires_at", "2026-08-13T00:00:00Z"))
    else:
        _rewrite_grant(
            grant_path,
            lambda grant: grant["authority_refs"].__setitem__("dossier_expected_set_file_sha256", "0" * 64),
        )
    output_path = tmp_path / "negative-output" / f"{failure}.json"

    with pytest.raises(IntegrityError):
        certify_scale01_eligibility(
            repository_root=REPO,
            roots=roots,
            root_grant_path=grant_path,
            output_path=output_path,
            now=NOW,
        )

    assert not output_path.exists()
    assert not output_path.parent.exists()


@pytest.mark.integration
def test_tampered_real_dossier_member_fails_before_eligibility_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    roots = _real_roots_or_skip()
    grant_path = tmp_path / "scale01-root-grant.json"
    create_scale01_root_grant(
        repository_root=REPO,
        roots=roots,
        output_path=grant_path,
        expires_at=EXPIRY,
        now=NOW,
    )
    original = dossier_module._open_registered_member

    def tamper_scale01(member, registered_roots):
        raw = original(member, registered_roots)
        return b"tampered" if member.member_key == "SCALE-01" else raw

    monkeypatch.setattr(dossier_module, "_open_registered_member", tamper_scale01)
    output_path = tmp_path / "tampered-output" / "eligibility.json"

    with pytest.raises(IntegrityError, match="member_content_tampered"):
        certify_scale01_eligibility(
            repository_root=REPO,
            roots=roots,
            root_grant_path=grant_path,
            output_path=output_path,
            now=NOW,
        )

    assert not output_path.exists()
    assert not output_path.parent.exists()


@pytest.mark.integration
def test_final_gate6_certification_script_runs_the_real_dossier_selection(tmp_path: Path) -> None:
    roots = _real_roots_or_skip()
    grant_path = tmp_path / "scale01-root-grant.json"
    output_path = tmp_path / "scale01-eligibility-envelope.json"
    create_scale01_root_grant(
        repository_root=REPO,
        roots=roots,
        output_path=grant_path,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    environment = {
        **os.environ,
        "TDL_PYTHON": sys.executable,
        "TDL_REPOSITORY_ROOT": str(RUNTIME_ROOT),
        "TDA_VAULT_ROOT": str(VAULT_ROOT),
        "TDL_GATE6_ROOT_GRANT": str(grant_path),
        "TDL_GATE6_ENVELOPE_OUTPUT": str(output_path),
    }
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(REPO / "tools" / "certify_gate6_real_dossier.ps1"),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        env=environment,
        timeout=120,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert json.loads(output_path.read_bytes())["eligibility_verdict"] == "eligible"
