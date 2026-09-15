#!/usr/bin/env bash
# Solution du formateur. Rejouée sur le control plane après `dsoxlab run`,
# elle prouve que le lab est FAISABLE et que ses tests passent quand le
# travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le nœud : réservé par le taint, reconnaissable par le label.
$K taint nodes k8s-w1.lab env=prod:NoSchedule
$K label nodes k8s-w1.lab disktype=ssd

# 2. prod-app tolère le taint ET exige le label : il ne peut aller qu'ici.
cat <<'EOF' | $K apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: prod-app
  namespace: lab
spec:
  tolerations:
    - key: env
      operator: Equal
      value: prod
      effect: NoSchedule
  nodeSelector:
    disktype: ssd
  containers:
    - name: nginx
      image: nginx:1.27-alpine
---
apiVersion: v1
kind: Pod
metadata:
  name: dev-app
  namespace: lab
spec:
  containers:
    - name: nginx
      image: nginx:1.27-alpine
EOF

# 3. Le placement réel.
$K -n lab wait --for=condition=Ready pod/prod-app pod/dev-app --timeout=180s
$K -n lab get pods -o wide
echo "prod-app est sur k8s-w1.lab, dev-app ailleurs : le nœud est réservé."
