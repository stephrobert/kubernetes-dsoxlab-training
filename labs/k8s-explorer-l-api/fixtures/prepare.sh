#!/usr/bin/env bash
# Pose la situation du lab k8s-explorer-l-api sur le cluster kind « lab » :
#
#   - une CRD inventée, Sauvegarde, du groupe sauvegarde.formation.k8s en
#     version v1beta1, dont le schéma exige deux champs que seul
#     `kubectl explain` révèle ;
#   - le namespace archives, avec ce que `kubectl get all` ne montre pas
#     (ConfigMap, Secret, ServiceAccount, Role, RoleBinding) et un Deployment
#     catalogue SANS sonde de disponibilité ;
#   - ~/archives/, vide, où l'apprenant écrit son relevé.
#
# La CRD est attendue jusqu'à ce que `kubectl explain` connaisse son schéma :
# mesuré le 2026-11-11, il arrive environ 1 s APRÈS la condition Established.
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
NGINX="nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
CRD="sauvegardes.sauvegarde.formation.k8s"

kubectl delete namespace archives --ignore-not-found --wait=true --timeout=180s
kubectl delete crd "$CRD" --ignore-not-found --wait=true --timeout=120s

kubectl apply -f - <<'EOF'
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: sauvegardes.sauvegarde.formation.k8s
spec:
  group: sauvegarde.formation.k8s
  scope: Namespaced
  names:
    plural: sauvegardes
    singular: sauvegarde
    kind: Sauvegarde
    shortNames:
      - svg
  versions:
    - name: v1beta1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required:
                - cible
                - planification
              properties:
                cible:
                  type: string
                  description: Nom de la base de données à sauvegarder.
                planification:
                  type: string
                  description: Quand sauvegarder, en expression cron à cinq champs (minute heure jour mois jour-de-semaine).
                retention:
                  type: integer
                  description: Nombre de sauvegardes conservées. Facultatif.
EOF
kubectl wait --for=condition=Established "crd/$CRD" --timeout=60s
for _ in $(seq 1 30); do
  kubectl explain sauvegarde.spec >/dev/null 2>&1 && break
  sleep 1
done
kubectl explain sauvegarde.spec >/dev/null

kubectl create namespace archives
kubectl -n archives create configmap catalogue-config --from-literal=LANGUE=fr
kubectl -n archives create secret generic catalogue-db --from-literal=DB_PASSWORD=Archives-2026
kubectl -n archives create serviceaccount catalogue
kubectl -n archives create role lecture-config --verb=get,list --resource=configmaps
kubectl -n archives create rolebinding catalogue-lecture --role=lecture-config --serviceaccount=archives:catalogue
kubectl -n archives apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: catalogue
spec:
  replicas: 2
  selector:
    matchLabels:
      app: catalogue
  template:
    metadata:
      labels:
        app: catalogue
    spec:
      serviceAccountName: catalogue
      containers:
        - name: nginx
          image: ${NGINX}
          ports:
            - containerPort: 80
EOF
kubectl -n archives rollout status deployment catalogue --timeout=180s

rm -rf "${LAB_HOME:?}/archives"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/archives"
echo "Situation posée : CRD Sauvegarde, namespace archives, catalogue sans sonde."
