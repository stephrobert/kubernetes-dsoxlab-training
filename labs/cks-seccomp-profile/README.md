# Forbid one system call to a container, and prove it from the inside

**CKS** lab, *System Hardening* domain (10 % of the exam), competency
"Minimize host OS footprint (reduce attack surface)".

It is the twin of `cks-apparmor-confiner-un-pod`, and follows the same rule of
this repository: checking that a profile is loaded and that a Pod declares it
**does not prove** the confinement works, an empty profile would pass. So the
last test exercises both sides, inside the container: `chmod` must fail with
`EPERM`, and creating a file must still work.

A fourth test queries the witness Pod, which declares no profile: that is what
tells a filter applied to the right Pod from a blanket hardening of the node,
which would answer beside the point and break everything running on it.

The profile lives on the **node**, not in the cluster: same reason for the VMs
as with AppArmor.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 25 minutes |
| Companion lesson | [AppArmor and Seccomp](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/apparmor/) |

```bash
dsoxlab run   cks-seccomp-profile
dsoxlab check cks-seccomp-profile
```

The `cleanup.yaml` removes the profile from the node's disk. Without that, the
next run would find a profile already in place and the first test would pass
before any work, without the validator noticing: it photographs the cluster,
not the disk.

Ported from K8sExamLab on 2026-09-16, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
