#!/usr/bin/env bash
# Pose la situation du lab sur le cluster kind « boutique » :
#
#   - le namespace replicasets, neuf, avec deux Deployments qui ne sont pas
#     ceux de la leçon (api et compte-absent, dont la leçon imprime les noms
#     de ReplicaSets) : paiement, mis à jour une fois de nginx 1.30.5-alpine en
#     1.30.6-alpine, donc deux ReplicaSets ; rapports, dont le modèle de Pod
#     demande le ServiceAccount lecteur, absent du namespace, donc un
#     ReplicaSet en FailedCreate et aucun Pod ;
#   - un ServiceAccount lecteur dans le namespace default, en leurre : il
#     existe bien, mais pas là où les Pods le cherchent ;
#   - la mémoire de l'état initial, lisible par root seul : l'uid de
#     rapports, pour constater qu'il a été réparé et non recréé ;
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
V1="nginx:1.30.5-alpine@sha256:0985e772fb9f729e6fa0980da05fca5d9c468e870eed43071545afa9d2e27d94"
V2="nginx:1.30.6-alpine@sha256:901e593c95dc85f5a729f5765516321366ef4ac401821431d408897e95287d0a"
MEMOIRE=/var/lib/dsoxlab/lire-les-replicasets.json

# --ignore-not-found plutôt qu'un get préalable : un namespace encore en
# Terminating au moment du get disparaîtrait avant le delete (NotFound, set -e).
kubectl delete namespace "$NS" --ignore-not-found --wait=true --timeout=180s
kubectl create namespace "$NS"
# Le leurre : un lecteur existe, mais dans default.
kubectl -n default create serviceaccount lecteur --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "$NS" apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: paiement
spec:
  replicas: 3
  selector:
    matchLabels:
      app: paiement
  template:
    metadata:
      labels:
        app: paiement
    spec:
      containers:
        - name: nginx
          image: ${V1}
EOF
kubectl -n "$NS" rollout status deployment/paiement --timeout=180s
kubectl -n "$NS" set image deployment/paiement nginx="$V2"
kubectl -n "$NS" rollout status deployment/paiement --timeout=180s

kubectl -n "$NS" apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rapports
spec:
  replicas: 2
  selector:
    matchLabels:
      app: rapports
  template:
    metadata:
      labels:
        app: rapports
    spec:
      serviceAccountName: lecteur
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
uid="$(kubectl -n "$NS" get deployment rapports -o jsonpath='{.metadata.uid}')"
printf '{"rapports": "%s"}\n' "$uid" > "$MEMOIRE"
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
echo "Situation posée : paiement en deux ReplicaSets, rapports ${uid} en FailedCreate."
