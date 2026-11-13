#!/usr/bin/env bash
# Pose le namespace equipe-web, avec un Pod à lire et un Secret à ne pas lire,
# et le répertoire ~/acces, vide. Aucune demande, aucun droit pour camille.
# Rejouable : la demande camille et le namespace sont recréés.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x
LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
kubectl delete csr camille --ignore-not-found
kubectl delete namespace equipe-web --ignore-not-found --wait=true --timeout=180s
kubectl create namespace equipe-web
kubectl -n equipe-web run vitrine --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 \
  --restart=Never -- sleep infinity
kubectl -n equipe-web create secret generic cles --from-literal=api=ne-doit-pas-sortir
kubectl -n equipe-web wait --for=condition=Ready pod/vitrine --timeout=120s
rm -rf "${LAB_HOME}/acces"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0700 "${LAB_HOME}/acces"
echo "Lab posé : equipe-web attend sa lectrice, ~/acces est vide."
