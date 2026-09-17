#!/usr/bin/env bash
# Pose la situation : une application qui tourne avec son mot de passe ecrit en
# clair dans son propre manifeste.
#
# Le Deployment est REPOSE a l'identique a chaque passage, et le Secret d'un
# passage precedent est retire : sans cela, le lab rendrait 100 avant le
# travail.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace paiement -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/paiement --timeout=180s
fi
kubectl get namespace paiement >/dev/null 2>&1 || kubectl create namespace paiement

kubectl -n paiement delete secret --all --ignore-not-found 2>/dev/null || true
kubectl -n paiement delete deployment passerelle --ignore-not-found --wait=true

kubectl apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: passerelle
  namespace: paiement
spec:
  replicas: 1
  selector:
    matchLabels:
      app: passerelle
  template:
    metadata:
      labels:
        app: passerelle
    spec:
      containers:
        - name: appli
          image: busybox:1.37
          command: ["sh", "-c", "sleep 86400"]
          env:
            - name: DB_PASSWORD
              value: "Tr3s0r-2026"
YAML

kubectl -n paiement rollout status deployment/passerelle --timeout=240s
kubectl -n paiement get deployment passerelle -o yaml | grep -A2 DB_PASSWORD || true
echo "Situation posee : l'application tourne, et son mot de passe est dans son manifeste."
