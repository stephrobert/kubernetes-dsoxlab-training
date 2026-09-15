# A Job with parallel completions, and a CronJob

**CKAD** lab, *Application Design and Build* domain (20 % of the exam),
competency "Understand Jobs and CronJobs".

The inherited lab only read the Job spec. This one also reads the timestamps
of its Pods, to prove that two runs really were running at the same time.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Jobs and CronJobs](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/jobs-cronjobs/) |

```bash
dsoxlab run   ckad-job-cronjob
dsoxlab check ckad-job-cronjob
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
