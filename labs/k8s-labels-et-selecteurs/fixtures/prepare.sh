#!/usr/bin/env bash
# Pose la situation du lab sur le cluster kind « boutique » :
#
#   - le namespace etiquettes, neuf, avec trois Deployments qui ne sont pas
#     ceux de la leçon (web et api, clé env) : vitrine à trois réplicas et
#     facturation à deux, sans label palier, et outils à un réplica, déjà en
#     palier=interne, pour que palier!=front ne rende pas facturation seul ;
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
kubectl -n "$NS" create deployment vitrine --replicas=3 --image="$IMAGE"
kubectl -n "$NS" create deployment facturation --replicas=2 --image="$IMAGE"
# outils porte déjà palier=interne : palier!=front le rendrait avec
# facturation, seul !palier rend facturation seul.
kubectl -n "$NS" apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: outils
spec:
  replicas: 1
  selector:
    matchLabels:
      app: outils
  template:
    metadata:
      labels:
        app: outils
        palier: interne
    spec:
      containers:
        - name: nginx
          image: ${IMAGE}
EOF
for d in vitrine facturation outils; do
  kubectl -n "$NS" rollout status "deployment/$d" --timeout=180s
done

install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/${NS}"
cat > "${LAB_HOME}/${NS}/releve.txt" <<'RELEVE'
# Le sélecteur que vous passeriez à kubectl get pods -l, sans guillemets.
# The selector you would pass to kubectl get pods -l, without quotes.
# Les lignes qui commencent par # sont ignorées. Lines starting with # are ignored.

selecteur:
RELEVE
chown "$LAB_USER:$LAB_USER" "${LAB_HOME}/${NS}/releve.txt"
echo "Situation posée : vitrine à 3 réplicas, facturation à 2, outils à 1 en palier=interne."
