#!/usr/bin/env bash
# Pose la situation : webapp en 1.26-alpine, révision 1, saine ; puis la
# mise à jour vers nginx:1.27-alpin, une image qui n'existe pas, révision 2,
# qui reste bloquée. progressDeadlineSeconds est court pour que describe
# dise ProgressDeadlineExceeded sans attendre dix minutes.
#
# Rejouable : le namespace est attendu s'il se termine, le Deployment est
# supprimé et recréé pour que l'historique reparte de la révision 1.
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
  replicas: 3
  progressDeadlineSeconds: 60
  selector:
    matchLabels:
      app: webapp
  template:
    metadata:
      labels:
        app: webapp
    spec:
      containers:
        - name: nginx
          image: nginx:1.26-alpine
          ports:
            - containerPort: 80
EOF
kubectl -n lab rollout status deployment/webapp --timeout=180s

# La mise à jour fautive : révision 2, un Pod qui ne trouvera jamais son image.
kubectl -n lab set image deployment/webapp nginx=nginx:1.27-alpin

for essai in $(seq 1 40); do
  if kubectl -n lab get pods -l app=webapp -o jsonpath='{.items[*].status.containerStatuses[*].state.waiting.reason}' | grep -q -E 'ImagePullBackOff|ErrImagePull'; then
    break
  fi
  sleep 3
done
kubectl -n lab get pods -l app=webapp -o jsonpath='{.items[*].status.containerStatuses[*].state.waiting.reason}' | grep -q -E 'ImagePullBackOff|ErrImagePull'
kubectl -n lab get deployment webapp
kubectl -n lab get rs -l app=webapp
echo "webapp est bloqué en révision 2 sur une image qui n'existe pas."
