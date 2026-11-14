#!/usr/bin/env bash
# Pose les trois applications du challenge dans le namespace commerce, l'API
# server et le kubelet du worker étant encore sains :
#   - api : un Deployment qui cherche sa configuration là où rien n'est monté,
#     et redémarre en boucle (repris de cka-troubleshoot-crashloopbackoff) ;
#   - vitrine : un Pod dont l'image porte un tag qui n'existe pas (repris de
#     cka-troubleshoot-imagepullbackoff) ;
#   - entrepot : un Deployment réservé au worker, sain, qui tombera avec lui
#     (repris de cka-troubleshoot-kubelet).
# api et vitrine sont épinglés sur le control plane : leurs pannes restent
# visibles quand le worker tombe, et ne dépendent pas de lui.
#
# Rejouable : le namespace est attendu s'il se termine, les objets cassés sont
# recréés pour repartir de la panne, et ~/incident est vidé.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

NS=commerce
NGINX="nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
BUSYBOX="busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"

if [[ "$(kubectl get namespace "$NS" -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete "namespace/$NS" --timeout=180s
fi
kubectl get namespace "$NS" >/dev/null 2>&1 || kubectl create namespace commerce

# Un passage précédent a pu laisser des objets réparés : on repart de la panne.
kubectl -n "$NS" delete deployment api --ignore-not-found --wait=true
kubectl -n "$NS" delete pod vitrine --ignore-not-found --wait=true

cat <<'EOF' | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-config
  namespace: commerce
data:
  app.conf: |
    listen=8080
    log_level=info
    feature_flags=billing,exports
EOF

cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: commerce
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      nodeSelector:
        kubernetes.io/hostname: k8s-cp.lab
      containers:
        - name: api
          image: ${BUSYBOX}
          command:
            - sh
            - -c
            - 'cat "\${APP_CONFIG_PATH}/app.conf" && exec httpd -f -v -p 8080 -h "\${APP_CONFIG_PATH}"'
          env:
            - name: APP_CONFIG_PATH
              value: /nonexistent/path
          ports:
            - containerPort: 8080
---
apiVersion: v1
kind: Pod
metadata:
  name: vitrine
  namespace: commerce
  labels:
    app: vitrine
spec:
  nodeSelector:
    kubernetes.io/hostname: k8s-cp.lab
  containers:
    - name: web
      image: nginx:1.30.5-alpin
      ports:
        - containerPort: 80
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: entrepot
  namespace: commerce
spec:
  replicas: 3
  selector:
    matchLabels:
      app: entrepot
  template:
    metadata:
      labels:
        app: entrepot
    spec:
      nodeSelector:
        kubernetes.io/hostname: k8s-w1.lab
      containers:
        - name: web
          image: ${NGINX}
          ports:
            - containerPort: 80
EOF

# entrepot doit être sain AVANT la panne du worker, sinon on mesurerait autre chose.
kubectl -n "$NS" rollout status deployment/entrepot --timeout=180s

# Les deux pannes applicatives doivent être visibles avant que l'API tombe :
# après, plus rien ne s'en lit par kubectl.
for essai in $(seq 1 40); do
  if kubectl -n "$NS" get pods -l app=api \
      -o jsonpath='{.items[*].status.containerStatuses[*].state.waiting.reason}' 2>/dev/null \
      | grep -q CrashLoopBackOff; then
    break
  fi
  sleep 3
done
for essai in $(seq 1 40); do
  raison=$(kubectl -n "$NS" get pod vitrine \
    -o jsonpath='{.status.containerStatuses[0].state.waiting.reason}' 2>/dev/null || true)
  if [[ "$raison" == "ErrImagePull" || "$raison" == "ImagePullBackOff" ]]; then
    break
  fi
  sleep 3
done

# Le répertoire des causes, vide : chaque fichier y sera daté par l'apprenant.
LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
rm -rf "${LAB_HOME:?}/incident"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/incident"

echo "Applications posées : api en boucle, vitrine sans image, entrepot sain sur k8s-w1.lab."
