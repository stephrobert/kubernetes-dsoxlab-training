#!/usr/bin/env bash
# Pose la situation du lab k8s-verifier-et-attendre sur le cluster kind « lab » :
#
#   - le namespace paiements, avec le Deployment facturation en version 1,
#     2 réplicas, appliqué depuis le dossier ;
#   - ~/deploiement/, le dossier versionné : facturation.yaml (version 1, ce qui
#     tourne) et migration.yaml, un Job de migration jamais appliqué ;
#   - aucun script, aucun relevé : c'est le travail.
#
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
V1="nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
BUSYBOX="busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4"
D="${LAB_HOME}/deploiement"

kubectl delete namespace paiements --ignore-not-found --wait=true --timeout=180s
kubectl create namespace paiements
rm -rf "${D:?}"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "$D"

cat > "$D/facturation.yaml" <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: facturation
  namespace: paiements
  labels:
    app: facturation
spec:
  replicas: 2
  selector:
    matchLabels:
      app: facturation
  template:
    metadata:
      labels:
        app: facturation
    spec:
      containers:
        - name: facturation
          image: ${V1}
          ports:
            - containerPort: 80
          readinessProbe:
            httpGet:
              path: /
              port: 80
EOF
cat > "$D/migration.yaml" <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: migration
  namespace: paiements
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migration
          image: ${BUSYBOX}
          command: ["sh", "-c", "echo migration du schéma; sleep 8; echo terminée"]
EOF
chown -R "$LAB_USER:$LAB_USER" "$D"

kubectl apply -f "$D/facturation.yaml"
kubectl -n paiements rollout status deployment facturation --timeout=180s
# Un historique dont la longueur change à chaque préparation : de 1 à 3
# redémarrages, donc la révision qui portera la version 2 vaut 3, 4 ou 5. Le
# relevé la demande : elle se lit dans le cluster, pas dans la leçon. Un
# redémarrage ne touche qu'une annotation que le fichier ne gère pas : comparer
# le dossier au cluster ne montre toujours aucune différence.
for _ in $(seq 1 $((RANDOM % 3 + 1))); do
  kubectl -n paiements rollout restart deployment facturation
  kubectl -n paiements rollout status deployment facturation --timeout=180s
done
echo "Situation posée : facturation en version 1 (révision $(kubectl -n paiements get deployment facturation -o jsonpath='{.metadata.annotations.deployment\.kubernetes\.io/revision}')), migration non appliquée."
