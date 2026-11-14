#!/usr/bin/env bash
# Joué sur k8s-w1.lab par le setup, en root : la machine redevient un worker à
# joindre, et ce que la jonction exige est défait.
#
#   - kubeadm reset : plus de kubelet.conf, plus de certificats de nœud ;
#   - /etc/cni/net.d vidé (le joker est développé ICI, en root) ;
#   - paquets dégelés ;
#   - containerd revenu au pilote cgroupfs (SystemdCgroup = false), redémarré ;
#   - un fichier de swap actif ET inscrit dans fstab : le kubelet refuse de
#     démarrer tant qu'il est là, et un simple swapoff ne survit pas au reboot.
#
# Rejouable : chaque étape vérifie l'état avant d'agir.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

kubeadm reset -f > /dev/null 2>&1 || true
rm -rf /etc/cni/net.d/*
# iptables n'est pas vidé : kube-proxy et Calico reprogramment leurs règles à la
# jonction, et vider les règles d'une machine jointe par SSH est un risque inutile.

apt-mark unhold kubeadm kubelet kubectl > /dev/null

sed -i 's/SystemdCgroup = true/SystemdCgroup = false/' /etc/containerd/config.toml
systemctl restart containerd

SWAP=/swapfile-lab
if [ ! -f "$SWAP" ]; then
  fallocate -l 512M "$SWAP"
  chmod 600 "$SWAP"
  mkswap "$SWAP" > /dev/null
fi
# Toute ligne, commentée ou non, est retirée avant d'en écrire une active.
sed -i "\#${SWAP}#d" /etc/fstab
echo "${SWAP} none swap sw 0 0" >> /etc/fstab
swapon --show=NAME --noheadings | grep -qx "$SWAP" || swapon "$SWAP"

echo "worker réinitialisé : $(hostname)"
