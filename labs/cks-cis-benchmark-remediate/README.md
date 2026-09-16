# Bring down a CIS audit's count, and prove it with a second audit

**CKS** lab, *Cluster Setup* domain (15 % of the exam), competency "Use CIS
benchmark to review the security configuration of Kubernetes components".

Measured on 2026-09-16 on this catalogue's foundation: kube-bench fails **ten
checks** on a kubeadm cluster out of the box, three of which share one cause
across three different components.

The inherited lab asked for findings to be recorded in a free-text ConfigMap.
Here the last test **reruns the tool** and counts: a report can be edited, an
audit running before our eyes cannot. It also requires the total failure count
to have gone down, which a check-by-check look would miss: a fix that breaks
another leaves the count unchanged.

**kube-bench is not in mise**, unlike trivy and cosign. It does not need to
be: it runs as a Job INSIDE the cluster, with the node's directories mounted
read-only, which is also how it is used in production.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 30 minutes |
| Companion lesson | [CIS Benchmark](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/cis-benchmark/) |

```bash
dsoxlab run   cks-cis-benchmark-remediate
dsoxlab check cks-cis-benchmark-remediate
```

The setup backs up the **three** control plane manifests under `/var/backups`,
and the cleanup restores them: they are node files, which the validator does
not photograph, and leaving them modified would make the next run's first test
pass before any work.

Ported from K8sExamLab on 2026-09-16, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
