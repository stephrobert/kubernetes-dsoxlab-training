#!/usr/bin/env bash
# Pose la situation : deux namespaces vides, dev et prod, et ~/kustomize/,
# vide, où l'apprenant écrit sa base et ses overlays.
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
  # Les ConfigMaps générées par un passage précédent, pas kube-root-ca.crt,
  # que Kubernetes pose dans chaque namespace.
  { kubectl -n "$ns" get configmap -o name | grep -v '/kube-root-ca.crt$' || true; } \
    | xargs -r kubectl -n "$ns" delete --wait=true
done

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
rm -rf "${LAB_HOME:?}/kustomize"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/kustomize"

echo "Situation posée : dev et prod existent, vides, et ~/kustomize/ aussi."
