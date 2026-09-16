#!/usr/bin/env bash
# Pose la situation : un compte de service qui détient cluster-admin, et une
# application qui tourne avec.
#
# Le raccourci est reproduit tel qu'on le rencontre en production : quelqu'un a
# eu besoin que « ça marche », a lié le compte à cluster-admin, et l'affaire a
# été oubliée. Rien n'est en panne, l'application sert, et c'est ce qui rend ce
# genre de droit si difficile à reprendre.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne rend que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace equipe-dev -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/equipe-dev --timeout=180s
fi
kubectl get namespace equipe-dev >/dev/null 2>&1 || kubectl create namespace equipe-dev

# Ce que le candidat doit produire est retiré s'il traîne d'un passage
# précédent : sans cela, le lab rendrait 100 avant le travail.
kubectl -n equipe-dev delete role dev-role --ignore-not-found --wait=true
kubectl -n equipe-dev delete rolebinding dev-role-binding --ignore-not-found --wait=true

# Le compte, son application, et le secret auquel il ne devra plus toucher.
kubectl apply -f - <<'YAML'
apiVersion: v1
kind: ServiceAccount
metadata:
  name: dev-sa
  namespace: equipe-dev
---
apiVersion: v1
kind: Secret
metadata:
  name: jeton-de-paiement
  namespace: equipe-dev
type: Opaque
stringData:
  cle: "ce-que-dev-sa-ne-doit-plus-pouvoir-lire"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: portail-dev
  namespace: equipe-dev
  labels:
    app: portail-dev
spec:
  replicas: 1
  selector:
    matchLabels:
      app: portail-dev
  template:
    metadata:
      labels:
        app: portail-dev
    spec:
      serviceAccountName: dev-sa
      containers:
        - name: web
          image: nginx:1.27-alpine
YAML

# LE raccourci : cluster-admin sur tout le cluster, pour un compte qui n'a
# besoin que de son namespace.
kubectl delete clusterrolebinding dev-admin-binding --ignore-not-found --wait=true
kubectl create clusterrolebinding dev-admin-binding \
  --clusterrole=cluster-admin \
  --serviceaccount=equipe-dev:dev-sa

kubectl -n equipe-dev rollout status deployment/portail-dev --timeout=300s

echo "Situation posée : dev-sa est cluster-admin, et personne ne s'en plaint."
