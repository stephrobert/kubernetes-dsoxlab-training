#!/usr/bin/env bash
# Pose la situation du lab : ~/.kube/config de l'apprenant contient DÉJÀ deux
# contextes, kind-boutique (actif) et recette, qui vise le cluster « lab ». La
# fusion, que la leçon garde pour un approfondissement, est faite ici à la place
# de l'apprenant : le lab porte sur le geste de base, basculer et fixer le
# namespace par défaut.
#
# Rejouable : le kubeconfig est reconstruit à partir des deux kubeconfigs
# d'administration, et la ConfigMap preuve d'un passage précédent est retirée
# des deux clusters.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
CONF="${LAB_HOME}/.kube/config"

for cluster in lab boutique; do
  K="kubectl --kubeconfig /etc/kind/${cluster}.kubeconfig"
  for ns in $($K get configmap -A --field-selector metadata.name=preuve \
      -o jsonpath='{range .items[*]}{.metadata.namespace}{" "}{end}'); do
    $K -n "$ns" delete configmap preuve --ignore-not-found
  done
done

TMP="$(mktemp -d)"
sed 's/kind-lab/recette/g' /etc/kind/lab.kubeconfig > "${TMP}/recette.yaml"
KUBECONFIG="/etc/kind/boutique.kubeconfig:${TMP}/recette.yaml" kubectl config view --flatten > "${TMP}/config"
KUBECONFIG="${TMP}/config" kubectl config use-context kind-boutique
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0700 "${LAB_HOME}/.kube"
install -o "$LAB_USER" -g "$LAB_USER" -m 0600 "${TMP}/config" "$CONF"
rm -f "${TMP}/recette.yaml" "${TMP}/config"
rmdir "$TMP"

# La situation : deux contextes, kind-boutique actif, aucun namespace réglé.
KUBECONFIG="$CONF" kubectl config get-contexts
test "$(KUBECONFIG="$CONF" kubectl config current-context)" = kind-boutique
echo "Situation posée : deux contextes dans ~/.kube/config, kind-boutique actif."
