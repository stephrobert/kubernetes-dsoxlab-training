#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le Job : quatre complétions, deux à la fois, dix secondes chacune.
cat <<'YAML' | $K apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: batch-job
  namespace: lab
spec:
  completions: 4
  parallelism: 2
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: batch
          image: busybox:1.36
          command: ["sh", "-c", "echo \"traitement $(date)\"; sleep 10; echo fin"]
YAML
$K -n lab wait --for=condition=Complete job/batch-job --timeout=300s
$K -n lab get pods -l job-name=batch-job

# 2. Le CronJob : toutes les cinq minutes, historique borné.
cat <<'YAML' | $K apply -f -
apiVersion: batch/v1
kind: CronJob
metadata:
  name: log-cleanup
  namespace: lab
spec:
  schedule: "*/5 * * * *"
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: cleanup
              image: busybox:1.36
              command: ["sh", "-c", "echo nettoyage; find /tmp -type f -mmin +60 -delete"]
YAML
$K -n lab get cronjob log-cleanup
echo "batch-job a réussi quatre fois, deux à la fois ; log-cleanup est planifié."
