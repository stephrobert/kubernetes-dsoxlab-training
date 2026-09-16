#!/usr/bin/env bash
# Pose la situation : un Pod privilégié qui tourne, et que personne n'a
# signalé.
#
# Il cumule cinq défauts, et c'est délibéré : en production on n'en trouve
# jamais un seul. Le candidat doit les repérer AVANT de corriger, ce qui est le
# geste du CKS et la différence avec un lab qui dirait quoi écrire.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne rend que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace production -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/production --timeout=180s
fi
kubectl get namespace production >/dev/null 2>&1 || kubectl create namespace production

# Ce que le candidat doit produire est retiré s'il traîne.
kubectl -n production delete pod secure-app --ignore-not-found --wait=true

kubectl -n production delete pod insecure-app --ignore-not-found --wait=true
kubectl apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: insecure-app
  namespace: production
  labels:
    app: insecure-app
spec:
  # Defaut 1 : le Pod partage le namespace de processus du NOEUD. De
  # l'interieur, il voit et peut signaler tout ce qui tourne sur la machine,
  # kubelet et containerd compris.
  hostPID: true
  containers:
    - name: app
      # Defaut 2 : un tag flottant. Ce qui tourne aujourd'hui n'est pas ce qui
      # tournera au prochain redemarrage, et rien ne le dira.
      image: busybox:latest
      command: ["sh", "-c", "sleep 86400"]
      securityContext:
        # Defaut 3 : conteneur privilegie, donc toutes les capacites du noyau.
        privileged: true
        # Defaut 4 : execution en root.
        runAsUser: 0
        # Defaut 5 : l'escalade de privileges reste possible.
        allowPrivilegeEscalation: true
YAML

kubectl -n production wait --for=condition=ready pod/insecure-app --timeout=180s

echo "Situation posée : insecure-app tourne, privilégié, et personne ne s'en plaint."
