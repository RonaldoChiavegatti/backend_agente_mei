#!/usr/bin/env bash
# Provisiona uma VM Debian/Ubuntu minimal em Raspberry Pi para hospedar o homelab.
# Executar como root logo após instalar o SO base.
set -euo pipefail

HOMELAB_USER="homelab"
SSH_PUBLIC_KEY="${HOMELAB_PUBLIC_KEY:-}"
SSH_PUBLIC_KEY_FILE="${HOMELAB_PUBLIC_KEY_FILE:-}"
REQUIRED_PACKAGES=(
  openssh-server
  sudo
  curl
  ca-certificates
  unattended-upgrades
  fail2ban
  ufw
)

error() {
  echo "[erro] $*" >&2
  exit 1
}

require_root() {
  if [[ "$(id -u)" -ne 0 ]]; then
    error "Execute como root (sudo)."
  fi
}

validate_os() {
  if [[ ! -f /etc/os-release ]]; then
    error "Arquivo /etc/os-release não encontrado; SO não suportado."
  fi
  source /etc/os-release
  case "$ID" in
    ubuntu|debian|raspbian)
      echo "[ok] SO suportado: ${PRETTY_NAME}"
      ;;
    *)
      error "SO ${PRETTY_NAME:-$ID} não suportado. Use Debian/Ubuntu."
      ;;
  esac
}

resolve_public_key() {
  if [[ -n "$SSH_PUBLIC_KEY" ]]; then
    echo "$SSH_PUBLIC_KEY"
    return
  fi

  if [[ -n "$SSH_PUBLIC_KEY_FILE" ]]; then
    if [[ ! -f "$SSH_PUBLIC_KEY_FILE" ]]; then
      error "Arquivo de chave pública não encontrado em $SSH_PUBLIC_KEY_FILE"
    fi
    cat "$SSH_PUBLIC_KEY_FILE"
    return
  fi

  local default_key="$HOME/.ssh/id_rsa.pub"
  if [[ -f "$default_key" ]]; then
    cat "$default_key"
    return
  fi

  error "Forneça HOMELAB_PUBLIC_KEY ou HOMELAB_PUBLIC_KEY_FILE com a chave pública."
}

configure_user() {
  local pubkey="$1"
  if id "$HOMELAB_USER" &>/dev/null; then
    echo "[ok] Usuário $HOMELAB_USER já existe"
  else
    adduser --disabled-password --gecos "Homelab Admin" "$HOMELAB_USER"
    usermod -aG sudo "$HOMELAB_USER"
    echo "[ok] Usuário $HOMELAB_USER criado e adicionado ao sudo"
  fi

  local ssh_dir="/home/${HOMELAB_USER}/.ssh"
  mkdir -p "$ssh_dir"
  chmod 700 "$ssh_dir"
  echo "$pubkey" >"${ssh_dir}/authorized_keys"
  chmod 600 "${ssh_dir}/authorized_keys"
  chown -R "$HOMELAB_USER:$HOMELAB_USER" "$ssh_dir"
  echo "[ok] Chave pública instalada em ${ssh_dir}/authorized_keys"
}

install_packages() {
  echo "[info] Atualizando lista de pacotes..."
  apt-get update -y
  echo "[info] Instalando pacotes essenciais: ${REQUIRED_PACKAGES[*]}"
  apt-get install -y "${REQUIRED_PACKAGES[@]}"
}

configure_ssh() {
  mkdir -p /etc/ssh/sshd_config.d
  cat >/etc/ssh/sshd_config.d/10-homelab.conf <<'CFG'
# Endurecimento mínimo para acesso por chave
PasswordAuthentication no
ChallengeResponseAuthentication no
UsePAM yes
PermitRootLogin no
PubkeyAuthentication yes
CFG
  systemctl enable ssh
  systemctl restart ssh
  echo "[ok] SSH configurado para recusar senha e desabilitar login de root"
}

configure_unattended_upgrades() {
  cat >/etc/apt/apt.conf.d/20auto-upgrades <<'CFG'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
CFG

  cat >/etc/apt/apt.conf.d/51unattended-upgrades-homelab <<'CFG'
Unattended-Upgrade::Allowed-Origins {
        "${distro_id}:${distro_codename}";
        "${distro_id}:${distro_codename}-security";
        "${distro_id}ESM:${distro_codename}";
        "Debian:${distro_codename}-security";
};
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "03:00";
CFG

  systemctl enable unattended-upgrades
  systemctl restart unattended-upgrades || true
  echo "[ok] Atualizações automáticas de segurança habilitadas"
}

configure_firewall() {
  if command -v ufw >/dev/null 2>&1; then
    ufw allow OpenSSH
    ufw --force enable
    echo "[ok] UFW habilitado permitindo apenas SSH por padrão"
  fi
}

main() {
  require_root
  validate_os
  local pubkey
  pubkey=$(resolve_public_key)
  install_packages
  configure_user "$pubkey"
  configure_ssh
  configure_unattended_upgrades
  configure_firewall
  echo "[sucesso] Provisionamento concluído. Conecte-se via SSH como ${HOMELAB_USER}."
}

main "$@"
