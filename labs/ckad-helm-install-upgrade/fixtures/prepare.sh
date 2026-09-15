#!/usr/bin/env bash
# Pose la situation : un namespace vide, aucune release, et le chart de
# l'équipe dans ~/charts/web de l'apprenant, généré par helm create et
# aligné sur une image nginx à jour.
#
# Rejouable : le namespace est attendu s'il se termine, la release d'un
# passage précédent est désinstallée, le chart est régénéré.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

UTILISATEUR="${UTILISATEUR:-ubuntu}"
MAISON="/home/${UTILISATEUR}"

if [[ "$(kubectl get namespace lab -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/lab --timeout=180s
fi
kubectl get namespace lab >/dev/null 2>&1 || kubectl create namespace lab

helm uninstall web -n lab --ignore-not-found --wait

rm -rf "${MAISON}/charts/web"
mkdir -p "${MAISON}/charts"
(cd "${MAISON}/charts" && helm create web >/dev/null)
sed -i 's/^appVersion: .*/appVersion: "1.27-alpine"/' "${MAISON}/charts/web/Chart.yaml"
chown -R "${UTILISATEUR}:${UTILISATEUR}" "${MAISON}/charts"
helm version --short

echo "Situation posée : Helm 4, un chart dans ${MAISON}/charts/web, aucune release."
