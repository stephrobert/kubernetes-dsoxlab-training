#!/usr/bin/env bash
# Pose la situation du lab sur le cluster kind « boutique » : l'application
# inventaire a été créée dans default par erreur (un -n oublié), le namespace
# stock qui devait la recevoir est vide, et le Pod caisse tourne dans le
# namespace caisse. Le relevé à compléter est ~/namespaces/releve.txt.
#
# Ne touche qu'aux namespaces stock et caisse et aux objets inventaire de
# default. Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
AGNHOST=registry.k8s.io/e2e-test-images/agnhost:2.61@sha256:101f3357d1ad890c3090e78ea6c6a47dc5137cbe19836796e13d5dcb2b84d2e6
BUSYBOX=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4

# --ignore-not-found plutôt qu'un get préalable : un namespace encore en
# Terminating au moment du get disparaîtrait avant le delete (NotFound, set -e).
kubectl delete namespace stock caisse --ignore-not-found --wait=true --timeout=180s
kubectl -n default delete deployment/inventaire service/inventaire --ignore-not-found --wait=true

# L'erreur à corriger : inventaire dans default.
kubectl -n default create deployment inventaire --replicas=2 --image="$AGNHOST" \
  -- /agnhost netexec --http-port=8080
kubectl -n default expose deployment inventaire --port=8080
kubectl -n default rollout status deployment/inventaire --timeout=180s

kubectl create namespace stock
kubectl create namespace caisse
kubectl -n caisse run caisse --image="$BUSYBOX" --restart=Never -- sleep 86400
kubectl -n caisse wait --for=condition=Ready pod/caisse --timeout=120s

install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/namespaces"
cat > "${LAB_HOME}/namespaces/releve.txt" <<'RELEVE'
# Ce que vous observez depuis le Pod caisse, une valeur par clé.
# What you observe from the caisse Pod, one value per key.
# Les lignes qui commencent par # sont ignorées. Lines starting with # are ignored.

pod-qui-repond:
nom-court:
RELEVE
chown "$LAB_USER:$LAB_USER" "${LAB_HOME}/namespaces/releve.txt"
echo "Situation posée : inventaire dans default, stock vide, le Pod caisse dans caisse."
