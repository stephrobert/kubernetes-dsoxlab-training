#!/usr/bin/env bash
# Pose la situation du lab sur le cluster kind « boutique » :
#
#   - le namespace guichet, neuf, avec le Deployment annonces, autre que celui de
#     la leçon (echo sur 8080) : deux réplicas d'agnhost netexec sur le port
#     9376, label app=annonces. Sur /hostname, chaque Pod répond son propre nom ;
#   - aucun Service : l'apprenant le crée ;
#   - le relevé à compléter, ~/guichet/releve.txt.
#
# Ne touche ni aux Nodes, ni à kube-system, ni aux namespaces des autres labs.
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
NS=guichet
AGNHOST="registry.k8s.io/e2e-test-images/agnhost:2.61@sha256:101f3357d1ad890c3090e78ea6c6a47dc5137cbe19836796e13d5dcb2b84d2e6"

# --ignore-not-found plutôt qu'un get préalable : un namespace encore en
# Terminating au moment du get disparaîtrait avant le delete (NotFound, set -e).
kubectl delete namespace "$NS" --ignore-not-found --wait=true --timeout=180s
kubectl create namespace "$NS"
# La leçon montre echo sur 8080 : le challenge prend annonces sur 9376.
kubectl -n "$NS" create deployment annonces --replicas=2 --port=9376 --image="$AGNHOST" \
  -- /agnhost netexec --http-port=9376
kubectl -n "$NS" rollout status deployment/annonces --timeout=180s

install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/${NS}"
cat > "${LAB_HOME}/${NS}/releve.txt" <<'RELEVE'
# Ce que vous lisez à travers le tunnel, une valeur par clé.
# What you read through the tunnel, one value per key.
# Les lignes qui commencent par # sont ignorées. Lines starting with # are ignored.

pod-du-tunnel:
RELEVE
chown "$LAB_USER:$LAB_USER" "${LAB_HOME}/${NS}/releve.txt"
echo "Situation posée : annonces à 2 réplicas sur 9376, aucun Service."
