#!/usr/bin/env bash
# Pose la situation : une revendication qui reste en attente, et une
# application qui ne demarre donc pas.
#
# Le provisionneur est installe par le setup, mais la revendication posee ici
# ne DESIGNE AUCUNE CLASSE, avec un storageClassName vide. C'est le geste qui
# desactive explicitement le provisionnement dynamique : la revendication
# attend alors un volume cree a la main, qui n'existe pas.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace archives -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/archives --timeout=180s
fi
kubectl get namespace archives >/dev/null 2>&1 || kubectl create namespace archives

# Tout est REPOSE a l'identique a chaque passage : une revendication liee d'un
# passage precedent ferait rendre 100 avant le travail.
kubectl -n archives delete pod registre --ignore-not-found --wait=true
kubectl -n archives delete pvc donnees --ignore-not-found --wait=true

kubectl apply -f - <<'YAML'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: donnees
  namespace: archives
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ""
  resources:
    requests:
      storage: 128Mi
YAML

# La revendication ne se liera pas : on ne l'attend donc pas, on la constate.
sleep 5
kubectl -n archives get pvc donnees
kubectl get storageclass
echo "Situation posee : la revendication attend un volume que personne n'a cree."
