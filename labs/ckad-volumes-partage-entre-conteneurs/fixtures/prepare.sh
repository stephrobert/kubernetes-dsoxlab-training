#!/usr/bin/env bash
# Pose la situation : un Pod a deux conteneurs qui ne partagent RIEN.
#
# Le producteur ecrit en boucle dans /var/trace/messages, le lecteur cherche ce
# fichier au même chemin et ne le trouve pas : chaque conteneur a son propre
# système de fichiers, même dans un Pod commun. C'est le point que le lab fait
# constater avant de le faire corriger.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace journalisation -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/journalisation --timeout=180s
fi
kubectl get namespace journalisation >/dev/null 2>&1 || kubectl create namespace journalisation

# Le Pod est REPOSE a l'identique a chaque passage : sans cela, un candidat
# qui a deja corrige verrait le lab rendre 100 des le depart.
kubectl -n journalisation delete pod collecteur --ignore-not-found --wait=true

kubectl apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: collecteur
  namespace: journalisation
spec:
  containers:
    - name: producteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command:
        - sh
        - -c
        - "mkdir -p /var/trace; while true; do echo \"trace $(date +%s)\" >> /var/trace/messages; sleep 5; done"
    - name: lecteur
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "sleep 86400"]
YAML

kubectl -n journalisation wait --for=condition=ready pod/collecteur --timeout=240s

# On montre l'etat de depart dans le journal.
kubectl -n journalisation exec collecteur -c producteur -- sh -c 'ls -l /var/trace/messages' || true
kubectl -n journalisation exec collecteur -c lecteur -- sh -c 'ls /var/trace/messages' 2>&1 | head -1 || true
echo "Situation posée : le producteur écrit, le lecteur ne voit rien."
