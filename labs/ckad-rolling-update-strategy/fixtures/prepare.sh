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
# Les ReplicaSets d'un Deployment partent avec lui, mais un ReplicaSet SANS
# propriétaire, posé à la main au passage précédent, survit à cette
# suppression : il porterait le label app=webapp dans un namespace censé
# repartir d'une seule révision, et les tests le liraient comme un historique.
# La situation se pose sur un namespace vide de ReplicaSets, pas presque vide.
kubectl -n lab delete replicasets --all --wait=true

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
