#!/usr/bin/env bash
# Pose la situation : un namespace sans le Job ni le CronJob demandés.
#
# Rejouable : le namespace est attendu s'il se termine, et les objets d'un
# passage précédent sont retirés, Pods de Job compris.
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

kubectl -n lab delete cronjob log-cleanup --ignore-not-found
kubectl -n lab delete job batch-job --ignore-not-found --wait=true

echo "Situation posée : le namespace lab attend batch-job et log-cleanup."
