#!/usr/bin/env bash
# Pose la situation du lab k8s-attacher-une-seconde-interface, sur le cluster
# net-* que le setup vient de ramener aux valeurs du socle (Cilium 1.20.5 en
# cni.exclusive=true, son réglage par défaut) :
#
# - le manifeste de Multus v4.3.2 en mode thick, rangé dans
#   /opt/multus/multus-daemonset-thick.yml, son image ÉPINGLÉE par digest. Le
#   manifeste du tag v4.3.2 pointe l'image mobile snapshot-thick (relevé le
#   2026-11-17) : l'appliquer tel quel installe ce que l'amont a publié en
#   dernier, pas la v4.3.2 ;
# - le namespace multus-demo, vide.
#
# Rien de ce que l'apprenant doit produire n'existe : ni Multus, ni
# NetworkAttachmentDefinition, ni Pod. Rejouable : ce qu'un passage précédent
# a laissé est retiré d'abord (les fichiers des nœuds le sont par le setup).
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

MULTUS=v4.3.2
IMAGE="ghcr.io/k8snetworkplumbingwg/multus-cni:v4.3.2-thick@sha256:109b885d8752fe7a7bc3b2371750bfad6789b8b8e2d0b0820b337386ba9b93c9"
MANIFESTE=/opt/multus/multus-daemonset-thick.yml

# Hors de /root : l'utilisateur du lab doit pouvoir le lire.
install -d -m 0755 /opt/multus
curl -sSL -o "$MANIFESTE.amont" \
  "https://raw.githubusercontent.com/k8snetworkplumbingwg/multus-cni/$MULTUS/deployments/multus-daemonset-thick.yml"
# Deux occurrences attendues (conteneur et conteneur d'init) : un autre compte
# veut dire que l'amont a changé son manifeste, et le lab doit le savoir.
test "$(grep -c 'image: ghcr.io/k8snetworkplumbingwg/multus-cni:snapshot-thick' "$MANIFESTE.amont")" -eq 2
sed "s#ghcr.io/k8snetworkplumbingwg/multus-cni:snapshot-thick#$IMAGE#" "$MANIFESTE.amont" > "$MANIFESTE"
rm -f "$MANIFESTE.amont"
chmod 0644 "$MANIFESTE"

# Ce que l'apprenant a produit disparaît : le namespace, puis Multus en entier
# (DaemonSet, CRD des NetworkAttachmentDefinition, rôles).
kubectl delete namespace multus-demo --ignore-not-found --wait=true --timeout=180s
kubectl delete -f "$MANIFESTE" --ignore-not-found --wait=true --timeout=180s

kubectl create namespace multus-demo
kubectl -n kube-system get configmap cilium-config -o jsonpath='{.data.cni-exclusive}'; echo
grep -n 'image:' "$MANIFESTE"
echo "Situation posée : Cilium exclusif, Multus épinglé prêt dans $MANIFESTE, namespace multus-demo vide."
