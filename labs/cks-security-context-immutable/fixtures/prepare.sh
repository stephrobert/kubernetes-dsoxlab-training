#!/usr/bin/env bash
# Pose la situation : un Deployment qui sert, et dont l'interieur est encore
# inscriptible.
#
# L'image tourne deja sous l'UID 101, et c'est deliberé : la racine est donc
# refusee a l'ecriture par les DROITS POSIX avant meme le travail. Mesure le
# 2026-09-16 : `touch /preuve` rend « Permission denied » sur le Pod nu.
# Un test qui viserait la racine serait donc vert avant le travail.
#
# Le chemin qui distingue vraiment les deux etats est /etc/nginx/conf.d :
# l'image le rend inscriptible a son UID pour que ses scripts d'entree y
# ecrivent, et seul readOnlyRootFilesystem le ferme. Mesure le meme jour :
# INSCRIPTIBLE sur le Pod nu, « Read-only file system » sur le Pod durci.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace catalogue -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/catalogue --timeout=180s
fi
kubectl get namespace catalogue >/dev/null 2>&1 || kubectl create namespace catalogue

# Le Deployment est REPOSE a l'identique a chaque passage : sans cela, un
# candidat qui a deja corrige verrait le lab rendre 100 des le depart.
kubectl -n catalogue delete deployment vitrine --ignore-not-found --wait=true

kubectl apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vitrine
  namespace: catalogue
spec:
  replicas: 2
  selector:
    matchLabels:
      app: vitrine
  template:
    metadata:
      labels:
        app: vitrine
    spec:
      containers:
        - name: web
          image: nginxinc/nginx-unprivileged:1.27-alpine
          ports:
            - containerPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: vitrine
  namespace: catalogue
spec:
  selector:
    app: vitrine
  ports:
    - port: 80
      targetPort: 8080
---
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: catalogue
spec:
  containers:
    - name: outil
      image: busybox:1.37
      command: ["sh", "-c", "sleep 86400"]
YAML

kubectl -n catalogue rollout status deployment/vitrine --timeout=240s
kubectl -n catalogue wait --for=condition=ready pod/client --timeout=240s

# On montre l'etat de depart dans le journal.
POD=$(kubectl -n catalogue get pod -l app=vitrine -o jsonpath='{.items[0].metadata.name}')
kubectl -n catalogue exec "$POD" -- sh -c 'touch /etc/nginx/conf.d/preuve && echo "INSCRIPTIBLE avant le travail"' || true
echo "Situation posee : le site sert, et son interieur s'ecrit encore."
