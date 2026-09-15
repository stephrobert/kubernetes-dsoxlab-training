#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# Le Pod durci. nginx non privilégié écrit son pid dans /tmp et son cache
# dans /var/cache/nginx : deux emptyDir, et la racine peut rester en lecture
# seule. L'utilisateur se déclare au niveau du Pod, le reste au niveau du
# conteneur, parce que readOnlyRootFilesystem, allowPrivilegeEscalation et
# capabilities n'existent pas au niveau du Pod.
cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: hardened
  namespace: lab
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
  containers:
    - name: web
      image: nginxinc/nginx-unprivileged:1.27-alpine
      ports:
        - containerPort: 8080
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop:
            - ALL
      volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: cache
          mountPath: /var/cache/nginx
  volumes:
    - name: tmp
      emptyDir: {}
    - name: cache
      emptyDir: {}
YAML
$K -n lab wait --for=condition=Ready pod/hardened --timeout=180s

# La preuve, de l'intérieur et depuis le nœud.
$K -n lab exec hardened -- id -u
$K -n lab exec hardened -- sh -c 'touch /etc/preuve 2>&1 || echo "racine en lecture seule : refusé, comme prévu"'
IP=$($K -n lab get pod hardened -o jsonpath='{.status.podIP}')
curl -sS -m 5 "http://${IP}:8080/" | grep -i -m1 'nginx'
echo "hardened tourne en 1000, racine en lecture seule, et sert sur 8080."
