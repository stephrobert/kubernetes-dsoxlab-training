# Isolate a Pod from the host kernel, and prove it by reading its version

**CKS** lab, *Minimize Microservice Vulnerabilities* domain (20 % of the
exam), sandbox isolation.

**This lab lifts a negative attestation from the training.** The
`non_couvert` field of the `runtime-sandboxes` guide said "containerd only
declares runc": the competency could not be exercised anywhere. The setup
installs gVisor and declares it to containerd, making it measurable for the
first time.

The proof cannot be faked and hangs on no string of our choosing: the test
compares the kernel seen by the sandboxed Pod, the one seen by a witness Pod
launched with the default runtime, and the machine's. Measured on 2026-09-16:
the sandboxed Pod reads `Linux version 4.19.0-gvisor`, the node runs
`6.8.0-139-generic`.

**Three distribution traps**, all measured the same day:

- gVisor **no longer publishes its binaries separately**. The URL
  `.../latest/x86_64/containerd-shim-runsc-v1` returns 404, and only the
  `gvisor.tar.bz2` archive still carries the shim;
- **bzip2 is not installed** on a minimal Ubuntu 24.04: `tar` fails with
  "bzip2: Cannot exec";
- Ubuntu's APT `runsc` package dates from 2023 and **does not provide the
  shim**.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 25 minutes |
| Companion lesson | [Runtime Sandboxes](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/runtime-sandboxes/) |

```bash
dsoxlab run   cks-runtime-sandbox-gvisor
dsoxlab check cks-runtime-sandbox-gvisor
```

The `cleanup.yaml` removes the RuntimeClass, a cluster-scoped object that
would outlive the namespace.

Ported from K8sExamLab on 2026-09-16, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
