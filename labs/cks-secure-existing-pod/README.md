# Take back a privileged Pod in production, without stopping its work

**CKS** lab, *Minimize Microservice Vulnerabilities* domain (20 % of the
exam), competency "Use appropriate pod security standards", remediation side.

The catalogue already has `ckad-security-context-hardened`, which teaches how
to **build** a hardened Pod. This one starts from an **existing** privileged
Pod, running, that nobody has flagged. Taking back what exists is the CKS
gesture, and it is the harder one: you must find what is wrong before fixing
it, and the scenario does not say how many defects there are.

The last test does not read `hostPID: false` from a spec, which would only be
an absence: it **counts** the processes the container can see. With the host
namespace, it enumerates the kubelet, containerd and every container on the
node, and can signal them.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 20 minutes |
| Companion lesson | [Security Context](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/security-context/) |

```bash
dsoxlab run   cks-secure-existing-pod
dsoxlab check cks-secure-existing-pod
```

Ported from K8sExamLab on 2026-09-16, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
