#!/usr/bin/env bash
# Pose la situation : un namespace SANS plafond ni valeurs par defaut.
#
# Il n'y a presque rien a poser, et c'est voulu : ce lab ne repare pas un objet
# casse, il fait constater ce qu'un namespace nu autorise. Une application y
# tourne pour que le candidat voie que son travail ne doit pas la faire tomber.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

# Ce que le candidat doit produire est retire s'il traine d'un passage
# precedent : sans cela, le lab rendrait 100 avant le travail.
kubectl -n equipe-produit delete resourcequota --all --ignore-not-found 2>/dev/null || true
kubectl -n equipe-produit delete limitrange --all --ignore-not-found 2>/dev/null || true

if [[ "$(kubectl get namespace equipe-produit -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/equipe-produit --timeout=180s
fi
kubectl get namespace equipe-produit >/dev/null 2>&1 || kubectl create namespace equipe-produit

kubectl -n equipe-produit delete deployment catalogue --ignore-not-found --wait=true
kubectl apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: catalogue
  namespace: equipe-produit
spec:
  replicas: 1
  selector:
    matchLabels:
      app: catalogue
  template:
    metadata:
      labels:
        app: catalogue
    spec:
      containers:
        - name: web
          image: nginxinc/nginx-unprivileged:1.27-alpine
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 50m
              memory: 32Mi
            limits:
              cpu: 200m
              memory: 128Mi
YAML

kubectl -n equipe-produit rollout status deployment/catalogue --timeout=240s

# On montre l'etat de depart dans le journal : tout passe, y compris
# l'extravagant.
kubectl -n equipe-produit run sonde-depart --image=busybox:1.37 --restart=Never \
  --overrides='{"spec":{"containers":[{"name":"x","image":"busybox:1.37","command":["sh","-c","sleep 5"],"resources":{"requests":{"cpu":"64","memory":"8Gi"},"limits":{"cpu":"64","memory":"8Gi"}}}]}}' \
  >/dev/null 2>&1 && echo "un Pod demandant 64 CPU est ACCEPTE" || echo "refuse"
kubectl -n equipe-produit delete pod sonde-depart --ignore-not-found --wait=false >/dev/null 2>&1 || true
echo "Situation posee : le namespace n'a ni plafond ni valeurs par defaut."
