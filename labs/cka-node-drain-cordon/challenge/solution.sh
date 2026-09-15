#!/usr/bin/env bash
# Solution du formateur. Rejouée sur le control plane après `dsoxlab run`,
# elle prouve que le lab est FAISABLE et que ses tests passent quand le
# travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le budget d'abord : sans lui, le drain évacuerait tout d'un coup.
cat <<'EOF' | $K apply -f -
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
  namespace: lab
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web
EOF
$K -n lab get pdb web-pdb

# 2. Retirer le nœud du scheduling, puis l'évacuer. Les trois options
#    répondent aux trois refus : le DaemonSet calico-node, l'emptyDir de
#    web, et outil-diag qui n'a aucun contrôleur.
$K cordon k8s-w1.lab
$K drain k8s-w1.lab --ignore-daemonsets --delete-emptydir-data --force --timeout=240s

# 3. Tout web est revenu ailleurs. C'est ici qu'aurait lieu la maintenance.
$K -n lab rollout status deployment/web --timeout=180s
$K -n lab get pods -o wide

# 4. Remise en service, et la trace.
$K uncordon k8s-w1.lab
$K -n lab create configmap drain-evidence \
  --from-literal=drained-node=k8s-w1.lab --from-literal=status=completed
$K get nodes
echo "k8s-w1.lab a été vidé sous budget, puis remis en service."
