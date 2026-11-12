#!/usr/bin/env bash
# Pose la situation du challenge k8s-challenge-choisir-le-bon-workload sur le
# cluster kind « multi » (un control plane, deux workers) :
#
#   - le namespace entrepot, vide ;
#   - aucune CRD Collecte : l'apprenant l'installe depuis
#     ~/entrepot/collecte-crd.yaml, après y avoir ajouté la borne que le cahier
#     des charges exige ;
#   - ~/entrepot/, avec ce seul fichier.
#
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"

kubectl delete namespace entrepot --ignore-not-found --wait=true --timeout=180s
kubectl delete crd collectes.atelier.formation.k8s --ignore-not-found --wait=true --timeout=120s
kubectl create namespace entrepot

# Le taint du control plane est la situation de départ : kind le pose dès qu'un
# worker existe.
kubectl get node multi-control-plane -o jsonpath='{.spec.taints[*].key}' | grep -q node-role.kubernetes.io/control-plane

rm -rf "${LAB_HOME:?}/entrepot"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/entrepot"
install -o "$LAB_USER" -g "$LAB_USER" -m 0644 /var/lib/dsoxlab/collecte-crd.yaml "${LAB_HOME}/entrepot/collecte-crd.yaml"
echo "Situation posée : entrepot vide, CRD Collecte à installer depuis ~/entrepot/."
