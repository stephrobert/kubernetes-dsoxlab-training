#!/usr/bin/env bash
# Pose la situation : une application qui marche, puis un DNS de cluster
# qu'on éteint.
#
# Rejouable : `dsoxlab reset` relance ce script sur un cluster où le namespace
# existe peut-être déjà, et où CoreDNS est peut-être encore éteint par un
# passage précédent. Chaque étape doit donc partir de l'état qu'elle trouve.
set -euo pipefail

# `dsoxlab clean` supprime le namespace sans attendre : un `reset` enchaîne
# donc sur un namespace encore en Terminating, dans lequel l'API server refuse
# toute création. On attend qu'il ait vraiment disparu avant de le recréer.
if [[ "$(kubectl get namespace app -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/app --timeout=180s
fi
kubectl get namespace app >/dev/null 2>&1 || kubectl create namespace app

# Un Pod nu plutôt qu'un Deployment : le scénario dit « rien de compliqué »,
# et un Deployment inviterait à chercher la panne du côté de l'application.
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
      image: nginx:1.27-alpine
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

kubectl wait --for=condition=ready pod/web -n app --timeout=180s
kubectl wait --for=condition=ready pod/client -n app --timeout=180s

# Le DNS doit marcher AVANT qu'on le casse, sinon le lab mesurerait une autre
# panne que la sienne. On remet donc CoreDNS à l'état que kubeadm pose, et on
# constate une résolution qui réussit.
kubectl -n kube-system scale deployment coredns --replicas=2
kubectl -n kube-system rollout status deployment/coredns --timeout=180s
for essai in $(seq 1 15); do
  if kubectl exec client -n app -- nslookup web-svc.app.svc.cluster.local >/dev/null 2>&1; then
    break
  fi
  if (( essai == 15 )); then
    echo "La résolution DNS ne marche pas avant la panne : le socle est en défaut." >&2
    exit 1
  fi
  sleep 3
done

# La panne : CoreDNS à zéro replica. Le Service kube-dns reste, sans endpoint.
kubectl -n kube-system scale deployment coredns --replicas=0
kubectl -n kube-system wait --for=delete pod -l k8s-app=kube-dns --timeout=90s || true

echo "Situation posée : CoreDNS est à zéro replica, le client ne résout plus rien."
