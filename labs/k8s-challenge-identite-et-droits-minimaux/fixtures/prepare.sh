#!/usr/bin/env bash
# Pose la situation du challenge k8s-challenge-identite-et-droits-minimaux,
# fausse sur les cinq états par construction :
#
#   - production : le Pod commandes, qui écrit son journal, et un Secret que
#     personne d'autre ne doit lire ;
#   - observatoire : collecte (curl) et tableau (une page statique), tous deux
#     sous le compte par défaut, qui monte un jeton dans chaque Pod ;
#   - le droit hérité : le RoleBinding heritage donne le ClusterRole edit au
#     compte par défaut d'observatoire.
#
# Rejouable : les namespaces sont attendus s'ils se terminent, puis recréés.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

CURL="curlimages/curl:8.22.0@sha256:58adaa4e8dca9c988bae2aba4ab3434a0bb2da16bbe3f92dec39ec7785166777"
BUSYBOX="busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"

for ns in production observatoire; do
  if [[ "$(kubectl get namespace "$ns" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
    kubectl wait --for=delete "namespace/$ns" --timeout=180s
  fi
  kubectl get namespace "$ns" >/dev/null 2>&1 || kubectl create namespace "$ns"
done

# Ce qu'un passage précédent aurait posé dans observatoire.
kubectl -n observatoire delete deployment collecte tableau --ignore-not-found --wait=true
kubectl -n observatoire delete serviceaccount collecte tableau --ignore-not-found
kubectl -n production delete role,rolebinding --all
kubectl -n observatoire patch serviceaccount default --type json \
  -p '[{"op":"remove","path":"/automountServiceAccountToken"}]' 2>/dev/null || true

cat <<YAML | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: cles-api
  namespace: production
stringData:
  cle: ne-doit-pas-sortir-de-production
---
apiVersion: v1
kind: Pod
metadata:
  name: commandes
  namespace: production
  labels:
    app: commandes
spec:
  automountServiceAccountToken: false
  containers:
    - name: commandes
      image: ${BUSYBOX}
      command: ["sh", "-c", "while true; do echo \"commande traitee \$(date +%s)\"; sleep 5; done"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: heritage
  namespace: observatoire
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: edit
subjects:
  - kind: ServiceAccount
    name: default
    namespace: observatoire
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: collecte
  namespace: observatoire
spec:
  replicas: 1
  selector:
    matchLabels:
      app: collecte
  template:
    metadata:
      labels:
        app: collecte
    spec:
      containers:
        - name: collecte
          image: ${CURL}
          command: ["sh", "-c", "sleep infinity"]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tableau
  namespace: observatoire
spec:
  replicas: 1
  selector:
    matchLabels:
      app: tableau
  template:
    metadata:
      labels:
        app: tableau
    spec:
      containers:
        - name: tableau
          image: ${BUSYBOX}
          command: ["sh", "-c", "mkdir -p /www && echo tableau > /www/index.html && httpd -f -p 8080 -h /www"]
YAML

kubectl -n production wait --for=condition=Ready pod/commandes --timeout=180s
kubectl -n observatoire rollout status deployment/collecte --timeout=180s
kubectl -n observatoire rollout status deployment/tableau --timeout=180s
# La situation est posée quand le compte par défaut a bien le droit hérité.
test "$(kubectl auth can-i create deployments -n observatoire --as system:serviceaccount:observatoire:default)" = yes
echo "Challenge posé : collecte et tableau tournent sous le compte par défaut, qui a hérité d'edit."
