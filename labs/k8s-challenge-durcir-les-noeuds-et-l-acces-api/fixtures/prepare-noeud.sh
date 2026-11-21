#!/usr/bin/env bash
# Pose la partie « nœud » du challenge sur k8s-w2.lab, jointe au cluster juste
# avant. Ce qu'un ancien modèle de serveur a laissé :
#
#   1. apache2, un paquet du dépôt, actif sur le port 80 dès son installation ;
#   2. releve-inventaire.socket, une unité qu'aucun paquet ne fournit, qui
#      écoute sur le port 9090 et lance un service à chaque connexion :
#      arrêter le service ne ferme pas le port, c'est la socket qui écoute ;
#   3. un compte « prestataire » qui entre en SSH par mot de passe, membre du
#      groupe sudo et titulaire en plus d'un fichier sudoers NOPASSWD ;
#   4. sshd qui accepte le mot de passe et root (05-heritage.conf, lu avant
#      50-cloud-init.conf : sshd garde la PREMIÈRE valeur lue) ;
#   5. le kubelet ouvert à l'anonyme, en AlwaysAllow, avec son port en lecture
#      seule 10255 ;
#   6. aucun pare-feu, et le nftables.conf livré par Ubuntu, qui commence par
#      `flush ruleset`.
#
# Tout est RESTAURÉ au début de chaque passage : un second run après un
# travail réussi doit repartir de la même situation.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare-noeud.log) 2>&1
set -x
export DEBIAN_FRONTEND=noninteractive

APACHE_VERSION="2.4.58-1ubuntu8.19"
KUBELET=/var/lib/kubelet/config.yaml
ESSAIS=/root/.lab-durcir

# ----------------------------------------------------------------------
# 0. Repartir de l'état d'origine
# ----------------------------------------------------------------------
# Pare-feu : `disable` seul, jamais `stop` : l'ExecStop de l'unité est
# `nft flush ruleset`, qui effacerait aussi les règles de kube-proxy et de
# Calico (mesuré le 2026-11-17 dans cks-fermer-l-acces-reseau-au-noeud).
[[ -f /var/backups/nftables.conf.livre ]] || cp /etc/nftables.conf /var/backups/nftables.conf.livre
systemctl disable nftables.service || true
for t in $(nft list tables | awk '$2 == "inet" {print $3}'); do
  nft delete table inet "$t"
done
rm -rf /etc/nftables.d
install -m 0644 /var/backups/nftables.conf.livre /etc/nftables.conf
for t in $(systemctl list-units --type=timer --no-legend 'run-*' | awk '{print $1}'); do
  systemctl stop "$t" || true
done

# SSH : seuls les deux fichiers de l'image restent dans sshd_config.d.
find /etc/ssh/sshd_config.d -type f ! -name 50-cloud-init.conf ! -name 60-cloudimg-settings.conf -delete
if getent group ops-noeuds >/dev/null; then groupdel ops-noeuds; fi
loginctl terminate-user prestataire 2>/dev/null || true
pkill -KILL -u prestataire 2>/dev/null || true
sleep 1
if id prestataire >/dev/null 2>&1; then userdel -r -f prestataire 2>/dev/null || true; fi
rm -f /etc/sudoers.d/90-prestataire

# Services : l'unité maison et apache2, tels que le setup les pose.
systemctl unmask releve-inventaire.socket apache2.service 2>/dev/null || true
systemctl disable --now releve-inventaire.socket 2>/dev/null || true
rm -f /etc/systemd/system/releve-inventaire.socket /etc/systemd/system/releve-inventaire@.service
systemctl daemon-reload

# ----------------------------------------------------------------------
# 1. apache2
# ----------------------------------------------------------------------
apt-get install -y -o DPkg::Lock::Timeout=300 "apache2=${APACHE_VERSION}"
systemctl enable --now apache2.service

# ----------------------------------------------------------------------
# 2. releve-inventaire.socket
# ----------------------------------------------------------------------
cat > /etc/systemd/system/releve-inventaire.socket <<'UNIT'
[Unit]
Description=Releve d'inventaire laisse par l'ancien modele

