#!/usr/bin/env bash
# Pose la situation : un namespace avec un Pod qui écrit des logs, et aucun
# droit pour dev-user.
#
# Rejouable : le namespace est attendu s'il se termine, et le Role comme le
# RoleBinding d'un passage précédent sont retirés.
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

kubectl -n lab delete rolebinding read-pods-binding --ignore-not-found
kubectl -n lab delete role pod-reader --ignore-not-found

cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: journal
  namespace: lab
spec:
  containers:
    - name: journal
      image: busybox:1.36
      command: ["sh", "-c", "while true; do echo \"$(date) journal en marche\"; sleep 10; done"]
EOF
kubectl -n lab wait --for=condition=Ready pod/journal --timeout=180s

echo "Situation posée : dev-user n'a aucun droit sur lab."
