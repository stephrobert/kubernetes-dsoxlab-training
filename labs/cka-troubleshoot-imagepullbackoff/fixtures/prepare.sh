#!/usr/bin/env bash
# Pose la situation : un Pod dont le tag d'image porte une faute de frappe,
# « alpin » pour « alpine ». Le registre répond que le manifest n'existe pas,
# et le kubelet espace ses tentatives.
#
# Rejouable : le Pod est supprimé puis recréé, pour défaire la correction d'un
# passage précédent.
set -euo pipefail

if [[ "$(kubectl get namespace lab -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/lab --timeout=180s
fi
kubectl get namespace lab >/dev/null 2>&1 || kubectl create namespace lab

kubectl -n lab delete pod broken-pod --ignore-not-found --wait=true

cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: broken-pod
  namespace: lab
  labels:
    app: broken-pod
spec:
  containers:
    - name: app
      image: nginx:1.27-alpin
      ports:
        - containerPort: 80
EOF

# On attend que l'échec de téléchargement soit visible : ErrImagePull ou
# ImagePullBackOff, les deux alternent en 1.37.
for essai in $(seq 1 40); do
  raison=$(kubectl -n lab get pod broken-pod \
    -o jsonpath='{.status.containerStatuses[0].state.waiting.reason}' 2>/dev/null || true)
  if [[ "$raison" == "ErrImagePull" || "$raison" == "ImagePullBackOff" ]]; then
    break
  fi
  sleep 3
done

echo "Situation posée : broken-pod ne télécharge pas son image."
