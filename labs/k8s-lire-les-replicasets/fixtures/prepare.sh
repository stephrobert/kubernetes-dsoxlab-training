#!/usr/bin/env bash
# Pose la situation du lab sur le cluster kind « boutique » :
#
#   - le namespace replicasets, neuf, avec les deux Deployments de la
#     démonstration de la leçon : api, mis à jour une fois de nginx 1.30.5 en
#     1.30.6, donc deux ReplicaSets ; compte-absent, dont le modèle de Pod
#     demande un ServiceAccount qui n'existe pas, donc un ReplicaSet en
#     FailedCreate et aucun Pod ;
#   - la mémoire de l'état initial, lisible par root seul : l'uid de
#     compte-absent, pour constater qu'il a été réparé et non recréé ;
#   - le relevé à compléter, ~/replicasets/releve.txt.
#
# Ne touche ni aux Nodes, ni à kube-system, ni aux namespaces des autres labs.
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
NS=replicasets
V1="nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
V2="nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703"
MEMOIRE=/var/lib/dsoxlab/lire-les-replicasets.json

# --ignore-not-found plutôt qu'un get préalable : un namespace encore en
# Terminating au moment du get disparaîtrait avant le delete (NotFound, set -e).
kubectl delete namespace "$NS" --ignore-not-found --wait=true --timeout=180s
kubectl create namespace "$NS"

kubectl -n "$NS" apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
        - name: nginx
          image: ${V1}
EOF
kubectl -n "$NS" rollout status deployment/api --timeout=180s
kubectl -n "$NS" set image deployment/api nginx="$V2"
kubectl -n "$NS" rollout status deployment/api --timeout=180s

kubectl -n "$NS" apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compte-absent
spec:
  replicas: 2
  selector:
    matchLabels:
      app: compte-absent
  template:
    metadata:
      labels:
        app: compte-absent
    spec:
      serviceAccountName: compte-absent
      containers:
        - name: nginx
          image: ${V1}
EOF

# Le FailedCreate ne s'écrit qu'une fois le ReplicaSet créé et sa première
# tentative refusée.
for _ in $(seq 1 30); do
  kubectl -n "$NS" get events --field-selector reason=FailedCreate -o name | grep -q . && break
  sleep 2
done

install -d -m 0700 /var/lib/dsoxlab
uid="$(kubectl -n "$NS" get deployment compte-absent -o jsonpath='{.metadata.uid}')"
printf '{"compte-absent": "%s"}\n' "$uid" > "$MEMOIRE"
chmod 0600 "$MEMOIRE"

install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/${NS}"
cat > "${LAB_HOME}/${NS}/releve.txt" <<'RELEVE'
# Ce que vous lisez dans le cluster, une valeur par clé.
# What you read in the cluster, one value per key.
# Les lignes qui commencent par # sont ignorées. Lines starting with # are ignored.

replicaset-actif:
replicaset-ancien:
cause-failedcreate:
RELEVE
chown "$LAB_USER:$LAB_USER" "${LAB_HOME}/${NS}/releve.txt"
echo "Situation posée : api en deux ReplicaSets, compte-absent ${uid} en FailedCreate."
