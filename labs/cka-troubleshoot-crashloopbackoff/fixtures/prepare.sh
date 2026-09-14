#!/usr/bin/env bash
# Pose la situation : la configuration est bien dans le namespace, mais le
# Deployment ne la monte pas et pointe la variable vers un chemin qui n'existe
# pas. Le conteneur meurt en le disant, et le kubelet le relance en boucle.
#
# Rejouable : le Deployment est supprimé puis recréé, pour défaire la
# correction d'un passage précédent.
set -euo pipefail

if [[ "$(kubectl get namespace production -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/production --timeout=180s
fi
kubectl get namespace production >/dev/null 2>&1 || kubectl create namespace production

cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-config
  namespace: production
data:
  app.conf: |
    listen=8080
    log_level=info
    feature_flags=billing,exports
EOF

kubectl -n production delete deployment api-server --ignore-not-found --wait=true

# La commande lit la configuration là où APP_CONFIG_PATH la désigne, puis
# sert ce répertoire en HTTP. Avec un chemin inexistant et rien de monté, le
# cat échoue et le conteneur sort en erreur : c'est la panne du lab.
cat <<'EOF' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
  namespace: production
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api-server
  template:
    metadata:
      labels:
        app: api-server
    spec:
      containers:
        - name: api
          image: busybox:1.36
          command:
            - sh
            - -c
            - 'cat "${APP_CONFIG_PATH}/app.conf" && exec httpd -f -v -p 8080 -h "${APP_CONFIG_PATH}"'
          env:
            - name: APP_CONFIG_PATH
              value: /nonexistent/path
          ports:
            - containerPort: 8080
EOF

# On attend que la boucle soit visible : au moins un Pod en CrashLoopBackOff.
for essai in $(seq 1 40); do
  if kubectl -n production get pods -l app=api-server \
      -o jsonpath='{.items[*].status.containerStatuses[*].state.waiting.reason}' 2>/dev/null \
      | grep -q CrashLoopBackOff; then
    break
  fi
  sleep 3
done

echo "Situation posée : api-server redémarre en boucle dans production."
