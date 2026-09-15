#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# Le sidecar natif : un initContainer avec restartPolicy Always. Il démarre
# avant app, reste en vie pendant tout le Pod, et s'arrête après app. Le
# fichier est créé par touch avant tail -F, pour que le sidecar n'ait rien à
# attendre.
cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: app-with-sidecar
  namespace: lab
spec:
  volumes:
    - name: logs
      emptyDir: {}
  initContainers:
    - name: log-shipper
      image: busybox:1.36
      restartPolicy: Always
      command: ["sh", "-c", "touch /var/log/app/output.log; tail -n +1 -F /var/log/app/output.log"]
      volumeMounts:
        - name: logs
          mountPath: /var/log/app
  containers:
    - name: app
      image: busybox:1.36
      command: ["sh", "-c", "while true; do echo \"$(date) traitement en cours\" >> /var/log/app/output.log; sleep 1; done"]
      volumeMounts:
        - name: logs
          mountPath: /var/log/app
YAML
$K -n lab wait --for=condition=Ready pod/app-with-sidecar --timeout=180s
sleep 5

# La preuve : le fichier se remplit, et le sidecar le recopie.
$K -n lab exec app-with-sidecar -c app -- tail -n 2 /var/log/app/output.log
$K -n lab logs app-with-sidecar -c log-shipper --tail=2
echo "log-shipper suit les logs de app."
