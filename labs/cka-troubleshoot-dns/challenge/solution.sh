#!/usr/bin/env bash
# Solution for troubleshoot-dns lab
set -euo pipefail

SOLUTION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Apply namespace, deployment, service, and client pod
kubectl apply -f "$SOLUTION_DIR/solution.yaml"

# Wait for deployment and client pod
kubectl rollout status deployment/web -n app --timeout=90s
kubectl wait --for=condition=ready pod/client -n app --timeout=90s

# CoreDNS is already running in a fresh cluster — no fix needed
echo "troubleshoot-dns solution applied."
# Give CoreDNS a moment to initialize
sleep 5
kubectl exec client -n app -- nslookup web-svc.app.svc.cluster.local
kubectl exec client -n app -- wget -q -O /dev/null http://web-svc.app.svc.cluster.local
echo "DNS resolution is working again."
