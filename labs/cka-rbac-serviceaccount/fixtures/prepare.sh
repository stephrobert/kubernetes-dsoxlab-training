#!/usr/bin/env bash
# Pose la situation : le Deployment inventaire, dont le Pod doit tourner
# sous un ServiceAccount qui n'existe pas. Le ReplicaSet le dit dans un
# event FailedCreate, et c'est cet event que le script attend : sans lui,
# la situation n'est pas posée.
#
# Rejouable : le namespace est attendu s'il se termine, et ce qu'un passage
# précédent aurait créé, ServiceAccount, Role, RoleBinding, est retiré pour
# que le Pod ne démarre pas tout seul.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace app-team -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/app-team --timeout=180s
fi
kubectl get namespace app-team >/dev/null 2>&1 || kubectl create namespace app-team

kubectl -n app-team delete rolebinding pod-reader-binding --ignore-not-found
kubectl -n app-team delete role pod-reader-role --ignore-not-found
kubectl -n app-team delete deployment inventaire --ignore-not-found --wait=true
kubectl -n app-team delete serviceaccount pod-reader --ignore-not-found

cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inventaire
  namespace: app-team
spec:
  replicas: 1
  selector:
    matchLabels:
      app: inventaire
  template:
    metadata:
      labels:
        app: inventaire
    spec:
      serviceAccountName: pod-reader
      containers:
        - name: inventaire
          image: curlimages/curl:8.22.0
          command: ["sh", "-c", "sleep infinity"]
EOF

# La situation est posée quand le ReplicaSet a échoué à créer son Pod.
for essai in $(seq 1 30); do
  if kubectl -n app-team get events --field-selector reason=FailedCreate -o jsonpath='{.items[*].message}' | grep -q 'serviceaccount "pod-reader" not found'; then
    break
  fi
  sleep 2
done
kubectl -n app-team get events --field-selector reason=FailedCreate -o jsonpath='{.items[*].message}' | grep -q 'serviceaccount "pod-reader" not found'
kubectl -n app-team get deployment inventaire
echo "inventaire attend son ServiceAccount : aucun Pod ne peut être créé."
