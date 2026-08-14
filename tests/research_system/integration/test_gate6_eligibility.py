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
import research_system.gate6_eligibility as gate6_module
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
def test_real_dossier_preflight_refuses_to_publish_without_accepted_admission_event_authority(tmp_path: Path) -> None:
    """A reconstructed event cannot substitute for the governed WP6.6 admission record."""

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
    with pytest.raises(IntegrityError, match="accepted WP6.6 admission event authority is unavailable"):
        certify_scale01_eligibility(
            repository_root=REPO,
            roots=roots,
            root_grant_path=grant_path,
            output_path=output_path,
            now=NOW,
        )

    assert grant["enforcement"] == "capability_read_only"
    assert not output_path.exists()
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
        == 1
    )
    failure = capsys.readouterr()
    assert "accepted WP6.6 admission event authority is unavailable" in failure.err
    assert failure.out == ""
    assert not output_path.exists()


@pytest.mark.integration
def test_public_gate6_cli_unavailable_repository_root_fails_cleanly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output_path = tmp_path / "must-not-exist.json"

    assert (
        main(
            [
                "gate6",
                "root-grant",
                "--repository-root",
                str(tmp_path / "missing-repository-root"),
                "--repository-contract-root",
                str(tmp_path / "irrelevant-contract-root"),
                "--vault-root",
                str(tmp_path / "irrelevant-vault-root"),
                "--expires-at",
                "2026-09-30T00:00:00Z",
                "--output",
                str(output_path),
            ]
        )
        == 1
    )

    captured = capsys.readouterr()
    assert "Gate 6 repository root is unavailable" in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""
    assert not output_path.exists()


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
def test_gate6_admission_uses_sealed_read_only_capabilities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid grant issues narrow readers; raw root paths are not passed to admission."""

    roots = _real_roots_or_skip()
    grant_path = tmp_path / "scale01-root-grant.json"
    output_path = tmp_path / "scale01-eligibility-envelope.json"
    create_scale01_root_grant(
        repository_root=REPO,
        roots=roots,
        output_path=grant_path,
        expires_at=EXPIRY,
        now=NOW,
    )
    original_prepare = gate6_module.prepare_dossier_admission

    # This test examines the narrow capability route only. The unmocked public
    # seam remains fail-closed until an owner supplies accepted event authority.
    monkeypatch.setattr(gate6_module, "_require_accepted_admission_event_authority", lambda _contract: None)

    def require_capabilities(**kwargs):
        capabilities = kwargs["read_only_capabilities"]
        assert kwargs["registered_roots"] == {}
        assert set(capabilities) == {"repo", "vault"}
        assert all(type(capability) is dossier_module.ReadOnlyRootCapability for capability in capabilities.values())
        assert all(not hasattr(capability, "path") for capability in capabilities.values())
        return original_prepare(**kwargs)

    monkeypatch.setattr(gate6_module, "prepare_dossier_admission", require_capabilities)
    envelope = certify_scale01_eligibility(
        repository_root=REPO,
        roots=roots,
        root_grant_path=grant_path,
        output_path=output_path,
        now=NOW,
    )

    assert envelope["eligibility_verdict"] == "eligible"
    with pytest.raises(TypeError, match="issued only for a registered root"):
        dossier_module.ReadOnlyRootCapability()


@pytest.mark.integration
def test_output_under_lexical_vault_junction_is_rejected_before_root_grant_publication(tmp_path: Path) -> None:
    """Physical resolution cannot turn an output inside the vault into an external path."""

    roots = _real_roots_or_skip()
    output_path = VAULT_ROOT / f"gate6-output-isolation-{tmp_path.name}.json"
    assert not output_path.exists()

    with pytest.raises(IntegrityError, match="outside every governed input root"):
        create_scale01_root_grant(
            repository_root=REPO,
            roots=roots,
            output_path=output_path,
            expires_at=EXPIRY,
            now=NOW,
        )

    assert not output_path.exists()


@pytest.mark.integration
def test_uncommitted_gate6_contract_cannot_be_used_for_a_root_grant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The public seam binds its candidate contract to the current Git subject."""

    roots = _real_roots_or_skip()
    original_run = gate6_module.subprocess.run

    def substitute_contract_git_bytes(*args, **kwargs):
        result = original_run(*args, **kwargs)
        if args[0][-1] == "HEAD:.research-system/contracts/gate6/scale01-eligibility-envelope-contract.json":
            return subprocess.CompletedProcess(args[0], 0, stdout=b'{"substituted":true}', stderr=b"")
        return result

    monkeypatch.setattr(gate6_module.subprocess, "run", substitute_contract_git_bytes)
    grant_path = tmp_path / "uncommitted-contract" / "scale01-root-grant.json"

    with pytest.raises(IntegrityError, match="differs from its current Git bytes"):
        create_scale01_root_grant(
            repository_root=REPO,
            roots=roots,
            output_path=grant_path,
            expires_at=EXPIRY,
            now=NOW,
        )

    assert not grant_path.exists()
    assert not grant_path.parent.exists()


@pytest.mark.integration
def test_final_gate6_certification_script_fails_closed_without_admission_event_authority(tmp_path: Path) -> None:
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

    assert result.returncode != 0
    assert "accepted WP6.6 admission event authority is unavailable" in result.stderr
    assert not output_path.exists()
