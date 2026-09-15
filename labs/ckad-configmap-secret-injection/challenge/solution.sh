#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le ConfigMap : deux réglages simples et un fichier entier.
cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-settings
  namespace: lab
data:
  APP_MODE: production
  LOG_LEVEL: info
  config.yaml: |
    server:
      port: 8080
      debug: false
YAML

# 2. Le Secret : stringData épargne l'encodage à la main.
cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
  namespace: lab
type: Opaque
stringData:
  DB_HOST: db.internal.svc
  DB_PASSWORD: S3cur3P4ss
YAML

# 3. Le Pod : envFrom pour tout charger d'un bloc, le volume pour le fichier.
#    Aucune valeur en clair, seulement des références.
cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: app
  namespace: lab
spec:
  containers:
    - name: app
      image: nginx:1.27-alpine
      envFrom:
        - configMapRef:
            name: app-settings
        - secretRef:
            name: db-credentials
      volumeMounts:
        - name: config
          mountPath: /etc/app-config
  volumes:
    - name: config
      configMap:
        name: app-settings
YAML
$K -n lab wait --for=condition=Ready pod/app --timeout=180s

# 4. La preuve, de l'intérieur.
$K -n lab exec app -- printenv APP_MODE LOG_LEVEL DB_HOST
$K -n lab exec app -- sh -c 'test -n "$DB_PASSWORD" && echo "DB_PASSWORD est défini"'
$K -n lab exec app -- cat /etc/app-config/config.yaml
echo "app reçoit sa configuration et ses identifiants."
