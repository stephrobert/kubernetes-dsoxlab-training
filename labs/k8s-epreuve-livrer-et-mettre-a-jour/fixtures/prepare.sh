#!/usr/bin/env bash
# Pose la situation de l'épreuve du niveau 1 sur le cluster kind « boutique » :
#
#   - aucun namespace livraison : l'apprenant crée lui-même l'espace de son
#     équipe ;
#   - le namespace entrepot, avec le composant stock EN PANNE : un Deployment
#     busybox qui lit la clé SEUIL d'un ConfigMap qui ne la porte pas. Son
#     conteneur reste en CreateContainerConfigError, la panne que montre la
#     leçon ConfigMaps ;
#   - ~/epreuve/, vide, où l'apprenant écrit la cause de la panne
#     (cause-stock.txt) avant de la réparer.
#
# Ne touche qu'à livraison, entrepot et à l'ancien namespace boutique de
# l'épreuve. Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
BUSYBOX="busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"

# --ignore-not-found plutôt qu'un get préalable : un namespace encore en
# Terminating au moment du get disparaîtrait avant le delete (NotFound, set -e).
kubectl delete namespace livraison entrepot boutique --ignore-not-found --wait=true --timeout=180s
kubectl -n default delete deployment/vitrine service/vitrine --ignore-not-found
kubectl create namespace entrepot
kubectl -n entrepot create configmap stock-config --from-literal=UNITE=pieces
kubectl -n entrepot apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stock
spec:
  replicas: 1
  selector:
    matchLabels:
      app: stock
  template:
    metadata:
      labels:
        app: stock
    spec:
      containers:
        - name: stock
          image: ${BUSYBOX}
          command: ["sleep", "86400"]
          env:
            - name: STOCK_SEUIL
              valueFrom:
                configMapKeyRef:
                  name: stock-config
                  key: SEUIL
EOF
kubectl -n entrepot wait pod -l app=stock \
  --for=jsonpath='{.status.containerStatuses[0].state.waiting.reason}'=CreateContainerConfigError --timeout=120s

rm -rf "${LAB_HOME:?}/epreuve"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/epreuve"
echo "Situation posée : stock en panne dans entrepot, aucun namespace livraison."
