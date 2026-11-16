#!/usr/bin/env bash
# Pose la situation : la release vitrine (chart podinfo) a été installée en
# 6.16.0 (révision 1, saine), puis montée en 6.17.0 avec une image qui
# n'existe pas (révision 2, en échec). Le dépôt de charts podinfo est déclaré
# pour le compte de la session.
#
# Rejouable : la release et le namespace sont recréés.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

NS=helm-demo
SESSION="${SESSION_UTILISATEUR:?le setup passe le compte de la session}"
MAISON=$(getent passwd "$SESSION" | cut -d: -f6)
DEPOT=https://stefanprodan.github.io/podinfo

helm version --short
helm uninstall vitrine -n "$NS" --ignore-not-found --wait
if [[ "$(kubectl get namespace "$NS" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete "namespace/$NS" --timeout=180s
fi
kubectl delete namespace "$NS" --ignore-not-found --wait=true
kubectl create namespace "$NS"

# Le dépôt, côté root pour poser la situation, côté session pour l'apprenant.
helm repo add podinfo "$DEPOT" --force-update
helm repo update podinfo
sudo -u "$SESSION" -H helm repo add podinfo "$DEPOT" --force-update
sudo -u "$SESSION" -H helm repo update podinfo
rm -rf "$MAISON/vitrine"
install -d -o "$SESSION" -g "$SESSION" -m 0755 "$MAISON/vitrine"

# Révision 1 : saine.
helm install vitrine podinfo/podinfo --version 6.16.0 -n "$NS" --wait --timeout 180s
# Révision 2 : l'image demandée n'existe pas, la montée échoue à l'attente.
helm upgrade vitrine podinfo/podinfo --version 6.17.0 -n "$NS" \
  --set image.tag=6.17.99-introuvable --wait --timeout 60s || true

helm history vitrine -n "$NS"
helm status vitrine -n "$NS" | head -8
echo "Situation posée : vitrine en échec à la révision 2."
