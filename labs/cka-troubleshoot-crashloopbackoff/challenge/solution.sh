#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le diagnostic : ce que le processus a dit avant de mourir, et ce que le
#    Deployment lui donne.
POD=$($K -n production get pods -l app=api-server -o jsonpath='{.items[0].metadata.name}')
$K -n production logs "$POD" --previous 2>/dev/null || $K -n production logs "$POD" || true
$K -n production get deployment api-server -o jsonpath='{.spec.template.spec.containers[0].env}{"\n"}'
$K -n production get configmap

# 2. La réparation, sur le Deployment : la variable désigne /etc/config, et le
#    ConfigMap y est monté. Le Deployment redéploie tout seul.
$K -n production set env deployment/api-server APP_CONFIG_PATH=/etc/config
$K -n production patch deployment api-server --type=json -p '[
  {"op": "add", "path": "/spec/template/spec/volumes",
   "value": [{"name": "config", "configMap": {"name": "api-config"}}]},
  {"op": "add", "path": "/spec/template/spec/containers/0/volumeMounts",
   "value": [{"name": "config", "mountPath": "/etc/config"}]}
]'
$K -n production rollout status deployment/api-server --timeout=180s

# 3. La preuve : la configuration est lue, et l'application la sert.
POD=$($K -n production get pods -l app=api-server -o jsonpath='{.items[0].metadata.name}')
$K -n production exec "$POD" -- cat /etc/config/app.conf
$K -n production exec "$POD" -- wget -qO- http://127.0.0.1:8080/app.conf
echo "api-server tourne en 2/2 et sert sa configuration."
