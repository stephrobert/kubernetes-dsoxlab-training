# Pin an image by its digest, and prove the tag was not enough

**CKS** lab, *Supply Chain Security* domain (20 % of the exam). That domain is
a fifth of the exam and had no lab in the catalogue.

The lab inherited from K8sExamLab stopped at looking for `@sha256:` in the
`image` field. That is a check on **shape**: a string of the right form,
copied from another image, went through. Here the last test compares the
declared digest with `status.containerStatuses[].imageID`, which the kubelet
writes once the runtime has resolved the image. That is what runs, not what
was asked for.

The inherited lab also assumed `docker inspect`. This cluster runs containerd
and has no docker: the hints point to `crictl`.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 15 minutes |
| Companion lesson | [Supply Chain Security](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/supply-chain-security/) |

```bash
dsoxlab run   cks-image-pinned-digest
dsoxlab check cks-image-pinned-digest
```

Ported from K8sExamLab on 2026-09-15, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
