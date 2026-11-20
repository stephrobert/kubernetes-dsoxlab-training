#!/usr/bin/env bash
# Pose la situation du challenge : le namespace plateforme, vide, et le dépôt
# ~/plateforme de huit manifestes, dont quatre, tirés au sort parmi six, sont
# écrits dans une API que Kubernetes a retirée. Rien n'est appliqué : c'est
# la montée de version qui approche, et ces fichiers ne passeraient plus.
#
# generer.py écrit les fichiers et garde dans la mémoire la liste attendue
# (fichier, API retirée, API courante) : le rapport ne se recopie pas d'une
# session à l'autre.
#
# Rejouable : le namespace, la PriorityClass et le dépôt sont recréés à neuf.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

NS=plateforme
LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
DEPOT="${LAB_HOME}/plateforme"
MEMOIRE=/var/lib/dsoxlab/challenge-migrer-les-api-retirees.json
GENERATEUR="${GENERATEUR:?le setup dépose generer.py et passe son chemin}"

if [[ "$(kubectl get namespace "$NS" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete "namespace/$NS" --timeout=180s
fi
kubectl delete namespace "$NS" --ignore-not-found --wait=true --timeout=180s
kubectl delete priorityclass plateforme-critique --ignore-not-found
kubectl create namespace "$NS"

rm -rf "$DEPOT"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "$DEPOT"
install -d -m 0755 /var/lib/dsoxlab
python3 "$GENERATEUR" "$DEPOT" "$MEMOIRE"
chmod 0600 "$MEMOIRE"
chown -R "$LAB_USER:$LAB_USER" "$DEPOT"

ls -l "$DEPOT"
echo "Situation posée : ~/plateforme, quatre manifestes en API retirée, rien d'appliqué."
