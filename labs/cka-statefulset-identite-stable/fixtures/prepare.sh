#!/usr/bin/env bash
# Pose la situation du lab cka-statefulset-identite-stable sur le cluster kind
# « lab » : le namespace identites, où l'annuaire tourne en Deployment à trois
# réplicas. Ses Pods portent des noms tirés au hasard et ne gardent rien :
# c'est ce que l'apprenant remplace par un StatefulSet.
#
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

BUSYBOX="busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"

kubectl delete namespace identites --ignore-not-found --wait=true --timeout=180s
kubectl create namespace identites
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: annuaire
  namespace: identites
spec:
  replicas: 3
  selector:
    matchLabels:
      app: annuaire
  template:
    metadata:
      labels:
        app: annuaire
    spec:
      terminationGracePeriodSeconds: 5
      containers:
        - name: annuaire
          image: ${BUSYBOX}
          command: ["sh", "-c", "sleep 86400"]
EOF
kubectl -n identites rollout status deployment/annuaire --timeout=180s
echo "Situation posée : l'annuaire tourne en Deployment, sans identité stable."
