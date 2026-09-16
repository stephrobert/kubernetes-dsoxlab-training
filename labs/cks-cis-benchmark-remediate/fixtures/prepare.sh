#!/usr/bin/env bash
# Pose la situation : un control plane kubeadm sorti de l installation, et le
# Job qui l audite.
#
# Les TROIS manifestes sont sauvegardes, pas seulement celui de l API server :
# le referentiel CIS reproche le meme reglage au controller-manager et au
# scheduler, et le candidat touchera aux trois.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

MANIFESTES=/etc/kubernetes/manifests
mkdir -p /var/backups

attendre_le_control_plane() {
  for _ in $(seq 1 60); do
    kubectl get --raw /healthz >/dev/null 2>&1 && break
    sleep 3
  done
  kubectl get --raw /healthz >/dev/null
  for _ in $(seq 1 40); do
    phases=$(kubectl -n kube-system get pods -l tier=control-plane \
      -o jsonpath='{.items[*].status.phase}' 2>/dev/null || true)
    [[ -n "$phases" && "$phases" != *Pending* ]] && return 0
    sleep 3
  done
  echo "Le control plane ne revient pas en Running." >&2
  return 1
}

for composant in kube-apiserver kube-controller-manager kube-scheduler; do
  sauvegarde="/var/backups/${composant}.avant-cis.yaml"
  if [[ -f "$sauvegarde" ]]; then
    cp -f "$sauvegarde" "${MANIFESTES}/${composant}.yaml"
  else
    cp -f "${MANIFESTES}/${composant}.yaml" "$sauvegarde"
  fi
done
attendre_le_control_plane

if [[ "$(kubectl get namespace conformite -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/conformite --timeout=180s
fi
kubectl get namespace conformite >/dev/null 2>&1 || kubectl create namespace conformite
kubectl -n conformite delete job kube-bench --ignore-not-found --wait=true

# L image est tiree MAINTENANT : le premier audit du candidat ne doit pas
# passer plusieurs minutes a la telecharger.
crictl pull aquasec/kube-bench:latest >/dev/null 2>&1 || true

echo "Situation posee : le control plane est intact, et le Job kube-bench attend en /root."
