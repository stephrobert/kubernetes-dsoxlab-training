#!/usr/bin/env bash
# Pose la situation : un Service config-svc sans rien derrière, et aucun des
# deux Pods demandés.
#
# Rejouable : le namespace est attendu s'il se termine, les Pods d'un passage
# précédent sont retirés, le Service est réappliqué à l'identique.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace lab -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/lab --timeout=180s
fi
kubectl get namespace lab >/dev/null 2>&1 || kubectl create namespace lab

kubectl -n lab delete pod app config-server --ignore-not-found --wait=true

cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: config-svc
  namespace: lab
spec:
  selector:
    app: config
  ports:
    - port: 80
      targetPort: 80
EOF

echo "Situation posée : config-svc existe, sans endpoint."
