#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le diagnostic : pas de logs, mais des events qui nomment ce qui manque.
$K -n lab get pod broken-app
$K -n lab get events --field-selector involvedObject.name=broken-app | tail -3

# 2. La ressource manquante, avec le contenu attendu.
$K -n lab create configmap app-settings --from-literal=settings.conf='mode=production
log_level=info'

# 3. Le Pod se débloque tout seul.
$K -n lab wait --for=condition=Ready pod/broken-app --timeout=180s

# 4. La preuve : l'application sert sa configuration.
IP=$($K -n lab get pod broken-app -o jsonpath='{.status.podIP}')
curl -sS -m 5 "http://${IP}/" | grep -m1 'mode=production'
echo "broken-app tourne et sert sa configuration."
