#!/usr/bin/env bash
# Pose la situation du challenge, fausse sur les six états par construction :
#   - paiement : un seul exemplaire, sans sonde, sans budget de perturbation,
#     sans règle de répartition, derrière un Service. L'application met une
#     vingtaine de secondes à se mettre en route : / ne sert sa page qu'après,
#     /vivant.html répond dès que nginx tourne, /pret.html une fois prête ;
#   - exploitation : de quoi nourrir le rapport de routine, un Pod en erreur
#     d'image (facturation-batch) et un Job terminé qui traîne (export-ancien).
# Le worker est remis dans le scheduling, au cas où un check interrompu
# l'aurait laissé cordonné.
#
# Rejouable : les namespaces sont attendus s'ils se terminent, l'application
# est recréée à un exemplaire, les budgets d'un passage précédent sont retirés,
# et ~/routine est vidé.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

NGINX="nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
BUSYBOX="busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"

kubectl uncordon k8s-w1.lab
kubectl wait --for=condition=Ready node/k8s-w1.lab --timeout=180s

for ns in paiement exploitation; do
  if [[ "$(kubectl get namespace "$ns" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
    kubectl wait --for=delete "namespace/$ns" --timeout=180s
  fi
done
kubectl get namespace paiement >/dev/null 2>&1 || kubectl create namespace paiement
kubectl get namespace exploitation >/dev/null 2>&1 || kubectl create namespace exploitation

# Un passage précédent a pu laisser le travail de l'apprenant : on repart de zéro.
kubectl -n paiement delete pdb --all --ignore-not-found
kubectl -n paiement delete deployment paiement --ignore-not-found --wait=true
kubectl -n exploitation delete pod facturation-batch --ignore-not-found --wait=true
kubectl -n exploitation delete job export-ancien --ignore-not-found --wait=true

cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: paiement
  namespace: paiement
spec:
  replicas: 1
  selector:
    matchLabels:
      app: paiement
  template:
    metadata:
      labels:
        app: paiement
    spec:
      containers:
        - name: paiement
          image: ${NGINX}
          command:
            - sh
            - -c
            - >-
              rm -f /usr/share/nginx/html/index.html /usr/share/nginx/html/pret.html;
              echo vivant > /usr/share/nginx/html/vivant.html;
              (sleep 20; echo paiement > /usr/share/nginx/html/index.html;
              echo pret > /usr/share/nginx/html/pret.html) &
              exec nginx -g 'daemon off;'
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 20m
              memory: 32Mi
---
apiVersion: v1
kind: Service
metadata:
  name: paiement
  namespace: paiement
spec:
  selector:
    app: paiement
  ports:
    - port: 80
      targetPort: 80
---
apiVersion: v1
kind: Pod
metadata:
  name: facturation-batch
  namespace: exploitation
  labels:
    app: facturation-batch
spec:
  containers:
    - name: batch
      image: busybox:1.38.99
      command: ["sh", "-c", "echo facturation; sleep 3600"]
---
apiVersion: batch/v1
kind: Job
metadata:
  name: export-ancien
  namespace: exploitation
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: export
          image: ${BUSYBOX}
          command: ["sh", "-c", "echo export termine"]
EOF

kubectl -n paiement rollout status deployment/paiement --timeout=180s
kubectl -n exploitation wait --for=condition=Complete job/export-ancien --timeout=180s
for essai in $(seq 1 40); do
  raison=$(kubectl -n exploitation get pod facturation-batch \
    -o jsonpath='{.status.containerStatuses[0].state.waiting.reason}' 2>/dev/null || true)
  if [[ "$raison" == "ErrImagePull" || "$raison" == "ImagePullBackOff" ]]; then
    break
  fi
  sleep 3
done

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
rm -rf "${LAB_HOME:?}/routine"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/routine"

echo "Situation posée : paiement à un exemplaire, facturation-batch en erreur, export-ancien terminé."
