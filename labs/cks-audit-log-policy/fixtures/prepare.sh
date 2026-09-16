#!/usr/bin/env bash
# Pose la situation : un API server qui n'audite rien, et qui doit repartir
# propre à chaque passage.
#
# Ce lab modifie le manifeste statique du kube-apiserver. Deux précautions
# gouvernent ce script, et chacune évite un dégât réel :
#
#   1. La sauvegarde du manifeste vit dans /var/backups, JAMAIS dans
#      /etc/kubernetes/manifests. Le kubelet surveille ce répertoire et
#      lancerait la copie comme un second Pod statique : deux API servers sur
#      le même port, et le cluster ne répond plus.
#   2. Le manifeste est RESTAURÉ au début de chaque passage. Sans cela, un
#      second `run` après un travail réussi partirait d'un audit déjà en
#      place, et le lab rendrait 100 avant que le candidat n'ait rien fait.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne rend que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

MANIFESTE=/etc/kubernetes/manifests/kube-apiserver.yaml
SAUVEGARDE=/var/backups/kube-apiserver.avant-audit.yaml

attendre_l_api() {
  # Deux attentes, et la seconde n'est pas superflue. `/healthz` répond avant
  # que le Pod statique ne soit revenu Running : le kubelet a recréé le
  # conteneur, mais l'objet Pod passe par Pending le temps que son état
  # remonte. Un lab qui démarrerait dans cette fenêtre partirait d'un cluster
  # que le validateur juge dégradé.
  for _ in $(seq 1 60); do
    kubectl get --raw /healthz >/dev/null 2>&1 && break
    sleep 3
  done
  kubectl get --raw /healthz >/dev/null 2>&1 || {
    echo "L'API server ne répond plus après modification du manifeste." >&2
    return 1
  }
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
  # Un passage précédent a modifié le manifeste : on repart de l'original.
  cp -f "$SAUVEGARDE" "$MANIFESTE"
  attendre_l_api
else
  # Premier passage : on garde l'original tel que le socle l'a écrit.
  cp -f "$MANIFESTE" "$SAUVEGARDE"
fi

# Le journal et la politique d'un passage précédent n'ont rien à faire là :
# le test final cherche une trace ÉCRITE PENDANT la session, et un vieux
# journal la lui donnerait sans que l'audit soit activé.
rm -f /var/log/kubernetes/audit.log
rm -f /etc/kubernetes/audit-policy.yaml

# Le namespace dans lequel le candidat fera lire un Secret.
if [[ "$(kubectl get namespace coffre -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/coffre --timeout=180s
fi
kubectl get namespace coffre >/dev/null 2>&1 || kubectl create namespace coffre

kubectl -n coffre delete secret dossier-medical --ignore-not-found --wait=true
kubectl -n coffre create secret generic dossier-medical \
  --from-literal=numero="ce-que-l-audit-doit-tracer"

attendre_l_api

grep -q -- "--audit-policy-file" "$MANIFESTE" && {
  echo "Le manifeste porte déjà un audit : la restauration n'a pas marché." >&2
  exit 1
}

echo "Situation posée : l'API server n'audite rien, et le coffre est rempli."
