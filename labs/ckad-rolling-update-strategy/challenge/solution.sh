#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. La stratégie d'abord : c'est elle qui pilotera le remplacement.
$K -n lab patch deployment webapp --type=merge \
  -p '{"spec":{"strategy":{"type":"RollingUpdate","rollingUpdate":{"maxSurge":2,"maxUnavailable":1}}}}'

# 2. La mise à jour, puis l'attente de sa fin.
$K -n lab set image deployment/webapp web=nginx:1.27-alpine
$K -n lab rollout status deployment/webapp --timeout=300s

# 3. La preuve : deux révisions, l'ancienne à zéro.
$K -n lab rollout history deployment/webapp
$K -n lab get replicasets -l app=webapp
echo "webapp est en 1.27, cinq replicas, sous contrainte 2 en trop, 1 indisponible."
