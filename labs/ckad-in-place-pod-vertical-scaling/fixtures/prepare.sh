#!/usr/bin/env bash
# Pose la situation : un Pod au budget trop juste, avec une politique de
# redimensionnement sans redémarrage, et sa date de création gardée dans une
# annotation : un Pod recréé aurait une autre date.
#
# Rejouable : le namespace est attendu s'il se termine, et le Pod est
# supprimé puis recréé avec son budget initial.
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

kubectl -n lab delete pod scaling-pod --ignore-not-found --wait=true

cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: scaling-pod
  namespace: lab
spec:
  containers:
    - name: app
      image: nginx:1.27-alpine
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 200m
          memory: 128Mi
      resizePolicy:
        - resourceName: cpu
          restartPolicy: NotRequired
        - resourceName: memory
          restartPolicy: NotRequired
EOF
kubectl -n lab wait --for=condition=Ready pod/scaling-pod --timeout=180s
creation=$(kubectl -n lab get pod scaling-pod -o jsonpath='{.metadata.creationTimestamp}')
kubectl -n lab annotate pod scaling-pod "lab.dsoxlab/cree-le=${creation}" --overwrite

echo "Situation posée : scaling-pod tourne avec 100m et 128Mi, créé le ${creation}."
