# Run one-off and scheduled tasks with Jobs and CronJobs

Challenge of the Kubernetes training, in the Put it into practice section of
the "Jobs and CronJobs" lesson: an indexed Job whose number of completions
depends on the cluster, a CronJob with an imposed schedule and time zone, a
run started by hand, and a failed Job to repair. Five requirements, pass mark
80%, two of them blocking.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the kubeadm cluster; the lab sets up the `compta` namespace |
| Duration | about 40 minutes |
| Related page | [Jobs and CronJobs, Put it into practice section](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/jobs-and-cronjobs/#put-it-into-practice) |

```bash
dsoxlab run    k8s-challenge-executer-et-planifier-des-taches
dsoxlab check  k8s-challenge-executer-et-planifier-des-taches
dsoxlab submit k8s-challenge-executer-et-planifier-des-taches
```
