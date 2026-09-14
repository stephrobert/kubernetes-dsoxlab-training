#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
#
# Transposée de K8sExamLab, dont la solution faisait un `kubectl apply` d'un
# Pod au conteneur renommé, ce qu'un Pod existant refuse : elle ne pouvait pas
# passer sur la situation que son propre setup posait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le diagnostic : le message exact du runtime est dans les events.
$K -n lab describe pod broken-pod | grep -E 'Failed|BackOff|Warning' | tail -3 || true

# 2. La réparation, en place : un Pod nu accepte qu'on change son image.
$K -n lab set image pod/broken-pod app=nginx:1.27-alpine
$K -n lab wait --for=condition=Ready pod/broken-pod --timeout=180s

# 3. La preuve : le serveur répond, depuis le nœud.
IP=$($K -n lab get pod broken-pod -o jsonpath='{.status.podIP}')
curl -sS -m 5 "http://${IP}/" | grep -i -m1 'nginx'
echo "broken-pod tourne avec nginx:1.27-alpine et sert sa page d'accueil."
