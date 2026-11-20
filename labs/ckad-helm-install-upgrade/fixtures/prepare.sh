#!/usr/bin/env bash
# Pose la situation : un namespace vide, aucune release, et le chart de
# l'équipe dans ~/charts/web de l'apprenant, généré par helm create (version
# 0.1.0) et aligné sur l'image nginx 1.30.5 de la formation, épinglée par
# digest.
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
# L'image de la formation, épinglée par digest dans values.yaml (le template
# de helm create écrit repository:tag). Avant le 2026-11-20, l'appVersion
# posait nginx:1.27-alpine, une version périmée et sans digest.
sed -i 's/^appVersion: .*/appVersion: "1.30.5"/' "${MAISON}/charts/web/Chart.yaml"
sed -i 's/^  tag: ""/  tag: "1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"/' \
  "${MAISON}/charts/web/values.yaml"
grep -q '^  tag: "1.30.5@sha256:' "${MAISON}/charts/web/values.yaml"
grep -E '^(version|appVersion):' "${MAISON}/charts/web/Chart.yaml"
chown -R "${UTILISATEUR}:${UTILISATEUR}" "${MAISON}/charts"
helm version --short

echo "Situation posée : Helm 4, un chart dans ${MAISON}/charts/web, aucune release."
