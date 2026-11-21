#!/usr/bin/env bash
# Pose la situation : un cluster kubeadm sorti de l'installation, et le Job
# qui audite le worker k8s-w1.lab. Les droits des fichiers du kubelet sont
# remis en état par setup.yaml, sur le worker lui-même.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

for _ in $(seq 1 60); do
  kubectl get --raw /healthz >/dev/null 2>&1 && break
  sleep 3
done
kubectl get --raw /healthz >/dev/null
kubectl wait --for=condition=Ready node/k8s-w1.lab --timeout=180s

if [[ "$(kubectl get namespace conformite -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/conformite --timeout=180s
fi
kubectl get namespace conformite >/dev/null 2>&1 || kubectl create namespace conformite
kubectl -n conformite delete job kube-bench --ignore-not-found --wait=true

echo "Situation posee : le worker est dans son etat d'installation, et le Job kube-bench attend en /root."