[Socket]
ListenStream=9090
Accept=yes

[Install]
WantedBy=sockets.target
UNIT
cat > /etc/systemd/system/releve-inventaire@.service <<'UNIT'
[Unit]
Description=Releve d'inventaire, une connexion

[Service]
ExecStart=/usr/bin/cat /etc/os-release
StandardInput=socket
StandardOutput=socket
UNIT
systemctl daemon-reload
systemctl enable --now releve-inventaire.socket

# ----------------------------------------------------------------------
# 3. et 4. Le compte du prestataire, et sshd trop large
# ----------------------------------------------------------------------
useradd -m -s /bin/bash -G sudo prestataire
echo 'prestataire:Prestation-2026' | chpasswd
echo 'prestataire ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/90-prestataire
chmod 0440 /etc/sudoers.d/90-prestataire
visudo -cf /etc/sudoers.d/90-prestataire

cat > /etc/ssh/sshd_config.d/05-heritage.conf <<'CONF'
# Reprise d'un ancien modele de serveur.
PasswordAuthentication yes
PermitRootLogin yes
CONF

# Une clé d'essai, posée chez les trois comptes : les tests ouvrent de VRAIES
# sessions SSH sur 127.0.0.1 et lisent la décision de sshd.
install -d -m 0700 "$ESSAIS"
[[ -f "$ESSAIS/essai_ed25519" ]] || ssh-keygen -q -t ed25519 -N "" -C lab-durcir-essai -f "$ESSAIS/essai_ed25519"
for compte in prestataire student ansible; do
  maison=$(getent passwd "$compte" | cut -d: -f6)
  install -d -m 0700 -o "$compte" -g "$compte" "$maison/.ssh"
  touch "$maison/.ssh/authorized_keys"
  grep -q 'lab-durcir-essai$' "$maison/.ssh/authorized_keys" || cat "$ESSAIS/essai_ed25519.pub" >> "$maison/.ssh/authorized_keys"
  chown "$compte:$compte" "$maison/.ssh/authorized_keys"
  chmod 0600 "$maison/.ssh/authorized_keys"
done

# Un « sshd -D [listener] » orphelin d'un premier démarrage garde l'ancienne
# configuration (mesuré le 2026-11-17 sur un k8s-w2 neuf) : on part d'un seul.
main=$(systemctl show ssh -p MainPID --value)
for p in $(pgrep -f 'sshd -D \[listener\]' || true); do
  [[ "$p" != "$main" ]] && kill "$p" && echo "listener orphelin $p arrete"
done
sshd -t
systemctl reload ssh

# ----------------------------------------------------------------------
# 5. Le kubelet ouvert
# ----------------------------------------------------------------------
python3 - "$KUBELET" <<'PY'
import sys
import yaml
chemin = sys.argv[1]
with open(chemin, encoding="utf-8") as f:
    conf = yaml.safe_load(f)
conf["authentication"]["anonymous"]["enabled"] = True
conf["authorization"]["mode"] = "AlwaysAllow"
conf["readOnlyPort"] = 10255
with open(chemin, "w", encoding="utf-8") as f:
    yaml.safe_dump(conf, f, sort_keys=False)
PY
systemctl restart kubelet

# ----------------------------------------------------------------------
# 6. Vérifier que la situation est posée, sinon le challenge ne mesure rien
# ----------------------------------------------------------------------
for _ in $(seq 1 30); do
  n=$(ss -Htln | awk '{print $4}' | grep -cE ':(80|9090|10255)$' || true)
  [[ "$n" -ge 3 ]] && break
  sleep 2
done
[[ "$n" -ge 3 ]] || { echo "Les ports 80, 9090 et 10255 n ecoutent pas tous ($n sur 3)." >&2; exit 1; }
code=$(curl -sk -o /dev/null -w '%{http_code}' https://127.0.0.1:10250/pods)
[[ "$code" == 200 ]] || { echo "Le kubelet ne rend pas 200 a l anonyme ($code)." >&2; exit 1; }
echo "Situation posee sur k8s-w2 : apache2, releve-inventaire, prestataire, sshd et kubelet ouverts, aucun pare-feu."
