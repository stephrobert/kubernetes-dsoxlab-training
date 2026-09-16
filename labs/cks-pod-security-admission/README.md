# Refuse a privileged Pod at admission, with Pod Security Admission

**CKS** lab, *Minimize Microservice Vulnerabilities* domain (20 % of the
exam), competency "Use appropriate pod security standards".

This is the control that replaced PodSecurityPolicy, removed in 1.25. It is
built into the API server: nothing to install, which makes it the first CKS
lab to write after AppArmor.

The last test is the only one that proves anything. Reading a namespace's
labels shows they are set, not that admission enforces them. So it submits two
real Pods to the API server, one forbidden and one compliant, as a
**server-side dry run**: the verdict is real, and nothing is written.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Pod Security Standards](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/pod-security-standards/) |

```bash
dsoxlab run   cks-pod-security-admission
dsoxlab check cks-pod-security-admission
```

The `laxiste` Pod, created by the setup before anything was switched on, keeps
running once the standard is in place. That is not an oversight: admission
acts on requests, never retroactively, and it is what candidates most often
discover on exam day.

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
