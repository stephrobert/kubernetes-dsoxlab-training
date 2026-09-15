#!/usr/bin/env bash
# Pose la situation : un namespace sans le Pod demandé. Le travail de
# l'apprenant, c'est de l'écrire, durci, et de le faire tourner.
#
# Rejouable : le namespace est attendu s'il se termine, et le Pod d'un
# passage précédent est retiré.
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

kubectl -n lab delete pod hardened --ignore-not-found --wait=true

echo "Situation posée : le namespace lab attend le Pod hardened."
