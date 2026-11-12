#!/usr/bin/env bash
# Pose la situation : trois tiers et un intrus, tous joignables par tous,
# sans aucune politique.
#
# Rejouable : le namespace est attendu s'il se termine, les politiques d'un
# passage précédent sont retirées, les Pods sont réappliqués.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace lab -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/lab --timeout=180s
fi
kubectl get namespace lab >/dev/null 2>&1 || kubectl create namespace lab

kubectl -n lab delete networkpolicy --all

cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: frontend
  namespace: lab
  labels:
    tier: frontend
spec:
  containers:
    - name: app
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "sleep 3600"]
---
apiVersion: v1
kind: Pod
metadata:
  name: backend
  namespace: lab
  labels:
    tier: backend
spec:
  containers:
    - name: app
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "mkdir -p /www && echo backend > /www/index.html && exec httpd -f -p 80 -h /www"]
      ports:
        - containerPort: 80
---
apiVersion: v1
kind: Pod
metadata:
  name: database
  namespace: lab
  labels:
    tier: database
spec:
  containers:
    - name: app
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "mkdir -p /www && echo database > /www/index.html && exec httpd -f -p 80 -h /www"]
      ports:
        - containerPort: 80
---
apiVersion: v1
kind: Pod
metadata:
  name: intrus
  namespace: lab
spec:
  containers:
    - name: app
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      # L'intrus sert aussi son nom : c'est la destination que la sortie du
      # backend doit refuser, faute de quoi aucun test ne verrait une sortie
      # restée grande ouverte.
      command: ["sh", "-c", "mkdir -p /www && echo intrus > /www/index.html && exec httpd -f -p 80 -h /www"]
      ports:
        - containerPort: 80
EOF
kubectl -n lab wait --for=condition=Ready pod/frontend pod/backend pod/database pod/intrus --timeout=180s

# Tout doit parler à tout AVANT les politiques, sinon on mesurerait autre chose.
IP_DB=$(kubectl -n lab get pod database -o jsonpath='{.status.podIP}')
kubectl -n lab exec intrus -- wget -qO- -T 5 "http://${IP_DB}/" >/dev/null

echo "Situation posée : quatre Pods, aucune politique, l'intrus atteint la base."
