#!/usr/bin/env bash
# Pose la situation : un API server de cluster kubeadm, tel qu'il sort de
# l'installation, profileur compris.
#
# Deux precautions gouvernent ce script, et chacune evite un degat reel :
#
#   1. La sauvegarde du manifeste vit dans /var/backups, JAMAIS dans
#      /etc/kubernetes/manifests. Le kubelet surveille ce repertoire et
#      lancerait la copie comme un second Pod statique : deux API servers sur
#      le meme port, et le cluster ne repond plus.
#   2. Le manifeste est RESTAURE au debut de chaque passage, faute de quoi un
#      second run apres un travail reussi partirait d'un API server deja
#      durci, et le lab rendrait 100 avant que le candidat n'ait rien fait.
set -euo pipefail
# La trace complete va dans un journal sur le noeud : dsoxlab ne rend que
# « non-zero return code » quand ce script echoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

MANIFESTE=/etc/kubernetes/manifests/kube-apiserver.yaml
SAUVEGARDE=/var/backups/kube-apiserver.avant-durcissement.yaml

attendre_l_api() {
  for _ in $(seq 1 60); do
    kubectl get --raw /healthz >/dev/null 2>&1 && break
    sleep 3
  done
  kubectl get --raw /healthz >/dev/null 2>&1 || {
    echo "L API server ne repond plus apres modification du manifeste." >&2
    return 1
  }
  # /healthz repond avant que le Pod statique ne soit revenu Running : le
  # kubelet a recree le conteneur, mais l etat de l objet Pod met une seconde
  # a remonter.
  for _ in $(seq 1 40); do
    phases=$(kubectl -n kube-system get pods -l component=kube-apiserver \
      -o jsonpath='{.items[*].status.phase}' 2>/dev/null || true)
    [[ -n "$phases" && "$phases" != *Pending* ]] && return 0
    sleep 3
  done
  echo "Le Pod statique kube-apiserver ne revient pas en Running." >&2
  return 1
}

mkdir -p /var/backups

if [[ -f "$SAUVEGARDE" ]]; then
  cp -f "$SAUVEGARDE" "$MANIFESTE"
  attendre_l_api
else
  cp -f "$MANIFESTE" "$SAUVEGARDE"
fi

attendre_l_api

# Le profileur doit etre ACCESSIBLE au depart, sinon le lab ne mesure rien.
kubectl get --raw /debug/pprof/ >/dev/null 2>&1 || {
  echo "Le profileur est deja ferme : le socle a change, le lab ne s applique plus." >&2
  exit 1
}

echo "Situation posee : l API server expose son profileur, et rien n est durci."
