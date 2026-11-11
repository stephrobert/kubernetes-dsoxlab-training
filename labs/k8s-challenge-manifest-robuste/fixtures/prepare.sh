#!/usr/bin/env bash
# Pose la situation du challenge k8s-challenge-manifest-robuste sur le cluster
# kind « lab » :
#
#   - le namespace expedition, vide de toute application ;
#   - etiquettes, un Pod EN PANNE : il lit la clé FORMAT d'une ConfigMap
#     etiquettes-config qui n'existe pas, et son conteneur reste en
#     CreateContainerConfigError. Son uid est mémorisé dans
#     /var/lib/dsoxlab/challenge-manifest-robuste.json : il doit être réparé
#     sans être recréé ;
#   - ~/expedition/, vide, où l'apprenant écrit sa base, ses overlays et la
#     cause de la panne.
#
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
BUSYBOX="busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"
MEMOIRE=/var/lib/dsoxlab/challenge-manifest-robuste.json

kubectl delete namespace expedition --ignore-not-found --wait=true --timeout=180s
kubectl create namespace expedition
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: etiquettes
  namespace: expedition
spec:
  containers:
    - name: etiquettes
      image: ${BUSYBOX}
      command: ["sh", "-c", "echo format \$FORMAT; sleep 86400"]
      env:
        - name: FORMAT
          valueFrom:
            configMapKeyRef:
              name: etiquettes-config
              key: FORMAT
EOF
kubectl -n expedition wait pod/etiquettes \
  --for=jsonpath='{.status.containerStatuses[0].state.waiting.reason}'=CreateContainerConfigError --timeout=120s

install -d -m 0755 /var/lib/dsoxlab
printf '{"etiquettes_uid": "%s"}\n' "$(kubectl -n expedition get pod etiquettes -o jsonpath='{.metadata.uid}')" > "$MEMOIRE"

rm -rf "${LAB_HOME:?}/expedition"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/expedition"
echo "Situation posée : expedition vide, etiquettes en CreateContainerConfigError."
