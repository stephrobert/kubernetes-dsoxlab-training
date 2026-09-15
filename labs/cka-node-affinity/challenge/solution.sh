#!/usr/bin/env bash
# Solution du formateur. Rejouée sur le control plane après `dsoxlab run`,
# elle prouve que le lab est FAISABLE et que ses tests passent quand le
# travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le seul nœud à disques rapides.
$K label nodes k8s-w1.lab disktype=ssd

# 2. storage-app : obligatoire sur disktype In (ssd, nvme), préféré sur
#    storage-tier=fast. gpu-app : obligatoire sur accelerator=gpu, qui
#    n'existe pas encore.
cat <<'EOF' | $K apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: storage-app
  namespace: lab
spec:
  replicas: 3
  selector:
    matchLabels:
      app: storage-app
  template:
    metadata:
      labels:
        app: storage-app
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: disktype
                    operator: In
                    values: ["ssd", "nvme"]
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 80
              preference:
                matchExpressions:
                  - key: storage-tier
                    operator: In
                    values: ["fast"]
      containers:
        - name: nginx
          image: nginx:1.27-alpine
---
apiVersion: v1
kind: Pod
metadata:
  name: gpu-app
  namespace: lab
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
          - matchExpressions:
              - key: accelerator
                operator: In
                values: ["gpu"]
  containers:
    - name: nginx
      image: nginx:1.27-alpine
EOF
$K -n lab rollout status deployment/storage-app --timeout=180s

# 3. gpu-app attend : describe le dit. Puis le label arrive, et il démarre.
sleep 5
$K -n lab get pod gpu-app
$K label nodes k8s-w1.lab accelerator=gpu
$K -n lab wait --for=condition=Ready pod/gpu-app --timeout=180s
$K -n lab get pods -o wide
echo "storage-app est sur le nœud ssd, gpu-app a démarré dès le label posé."
