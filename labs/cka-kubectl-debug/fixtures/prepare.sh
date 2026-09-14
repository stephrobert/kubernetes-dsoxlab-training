#!/usr/bin/env bash
# Pose la situation : un Pod dont l'image n'a aucun shell, dans un namespace
# propre, sans trace d'un passage précédent. Rejouable par `dsoxlab reset`.
set -euo pipefail

# `dsoxlab clean` supprime le namespace sans attendre : on attend qu'il ait
# vraiment disparu avant de le recréer.
if [[ "$(kubectl get namespace lab -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/lab --timeout=180s
fi
kubectl get namespace lab >/dev/null 2>&1 || kubectl create namespace lab

# Un conteneur éphémère ne se retire jamais d'un Pod : pour repartir d'un Pod
# vierge, on le supprime et on le recrée.
kubectl -n lab delete pod distroless-app --ignore-not-found --wait=true

# L'image CoreDNS est vraiment distroless : ni sh ni ls, un seul binaire
# statique. Mesuré le 2026-09-14 : « exec: "sh": executable file not found ».
# Le lab hérité employait agnhost, qui a un shell, et sa consigne « no shell
# available » était fausse. Celle-ci est déjà sur le nœud, le socle l'a tirée
# pour le DNS du cluster.
IMAGE=$(kubectl -n kube-system get deployment coredns -o jsonpath='{.spec.template.spec.containers[0].image}')
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: distroless-app
  namespace: lab
  labels:
    app: distroless-app
spec:
  containers:
    - name: distroless-app
      image: ${IMAGE}
      ports:
        - containerPort: 53
          protocol: UDP
EOF
kubectl -n lab wait --for=condition=Ready pod/distroless-app --timeout=180s

# Les traces d'un passage précédent : Pods de débogage du nœud, quel que soit
# le namespace où l'apprenant les a créés, et fichier témoin sur le nœud.
kubectl get pods -A -o jsonpath='{range .items[?(@.spec.hostPID==true)]}{.metadata.namespace} {.metadata.name}{"\n"}{end}' \
  | { grep -v '^kube-system ' || true; } \
  | while read -r ns nom; do
      if [[ -n "${nom:-}" ]]; then
        kubectl -n "$ns" delete pod "$nom" --ignore-not-found --wait=false
      fi
    done
rm -f /tmp/node-debug.txt

echo "Situation posée : distroless-app tourne dans lab, sans shell."
