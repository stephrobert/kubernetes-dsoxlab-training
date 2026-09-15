#!/usr/bin/env bash
# Pose la situation : deux namespaces vides, dev et prod.
#
# Rejouable : chaque namespace est attendu s'il se termine, et ce qu'un
# passage précédent y a laissé est retiré.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

for ns in dev prod; do
  if [[ "$(kubectl get namespace "$ns" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
    kubectl wait --for=delete "namespace/$ns" --timeout=180s
  fi
  kubectl get namespace "$ns" >/dev/null 2>&1 || kubectl create namespace "$ns"
  kubectl -n "$ns" delete deployment,service --all --wait=true
done

echo "Situation posée : dev et prod existent, vides."
