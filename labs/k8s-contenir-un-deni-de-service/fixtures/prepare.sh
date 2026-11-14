#!/usr/bin/env bash
# Pose la situation du lab k8s-contenir-un-deni-de-service, fausse sur les cinq
# états par construction :
#
#   - bac-a-sable, le namespace de test : ni ResourceQuota ni LimitRange, et le
#     Deployment gourmand, deux réplicas sans requests ni limits ;
#   - annuaire : une application de deux réplicas derrière un Service, qui doit
#     continuer de répondre.
#
# LA CHARGE EST SÛRE POUR LE NŒUD PARTAGÉ, et c'est voulu. Chaque Pod de
# gourmand écrit un bloc FIXE de 96 Mio dans un emptyDir en mémoire, borné à
# 128 Mio, puis occupe un processeur par rafales de 20 secondes suivies de
# 10 secondes de pause. Deux Pods : moins de 200 Mio de mémoire en tout, et des
# Pods BestEffort, que le noyau sert en dernier quand le processeur manque. Le
# nœud n'approche jamais la pression mémoire, encore moins le NotReady.
#
# Rejouable : les deux namespaces sont supprimés puis recréés, ce qui retire
# aussi le quota et le LimitRange d'un passage précédent.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

for ns in bac-a-sable annuaire; do
  kubectl delete namespace "$ns" --ignore-not-found --wait=true --timeout=180s
  if [[ "$(kubectl get namespace "$ns" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
    kubectl wait --for=delete "namespace/$ns" --timeout=180s
  fi
done
kubectl create namespace bac-a-sable
kubectl create namespace annuaire

cat <<'YAML' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gourmand
  namespace: bac-a-sable
  labels:
    app: gourmand
spec:
  replicas: 2
  selector:
    matchLabels:
      app: gourmand
  template:
    metadata:
      labels:
        app: gourmand
    spec:
      automountServiceAccountToken: false
      containers:
        - name: charge
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command:
            - sh
            - -c
            - |
              dd if=/dev/zero of=/charge/bloc bs=1M count=96
              while true; do
                timeout 20 sh -c 'while :; do :; done'
                sleep 10
              done
          volumeMounts:
            - name: charge
              mountPath: /charge
      volumes:
        - name: charge
          emptyDir:
            medium: Memory
            sizeLimit: 128Mi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: annuaire
  namespace: annuaire
  labels:
    app: annuaire
spec:
  replicas: 2
  selector:
    matchLabels:
      app: annuaire
  template:
    metadata:
      labels:
        app: annuaire
    spec:
      automountServiceAccountToken: false
      containers:
        - name: web
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 50m
              memory: 32Mi
            limits:
              cpu: 200m
              memory: 128Mi
---
apiVersion: v1
kind: Service
metadata:
  name: annuaire
  namespace: annuaire
spec:
  selector:
    app: annuaire
  ports:
    - port: 80
      targetPort: 80
YAML

kubectl -n bac-a-sable rollout status deployment/gourmand --timeout=180s
kubectl -n annuaire rollout status deployment/annuaire --timeout=180s

# La situation est posée quand gourmand tourne sans aucune limite.
test -z "$(kubectl -n bac-a-sable get pods -l app=gourmand -o jsonpath='{.items[*].spec.containers[*].resources.limits}')"
echo "Situation posée : gourmand tourne sans limites dans bac-a-sable, annuaire répond."
