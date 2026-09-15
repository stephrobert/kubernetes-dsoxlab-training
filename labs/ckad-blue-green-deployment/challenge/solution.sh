#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Les deux versions, qui répondent leur nom.
for couleur in blue green; do
cat <<YAML | $K apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-${couleur}
  namespace: lab
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapp
      version: ${couleur}
  template:
    metadata:
      labels:
        app: myapp
        version: ${couleur}
    spec:
      containers:
        - name: web
          image: busybox:1.36
          command: ["sh", "-c", "mkdir -p /www && echo ${couleur} > /www/index.html && exec httpd -f -p 8080 -h /www"]
          ports:
            - containerPort: 8080
YAML
done
$K -n lab rollout status deployment/app-blue --timeout=180s
$K -n lab rollout status deployment/app-green --timeout=180s

# 2. Le Service, d'abord sur blue.
cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: Service
metadata:
  name: app-prod
  namespace: lab
spec:
  selector:
    app: myapp
    version: blue
  ports:
    - port: 8080
      targetPort: 8080
YAML
sleep 3
$K -n lab exec client -- wget -qO- -T 5 http://app-prod:8080/

# 3. La bascule : un selector, et rien d'autre.
$K -n lab patch service app-prod -p '{"spec":{"selector":{"app":"myapp","version":"green"}}}'
sleep 5
for essai in 1 2 3 4 5; do
  $K -n lab exec client -- wget -qO- -T 5 http://app-prod:8080/
done
$K -n lab get endpointslices -l kubernetes.io/service-name=app-prod
echo "app-prod sert green, blue reste prêt pour le retour arrière."
