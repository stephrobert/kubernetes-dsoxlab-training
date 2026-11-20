#!/usr/bin/env bash
# Pose la situation du lab k8s-ecrire-un-manifeste sur le cluster kind « lab » :
#
#   - le namespace commandes, où tourne une ANCIENNE version du Deployment api,
#     posée par kubectl apply : un réplica, nginx 1.30.4, sans configuration.
#     Son uid est mémorisé dans /var/lib/dsoxlab/ecrire-un-manifeste.json :
#     l'apprenant doit le mettre à jour en place, un api recréé ne compte pas ;
#   - ~/commandes/api.yaml, le manifeste d'un collègue, avec trois fautes que
#     la leçon apprend à trouver : la ConfigMap ne nomme pas son namespace, le
#     port du conteneur porte un protocole en minuscules (seul le serveur le
#     refuse), et le sélecteur du Service ne correspond à aucun Pod ;
#   - aucun objet api dans default.
#
# Avant le 2026-11-20, l'apprenant écrivait le fichier de zéro et corrigeait un
# Deployment rapport : c'était le scénario de la leçon.
#
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
MEMOIRE=/var/lib/dsoxlab/ecrire-un-manifeste.json
ANCIENNE="nginx:1.30.4@sha256:d5792f71a9496b833bc08ea834a758c46e2b6a6306c10f4be926f38a656cdc1c"

kubectl delete namespace commandes --ignore-not-found --wait=true --timeout=180s
kubectl -n default delete deployment/api service/api configmap/api-config --ignore-not-found
kubectl create namespace commandes
kubectl -n commandes apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 1
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
        - name: api
          image: ${ANCIENNE}
          ports:
            - containerPort: 80
EOF
kubectl -n commandes rollout status deployment/api --timeout=180s
uid="$(kubectl -n commandes get deployment api -o jsonpath='{.metadata.uid}')"
install -d -m 0755 /var/lib/dsoxlab
printf '{"api_uid": "%s"}\n' "$uid" > "$MEMOIRE"

rm -rf "${LAB_HOME:?}/commandes"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/commandes"
cat > "${LAB_HOME}/commandes/api.yaml" <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-config
data:
  DEVISE: EUR
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: commandes
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
      containers:
        - name: api
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
          ports:
            - containerPort: 80
              protocol: tcp
          envFrom:
            - configMapRef:
                name: api-config
---
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: commandes
spec:
  selector:
    app: apy
  ports:
    - port: 80
      targetPort: 80
YAML
chown "$LAB_USER:$LAB_USER" "${LAB_HOME}/commandes/api.yaml"
echo "Situation posée : api ancienne version (uid ${uid}), ~/commandes/api.yaml fautif."
