#!/usr/bin/env bash
# Pose la situation du lab k8s-interroger-prometheus-en-promql.
#
# Le socle de supervision (Prometheus v3.16.0, kube-state-metrics v2.20.0) est
# posé par setup.yaml. Ce script pose le namespace atelier-promql, où
# relance-auto s'arrête en erreur toutes les 10 secondes et redémarre (pour
# que la question des redémarrages ait une réponse non nulle), et retire le
# ConfigMap requetes qu'un passage précédent aurait laissé.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace atelier-promql -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/atelier-promql --timeout=180s
fi
kubectl delete namespace atelier-promql --ignore-not-found --wait=true --timeout=180s
kubectl create namespace atelier-promql
kubectl -n atelier-promql create deployment relance-auto --image=busybox:1.37 \
  -- sh -c 'sleep 10; exit 1'
kubectl -n atelier-promql rollout status deployment/relance-auto --timeout=60s || true
echo "Situation posee : atelier-promql et relance-auto, aucun ConfigMap requetes."
