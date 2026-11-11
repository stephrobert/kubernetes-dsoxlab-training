#!/usr/bin/env bash
# Pose la situation de l'épreuve k8s-epreuve-deployer-une-application sur le
# cluster kind « multi » (un control plane, deux workers) :
#
#   - le namespace magasin, vide ;
#   - la CRD Sauvegarde de la leçon « Operators et CRDs pour développeurs »,
#     installée : l'apprenant crée la ressource demandée, sans toucher au
#     schéma ;
#   - ~/boutique/, vide, où l'apprenant range sa base et son overlay Kustomize.
#
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"

kubectl delete namespace magasin --ignore-not-found --wait=true --timeout=240s
kubectl apply -f /var/lib/dsoxlab/sauvegarde-crd.yaml
kubectl wait --for=condition=Established crd/sauvegardes.atelier.formation.k8s --timeout=60s
kubectl create namespace magasin

# Le taint du control plane fait partie de la situation : l'agent doit le
# tolérer.
kubectl get node multi-control-plane -o jsonpath='{.spec.taints[*].key}' | grep -q node-role.kubernetes.io/control-plane

rm -rf "${LAB_HOME:?}/boutique"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/boutique"
echo "Situation posée : magasin vide, CRD Sauvegarde installée, ~/boutique/ vide."
