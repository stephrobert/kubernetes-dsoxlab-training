#!/usr/bin/env bash
# Pose le namespace migration, vide, et le dépôt ~/manifestes avec les six
# manifestes hérités, tels quels. Rien n'est appliqué : c'est le travail.
# Rejouable : le namespace et le dépôt sont recréés.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x
LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
kubectl delete namespace migration --ignore-not-found --wait=true --timeout=180s
kubectl create namespace migration
rm -rf "${LAB_HOME}/manifestes"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/manifestes"
cp "${SOURCE}"/*.yaml "${LAB_HOME}/manifestes/"
chown -R "$LAB_USER:$LAB_USER" "${LAB_HOME}/manifestes"
ls -l "${LAB_HOME}/manifestes"
echo "Lab posé : six manifestes hérités dans ~/manifestes, le namespace migration est vide."
