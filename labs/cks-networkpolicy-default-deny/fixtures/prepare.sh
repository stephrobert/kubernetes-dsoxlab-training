#!/usr/bin/env bash
# Pose la situation : trois Pods qui se parlent librement, et rien qui les en
# empêche.
#
# Les Pods sont FOURNIS, et c'est le choix qui distingue ce lab des deux autres
# labs NetworkPolicy du catalogue. Le sujet du CKS n'est pas de créer des Pods,
# c'est de fermer un namespace sans casser ce qui doit continuer. Faire écrire
# les Pods au candidat lui coûterait dix minutes sans rien mesurer de plus.
#
# `intrus` n'a pas de label `app` : il représente ce qui ne devrait pas avoir
# accès, et il en a pourtant, tant qu'aucune politique n'existe.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne rend que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace zero-confiance -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/zero-confiance --timeout=180s
fi
kubectl get namespace zero-confiance >/dev/null 2>&1 || kubectl create namespace zero-confiance

# Ce que le candidat doit produire est retiré s'il traîne d'un passage
# précédent : sans cela, le lab rendrait 100 avant le travail.
kubectl -n zero-confiance delete networkpolicy --all --ignore-not-found --wait=true

kubectl -n zero-confiance delete pod db web intrus annuaire --ignore-not-found --wait=true
kubectl apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: db
  namespace: zero-confiance
  labels:
    app: db
    tier: backend
spec:
  containers:
    - name: base
      image: nginx:1.27-alpine
      ports:
        - containerPort: 80
---
apiVersion: v1
kind: Pod
metadata:
  name: web
  namespace: zero-confiance
  labels:
    app: web
    tier: frontend
spec:
  containers:
    - name: client
      image: busybox:1.37
      command: ["sh", "-c", "sleep 86400"]
---
# `annuaire` sert d'instrument de mesure pour la SORTIE. Sans une seconde
# cible qui écoute vraiment, on ne peut pas distinguer « la sortie est
# fermée » de « personne n'écoutait de toute façon » : une requête vers un
# busybox échoue dans les deux cas, et un test qui ne sait pas faire la
# différence est vrai avant le travail.
apiVersion: v1
kind: Pod
metadata:
  name: annuaire
  namespace: zero-confiance
  labels:
    app: annuaire
    tier: backend
spec:
  containers:
    - name: service
      image: nginx:1.27-alpine
      ports:
        - containerPort: 80
---
apiVersion: v1
kind: Pod
metadata:
  name: intrus
  namespace: zero-confiance
  labels:
    tier: inconnu
spec:
  containers:
    - name: client
      image: busybox:1.37
      command: ["sh", "-c", "sleep 86400"]
YAML

for pod in db web intrus annuaire; do
  kubectl -n zero-confiance wait --for=condition=ready "pod/${pod}" --timeout=180s
done

echo "Situation posée : quatre Pods, aucune politique, et tout le monde se parle."
