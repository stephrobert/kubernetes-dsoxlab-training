# Close the API server's profiler, without closing the API

**CKS** lab, *Cluster Hardening* domain (15 % of the exam), competency
"Restrict access to Kubernetes API".

Measured on 2026-09-16 on this catalogue's foundation: a kubeadm cluster out
of the box does return an HTML page on `/debug/pprof/`, and carries none of
the three hardening flags asked for. So the lab starts from a real state, not
an assumption.

The last test exercises **both halves** of the requirement: the profiler must
return an error, and `/version` must answer normally. An API server at a
standstill closes the profiler just as surely as a well-placed flag, and that
is hardening's most common contradiction.

One test explicitly refuses `--anonymous-auth=false`, which was not asked for:
the probes kubeadm writes into that same manifest query `/livez` and `/readyz`
**without authenticating**. The flag makes them fail, the kubelet kills the API
server in a loop, and the hardening breaks the cluster it was meant to
protect.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 25 minutes |
| Companion lesson | [CIS Benchmark](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/cis-benchmark/) |

```bash
dsoxlab run   cks-api-server-hardening
dsoxlab check cks-api-server-hardening
```

The setup backs up the original manifest to `/var/backups`, **never** to
`/etc/kubernetes/manifests`: the kubelet would launch the copy there as a
second static Pod, and two API servers would fight over the same port.

Ported from K8sExamLab on 2026-09-16, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
