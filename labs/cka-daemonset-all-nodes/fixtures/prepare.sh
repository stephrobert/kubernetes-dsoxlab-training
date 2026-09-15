#!/usr/bin/env bash
# Pose la situation : le taint de production sur le control plane, le
# namespace monitoring vide. Le taint est NoSchedule : ce qui tourne déjà
# sur le control plane, CoreDNS et Calico, n'est pas évincé.
#
# Rejouable : le namespace est attendu s'il se termine, un DaemonSet laissé
# par un passage précédent est retiré, le taint est posé avec --overwrite.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

kubectl taint nodes k8s-cp.lab node-role.kubernetes.io/control-plane=:NoSchedule --overwrite

if [[ "$(kubectl get namespace monitoring -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/monitoring --timeout=180s
fi
kubectl get namespace monitoring >/dev/null 2>&1 || kubectl create namespace monitoring
kubectl -n monitoring delete daemonset monitor-agent --ignore-not-found --wait=true

kubectl get nodes -o custom-columns='NOM:.metadata.name,TAINTS:.spec.taints[*].key'
echo "k8s-cp.lab porte son taint, monitoring est vide : à l'apprenant de poser l'agent."
