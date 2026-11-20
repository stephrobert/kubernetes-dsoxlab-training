#!/usr/bin/env bash
# Pose la situation : catalogue en nginx:1.30.5-alpine, révision 1, saine ;
# puis la mise à jour vers busybox:1.38.0, livrée par erreur, révision 2 : son
# conteneur démarre puis s'arrête en boucle, et la mise à jour reste bloquée. progressDeadlineSeconds est court pour que describe
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
kubectl -n lab delete deployment catalogue --ignore-not-found --wait=true

cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: catalogue
  namespace: lab
spec:
  replicas: 3
  progressDeadlineSeconds: 60
  selector:
    matchLabels:
      app: catalogue
  template:
    metadata:
      labels:
        app: catalogue
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.5-alpine@sha256:0985e772fb9f729e6fa0980da05fca5d9c468e870eed43071545afa9d2e27d94
          ports:
            - containerPort: 80
EOF
kubectl -n lab rollout status deployment/catalogue --timeout=180s

# La mise à jour fautive : révision 2, un Pod qui ne trouvera jamais son image.
# ❌ Mauvaise image livrée : busybox démarre, n'a rien à faire et s'arrête,
# en boucle. La leçon, elle, montre un tag inexistant.
kubectl -n lab set image deployment/catalogue nginx=busybox:1.38.0

for essai in $(seq 1 40); do
  if kubectl -n lab get pods -l app=catalogue -o jsonpath='{.items[*].status.containerStatuses[*].state.waiting.reason}' | grep -q -E 'CrashLoopBackOff'; then
    break
  fi
  sleep 3
done
kubectl -n lab get pods -l app=catalogue -o jsonpath='{.items[*].status.containerStatuses[*].state.waiting.reason}' | grep -q -E 'CrashLoopBackOff'
kubectl -n lab get deployment catalogue
kubectl -n lab get rs -l app=catalogue
echo "catalogue est bloqué en révision 2 sur un conteneur qui s'arrête en boucle."
