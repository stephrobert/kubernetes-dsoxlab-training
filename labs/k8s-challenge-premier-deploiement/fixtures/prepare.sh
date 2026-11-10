#!/usr/bin/env bash
# Pose la situation du challenge sur le cluster kind « boutique » :
#
#   - le kubeconfig de l'apprenant connaît kind-boutique, mais son contexte
#     actif est « ancien-cluster », qui ne répond pas ;
#   - une copie de ce kubeconfig, ~/.kube/boutique.yaml, lisible par tous (644) ;
#   - le namespace catalogue avec le Deployment stock, dont l'image est mal
#     écrite (ImagePullBackOff), appliqué depuis ~/boutique/stock.yaml ;
#   - aucun objet vitrine.
#
# Rejouable : les namespaces sont recréés et les fichiers réécrits à chaque passage.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
ADMIN=/etc/kind/boutique.kubeconfig
# ❌ Tag volontairement faux (1.300 au lieu de 1.30) : c'est la panne de stock.
IMAGE_FAUTIVE="nginx:1.300"

# 1. Des namespaces neufs : catalogue repart de zéro, vitrine n'existe pas.
# --ignore-not-found et non un « get » préalable : le cleanup supprime ces
# namespaces sans attendre, et un namespace encore en Terminating au moment du
# get disparaissait avant le delete, qui sortait en NotFound et arrêtait le
# script (set -e). Mesuré le 2026-11-10 au rejeu de valider-labs.py.
for ns in vitrine catalogue; do
  kubectl delete namespace "$ns" --ignore-not-found --wait=true --timeout=180s
done
kubectl create namespace catalogue

# 2. Le manifeste de stock, à l'apprenant, puis appliqué tel quel.
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/boutique"
rm -f "${LAB_HOME}/boutique/cause-stock.txt"
cat > "${LAB_HOME}/boutique/stock.yaml" <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stock
  namespace: catalogue
  labels:
    app: stock
spec:
  replicas: 1
  selector:
    matchLabels:
      app: stock
  template:
    metadata:
      labels:
        app: stock
    spec:
      containers:
        - name: stock
          image: ${IMAGE_FAUTIVE}
          ports:
            - containerPort: 80
EOF
chown "$LAB_USER:$LAB_USER" "${LAB_HOME}/boutique/stock.yaml"
kubectl apply -f "${LAB_HOME}/boutique/stock.yaml"

# 3. Le kubeconfig de l'apprenant : il connaît kind-boutique, mais le
#    contexte actif est un ancien cluster qui ne répond pas.
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0700 "${LAB_HOME}/.kube"
install -o "$LAB_USER" -g "$LAB_USER" -m 0600 "$ADMIN" "${LAB_HOME}/.kube/config"
sudo -u "$LAB_USER" kubectl --kubeconfig "${LAB_HOME}/.kube/config" config set-cluster ancien-cluster \
  --server=https://127.0.0.1:1
sudo -u "$LAB_USER" kubectl --kubeconfig "${LAB_HOME}/.kube/config" config set-context ancien-cluster \
  --cluster=ancien-cluster --user=kind-boutique
sudo -u "$LAB_USER" kubectl --kubeconfig "${LAB_HOME}/.kube/config" config use-context ancien-cluster

# 4. Le kubeconfig reçu, laissé lisible par tous : à protéger.
install -o "$LAB_USER" -g "$LAB_USER" -m 0644 "$ADMIN" "${LAB_HOME}/.kube/boutique.yaml"

# 5. Attendre que stock soit bien en panne d'image avant d'ouvrir la session.
for _ in $(seq 1 24); do
  raison="$(kubectl -n catalogue get pods -l app=stock \
    -o jsonpath='{.items[0].status.containerStatuses[0].state.waiting.reason}' 2>/dev/null || true)"
  [[ "$raison" == "ErrImagePull" || "$raison" == "ImagePullBackOff" ]] && break
  sleep 5
done
echo "Situation posée : stock attend (${raison:-?}), la vitrine est à livrer."
