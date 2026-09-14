#!/usr/bin/env bash
# Setup script for troubleshoot-dns lab.
# Creates app namespace with pods, then breaks CoreDNS.

set -euo pipefail

kubectl create namespace app

# Web server pod + service
cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: web
  namespace: app
  labels:
    app: web
spec:
  containers:
    - name: nginx
      image: nginx:1.27
      ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: web-svc
  namespace: app
spec:
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 80
---
apiVersion: v1
kind: Pod
metadata:
  name: client
  namespace: app
spec:
  containers:
    - name: client
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
EOF

kubectl wait --for=condition=ready pod/web -n app --timeout=90s
kubectl wait --for=condition=ready pod/client -n app --timeout=60s

# Verify DNS works before breaking it
echo "Verifying DNS works before breaking..."
kubectl exec client -n app -- nslookup web-svc.app.svc.cluster.local || true

# Break DNS by scaling CoreDNS to 0
kubectl scale deployment coredns -n kube-system --replicas=0
kubectl wait --for=delete pod -l k8s-app=kube-dns -n kube-system --timeout=60s 2>/dev/null || true

echo "Setup complete: CoreDNS has been scaled to 0 replicas."
