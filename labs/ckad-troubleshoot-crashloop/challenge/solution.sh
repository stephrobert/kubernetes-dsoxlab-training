#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le diagnostic, trois lectures différentes.
$K -n lab get pods
$K -n lab get pod bad-command -o jsonpath='{.status.containerStatuses[0].lastState.terminated.reason}{" "}{.status.containerStatuses[0].lastState.terminated.message}{"\n"}' || true
$K -n lab logs missing-env --previous 2>/dev/null || $K -n lab logs missing-env || true
$K -n lab get pod oom-killed -o jsonpath='{.status.containerStatuses[0].lastState.terminated.reason}{"\n"}' || true

# 2. Les corrections : un Pod nu se recrée, avec le même nom.
$K -n lab delete pod bad-command missing-env oom-killed --wait=true
cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: bad-command
  namespace: lab
spec:
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "while true; do sleep 3600; done"]
---
apiVersion: v1
kind: Pod
metadata:
  name: missing-env
  namespace: lab
spec:
  containers:
    - name: app
      image: busybox:1.36
      env:
        - name: APP_MODE
          value: production
      command: ["sh", "-c", "if [ -z \"$APP_MODE\" ]; then echo 'APP_MODE est obligatoire, arrêt' >&2; exit 1; fi; echo \"démarré en mode $APP_MODE\"; while true; do sleep 3600; done"]
---
apiVersion: v1
kind: Pod
metadata:
  name: oom-killed
  namespace: lab
spec:
  containers:
    - name: app
      image: nginx:1.27-alpine
      resources:
        requests:
          memory: 64Mi
        limits:
          memory: 64Mi
YAML

# 3. La preuve : les trois tiennent.
$K -n lab wait --for=condition=Ready pod/bad-command pod/missing-env pod/oom-killed --timeout=180s
sleep 15
$K -n lab get pods
echo "Les trois Pods tournent, et ne redémarrent plus."
