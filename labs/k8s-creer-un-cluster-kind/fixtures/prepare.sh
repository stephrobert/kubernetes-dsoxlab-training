#!/usr/bin/env bash
# Libère la VM kind pour que l'apprenant y crée son propre cluster :
#
#   - supprime les clusters kind du catalogue, ET SEULEMENT EUX, désignés par
#     leur nom : lab, boutique, architecture (les valeurs de kind_cluster_name
#     des setup.yaml du dépôt), plus atelier, celui de ce lab, pour un départ
#     rejouable. Un cluster créé par l'apprenant sous un autre nom survit ;
#   - retire leurs contextes du kubeconfig de l'apprenant, et leurs kubeconfig
#     d'administration de /etc/kind : chaque lab les recrée par son setup ;
#   - pose ~/atelier/, vide, où l'apprenant écrit son fichier de configuration.
#
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
KUBECONFIG_APPRENANT="${LAB_HOME}/.kube/config"
CLUSTERS_DU_CATALOGUE=(lab boutique architecture atelier)

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

rm -rf "${LAB_HOME:?}/atelier"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/atelier"
echo "VM libérée : $(kind get clusters 2>/dev/null | tr '\n' ' ')"
