#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
RACINE=$(mktemp -d /tmp/kustomize.XXXXXX)
mkdir -p "$RACINE/base" "$RACINE/overlays/dev" "$RACINE/overlays/prod"

# La base : l'application, une fois.
cat <<'YAML' > "$RACINE/base/deployment.yaml"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: app
  template:
    metadata:
      labels:
        app: app
    spec:
      containers:
        - name: web
          image: nginx:1.27-alpine
          ports:
            - containerPort: 80
YAML
cat <<'YAML' > "$RACINE/base/service.yaml"
apiVersion: v1
kind: Service
metadata:
  name: app-svc
spec:
  selector:
    app: app
  ports:
    - port: 80
      targetPort: 80
YAML
cat <<'YAML' > "$RACINE/base/kustomization.yaml"
resources:
  - deployment.yaml
  - service.yaml
YAML

# Les overlays : seules les différences. includeSelectors met le label
# d'environnement jusque dans les selectors, sinon le Service ne trouverait
# plus ses Pods.
for env in dev prod; do
  if [[ "$env" == "dev" ]]; then replicas=1; else replicas=3; fi
cat <<YAML > "$RACINE/overlays/$env/kustomization.yaml"
resources:
  - ../../base
namespace: $env
namePrefix: $env-
labels:
  - pairs:
      env: $env
    includeSelectors: true
replicas:
  - name: app
    count: $replicas
YAML
done

$K apply -k "$RACINE/overlays/dev"
$K apply -k "$RACINE/overlays/prod"
$K -n dev rollout status deployment/dev-app --timeout=180s
$K -n prod rollout status deployment/prod-app --timeout=180s
$K get deployments,services -n dev
$K get deployments,services -n prod
echo "dev et prod tournent depuis la même base."
