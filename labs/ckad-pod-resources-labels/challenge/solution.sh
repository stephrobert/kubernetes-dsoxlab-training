#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: multi-app
  namespace: lab
  labels:
    app: multi-app
    tier: frontend
    version: v1
  annotations:
    description: "Serveur web et collecteur de logs, pour la démonstration multi-conteneurs"
spec:
  containers:
    - name: web
      image: nginx:1.27-alpine
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 200m
          memory: 128Mi
    - name: logger
      image: busybox:1.36
      command: ["sh", "-c", "while true; do date; sleep 5; done"]
      resources:
        requests:
          cpu: 50m
          memory: 32Mi
        limits:
          cpu: 100m
          memory: 64Mi
YAML
$K -n lab wait --for=condition=Ready pod/multi-app --timeout=180s

# La preuve : la limite que le noyau applique, lue depuis chaque conteneur.
$K -n lab exec multi-app -c web -- cat /sys/fs/cgroup/memory.max
$K -n lab exec multi-app -c logger -- cat /sys/fs/cgroup/memory.max
$K -n lab get pod multi-app --show-labels
echo "multi-app tourne avec ses deux conteneurs, leurs budgets et ses labels."
