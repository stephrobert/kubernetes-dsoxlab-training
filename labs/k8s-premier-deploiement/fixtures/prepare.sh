#!/usr/bin/env bash
# Pose la situation du lab sur le cluster kind « boutique » : aucun namespace
# demo-app, l'apprenant crée tout, et le répertoire ~/demo-app/ où il consigne
# la réponse HTTP.
#
# Ne touche qu'au namespace demo-app : les namespaces des autres labs de la
# boutique ne sont pas touchés. Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"

# --ignore-not-found plutôt qu'un get préalable : un namespace encore en
# Terminating au moment du get disparaîtrait avant le delete (NotFound, set -e).
kubectl delete namespace demo-app --ignore-not-found --wait=true --timeout=180s

rm -f "${LAB_HOME}/demo-app/reponse.html"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/demo-app"
echo "Situation posée : aucun namespace demo-app, ~/demo-app/ vide."
