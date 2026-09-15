# Restore the cluster's DNS resolution

**CKA** lab, *Troubleshooting* domain (30 % of the exam, the heaviest of the
three exams), competencies "Troubleshoot cluster components" and
"Troubleshoot services and networking".

Broken DNS is the classic exam question: there is nothing wrong with the
application, and it is a cluster component that has to be found and put back
in service.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 10 minutes |
| Companion lesson | [CoreDNS](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/coredns/) |

```bash
dsoxlab run   cka-troubleshoot-dns
dsoxlab check cka-troubleshoot-dns
```

Ported from K8sExamLab on 2026-09-14, then played: 0 before the work,
100 after the trainer's solution.
