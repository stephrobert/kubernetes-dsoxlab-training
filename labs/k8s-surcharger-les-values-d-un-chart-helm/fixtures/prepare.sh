#!/usr/bin/env bash
# Pose la situation : la release catalogue (chart podinfo 6.16.0) tourne avec
# deux réglages posés par l'exploitation, trois réplicas et une couleur. Le
# dépôt de charts podinfo est déclaré pour le compte de la session.
#
# Rejouable : la release et le namespace sont recréés.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

NS=helm-values
SESSION="${SESSION_UTILISATEUR:?le setup passe le compte de la session}"
MAISON=$(getent passwd "$SESSION" | cut -d: -f6)
DEPOT=https://stefanprodan.github.io/podinfo

helm version --short
helm uninstall catalogue -n "$NS" --ignore-not-found --wait
if [[ "$(kubectl get namespace "$NS" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete "namespace/$NS" --timeout=180s
fi
kubectl delete namespace "$NS" --ignore-not-found --wait=true
kubectl create namespace "$NS"

helm repo add podinfo "$DEPOT" --force-update
helm repo update podinfo
sudo -u "$SESSION" -H helm repo add podinfo "$DEPOT" --force-update
sudo -u "$SESSION" -H helm repo update podinfo
rm -rf "$MAISON/catalogue"
install -d -o "$SESSION" -g "$SESSION" -m 0755 "$MAISON/catalogue"

# Les réglages de l'exploitation, posés par --set : ils vivent dans la release.
helm install catalogue podinfo/podinfo --version 6.16.0 -n "$NS" \
  --set replicaCount=3 --set 'ui.color=#ff6b00' --wait --timeout 180s

helm get values catalogue -n "$NS"
echo "Situation posée : catalogue en 6.16.0, trois réplicas, couleur #ff6b00."
