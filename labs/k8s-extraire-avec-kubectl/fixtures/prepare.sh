#!/usr/bin/env bash
# Pose la situation du lab sur le cluster kind « boutique » :
#
#   - le namespace extraction, neuf, avec le Deployment web de l'aide-mémoire :
#     deux réplicas de nginx 1.30.5, label app=web, conteneur nginx ;
#   - le déploiement mis en PAUSE, puis son image passée en 1.30.6 : le modèle
#     dit 1.30.6, les Pods tournent toujours en 1.30.5. Seule la lecture du
#     modèle donne l'image demandée ;
#   - le relevé ~/extraction/releve.txt, et le répertoire où l'apprenant écrit
#     ses deux listes.
#
# Ne touche ni aux Nodes, ni à kube-system, ni aux namespaces des autres labs.
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
NS=extraction
V1="nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
V2="nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703"

# --ignore-not-found plutôt qu'un get préalable : un namespace encore en
# Terminating au moment du get disparaîtrait avant le delete (NotFound, set -e).
kubectl delete namespace "$NS" --ignore-not-found --wait=true --timeout=180s
kubectl create namespace "$NS"
kubectl -n "$NS" create deployment web --replicas=2 --image="$V1"
kubectl -n "$NS" rollout status deployment/web --timeout=180s
kubectl -n "$NS" rollout pause deployment/web
kubectl -n "$NS" set image deployment/web nginx="$V2"

rm -rf "${LAB_HOME:?}/${NS}"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/${NS}"
cat > "${LAB_HOME}/${NS}/releve.txt" <<'RELEVE'
# L'image demandée par le modèle de Pod du Deployment web.
# The image asked for by the Pod template of the web Deployment.
# Les lignes qui commencent par # sont ignorées. Lines starting with # are ignored.

image-modele:
RELEVE
chown "$LAB_USER:$LAB_USER" "${LAB_HOME}/${NS}/releve.txt"
echo "Situation posée : web en pause, modèle en 1.30.6, Pods en 1.30.5."
