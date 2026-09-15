#!/usr/bin/env bash
# Pose la situation : le worker schedulable, web en quatre replicas répartis
# sur les deux nœuds par une contrainte de répartition, avec un emptyDir
# pour que le drain exige --delete-emptydir-data ; un Pod sans contrôleur
# sur le worker, pour que le drain exige --force. L'heure de pose est notée
# en annotation du Deployment : les tests exigent des Pods nés après.
#
# Rejouable : le namespace est attendu s'il se termine, le nœud est remis
# schedulable au cas où un passage précédent l'aurait laissé cordonné, et
# les Pods sont recréés pour que l'annotation soit antérieure à leur date.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

kubectl uncordon k8s-w1.lab
kubectl wait --for=condition=Ready node/k8s-w1.lab --timeout=180s

if [[ "$(kubectl get namespace lab -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/lab --timeout=180s
fi
kubectl get namespace lab >/dev/null 2>&1 || kubectl create namespace lab

# Un passage précédent a pu laisser le budget et la trace : ils sont au candidat.
kubectl -n lab delete pdb web-pdb --ignore-not-found
kubectl -n lab delete configmap drain-evidence --ignore-not-found
kubectl -n lab delete deployment web --ignore-not-found --wait=true
kubectl -n lab delete pod outil-diag --ignore-not-found --wait=true

POSE_LE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: lab
  annotations:
    lab.dsoxlab/pose-le: "${POSE_LE}"
spec:
  replicas: 4
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: web
      containers:
        - name: web
          image: nginx:1.27-alpine
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 50m
              memory: 32Mi
          volumeMounts:
            - name: cache
              mountPath: /var/cache/nginx
      volumes:
        - name: cache
          emptyDir: {}
---
apiVersion: v1
kind: Pod
metadata:
  name: outil-diag
  namespace: lab
spec:
  nodeName: k8s-w1.lab
  containers:
    - name: shell
      image: busybox:1.37
      command: ["sleep", "infinity"]
EOF

kubectl -n lab rollout status deployment/web --timeout=180s
kubectl -n lab wait --for=condition=Ready pod/outil-diag --timeout=120s

# La situation exige des Pods de web sur le worker : sinon il n'y a rien à évacuer.
SUR_W1="$(kubectl -n lab get pods -l app=web -o json | python3 -c 'import json,sys; print(sum(1 for p in json.load(sys.stdin)["items"] if p["spec"].get("nodeName") == "k8s-w1.lab"))')"
if [[ "${SUR_W1}" -lt 1 ]]; then
  echo "Aucun Pod de web sur k8s-w1.lab : la contrainte de répartition n'a pas joué." >&2
  exit 1
fi
kubectl -n lab get pods -o wide
echo "web en 4/4 dont ${SUR_W1} sur k8s-w1.lab, outil-diag posé, heure notée : ${POSE_LE}."
