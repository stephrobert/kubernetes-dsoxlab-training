#!/usr/bin/env bash
# Pose la situation : un Deployment qui tourne sur une image de 2021.
#
# L'application marche. C'est ce qui rend le sujet difficile a faire entendre :
# une image vieille de trois ans sert les memes pages qu'une image recente, et
# rien dans le cluster ne signale les 30 failles critiques qu'elle traine.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace chaine-appro -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/chaine-appro --timeout=180s
fi
kubectl get namespace chaine-appro >/dev/null 2>&1 || kubectl create namespace chaine-appro

# Le Deployment est REPOSE a chaque passage, image comprise : sans cela, un
# second run apres un travail reussi repartirait de l'image corrigee, et le
# lab rendrait 100 avant que le candidat n'ait rien fait.
kubectl -n chaine-appro delete deployment web --ignore-not-found --wait=true

kubectl apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: chaine-appro
  labels:
    app: web
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: web
          image: nginx:1.21
          ports:
            - containerPort: 80
YAML

kubectl -n chaine-appro rollout status deployment/web --timeout=300s

# La base de vulnerabilites est telechargee MAINTENANT, pendant le setup. Sans
# cela, le premier scan du candidat passerait plusieurs minutes a la tirer, et
# le lab ressemblerait a une panne.
trivy image --quiet --download-db-only 2>&1 | tail -3 || true

echo "Situation posee : web tourne sur nginx:1.21, et Trivy est pret."
