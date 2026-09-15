#!/usr/bin/env bash
# Solution du formateur. Rejouée sur le control plane après `dsoxlab run`,
# elle prouve que le lab est FAISABLE et que ses tests passent quand le
# travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le HPA, en autoscaling/v2.
cat <<'EOF' | $K apply -f -
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: php-apache-hpa
  namespace: lab
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: php-apache
  minReplicas: 1
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 50
EOF

# 2. La charge, depuis un Pod du cluster.
$K -n lab run load-generator --image=busybox:1.37 --restart=Never -- \
  /bin/sh -c 'while true; do wget -q -O- http://php-apache >/dev/null 2>&1; done'

# 3. La montée : une à deux minutes.
for essai in $(seq 1 60); do
  REPLICAS="$($K -n lab get hpa php-apache-hpa -o jsonpath='{.status.currentReplicas}' 2>/dev/null || echo 0)"
  if [[ "${REPLICAS:-0}" -ge 2 ]]; then
    break
  fi
  sleep 5
done
$K -n lab get hpa php-apache-hpa
$K -n lab get events --field-selector reason=SuccessfulRescale -o jsonpath='{range .items[*]}{.message}{"\n"}{end}'

# 4. Couper la charge.
$K -n lab delete pod load-generator --wait=true
echo "php-apache est monté à ${REPLICAS} replicas sous charge, la charge est coupée."
