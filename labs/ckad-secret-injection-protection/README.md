# Move a password out of a manifest, without the application noticing

**CKAD** lab, *Application Environment, Configuration and Security* domain
(25 % of the exam), Secrets.

Distinct from [`ckad-configmap-secret-injection`](../ckad-configmap-secret-injection/),
which covers injection from a ConfigMap. This one covers what the Secret really
changes: **the value leaves the manifest**, and the application sees no
difference.

The final test exercises both sides in the **same** test, deliberately.
Separated, these two halves would measure nothing useful:

| isolated half | why it is worthless alone |
|---|---|
| "the value is no longer in the manifest" | green if the candidate deletes the variable and breaks the app |
| "the container sees the value" | already true BEFORE the work, the manifest hands it over in the clear |

The lab asks for **both** injection paths, because they are not equivalent: an
environment variable is frozen for the life of the process, a mounted file is
refreshed when the Secret changes. That is why an application reloading its
configuration reads a file rather than a variable.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 20 minutes |
| Companion lesson | [Secrets](https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/secrets/) |

```bash
dsoxlab run   ckad-secret-injection-protection
dsoxlab check ckad-secret-injection-protection
```
