#!/usr/bin/env bash
# Pose la situation du challenge sur le cluster kind « architecture » :
#
#   - le namespace architecture, neuf ;
#   - le Pod témoin « temoin », que le scheduler place sur l'un des workers ;
#   - le Deployment « file-attente », dont le template désigne un ordonnanceur
#     qui n'existe pas (schedulerName: ordonnanceur-equipe) : le
#     replicaset-controller crée ses Pods, mais aucun scheduler ne les place,
#     et ils restent Pending sans événement Scheduled ;
#   - le relevé à compléter, ~/architecture/releve.txt, clés posées et valeurs vides.
#
# Le cluster est partagé par les labs du module Architecture : ce script ne
# touche qu'au namespace architecture, jamais aux Nodes ni à kube-system.
#
# Rejouable : le namespace est recréé et les fichiers réécrits à chaque passage.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
IMAGE="nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"

# 1. Un namespace neuf.
if kubectl get namespace architecture >/dev/null 2>&1; then
  kubectl delete namespace architecture --wait=true --timeout=180s
fi
kubectl create namespace architecture

# 2. Le Pod témoin.
kubectl -n architecture run temoin --image="$IMAGE" --restart=Never --labels=app=temoin
kubectl -n architecture wait --for=condition=Ready pod/temoin --timeout=180s

# 3. Le Deployment qui ne revient pas : son ordonnanceur n'existe pas.
kubectl apply -f - <<MANIFESTE
apiVersion: apps/v1
kind: Deployment
metadata:
  name: file-attente
  namespace: architecture
  labels:
    app: file-attente
spec:
  replicas: 2
  selector:
    matchLabels:
      app: file-attente
  template:
    metadata:
      labels:
        app: file-attente
    spec:
      schedulerName: ordonnanceur-equipe
      containers:
        - name: web
          image: ${IMAGE}
MANIFESTE
for _ in $(seq 1 24); do
  n="$(kubectl -n architecture get pods -l app=file-attente --no-headers 2>/dev/null | wc -l)"
  [[ "$n" -eq 2 ]] && break
  sleep 5
done

# 4. Le relevé à compléter.
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/architecture"
cat > "${LAB_HOME}/architecture/releve.txt" <<'RELEVE'
# Relevé du cluster « architecture ». Complétez la valeur après chaque deux-points.
# Survey of the "architecture" cluster. Fill in the value after each colon.
# Les lignes qui commencent par # sont ignorées. Lines starting with # are ignored.

noeud-control-plane:

pod-apiserver:
role-apiserver:
pod-etcd:
role-etcd:
pod-scheduler:
role-scheduler:
pod-controller-manager:
role-controller-manager:

# Une ligne par Node worker, à ajouter : runtime-<nom du Node>: <runtime>
# One line per worker Node, to add: runtime-<Node name>: <runtime>

noeud-du-pod-temoin:
evenement-scheduled:

cree-par:
n-agit-pas:
RELEVE
chown "$LAB_USER:$LAB_USER" "${LAB_HOME}/architecture/releve.txt"

echo "Situation posée : temoin sur $(kubectl -n architecture get pod temoin -o jsonpath='{.spec.nodeName}'), file-attente en attente."
