#!/usr/bin/env bash
# Pose la situation : un Deployment qui référence son image par un TAG.
#
# Le tag est le défaut à corriger, et il tourne : l'application marche, rien
# n'est en panne. C'est exactement ce qui rend le sujet difficile à faire
# entendre en production, et c'est pourquoi le lab part d'un état sain plutôt
# que d'une panne.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne rend que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace chaine -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/chaine --timeout=180s
fi
kubectl get namespace chaine >/dev/null 2>&1 || kubectl create namespace chaine

# Le Deployment est REPOSÉ à chaque passage, tag compris : sans cela, un
# second `run` après un travail réussi repartirait d'un digest déjà épinglé,
# et le lab rendrait 100 avant que l'apprenant n'ait rien fait.
kubectl -n chaine delete deployment pinned-app --ignore-not-found --wait=true

kubectl apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pinned-app
  namespace: chaine
  labels:
    app: pinned-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: pinned-app
  template:
    metadata:
      labels:
        app: pinned-app
    spec:
      containers:
        - name: web
          image: nginx:1.27-alpine
          ports:
            - containerPort: 80
YAML

kubectl -n chaine rollout status deployment/pinned-app --timeout=300s

echo "Situation posée : pinned-app tourne, et fait confiance à un tag."
