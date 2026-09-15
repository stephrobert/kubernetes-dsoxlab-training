#!/usr/bin/env bash
# Pose l'application réservée au worker : trois replicas, nodeSelector sur
# k8s-w1.lab. Quand le nœud tombe, elle n'a nulle part où aller, et c'est ce
# qui rend la panne visible côté application.
#
# Rejouable : le namespace est attendu s'il se termine, le Deployment est
# réappliqué à l'identique.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace production -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/production --timeout=180s
fi
kubectl get namespace production >/dev/null 2>&1 || kubectl create namespace production

cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      nodeSelector:
        kubernetes.io/hostname: k8s-w1.lab
      containers:
        - name: web
          image: nginx:1.27-alpine
          ports:
            - containerPort: 80
EOF

# L'application doit être saine AVANT la panne, sinon on mesurerait autre chose.
kubectl -n production rollout status deployment/web-app --timeout=180s
echo "Application posée : web-app en 3/3 sur k8s-w1.lab."
