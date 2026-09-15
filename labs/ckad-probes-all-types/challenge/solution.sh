#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# Trois sondes, trois rôles. La sonde de démarrage tolère 30 échecs à 2 s
# d'intervalle, soit une minute ; tant qu'elle n'a pas réussi, les deux
# autres ne s'exécutent pas.
cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: probed-app
  namespace: lab
spec:
  containers:
    - name: web
      image: nginx:1.27-alpine
      ports:
        - containerPort: 80
      startupProbe:
        httpGet:
          path: /
          port: 80
        periodSeconds: 2
        failureThreshold: 30
      livenessProbe:
        httpGet:
          path: /
          port: 80
        periodSeconds: 10
        failureThreshold: 3
      readinessProbe:
        httpGet:
          path: /
          port: 80
        periodSeconds: 5
        failureThreshold: 3
YAML
$K -n lab wait --for=condition=Ready pod/probed-app --timeout=180s
$K -n lab get pod probed-app
echo "probed-app est Ready : ses trois sondes trouvent ce qu'elles cherchent."
