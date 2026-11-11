#!/usr/bin/env bash
# Pose la situation du lab k8s-gerer-les-images sur le cluster kind « lab » :
#
#   - un registre privé, protégé par mot de passe, dans le namespace
#     registre-galerie, servi en NodePort 30500. Mesuré le 2026-11-11 : containerd
#     le tire en localhost:30500 SANS configuration du nœud ;
#   - une image poussée dans ce registre, localhost:30500/galerie/vignettes:1.0,
#     par docker push à travers un port-forward (ctr images push échoue) ;
#   - le namespace galerie, avec :
#       - affiche, un Deployment sur le tag MUTABLE nginx:1.30. Le digest que ses
#         Pods font tourner est mémorisé dans
#         /var/lib/dsoxlab/gerer-les-images.json : c'est lui que l'apprenant fige ;
#       - vignettes, un Deployment au ServiceAccount vignettes, qui tire l'image
#         privée sans identifiants et reste en ImagePullBackOff ;
#   - ~/galerie/, vide, pour le relevé.
#
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
MEMOIRE=/var/lib/dsoxlab/gerer-les-images.json
REGISTRE="registry:3.1.2@sha256:38907510915c3f1604c7e83d6ab602ab3020d092f73bdaed8696773693ff768c"
HTTPD="httpd:2.4-alpine@sha256:610eddacdacf681838190f5e2fda06dba783384c71610b247a765e8f8faadfc6"
UTILISATEUR=galerie
MOT_DE_PASSE=Vignettes-2026

kubectl delete namespace galerie registre-galerie --ignore-not-found --wait=true --timeout=180s
kubectl create namespace registre-galerie
LIGNE="$(docker run --rm "$HTTPD" htpasswd -Bbn "$UTILISATEUR" "$MOT_DE_PASSE" 2>/dev/null | grep "^${UTILISATEUR}:")"
kubectl -n registre-galerie create secret generic registre-auth --from-literal=htpasswd="$LIGNE"
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: registre
  namespace: registre-galerie
spec:
  selector:
    matchLabels:
      app: registre
  template:
    metadata:
      labels:
        app: registre
    spec:
      containers:
        - name: registre
          image: ${REGISTRE}
          env:
            - name: REGISTRY_AUTH
              value: htpasswd
            - name: REGISTRY_AUTH_HTPASSWD_REALM
              value: galerie
            - name: REGISTRY_AUTH_HTPASSWD_PATH
              value: /auth/htpasswd
          ports:
            - containerPort: 5000
          volumeMounts:
            - name: auth
              mountPath: /auth
      volumes:
        - name: auth
          secret:
            secretName: registre-auth
---
apiVersion: v1
kind: Service
metadata:
  name: registre
  namespace: registre-galerie
spec:
  type: NodePort
  selector:
    app: registre
  ports:
    - port: 5000
      targetPort: 5000
      nodePort: 30500
EOF
kubectl -n registre-galerie rollout status deployment registre --timeout=180s

# Pousser l'image privée, par un port-forward vers le localhost de la VM.
kubectl -n registre-galerie port-forward service/registre 15500:5000 >/tmp/pf-galerie.log 2>&1 &
PF=$!
trap 'kill $PF 2>/dev/null || true' EXIT
for _ in $(seq 1 20); do
  curl -s -o /dev/null http://127.0.0.1:15500/v2/ && break
  sleep 1
done
docker pull -q "$HTTPD" >/dev/null
docker tag "$HTTPD" localhost:15500/galerie/vignettes:1.0
echo "$MOT_DE_PASSE" | docker login localhost:15500 -u "$UTILISATEUR" --password-stdin
docker push -q localhost:15500/galerie/vignettes:1.0
docker logout localhost:15500
docker rmi localhost:15500/galerie/vignettes:1.0 >/dev/null
kill $PF 2>/dev/null || true
trap - EXIT

kubectl create namespace galerie
kubectl -n galerie create serviceaccount vignettes
kubectl apply -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: affiche
  namespace: galerie
spec:
  replicas: 2
  selector:
    matchLabels:
      app: affiche
  template:
    metadata:
      labels:
        app: affiche
    spec:
      containers:
        - name: affiche
          image: nginx:1.30
          ports:
            - containerPort: 80
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vignettes
  namespace: galerie
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vignettes
  template:
    metadata:
      labels:
        app: vignettes
    spec:
      serviceAccountName: vignettes
      containers:
        - name: vignettes
          image: localhost:30500/galerie/vignettes:1.0
          ports:
            - containerPort: 80
EOF
kubectl -n galerie rollout status deployment affiche --timeout=180s
kubectl -n galerie wait pod -l app=vignettes \
  --for=jsonpath='{.status.containerStatuses[0].state.waiting.reason}'=ImagePullBackOff --timeout=120s

# Le digest que les Pods d'affiche font tourner aujourd'hui.
image_id="$(kubectl -n galerie get pods -l app=affiche -o jsonpath='{.items[0].status.containerStatuses[0].imageID}')"
install -d -m 0755 /var/lib/dsoxlab
printf '{"affiche_digest": "%s"}\n' "${image_id##*@}" > "$MEMOIRE"

rm -rf "${LAB_HOME:?}/galerie"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/galerie"
echo "Situation posée : affiche sur nginx:1.30 (${image_id##*@}), vignettes en ImagePullBackOff."
