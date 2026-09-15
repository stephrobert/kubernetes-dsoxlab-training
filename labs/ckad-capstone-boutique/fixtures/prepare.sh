#!/usr/bin/env bash
# Pose la situation : un namespace vide, et deux Pods clients qui serviront à
# prouver l'isolation à la fin.
#
# Un capstone pose le MINIMUM. Tout ce que le cahier des charges demande est le
# travail du candidat : c'est la différence entre un examen blanc et un
# exercice guidé.
#
# Les deux clients, eux, sont fournis : ils ne sont pas le sujet, ils sont
# l'instrument de mesure. Le candidat n'a aucune raison de les créer, et les
# lui faire écrire reviendrait à lui faire fabriquer la règle avec laquelle on
# le mesure.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace boutique -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/boutique --timeout=180s
fi
kubectl get namespace boutique >/dev/null 2>&1 || kubectl create namespace boutique

# Ce que le candidat doit produire est retiré s'il traîne d'un passage
# précédent : un capstone qui partirait d'un travail déjà fait ne mesurerait
# rien, et le validateur le verrait en rendant 100 avant le travail.
kubectl -n boutique delete deployment catalogue --ignore-not-found --wait=true
kubectl -n boutique delete service catalogue-svc --ignore-not-found --wait=true
kubectl -n boutique delete configmap catalogue-config --ignore-not-found --wait=true
kubectl -n boutique delete secret catalogue-db --ignore-not-found --wait=true
kubectl -n boutique delete networkpolicy --all --ignore-not-found --wait=true

# Les deux instruments de mesure. Le premier porte le label que la politique
# devra laisser entrer, le second ne le porte pas.
kubectl -n boutique delete pod frontend intrus --ignore-not-found --wait=true
kubectl -n boutique apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: frontend
  namespace: boutique
  labels:
    role: frontend
spec:
  containers:
    - name: client
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
---
apiVersion: v1
kind: Pod
metadata:
  name: intrus
  namespace: boutique
  labels:
    role: autre
spec:
  containers:
    - name: client
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
YAML

kubectl -n boutique wait --for=condition=ready pod/frontend --timeout=180s
kubectl -n boutique wait --for=condition=ready pod/intrus --timeout=180s

echo "Situation posée : le namespace boutique est vide, frontend et intrus attendent."
