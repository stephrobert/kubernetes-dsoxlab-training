#!/usr/bin/env bash
# Pose la situation du lab sur le cluster partagé « architecture » :
#
#   - le namespace reconciliation, neuf, avec le Deployment vitrine à trois
#     réplicas disponibles ;
#   - la mémoire de l'état initial, lisible par root seul : l'uid du
#     ReplicaSet de départ et la génération du Deployment. Elle permet aux
#     tests de constater que ce ReplicaSet a recréé un Pod, puis qu'il a été
#     remplacé sans que le Deployment ait été modifié ;
#   - le relevé à compléter, ~/reconciliation/releve.txt.
#
# Ne touche ni aux Nodes ni à kube-system. Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
IMAGE="nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
MEMOIRE=/var/lib/dsoxlab/observer-la-reconciliation.json

# --ignore-not-found plutôt qu'un get préalable : un namespace encore en
# Terminating au moment du get disparaîtrait avant le delete (NotFound, set -e).
kubectl delete namespace reconciliation --ignore-not-found --wait=true --timeout=180s
kubectl create namespace reconciliation
kubectl -n reconciliation create deployment vitrine --image="$IMAGE" --replicas=3
kubectl -n reconciliation rollout status deployment vitrine --timeout=180s

install -d -m 0700 /var/lib/dsoxlab
rs_uid="$(kubectl -n reconciliation get replicaset -l app=vitrine -o jsonpath='{.items[0].metadata.uid}')"
generation="$(kubectl -n reconciliation get deployment vitrine -o jsonpath='{.metadata.generation}')"
printf '{"replicaset": "%s", "generation": %s}\n' "$rs_uid" "$generation" > "$MEMOIRE"
chmod 0600 "$MEMOIRE"

install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/reconciliation"
cat > "${LAB_HOME}/reconciliation/releve.txt" <<'RELEVE'
# Le contrôleur qui a recréé chaque objet, lu dans les événements.
# The controller that recreated each object, read in the events.
# Les lignes qui commencent par # sont ignorées. Lines starting with # are ignored.

pod-recree-par:
replicaset-recree-par:
RELEVE
chown "$LAB_USER:$LAB_USER" "${LAB_HOME}/reconciliation/releve.txt"
echo "Situation posée : vitrine à 3 réplicas, ReplicaSet ${rs_uid}."
