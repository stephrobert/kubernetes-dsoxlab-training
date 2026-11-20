#!/usr/bin/env bash
# Pose la situation : un Service tarifs-svc (port 8080 vers le port 80 des
# Pods role=tarifs) sans rien derrière, et un Pod facturation déjà Running
# alors que tarifs ne répond pas. Son gardien ne fait qu'un nslookup : un
# Service se résout dès qu'il existe, le gardien n'a donc rien attendu.
#
# Le nom est absolu (point final) : le nslookup de busybox 1.38 sur un nom
# court interroge tous les domaines de recherche et rend 1 même quand le nom
# se résout (mesuré le 2026-11-20). Ce gardien-là attendrait sans fin.
#
# Rejouable : le namespace est attendu s'il se termine, les Pods d'un passage
# précédent sont retirés, le Service et facturation sont reposés à l'identique.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

NGINX="nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
BUSYBOX="busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"

if [[ "$(kubectl get namespace lab -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/lab --timeout=180s
fi
kubectl get namespace lab >/dev/null 2>&1 || kubectl create namespace lab

kubectl -n lab delete pod facturation tarifs app config-server --ignore-not-found --wait=true
kubectl -n lab delete service config-svc --ignore-not-found

cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: tarifs-svc
  namespace: lab
spec:
  selector:
    role: tarifs
  ports:
    - port: 8080
      targetPort: 80
---
apiVersion: v1
kind: Pod
metadata:
  name: facturation
  namespace: lab
spec:
  initContainers:
    - name: attendre-tarifs
      image: ${BUSYBOX}
      command: ["sh", "-c", "until nslookup tarifs-svc.lab.svc.cluster.local.; do echo tarifs-svc introuvable; sleep 2; done"]
  containers:
    - name: main
      image: ${NGINX}
EOF

kubectl -n lab wait pod/facturation --for=condition=Ready --timeout=180s
kubectl -n lab get pods,services
echo "Situation posée : facturation tourne, tarifs-svc n'a aucun endpoint."
