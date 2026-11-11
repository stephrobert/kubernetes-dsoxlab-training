#!/usr/bin/env bash
# Pose la situation du lab sur le cluster kind « boutique » :
#
#   - le namespace etiquettes, neuf, avec les deux Deployments de la
#     démonstration de la leçon : web à trois réplicas et api à deux, créés par
#     kubectl create deployment (labels app=web et app=api) ;
#   - le relevé à compléter, ~/etiquettes/releve.txt.
#
# Ne touche ni aux Nodes, ni à kube-system, ni aux namespaces des autres labs.
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
NS=etiquettes
IMAGE="nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"

# --ignore-not-found plutôt qu'un get préalable : un namespace encore en
# Terminating au moment du get disparaîtrait avant le delete (NotFound, set -e).
kubectl delete namespace "$NS" --ignore-not-found --wait=true --timeout=180s
kubectl create namespace "$NS"
kubectl -n "$NS" create deployment web --replicas=3 --image="$IMAGE"
kubectl -n "$NS" create deployment api --replicas=2 --image="$IMAGE"
kubectl -n "$NS" rollout status deployment/web --timeout=180s
kubectl -n "$NS" rollout status deployment/api --timeout=180s

install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/${NS}"
cat > "${LAB_HOME}/${NS}/releve.txt" <<'RELEVE'
# Le sélecteur que vous passeriez à kubectl get pods -l, sans guillemets.
# The selector you would pass to kubectl get pods -l, without quotes.
# Les lignes qui commencent par # sont ignorées. Lines starting with # are ignored.

selecteur:
RELEVE
chown "$LAB_USER:$LAB_USER" "${LAB_HOME}/${NS}/releve.txt"
echo "Situation posée : web à 3 réplicas, api à 2, aucun label env."
