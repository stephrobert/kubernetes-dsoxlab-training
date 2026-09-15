#!/usr/bin/env bash
# Pose la situation : une application qui marche, un Service refait de
# travers, selector et port faux, et une politique qui ferme tout le trafic
# entrant du namespace. Le client ne joint plus rien.
#
# Rejouable : les manifestes sont réappliqués à l'identique, ce qui remet le
# Service de travers, et la politique d'ouverture d'un passage précédent est
# retirée.
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

kubectl -n lab delete networkpolicy allow-web-ingress --ignore-not-found

cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: lab
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
        - name: nginx
          image: nginx:1.27-alpine
          ports:
            - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: web-svc
  namespace: lab
spec:
  selector:
    app: webapp
  ports:
    - port: 80
      targetPort: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: block-all
  namespace: lab
spec:
  podSelector: {}
  policyTypes:
    - Ingress
---
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: lab
spec:
  containers:
    - name: client
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
EOF

kubectl -n lab rollout status deployment/web-app --timeout=180s
kubectl -n lab wait --for=condition=Ready pod/client --timeout=180s
echo "Situation posée : web-svc ne dessert rien, block-all ferme le namespace."
