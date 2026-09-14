#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
#
# Transposée de K8sExamLab, dont la solution nommait le Pod de nœud
# « node-debug-<nœud> » alors que kubectl le nomme « node-debugger-<nœud>-xxxxx »
# et n'offre pas de le renommer : son propre check ne pouvait pas passer.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le constat : pas de shell dans le conteneur.
$K -n lab exec distroless-app -- sh -c 'echo present' 2>&1 | tail -1 || true

# 2. Un conteneur éphémère qui partage les processus de l'application, et qui
#    reste en vie après avoir écrit la liste, sinon plus personne ne la relit.
$K -n lab debug distroless-app --image=busybox:1.36 --target=distroless-app -c debugger \
  -- sh -c 'ps aux > /tmp/debug-output.txt; sleep 3600'
for essai in $(seq 1 30); do
  demarre=$($K -n lab get pod distroless-app \
    -o jsonpath='{.status.ephemeralContainerStatuses[?(@.name=="debugger")].state.running.startedAt}' 2>/dev/null)
  if [[ -n "$demarre" ]]; then
    break
  fi
  sleep 2
done
$K -n lab exec distroless-app -c debugger -- cat /tmp/debug-output.txt

# 3. Un Pod de débogage du nœud, qui écrit sur le nœud à travers /host.
$K debug node/k8s-cp.lab --image=busybox:1.36 \
  -- sh -c 'echo node-debug-ok > /host/tmp/node-debug.txt; sleep 3600'
for essai in $(seq 1 30); do
  if sudo test -f /tmp/node-debug.txt; then
    break
  fi
  sleep 2
done
sudo cat /tmp/node-debug.txt
echo "Le conteneur éphémère voit coredns, et le fichier témoin est sur le nœud."
