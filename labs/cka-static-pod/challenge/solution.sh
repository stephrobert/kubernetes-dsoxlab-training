#!/usr/bin/env bash
# Solution du formateur. Rejouée sur le control plane après `dsoxlab run`,
# elle prouve que le lab est FAISABLE et que ses tests passent quand le
# travail est fait. Elle passe par `ssh k8s-w1.lab`, comme le candidat.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# Ce script est lu par `bash -s` depuis l'entrée standard : chaque ssh doit
# porter -n, sinon il avale le reste du script comme entrée.

# 1. Où le kubelet du worker lit-il ses manifestes ? Dans sa configuration.
REPERTOIRE="$(ssh -n k8s-w1.lab 'sudo grep staticPodPath /var/lib/kubelet/config.yaml' | awk '{print $2}')"
echo "staticPodPath sur k8s-w1.lab : ${REPERTOIRE}"

# 2. Le manifeste, écrit sur le worker. Le heredoc est passé à ssh en une
#    seule commande, avec -n, et tee écrit le fichier en root.
ssh -n k8s-w1.lab "sudo tee ${REPERTOIRE}/static-web.yaml >/dev/null <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: static-web
  namespace: default
  labels:
    role: static
spec:
  containers:
    - name: web
      image: nginx:1.27-alpine
      ports:
        - containerPort: 80
          name: http
EOF"

# 3. Le kubelet relit le répertoire en quelques secondes et publie le miroir.
for essai in $(seq 1 30); do
  if [[ "$($K -n default get pod static-web-k8s-w1.lab -o jsonpath='{.status.phase}' 2>/dev/null)" == "Running" ]]; then
    break
  fi
  sleep 3
done
$K -n default get pod static-web-k8s-w1.lab -o wide
echo "static-web tourne sur k8s-w1.lab, géré par son kubelet."
