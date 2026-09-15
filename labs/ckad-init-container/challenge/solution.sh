#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le Pod avec son gardien : une boucle jusqu'à ce que config-svc réponde.
cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: app
  namespace: lab
spec:
  initContainers:
    - name: wait-for-config
      image: busybox:1.36
      command: ["sh", "-c", "until wget -qO- -T 3 http://config-svc/ >/dev/null 2>&1; do echo \"config-svc ne répond pas encore\"; sleep 2; done; echo \"config-svc répond\""]
  containers:
    - name: main
      image: nginx:1.27-alpine
YAML

# 2. Le constat : le Pod reste en Init tant que rien ne répond.
sleep 8
$K -n lab get pod app
$K -n lab logs app -c wait-for-config --tail=2 || true

# 3. La dépendance : un serveur que le Service sélectionne.
$K -n lab run config-server --image=nginx:1.27-alpine --labels=app=config --port=80
$K -n lab wait --for=condition=Ready pod/config-server --timeout=180s

# 4. La preuve : l'init se termine et app démarre sans qu'on y touche.
$K -n lab wait --for=condition=Ready pod/app --timeout=180s
$K -n lab get pod app config-server
$K -n lab get endpointslices -l kubernetes.io/service-name=config-svc
echo "app a attendu config-svc, puis a démarré."
