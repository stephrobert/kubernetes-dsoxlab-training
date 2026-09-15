#!/usr/bin/env bash
# Solution du formateur. Rejouée sur le control plane après `dsoxlab run`,
# elle prouve que le lab est FAISABLE et que ses tests passent quand le
# travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le taint exact, à recopier dans la tolérance.
$K describe node k8s-cp.lab | grep -A2 '^Taints:'

# 2. Le DaemonSet, avec la tolérance du control plane.
cat <<'EOF' | $K apply -f -
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: monitor-agent
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: monitor
  template:
    metadata:
      labels:
        app: monitor
    spec:
      tolerations:
        - key: node-role.kubernetes.io/control-plane
          operator: Exists
          effect: NoSchedule
      containers:
        - name: agent
          image: busybox:1.37
          command: ["sh", "-c", "while true; do echo heartbeat; sleep 60; done"]
EOF

# 3. Un Pod par nœud, prêts.
$K -n monitoring rollout status daemonset/monitor-agent --timeout=180s
$K -n monitoring get pods -o wide
$K -n monitoring logs -l app=monitor --tail=1
echo "monitor-agent tourne sur chaque nœud, control plane compris."
