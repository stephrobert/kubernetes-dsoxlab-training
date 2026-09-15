#!/usr/bin/env bash
# Pose la situation : le namespace lab vide, aucun PV lab-pv, aucune
# StorageClass manual. Le répertoire réservé a été recréé par le setup.
#
# Rejouable : le namespace est attendu s'il se termine, le PV d'un passage
# précédent est supprimé, et son finalizer retiré s'il reste Released.
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
kubectl -n lab delete pod data-pod --ignore-not-found --wait=true
kubectl -n lab delete pvc lab-pvc --ignore-not-found --wait=true
kubectl delete pv lab-pv --ignore-not-found --wait=true --timeout=60s || true
kubectl delete storageclass manual --ignore-not-found

kubectl get storageclass
kubectl get pv
echo "Aucune StorageClass, aucun PV : à l'apprenant de créer le volume."
