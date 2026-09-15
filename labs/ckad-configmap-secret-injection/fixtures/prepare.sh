#!/usr/bin/env bash
# Pose la situation : un namespace vide de tout ce que le lab demande. Le
# travail de l'apprenant, c'est de le remplir.
#
# Rejouable : le namespace est attendu s'il se termine, et les objets d'un
# passage précédent sont retirés.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace lab -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/lab --timeout=180s
fi
kubectl get namespace lab >/dev/null 2>&1 || kubectl create namespace lab

kubectl -n lab delete pod app --ignore-not-found --wait=true
kubectl -n lab delete configmap app-settings --ignore-not-found
kubectl -n lab delete secret db-credentials --ignore-not-found

echo "Situation posée : le namespace lab attend app-settings, db-credentials et app."
