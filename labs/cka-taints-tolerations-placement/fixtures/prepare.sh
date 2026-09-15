#!/usr/bin/env bash
# Pose la situation : le worker sans taint env ni label disktype, le
# namespace lab vide, l'image sur les deux nœuds pour que les Pods
# démarrent vite.
#
# Rejouable : le namespace est attendu s'il se termine, le taint et le label
# d'un passage précédent sont retirés.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

kubectl taint nodes k8s-w1.lab env- 2>/dev/null || true
kubectl label nodes k8s-w1.lab disktype- 2>/dev/null || true

if [[ "$(kubectl get namespace lab -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/lab --timeout=180s
fi
kubectl get namespace lab >/dev/null 2>&1 || kubectl create namespace lab
kubectl -n lab delete pod prod-app dev-app --ignore-not-found --wait=true

kubectl get nodes -o custom-columns='NOM:.metadata.name,TAINTS:.spec.taints[*].key,DISKTYPE:.metadata.labels.disktype'
echo "k8s-w1.lab n'a ni taint env ni label disktype ; lab est vide."
