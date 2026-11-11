#!/usr/bin/env bash
# Pose la situation du lab sur le cluster kind « boutique » : le namespace
# configuration, neuf et vide. L'apprenant crée les ConfigMaps et le
# Deployment.
#
# Ne touche ni aux Nodes, ni à kube-system, ni aux namespaces des autres labs.
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

# --ignore-not-found plutôt qu'un get préalable : un namespace encore en
# Terminating au moment du get disparaîtrait avant le delete (NotFound, set -e).
kubectl delete namespace configuration --ignore-not-found --wait=true --timeout=180s
kubectl create namespace configuration
echo "Situation posée : namespace configuration vide."
