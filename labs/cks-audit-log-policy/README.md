# Record who reads Secrets, and only the metadata of everything else

**CKS** lab, *Monitoring, Logging and Runtime Security* domain (20 % of the
exam). That domain is a fifth of the exam and had no lab.

This lab modifies the **kube-apiserver static manifest**, which a cluster in a
container does not let you do cleanly: it is one of the reasons this catalogue
runs on VMs.

The last test does not read the policy, it reads the **log the cluster has
just written**. A policy sitting on disk proves nothing: the file may be
malformed, the flags missing, the volumes unmounted, and the API server still
runs without writing a line. It also requires both levels: a policy recording
everything at `RequestResponse` would copy every Secret in clear into the log,
and fails here.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 25 minutes |
| Companion lesson | [Audit Logs](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/audit-logs/) |

```bash
dsoxlab run   cks-audit-log-policy
dsoxlab check cks-audit-log-policy
```

The setup backs up the original manifest to `/var/backups`, **never** to
`/etc/kubernetes/manifests`: the kubelet would launch the copy there as a
second static Pod, and two API servers would fight over the same port. The
cleanup restores from that backup, then waits for the API to answer.

Ported from K8sExamLab on 2026-09-16, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
