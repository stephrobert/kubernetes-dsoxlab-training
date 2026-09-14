#!/usr/bin/env bash
# Pose la situation : un flag mal orthographié dans le manifeste statique de
# l'API server. Le kubelet redéploie le Pod, l'API server refuse un flag
# inconnu et sort, et kubectl ne répond plus.
#
# Rejouable : si un passage précédent a laissé la faute, on repart d'un
# manifeste sain et d'une API qui répond, sinon on ne mesurerait rien.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

MANIFESTE=/etc/kubernetes/manifests/kube-apiserver.yaml
BON='--authorization-mode='
FAUX='--authorization-modes='

sed -i "s|${FAUX}|${BON}|" "$MANIFESTE"
for essai in $(seq 1 60); do
  if kubectl get --raw /healthz >/dev/null 2>&1; then
    break
  fi
  sleep 3
done
kubectl get --raw /healthz >/dev/null

grep -q -- "${BON}Node,RBAC" "$MANIFESTE" || {
  echo "Le manifeste ne porte pas ${BON}Node,RBAC : le socle a changé, le lab ne s'applique plus." >&2
  exit 1
}

# La faute. Le kubelet la voit en quelques secondes et redéploie le Pod. On
# exige trois silences consécutifs de l'API avant de conclure : un seul peut
# n'être que le redémarrage du conteneur, et le premier passage à deux nœuds
# a échoué sur une lecture unique, sans qu'on sache laquelle.
sed -i "s|${BON}|${FAUX}|" "$MANIFESTE"
silences=0
for essai in $(seq 1 60); do
  if kubectl get --raw /healthz >/dev/null 2>&1; then
    silences=0
  else
    silences=$((silences + 1))
  fi
  if (( silences >= 3 )); then
    break
  fi
  sleep 3
done
if (( silences < 3 )); then
  echo "L'API répond encore après le changement de manifeste : le kubelet n'a pas redéployé le Pod." >&2
  exit 1
fi

echo "Situation posée : l'API server ne répond plus."
