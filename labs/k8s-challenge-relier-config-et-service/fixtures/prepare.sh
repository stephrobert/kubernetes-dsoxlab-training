#!/usr/bin/env bash
# Pose la situation du challenge sur le cluster kind « boutique » : aucun objet
# de la vitrine, ni dans magasin ni dans default. L'apprenant crée tout.
#
# Ne touche qu'au namespace magasin et aux quatre noms de la vitrine dans
# default : les namespaces des autres labs de la boutique ne sont pas touchés.
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

# --ignore-not-found plutôt qu'un get préalable : un namespace encore en
# Terminating au moment du get disparaîtrait avant le delete (NotFound, set -e).
kubectl delete namespace magasin --ignore-not-found --wait=true --timeout=180s
kubectl -n default delete deployment/vitrine service/vitrine \
  configmap/vitrine-config secret/vitrine-secret --ignore-not-found

echo "Situation posée : aucun objet de la vitrine, le challenge part de zéro."
