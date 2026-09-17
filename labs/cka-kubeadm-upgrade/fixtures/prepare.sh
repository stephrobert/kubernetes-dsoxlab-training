#!/usr/bin/env bash
# Pose l'application qui devra survivre a la montee de version.
#
# Le gros du travail de ce setup est AILLEURS, dans setup.yaml : c'est lui qui
# reconstruit le cluster une version mineure en arriere, parce qu'une montee de
# version ne se joue pas autrement. Ici on ne pose que le temoin.
#
# Deux exemplaires, et une contrainte d'anti-affinite : sans elle, les deux
# Pods pourraient atterrir sur le meme noeud, et vider ce noeud les
# emporterait tous les deux. Le lab n'aurait alors plus rien a prouver sur la
# disponibilite.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace supervision -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/supervision --timeout=180s
fi
kubectl get namespace supervision >/dev/null 2>&1 || kubectl create namespace supervision

kubectl -n supervision delete deployment sonde --ignore-not-found --wait=true
kubectl apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sonde
  namespace: supervision
spec:
  replicas: 2
  selector:
    matchLabels:
      app: sonde
  template:
    metadata:
      labels:
        app: sonde
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                topologyKey: kubernetes.io/hostname
                labelSelector:
                  matchLabels:
                    app: sonde
      containers:
        - name: web
          image: nginxinc/nginx-unprivileged:1.27-alpine
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 20m
              memory: 32Mi
YAML

kubectl -n supervision rollout status deployment/sonde --timeout=300s

# On montre l'etat de depart dans le journal.
kubectl get nodes -o wide
echo "Situation posee : le cluster est en retard d'une version mineure."
