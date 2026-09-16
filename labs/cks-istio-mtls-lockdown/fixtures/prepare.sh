#!/usr/bin/env bash
# Pose la situation : un maillage installe, trois Pods, et aucune exigence de
# chiffrement.
#
# Istio est installe par le setup, pas par le candidat : installer un maillage
# n'est pas la competence que l'examen mesure, et cela prendrait tout le temps
# du lab. Ce qui est demande, c'est de l'employer.
#
# Le profil `minimal` ne deploie qu'istiod. Mesure le 2026-09-16 : environ
# 194 Mo, la ou le profil par defaut ajoute des passerelles dont ce lab n'a
# aucun usage.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

# Ce que le candidat doit produire est retire s'il traine d'un passage
# precedent : sans cela, le lab rendrait 100 avant le travail.
kubectl -n maillage delete peerauthentication --all --ignore-not-found --wait=true 2>/dev/null || true

if ! kubectl -n istio-system get deployment istiod >/dev/null 2>&1; then
  istioctl install --set profile=minimal -y
fi
kubectl -n istio-system rollout status deployment/istiod --timeout=300s

for ns in maillage dehors; do
  if [[ "$(kubectl get namespace "$ns" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
    kubectl wait --for=delete "namespace/${ns}" --timeout=180s
  fi
  kubectl get namespace "$ns" >/dev/null 2>&1 || kubectl create namespace "$ns"
done

# Seul `maillage` recoit les sidecars. `dehors` n'en a pas, et c'est lui qui
# servira a prouver que l'exigence agit.
kubectl label namespace maillage istio-injection=enabled --overwrite
kubectl label namespace dehors istio-injection- --overwrite 2>/dev/null || true

kubectl -n maillage delete pod service client-maille --ignore-not-found --wait=true
kubectl -n dehors delete pod client-nu --ignore-not-found --wait=true

kubectl apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: service
  namespace: maillage
  labels:
    app: service
spec:
  containers:
    - name: web
      image: nginx:1.27-alpine
      ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: service
  namespace: maillage
spec:
  selector:
    app: service
  ports:
    - port: 80
      targetPort: 80
---
apiVersion: v1
kind: Pod
metadata:
  name: client-maille
  namespace: maillage
  labels:
    app: client
spec:
  containers:
    - name: outil
      image: busybox:1.37
      command: ["sh", "-c", "sleep 86400"]
---
apiVersion: v1
kind: Pod
metadata:
  name: client-nu
  namespace: dehors
spec:
  containers:
    - name: outil
      image: busybox:1.37
      command: ["sh", "-c", "sleep 86400"]
YAML

kubectl -n maillage wait --for=condition=ready pod/service --timeout=240s
kubectl -n maillage wait --for=condition=ready pod/client-maille --timeout=240s
kubectl -n dehors wait --for=condition=ready pod/client-nu --timeout=240s

kubectl -n maillage get pods
echo "Situation posee : le maillage tourne, et il accepte encore le trafic en clair."
