#!/usr/bin/env bash
# Pose la situation du lab k8s-creer-ou-appliquer sur le cluster kind « lab »,
# dans le namespace livraisons :
#
#   - ~/livraisons/appli/, le dossier versionné de l'application suivi :
#     suivi.yaml à la racine, le Service et la ConfigMap dans deux
#     sous-dossiers. Seul suivi.yaml est appliqué par le setup ; suivi.yaml
#     fixe encore replicas: 2 ;
#   - suivi, mis à 4 réplicas par un kubectl scale, comme le ferait un
#     autoscaler ;
#   - suivi-ancien, une ConfigMap appliquée autrefois (label app=suivi) dont le
#     fichier a été retiré du dossier ;
#   - journal, une ConfigMap appliquée d'un autre dossier (label app=journal),
#     qui doit survivre. Son uid est mémorisé ;
#   - tarifs, un Deployment né d'un kubectl create, en version 1.
#
# Rejouable.
set -euo pipefail
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

LAB_USER="${LAB_USER:-ansible}"
LAB_HOME="$(getent passwd "$LAB_USER" | cut -d: -f6)"
V1="nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb"
MEMOIRE=/var/lib/dsoxlab/creer-ou-appliquer.json
D="${LAB_HOME}/livraisons/appli"

kubectl delete namespace livraisons --ignore-not-found --wait=true --timeout=180s
kubectl create namespace livraisons
rm -rf "${LAB_HOME:?}/livraisons"
install -d -o "$LAB_USER" -g "$LAB_USER" -m 0755 "${LAB_HOME}/livraisons" "$D" "$D/services" "$D/config"

cat > "$D/suivi.yaml" <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: suivi
  namespace: livraisons
  labels:
    app: suivi
spec:
  replicas: 2
  selector:
    matchLabels:
      app: suivi
  template:
    metadata:
      labels:
        app: suivi
    spec:
      containers:
        - name: suivi
          image: ${V1}
          ports:
            - containerPort: 80
EOF
cat > "$D/services/suivi-svc.yaml" <<'EOF'
apiVersion: v1
kind: Service
metadata:
  name: suivi
  namespace: livraisons
  labels:
    app: suivi
spec:
  selector:
    app: suivi
  ports:
    - port: 80
      targetPort: 80
EOF
cat > "$D/config/suivi-config.yaml" <<'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: suivi-config
  namespace: livraisons
  labels:
    app: suivi
data:
  RETARD_MAX: "48h"
EOF
chown -R "$LAB_USER:$LAB_USER" "${LAB_HOME}/livraisons"

kubectl apply -f "$D/suivi.yaml"
kubectl -n livraisons rollout status deployment suivi --timeout=180s
kubectl -n livraisons scale deployment suivi --replicas=4

# suivi-ancien : appliquée autrefois depuis le dossier, fichier retiré depuis.
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: suivi-ancien
  namespace: livraisons
  labels:
    app: suivi
data:
  RETARD_MAX: "72h"
EOF
# journal : appliquée depuis un autre dossier, hors de l'application suivi.
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: journal
  namespace: livraisons
  labels:
    app: journal
data:
  NIVEAU: info
EOF
kubectl -n livraisons create deployment tarifs --image="$V1" --replicas=1 --port=80
kubectl -n livraisons rollout status deployment suivi --timeout=180s
kubectl -n livraisons rollout status deployment tarifs --timeout=180s

install -d -m 0755 /var/lib/dsoxlab
printf '{"journal_uid": "%s"}\n' "$(kubectl -n livraisons get configmap journal -o jsonpath='{.metadata.uid}')" > "$MEMOIRE"
echo "Situation posée : suivi à 4 réplicas, suivi-ancien, journal, tarifs."
