# Sign an image, and prove the signature by having another one refused

**CKS** lab, *Supply Chain Security* domain (20 % of the exam), competency
"Verify platform binaries before deploying" applied to images.

The registry is **local**, run by the setup in `hostNetwork` on the node's
port 5000. That is not a shortcut: signing means **pushing** the signature
next to the image, in the same repository, and no public registry would allow
that write without credentials. A lab requiring a Docker Hub account would be
playable by nobody.

The last test takes the public key from the ConfigMap, as a third party would,
and uses it on **both** images. It is the refusal of the unsigned image that
gives value to the acceptance of the other: a verification that accepts
everything looks like a chain that works.

Measured on 2026-09-16, and **cosign 3.x holds two version traps**.

The first: `--tlog-upload=false` is no longer accepted and points to a
`--signing-config`. Signing against a local registry works without disabling
anything, and that is the path this lab takes.

The second is more misleading, because every article on the subject still says
otherwise: the signature tag is **no longer suffixed `.sig`**. The repository
carries plain `sha256-<digest>`. A first version of the test looked for
`.sig`, found nothing, and declared no signature had been pushed when it was
right there.

cosign 3.1.3 and crane 0.22.1 are installed by **mise**, from
`shared/outil-par-mise.yml`.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 30 minutes |
| Companion lesson | [Supply Chain Security](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/supply-chain-security/) |

```bash
dsoxlab run   cks-cosign-verify-image
dsoxlab check cks-cosign-verify-image
```

The `cleanup.yaml` removes the keys from the node: a private key left on a
shared machine is exactly what this domain teaches you not to do.

Ported from K8sExamLab on 2026-09-16, then validated by
`scripts/valider-labs.py`: 0 before the work, 100 after the trainer's
solution, replayable and leaving no trace.
