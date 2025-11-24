"""Testes de unidade para o validador de provisionamento de VM."""

from __future__ import annotations

from pathlib import Path

import pytest

from infra import validate_vm


def test_parse_os_release_reads_id_and_pretty(tmp_path: Path) -> None:
    content = "\n".join([
        "NAME=Ubuntu",
        "ID=ubuntu",
        "PRETTY_NAME=\"Ubuntu 22.04.3 LTS\"",
    ])
    path = tmp_path / "os-release"
    path.write_text(content)

    os_id, pretty = validate_vm.parse_os_release(path)

    assert os_id == "ubuntu"
    assert pretty == "Ubuntu 22.04.3 LTS"


def test_check_supported_os_rejects_unknown(tmp_path: Path) -> None:
    path = tmp_path / "os-release"
    path.write_text("ID=arch\nPRETTY_NAME=\"Arch Linux\"")

    with pytest.raises(validate_vm.ValidationError):
        validate_vm.check_supported_os(path)


def test_check_packages_reports_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeCompletedProcess:
        def __init__(self, stdout: str):
            self.stdout = stdout

    def fake_run(cmd, capture_output, text, check):  # type: ignore[no-untyped-def]
        package = cmd[-1]
        stdout = "Status: install ok installed" if package != "sudo" else "Status: install ok not-installed"
        return FakeCompletedProcess(stdout=stdout)

    monkeypatch.setattr(validate_vm.subprocess, "run", fake_run)

    with pytest.raises(validate_vm.ValidationError) as excinfo:
        validate_vm.check_packages(["openssh-server", "sudo"])

    assert "sudo" in str(excinfo.value)


def test_check_ssh_password_disabled_reads_conf(tmp_path: Path) -> None:
    main_conf = tmp_path / "sshd_config"
    main_conf.write_text("PasswordAuthentication no\n")
    conf_d = tmp_path / "sshd_config.d"
    conf_d.mkdir()
    (conf_d / "10-homelab.conf").write_text("PermitRootLogin no\n")

    validate_vm.check_ssh_password_disabled(main_conf, conf_d)
