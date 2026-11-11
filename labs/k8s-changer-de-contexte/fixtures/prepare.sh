#!/usr/bin/env bash
# Pose la situation du lab :
#
#   - ~/.kube/config de l'apprenant, celui que le socle vient de régler sur le
#     cluster « boutique », seul contexte kind-boutique, laissé lisible par
#     tous ;
#   - ~/Downloads/kubeconfig-recette.yaml, le fichier « reçu » : le kubeconfig
#     du cluster « lab », dont les noms kind-lab deviennent kind-recette. Il est
#     posé lisible par tous, comme un fichier qu'on vient de télécharger ;
#   - aucun reste d'un passage précédent : ni ~/.kube/configs/recette.yaml, ni
#     sauvegarde.
#
# Ne touche à aucun objet des clusters. Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"

rm -f "${LAB_HOME}/.kube/configs/recette.yaml" "${LAB_HOME}/.kube/config.backup" \
  "${LAB_HOME}/.kube/config.merged"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/Downloads"
sed 's/kind-lab/kind-recette/g' /etc/kind/lab.kubeconfig > "${LAB_HOME}/Downloads/kubeconfig-recette.yaml"
chown "$LAB_USER:$LAB_USER" "${LAB_HOME}/Downloads/kubeconfig-recette.yaml"
chmod 0644 "${LAB_HOME}/Downloads/kubeconfig-recette.yaml"
# Le kubeconfig de départ est lisible par tous, comme après une fusion faite
# par redirection sans chmod : le protéger fait partie du travail.
chmod 0644 "${LAB_HOME}/.kube/config"
echo "Situation posée : kubeconfig reçu dans ~/Downloads, contexte actif kind-boutique."
