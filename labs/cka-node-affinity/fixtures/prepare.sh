#!/usr/bin/env bash
# Pose la situation : aucun nœud avec disktype, storage-tier ou accelerator,
# le namespace lab vide.
#
# Rejouable : le namespace est attendu s'il se termine, les labels d'un
# passage précédent sont retirés de tous les nœuds.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

kubectl label nodes --all disktype- storage-tier- accelerator- 2>/dev/null || true

if [[ "$(kubectl get namespace lab -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/lab --timeout=180s
fi
kubectl get namespace lab >/dev/null 2>&1 || kubectl create namespace lab
kubectl -n lab delete deployment storage-app --ignore-not-found --wait=true
kubectl -n lab delete pod gpu-app --ignore-not-found --wait=true

kubectl get nodes -o custom-columns='NOM:.metadata.name,DISKTYPE:.metadata.labels.disktype,ACCELERATOR:.metadata.labels.accelerator'
echo "Aucun nœud étiqueté, lab est vide : à l'apprenant de placer."
