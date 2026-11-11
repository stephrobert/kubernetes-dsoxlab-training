#!/usr/bin/env bash
# Pose la situation de l'épreuve sur le cluster kind « boutique » : le
# namespace boutique, neuf et vide. L'apprenant choisit et crée lui-même ses
# ressources d'après le cahier des charges.
#
# Ne touche qu'au namespace boutique. Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

# --ignore-not-found plutôt qu'un get préalable : un namespace encore en
# Terminating au moment du get disparaîtrait avant le delete (NotFound, set -e).
kubectl delete namespace boutique --ignore-not-found --wait=true --timeout=180s
kubectl create namespace boutique

echo "Situation posée : namespace boutique vide, le cahier des charges est à livrer."
