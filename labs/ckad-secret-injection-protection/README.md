# Move a password out of a manifest, without the application noticing

**CKAD** lab, *Application Environment, Configuration and Security* domain
(25 % of the exam), Secrets.

Distinct from [`ckad-configmap-secret-injection`](../ckad-configmap-secret-injection/),
which covers injection from a ConfigMap. This one covers what the Secret really
changes: **the value leaves the manifest**, and the application sees no
difference.

**Nine tests, one per state the statement asks for**, each weighing the same
ninth of the mark. Two of them carry the point of the lab:

| test | what it closes |
|---|---|
| it reads the Secret's `.data` and decodes it | the Secret is no longer a mere formality whose content nobody reads |
| it sweeps the namespace's ConfigMaps for the value | the value moved into a ConfigMap leaves the manifest and protects nothing |

Without those two, the password written in clear text in a ConfigMap and
injected from there scored full marks, which is the exact opposite of what the
lab teaches. Taking a value out of a manifest is worth nothing by itself: what
counts is the object it lands in.

Neither half of the pair "it left the manifest" and "the container sees it"
proves anything alone, and that is still true: the first is green if the
candidate deletes the variable and breaks the application, and the second was
already true BEFORE the work, since the variable already carried the right
value, taken from the manifest. Both are therefore required, as separate tests,
so an incomplete piece of work is told which state is missing rather than only
the first failure.

And since a half that is already true at the start measures nothing, **every
test now demands the arrival state**. Three of them passed before any work,
measured on 2026-11-10: the ConfigMap sweep, because an absence is true before
you begin; "a Pod is running", because the setup already runs one; and
`DB_PASSWORD` inside the container, for the reason above. The first is now
conditioned on the value being held by a Secret, the other two read the running
Pod and demand the Secret projection and the variable's origin there.

The lab asks for **both** injection paths, because they are not equivalent: an
environment variable is frozen for the life of the process, a mounted file is
refreshed when the Secret changes. That is why an application reloading its
configuration reads a file rather than a variable.

| | |
|---|---|
| Target | `k8s-cp.lab`, control plane of the vanilla kubeadm cluster |
| Duration | about 20 minutes |
| Companion lesson | [Secrets](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/secrets/) |

```bash
dsoxlab run   ckad-secret-injection-protection
dsoxlab check ckad-secret-injection-protection
```
