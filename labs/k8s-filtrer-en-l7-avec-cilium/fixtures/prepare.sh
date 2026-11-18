#!/usr/bin/env bash
# Pose la situation du lab k8s-filtrer-en-l7-avec-cilium, sur le cluster net-*
# que le setup vient de ramener aux valeurs du socle (Cilium 1.20.5, Gateway
# API éteinte, aucun pool, aucune politique).
#
# - Les CRD de la Gateway API sont RETIRÉES s'il en reste : l'apprenant les
#   installe. Le setup a ramené Cilium au socle AVANT, dans cet ordre (mesuré
#   le 2026-11-18 : retirer les CRD pendant que gatewayAPI est actif rend la
#   release Helm illisible).
# - catalogue : l'application fiches (http-echo), son Service, et le client
#   lecteur.
#
# Rien de ce que l'apprenant doit produire n'existe. Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

ECHO="hashicorp/http-echo:1.0.0@sha256:fcb75f691c8b0414d670ae570240cbf95502cc18a9ba57e982ecac589760a186"
CURL="curlimages/curl:8.17.0@sha256:935d9100e9ba842cdb060de42472c7ca90cfe9a7c96e4dacb55e79e560b3ff40"
GWAPI=https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.6.3/standard-install.yaml

kubectl delete namespace catalogue --ignore-not-found --wait=true --timeout=180s
kubectl delete ciliumloadbalancerippools.cilium.io --all --ignore-not-found 2>/dev/null || true
kubectl delete gatewayclass cilium --ignore-not-found 2>/dev/null || true
kubectl delete -f "$GWAPI" --ignore-not-found > /dev/null

kubectl create namespace catalogue
kubectl apply -f - <<YAML
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fiches
  namespace: catalogue
spec:
  replicas: 1
  selector:
    matchLabels: {app: fiches}
  template:
    metadata:
      labels: {app: fiches}
    spec:
      containers:
        - name: fiches
          image: "$ECHO"
          args: ["-text=fiches", "-listen=:5678"]
          ports:
            - containerPort: 5678
---
apiVersion: v1
kind: Service
metadata:
  name: fiches
  namespace: catalogue
spec:
  selector: {app: fiches}
  ports:
    - {name: http, port: 80, targetPort: 5678}
---
apiVersion: v1
kind: Pod
metadata:
  name: lecteur
  namespace: catalogue
  labels: {app: lecteur}
spec:
  containers:
    - {name: c, image: "$CURL", command: [sleep, "36000"]}
YAML
kubectl -n catalogue rollout status deployment/fiches --timeout=180s
kubectl -n catalogue wait --for=condition=Ready pod/lecteur --timeout=180s
# Pod prêt ne veut pas dire backend inscrit : juste après un redémarrage des
# agents Cilium, la première requête a été refusée (curl 7, validation du
# 2026-11-18). On attend que fiches réponde, une minute au plus.
for essai in $(seq 1 12); do
  if kubectl -n catalogue exec lecteur -- curl -s -m 5 http://fiches/; then break; fi
  echo "fiches ne répond pas encore (essai ${essai})"
  sleep 5
done
kubectl -n catalogue exec lecteur -- curl -s -m 5 http://fiches/
echo "Situation posée : fiches répond en HTTP, aucune Gateway, aucune politique."
