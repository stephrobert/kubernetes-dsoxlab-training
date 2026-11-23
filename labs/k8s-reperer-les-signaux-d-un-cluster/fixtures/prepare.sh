#!/usr/bin/env bash
# Pose la situation du lab k8s-reperer-les-signaux-d-un-cluster.
#
# Le socle de supervision (Prometheus v3.16.0, kube-state-metrics v2.20.0) est
# posé par setup.yaml. Ce script pose le namespace signaux et trois charges :
#
#   - memoire-courte : un conteneur qui remplit sa mémoire jusqu'à sa limite
#     (32 Mi), tué en OOMKilled puis relancé, en boucle ;
#   - calcul-serre : une boucle CPU sous une limite de 20m, bridée en
#     permanence par le CFS (throttling). Mesuré le 2026-11-23 : sous 50m, le
#     ratio de la leçon (temps bridé / temps CPU) ne valait que 0,23, trop
#     près de son seuil de 0,2 pour faire un signal net ;
#   - temoin-calme : un conteneur qui dort, qui ne doit déclencher aucune
#     alerte.
#
# Il vide aussi les règles d'alerte de Prometheus : ce que le candidat doit
# écrire ne doit pas traîner d'un passage précédent.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

kubectl -n supervision create configmap prometheus-regles --dry-run=client -o yaml \
  | kubectl apply -f -
kubectl -n supervision rollout restart deployment/prometheus
kubectl -n supervision rollout status deployment/prometheus --timeout=300s

if [[ "$(kubectl get namespace signaux -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/signaux --timeout=180s
fi
kubectl delete namespace signaux --ignore-not-found --wait=true --timeout=180s
kubectl create namespace signaux
kubectl apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: memoire-courte
  namespace: signaux
spec:
  replicas: 1
  selector:
    matchLabels:
      app: memoire-courte
  template:
    metadata:
      labels:
        app: memoire-courte
    spec:
      containers:
        - name: appli
          image: busybox:1.37
          command: ["sh", "-c", "sleep 20; tail /dev/zero"]
          resources:
            requests:
              memory: 16Mi
            limits:
              memory: 32Mi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: calcul-serre
  namespace: signaux
spec:
  replicas: 1
  selector:
    matchLabels:
      app: calcul-serre
  template:
    metadata:
      labels:
        app: calcul-serre
    spec:
      containers:
        - name: appli
          image: busybox:1.37
          command: ["sh", "-c", "while :; do :; done"]
          resources:
            requests:
              cpu: 20m
            limits:
              cpu: 20m
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: temoin-calme
  namespace: signaux
spec:
  replicas: 1
  selector:
    matchLabels:
      app: temoin-calme
  template:
    metadata:
      labels:
        app: temoin-calme
    spec:
      containers:
        - name: appli
          image: busybox:1.37
          command: ["sh", "-c", "sleep 86400"]
          resources:
            limits:
              cpu: 50m
              memory: 32Mi
YAML
kubectl -n signaux rollout status deployment/calcul-serre --timeout=180s
kubectl -n signaux rollout status deployment/temoin-calme --timeout=180s
echo "Situation posee : memoire-courte, calcul-serre et temoin-calme tournent dans signaux."
