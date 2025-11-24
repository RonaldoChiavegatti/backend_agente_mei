"""Validador do provisionamento da VM Linux para o homelab.

Executa verificações locais para garantir que:
- O SO é Debian/Ubuntu (ou variante Raspberry Pi) suportado.
- Pacotes essenciais estão instalados.
- O SSH está configurado para recusar autenticação por senha.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable, List, Tuple

SUPPORTED_OS = {"ubuntu", "debian", "raspbian"}
REQUIRED_PACKAGES = [
    "openssh-server",
    "sudo",
    "unattended-upgrades",
    "ca-certificates",
]


class ValidationError(RuntimeError):
    """Erro quando um requisito não é atendido."""


def parse_os_release(path: Path = Path("/etc/os-release")) -> Tuple[str, str]:
    if not path.exists():
        raise ValidationError("/etc/os-release não encontrado")

    os_id = ""
    pretty = ""
    for line in path.read_text().splitlines():
        if line.startswith("ID="):
            os_id = line.split("=", 1)[1].strip().strip('"')
        elif line.startswith("PRETTY_NAME="):
            pretty = line.split("=", 1)[1].strip().strip('"')

    if not os_id:
        raise ValidationError("ID do SO não encontrado em /etc/os-release")
    return os_id, pretty or os_id


def check_supported_os(path: Path = Path("/etc/os-release")) -> str:
    os_id, pretty = parse_os_release(path)
    if os_id not in SUPPORTED_OS:
        raise ValidationError(f"SO {pretty} não é suportado; use Debian/Ubuntu.")
    return pretty


def check_packages(packages: Iterable[str] = REQUIRED_PACKAGES) -> List[str]:
    missing: List[str] = []
    for package in packages:
        result = subprocess.run(
            ["dpkg-query", "-W", "-f", "${Status}", package],
            capture_output=True,
            text=True,
            check=False,
        )
        if "install ok installed" not in result.stdout:
            missing.append(package)
    if missing:
        raise ValidationError(f"Pacotes ausentes: {', '.join(missing)}")
    return list(packages)


def _collect_sshd_configs(sshd_config: Path, sshd_config_d: Path) -> str:
    contents = []
    if sshd_config.exists():
        contents.append(sshd_config.read_text())
    if sshd_config_d.exists():
        for path in sorted(sshd_config_d.glob("*.conf")):
            contents.append(path.read_text())
    return "\n".join(contents)


def check_ssh_password_disabled(
    sshd_config: Path = Path("/etc/ssh/sshd_config"),
    sshd_config_d: Path = Path("/etc/ssh/sshd_config.d"),
) -> None:
    text = _collect_sshd_configs(sshd_config, sshd_config_d)
    lowered = text.lower()
    if "passwordauthentication no" not in lowered:
        raise ValidationError("PasswordAuthentication não está configurado como 'no'")
    if "permitrootlogin no" not in lowered:
        raise ValidationError("PermitRootLogin não está configurado como 'no'")


def main() -> int:
    try:
        pretty = check_supported_os()
        print(f"[ok] SO suportado: {pretty}")

        installed = check_packages()
        print(f"[ok] Pacotes encontrados: {', '.join(installed)}")

        check_ssh_password_disabled()
        print("[ok] SSH configurado para recusar senha e login de root")

    except ValidationError as exc:  # pragma: no cover - fluxo de erro controlado
        print(f"[erro] {exc}")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - chamado direto
    raise SystemExit(main())
