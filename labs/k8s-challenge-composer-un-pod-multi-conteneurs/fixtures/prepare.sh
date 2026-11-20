#!/usr/bin/env bash
# Pose la situation du challenge : le namespace photo et une ConfigMap
# vitrine dont le titre est tiré au sort. L'apprenant compose tout le reste :
# l'init container qui écrit la page, le serveur qui la sert, le sidecar
# natif qui relaie le journal d'accès, et leurs deux volumes.
#
# Le titre change à chaque préparation : la page attendue ne se recopie pas.
# Rejouable : le namespace est recréé à neuf.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

NS=photo
MEMOIRE=/var/lib/dsoxlab/challenge-composer-un-pod-multi-conteneurs.json

if [[ "$(kubectl get namespace "$NS" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete "namespace/$NS" --timeout=180s
fi
kubectl delete namespace "$NS" --ignore-not-found --wait=true --timeout=180s
kubectl create namespace "$NS"

TITRE="Exposition-$(head -c 4 /dev/urandom | od -An -tx1 | tr -d ' \n')"
kubectl create configmap vitrine -n "$NS" --from-literal=titre="$TITRE"

install -d -m 0755 /var/lib/dsoxlab
printf '{"titre": "%s"}\n' "$TITRE" > "$MEMOIRE"
chmod 0600 "$MEMOIRE"

kubectl get configmap vitrine -n "$NS"
echo "Situation posée : namespace photo, ConfigMap vitrine."
