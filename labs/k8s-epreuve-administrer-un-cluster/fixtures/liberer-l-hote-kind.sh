#!/usr/bin/env bash
# Joué sur k8s-kind.lab par le setup, en root : libère la VM kind pour que
# l'apprenant y crée son cluster à trois plans de contrôle.
#
#   - un nœud du cluster ha laissé gelé par un check interrompu est dégelé,
#     sans quoi `kind delete` bute dessus ;
#   - les clusters kind du catalogue, ET SEULEMENT EUX, désignés par leur nom,
#     sont supprimés : lab, boutique, architecture, multi, atelier (les valeurs
#     de kind_cluster_name des setup.yaml du dépôt), plus ha, celui de ce lab,
#     pour un départ rejouable. Trois plans de contrôle kind demandent environ
#     2 Go sur les 4 de la VM, qui n'a aucun swap : un cluster voisin laissé en
#     place ferait un OOM franc. Chaque lab recrée le sien par son setup, comme
#     après k8s-creer-un-cluster-kind ;
#   - leurs contextes sont retirés du kubeconfig de l'apprenant, et leurs
#     kubeconfig d'administration de /etc/kind ;
#   - ~/ha/ est posé, vide, pour le fichier de configuration de l'apprenant.
#
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
KUBECONFIG_APPRENANT="${LAB_HOME}/.kube/config"
CLUSTERS_DU_CATALOGUE=(lab boutique architecture multi atelier ha)

for conteneur in $(docker ps --filter status=paused --filter name=ha- --format '{{.Names}}'); do
  docker unpause "$conteneur"
done

existants="$(kind get clusters 2>/dev/null || true)"
for nom in "${CLUSTERS_DU_CATALOGUE[@]}"; do
  if grep -qx "$nom" <<< "$existants"; then
    if [ -f "$KUBECONFIG_APPRENANT" ]; then
      kind delete cluster --name "$nom" --kubeconfig "$KUBECONFIG_APPRENANT"
    else
      kind delete cluster --name "$nom"
    fi
  fi
  rm -f "/etc/kind/${nom}.kubeconfig"
done
[ -f "$KUBECONFIG_APPRENANT" ] && chown "$LAB_USER:$LAB_USER" "$KUBECONFIG_APPRENANT"
rm -f /root/ha-correcteur.kubeconfig

rm -rf "${LAB_HOME:?}/ha"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/ha"
free -m
echo "VM kind libérée : $(kind get clusters 2>/dev/null | tr '\n' ' ')"
