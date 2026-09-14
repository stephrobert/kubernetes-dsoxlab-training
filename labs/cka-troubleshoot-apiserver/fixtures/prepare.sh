#!/usr/bin/env bash
# Pose la situation : un flag mal orthographié dans le manifeste statique de
# l'API server. Le kubelet redéploie le Pod, l'API server refuse un flag
# inconnu et sort, et kubectl ne répond plus.
#
# Rejouable : si un passage précédent a laissé la faute, on repart d'un
# manifeste sain et d'une API qui répond, sinon on ne mesurerait rien.
set -euo pipefail

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

# La faute. Le kubelet la voit en quelques secondes et redéploie le Pod.
sed -i "s|${BON}|${FAUX}|" "$MANIFESTE"
for essai in $(seq 1 60); do
  if ! kubectl get --raw /healthz >/dev/null 2>&1; then
    break
  fi
  sleep 3
done
if kubectl get --raw /healthz >/dev/null 2>&1; then
  echo "L'API répond encore après le changement de manifeste : le kubelet n'a pas redéployé le Pod." >&2
  exit 1
fi

echo "Situation posée : l'API server ne répond plus."
