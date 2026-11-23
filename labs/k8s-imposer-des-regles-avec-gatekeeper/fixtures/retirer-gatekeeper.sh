#!/usr/bin/env bash
# Retire Gatekeeper et tout ce qu'il a cree, qu'il ait ete installe par le
# candidat ou non. Joue par prepare.sh (passage precedent) et par cleanup.yaml.
#
# L'ordre compte : les Constraints d'abord, puis les ConstraintTemplates, dont
# la suppression retire les CRD qu'ils ont declarees, puis le manifeste. Dans
# l'autre ordre, les CRD des contraintes resteraient orphelines, sans le
# controleur qui saurait les retirer.
set -euo pipefail
# Trace sur le noeud, en AJOUT : appele par prepare.sh, ce script ne doit pas
# effacer le journal de celui-ci.
exec > >(tee -a /var/log/dsoxlab-retirer-gatekeeper.log) 2>&1
set -x
export KUBECONFIG=/etc/kubernetes/admin.conf
MANIFESTE=/var/lib/dsoxlab/gatekeeper-v3.23.1.yaml

if kubectl get crd constrainttemplates.templates.gatekeeper.sh >/dev/null 2>&1; then
  kubectl get constraints -o name 2>/dev/null | xargs -r kubectl delete --ignore-not-found || true
  kubectl delete constrainttemplates --all --ignore-not-found --wait=true --timeout=120s || true
fi
kubectl delete -f "$MANIFESTE" --ignore-not-found --wait=true --timeout=180s || true

# Ce qui resterait d'une installation par un autre moyen (Helm, autre version).
kubectl get crd -o name | grep 'gatekeeper\.sh' | xargs -r kubectl delete --ignore-not-found || true
kubectl get validatingwebhookconfiguration,mutatingwebhookconfiguration -o name \
  | grep gatekeeper | xargs -r kubectl delete --ignore-not-found || true
kubectl delete namespace gatekeeper-system --ignore-not-found --wait=true --timeout=180s || true

if kubectl get crd -o name | grep -q 'gatekeeper\.sh'; then
  echo "Des CRD de Gatekeeper restent." >&2
  exit 1
fi
echo "Gatekeeper retire."
