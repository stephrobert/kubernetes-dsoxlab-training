#!/usr/bin/env bash
# Pose la situation : metrics-server installé et répondant, php-apache en
# un replica avec des requests CPU, son Service. Aucun HPA.
#
# Sur kubeadm, le kubelet sert des certificats auto-signés : metrics-server
# les refuse sans --kubelet-insecure-tls, et kubectl top ne répond jamais.
# L'option est ajoutée après l'apply, qui remet à chaque passage la liste
# d'arguments d'origine.
#
# Rejouable : le namespace est attendu s'il se termine, le HPA et le
# générateur de charge d'un passage précédent sont retirés.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

MANIFESTE="${MANIFESTE:-/root/metrics-server-v0.9.0.yaml}"

kubectl apply -f "${MANIFESTE}"
kubectl -n kube-system patch deployment metrics-server --type=json \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
kubectl -n kube-system rollout status deployment/metrics-server --timeout=180s

for essai in $(seq 1 40); do
  if kubectl top nodes >/dev/null 2>&1; then
    break
  fi
  sleep 5
done
kubectl top nodes

if [[ "$(kubectl get namespace lab -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/lab --timeout=180s
fi
kubectl get namespace lab >/dev/null 2>&1 || kubectl create namespace lab
kubectl -n lab delete hpa php-apache-hpa --ignore-not-found
kubectl -n lab delete pod load-generator --ignore-not-found --wait=true
kubectl -n lab delete deployment php-apache --ignore-not-found --wait=true

cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: php-apache
  namespace: lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: php-apache
  template:
    metadata:
      labels:
        app: php-apache
    spec:
      containers:
        - name: php-apache
          image: registry.k8s.io/hpa-example
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 200m
            limits:
              cpu: 500m
---
apiVersion: v1
kind: Service
metadata:
  name: php-apache
  namespace: lab
spec:
  selector:
    app: php-apache
  ports:
    - port: 80
      targetPort: 80
EOF
kubectl -n lab rollout status deployment/php-apache --timeout=180s

# Les métriques du Pod doivent être lisibles avant de rendre la main.
for essai in $(seq 1 24); do
  if kubectl -n lab top pods 2>/dev/null | grep -q php-apache; then
    break
  fi
  sleep 5
done
kubectl -n lab top pods
echo "metrics-server répond, php-apache tourne en un replica : à l'apprenant de poser le HPA."
