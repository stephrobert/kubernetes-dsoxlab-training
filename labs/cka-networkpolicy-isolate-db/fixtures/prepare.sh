#!/usr/bin/env bash
# Pose la situation : db (postgres 17), backend et frontend dans database,
# un Service db, et intrus dans autre avec le label app=backend. Aucune
# politique. Avant de rendre la main, le script mesure que les trois
# atteignent la base : sinon la situation n'est pas celle du scénario.
#
# Rejouable : les namespaces sont attendus s'ils se terminent, la politique
# d'un passage précédent est retirée, les Pods sont réappliqués.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

for ns in database autre; do
  if [[ "$(kubectl get namespace "$ns" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
    kubectl wait --for=delete "namespace/$ns" --timeout=180s
  fi
  kubectl get namespace "$ns" >/dev/null 2>&1 || kubectl create namespace "$ns"
done
kubectl -n database delete networkpolicy --all

cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: db
  namespace: database
  labels:
    app: db
spec:
  containers:
    - name: postgres
      image: postgres:17-alpine
      env:
        - name: POSTGRES_PASSWORD
          value: lab-seulement
      ports:
        - containerPort: 5432
---
apiVersion: v1
kind: Service
metadata:
  name: db
  namespace: database
spec:
  selector:
    app: db
  ports:
    - port: 5432
      targetPort: 5432
---
apiVersion: v1
kind: Pod
metadata:
  name: backend
  namespace: database
  labels:
    app: backend
spec:
  containers:
    - name: shell
      image: busybox:1.37
      command: ["sleep", "infinity"]
---
apiVersion: v1
kind: Pod
metadata:
  name: frontend
  namespace: database
  labels:
    app: frontend
spec:
  containers:
    - name: shell
      image: busybox:1.37
      command: ["sleep", "infinity"]
---
apiVersion: v1
kind: Pod
metadata:
  name: intrus
  namespace: autre
  labels:
    app: backend
spec:
  containers:
    - name: shell
      image: busybox:1.37
      command: ["sleep", "infinity"]
EOF

kubectl -n database wait --for=condition=Ready pod/db pod/backend pod/frontend --timeout=240s
kubectl -n autre wait --for=condition=Ready pod/intrus --timeout=120s

# La situation : tout le monde atteint la base. Postgres met quelques
# secondes à écouter après Ready.
for essai in $(seq 1 20); do
  if kubectl -n database exec backend -- nc -z -w 3 db 5432; then
    break
  fi
  sleep 3
done
kubectl -n database exec backend -- nc -z -w 3 db 5432
kubectl -n database exec frontend -- nc -z -w 3 db 5432
kubectl -n autre exec intrus -- nc -z -w 3 db.database.svc.cluster.local 5432
echo "db, backend, frontend et intrus tournent ; tout le monde atteint la base."
