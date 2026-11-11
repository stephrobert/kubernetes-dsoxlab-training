#!/usr/bin/env bash
# Pose la situation du lab k8s-ecrire-un-manifeste sur le cluster kind « lab » :
#
#   - le namespace commandes, avec un Deployment rapport FAUTIF : une image qui
#     n'existe pas et un seul réplica. Son uid est mémorisé dans
#     /var/lib/dsoxlab/ecrire-un-manifeste.json : l'apprenant doit le corriger
#     en place, un rapport recréé ne compte pas ;
#   - ~/commandes/, vide, où l'apprenant écrit son manifeste api.yaml ;
#   - aucun objet api dans default, ni dans commandes.
#
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
MEMOIRE=/var/lib/dsoxlab/ecrire-un-manifeste.json

kubectl delete namespace commandes --ignore-not-found --wait=true --timeout=180s
kubectl -n default delete deployment/api service/api configmap/api-config --ignore-not-found
kubectl create namespace commandes
kubectl -n commandes apply -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rapport
spec:
  replicas: 1
  selector:
    matchLabels:
      app: rapport
  template:
    metadata:
      labels:
        app: rapport
    spec:
      containers:
        - name: rapport
          image: nginx:1.30.5-introuvable
          ports:
            - containerPort: 80
EOF
uid="$(kubectl -n commandes get deployment rapport -o jsonpath='{.metadata.uid}')"
install -d -m 0755 /var/lib/dsoxlab
printf '{"rapport_uid": "%s"}\n' "$uid" > "$MEMOIRE"

rm -rf "${LAB_HOME:?}/commandes"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/commandes"
echo "Situation posée : rapport fautif (uid ${uid}), ~/commandes/ vide."
