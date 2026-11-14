#!/usr/bin/env bash
# Joué sur k8s-cp.lab par le setup, en root, après le kubeadm reset : la
# machine redevient un plan de contrôle à initialiser, et ce que kubeadm init
# exige est défait.
#
#   - les modules noyau et les réglages réseau ne sont plus persistants
#     (/etc/modules-load.d/k8s.conf, /etc/sysctl.d/99-kubernetes.conf retirés)
#     et net.ipv4.ip_forward vaut 0 : le preflight de kubeadm init le refuse ;
#   - un fichier de swap actif ET inscrit dans fstab ;
#   - les paquets dégelés ;
#   - le kubeconfig de l'utilisateur retiré (il visait le cluster défait) ;
#   - les manifestes Calico du socle copiés dans ~/kubeadm/calico.
#
# Rejouable : chaque étape vérifie l'état avant d'agir.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

MAISON="$(getent passwd "${LAB_USER}" | cut -d: -f6)"

rm -f /etc/modules-load.d/k8s.conf /etc/sysctl.d/99-kubernetes.conf
# Un passage précédent a pu écrire les mêmes réglages sous un autre nom : toute
# ligne active est commentée, quel que soit le fichier (liens suivis, pour
# /etc/sysctl.d/99-sysctl.conf qui pointe sur /etc/sysctl.conf).
for f in /etc/sysctl.conf /etc/sysctl.d/*.conf; do
  if [ -f "$f" ]; then sed -i --follow-symlinks -E 's/^([[:space:]]*net\.ipv4\.ip_forward[[:space:]]*=.*)$/# \1/' "$f"; fi
done
for f in /etc/modules-load.d/*.conf; do
  if [ -f "$f" ]; then sed -i --follow-symlinks -E 's/^([[:space:]]*(overlay|br_netfilter)[[:space:]]*)$/# \1/' "$f"; fi
done
sysctl -w net.ipv4.ip_forward=0

apt-mark unhold kubeadm kubelet kubectl > /dev/null

SWAP=/swapfile-lab
if [ ! -f "$SWAP" ]; then
  fallocate -l 512M "$SWAP"
  chmod 600 "$SWAP"
  mkswap "$SWAP" > /dev/null
fi
sed -i "\#${SWAP}#d" /etc/fstab
echo "${SWAP} none swap sw 0 0" >> /etc/fstab
swapon --show=NAME --noheadings | grep -qx "$SWAP" || swapon "$SWAP"

rm -f "${MAISON}/.kube/config"
rm -rf "${MAISON}/kubeadm"
install -d -o "${LAB_USER}" -g "${LAB_USER}" "${MAISON}/kubeadm" "${MAISON}/kubeadm/calico"
cp /root/operator-crds.yaml /root/tigera-operator.yaml "${MAISON}/kubeadm/calico/"
cp /root/calico-installation.yaml "${MAISON}/kubeadm/calico/installation.yaml"
chown -R "${LAB_USER}:${LAB_USER}" "${MAISON}/kubeadm"

echo "plan de contrôle à initialiser : $(hostname)"
