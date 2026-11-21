#!/usr/bin/env bash
# Pose la situation : dans le namespace comptes, une clé d'API montée depuis un
# Secret dans deux Pods. L'un, rapport, la lit toutes les 10 secondes avec un
# outil TIRÉ AU SORT ; l'autre, vitrine, ne la lit pas. Tetragon est déjà
# installé par setup.yaml.
#
# L'outil est gardé dans une mémoire lisible par root seulement : c'est
# l'événement de Tetragon qui doit le dire, il ne se devine pas.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

BB='busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4'
MEMOIRE=/var/lib/dsoxlab/k8s-observer-et-bloquer-avec-tetragon.json

# Repartir d'un état propre : aucune politique d'un passage précédent.
kubectl delete tracingpolicies.cilium.io --all --ignore-not-found
kubectl delete tracingpoliciesnamespaced.cilium.io --all -A --ignore-not-found
if kubectl get namespace comptes >/dev/null 2>&1; then
  kubectl delete namespace comptes --wait=true --timeout=180s
fi

OUTIL=$(python3 -c 'import random; print(random.choice(["head", "tail", "od", "wc", "md5sum"]))')
mkdir -p /var/lib/dsoxlab
printf '{"binaire": "/bin/%s", "pod": "rapport"}\n' "$OUTIL" > "$MEMOIRE"
chmod 0600 "$MEMOIRE"

kubectl create namespace comptes
kubectl -n comptes create secret generic cle-api \
  --from-literal=cle="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
kubectl apply -f - <<YAML
apiVersion: v1
kind: Pod
metadata:
  name: rapport
  namespace: comptes
spec:
  containers:
    - name: rapport
      image: $BB
      command: ["sh", "-c", "while true; do $OUTIL /etc/comptes/cle > /dev/null 2>&1; sleep 10; done"]
      volumeMounts: [{name: cle, mountPath: /etc/comptes, readOnly: true}]
  volumes: [{name: cle, secret: {secretName: cle-api}}]
---
apiVersion: v1
kind: Pod
metadata:
  name: vitrine
  namespace: comptes
spec:
  containers:
    - name: vitrine
      image: $BB
      command: ["sleep", "infinity"]
      volumeMounts: [{name: cle, mountPath: /etc/comptes, readOnly: true}]
  volumes: [{name: cle, secret: {secretName: cle-api}}]
YAML
kubectl -n comptes wait --for=condition=Ready pod/rapport pod/vitrine --timeout=180s

echo "Situation posee : rapport lit la cle toutes les 10 s, avec un outil tire au sort."
