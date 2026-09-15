#!/usr/bin/env bash
# Pose la situation : webapp en cinq replicas de nginx 1.26, stratégie par
# défaut, une seule révision.
#
# Rejouable : le namespace est attendu s'il se termine, et le Deployment est
# supprimé puis recréé, pour repartir d'une seule révision.
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

kubectl -n lab delete deployment webapp --ignore-not-found --wait=true

cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webapp
  namespace: lab
spec:
  replicas: 5
  selector:
    matchLabels:
      app: webapp
  template:
    metadata:
      labels:
        app: webapp
    spec:
      containers:
        - name: web
          image: nginx:1.26-alpine
          ports:
            - containerPort: 80
EOF
kubectl -n lab rollout status deployment/webapp --timeout=180s

echo "Situation posée : webapp en 5 replicas de nginx:1.26-alpine, stratégie par défaut."
