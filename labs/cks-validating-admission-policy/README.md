# Have the cluster itself refuse an unpinned image, with no webhook

**CKS** lab, *Supply Chain Security* domain (20 % of the exam), admission
control.

The neighbour [`cks-image-pinned-digest`](../cks-image-pinned-digest/) has you
**pin** an image. This one has you **refuse** the ones that are not: the
operator's move, which stops relying on everyone's discipline.

**ValidatingAdmissionPolicy is native** since 1.30 and stable since 1.32: no
component to install, unlike webhook-based solutions, whose failure blocks all
Pod creation while their `failurePolicy` is `Fail`. That is what makes this lab
playable in twenty lines of YAML.

**The test is an active proof both ways.** Re-reading the policy would prove
nothing, and three distinct mistakes each produce a perfectly valid object:

| mistake | effect |
|---|---|
| policy with no binding | acts on no request |
| `validationActions: [Warn]` | reports, and lets through |
| `exists` instead of `all` in CEL | lets through a Pod with one pinned container out of two |

Measured on 2026-09-17 on Kubernetes v1.37.0: the refusal carries the policy's
own message, `ValidatingAdmissionPolicy '<name>' with binding '<name>' denied
request: …`, and a digest-pinned image goes through right after.

The `cleanup.yaml` deletes the binding **then** the policy, both **cluster**
objects: left in place, they would refuse Pods in later labs. The Gateway API's
`safe-upgrades` ValidatingAdmissionPolicy, if present, is spared.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 30 minutes |
| Companion lesson | [ValidatingAdmissionPolicy](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/validating-admission-policy/) |

```bash
dsoxlab run   cks-validating-admission-policy
dsoxlab check cks-validating-admission-policy
```
