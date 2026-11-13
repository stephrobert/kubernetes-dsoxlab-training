# Give an application its own identity and the least rights

## The situation

The operations team installed two tools in the **`observatoire`** namespace of
the kubeadm cluster:

- **`collecte`** must read the **logs of the Pods** of the **`production`**
  namespace, to extract incidents from them. The production Pod to watch is
  named **`commandes`**.
- **`tableau`** serves a static page and **never calls the API**.

Both run today under the **default account** of `observatoire`. To "make it
work", someone gave that account broad rights in the namespace, and `collecte`
still does not read the logs of `production`.

You are on the control plane, with `kubectl` configured. No procedure is given:
the module taught you what you need.

## What you must achieve

1. **`collecte`** runs under **its own identity**, named **`collecte`**, not
   under the default account.
2. From the Pod of `collecte`, **with its own token**, reading the **log of the
   Pod `commandes`** of `production` succeeds.
3. **That is all**: the `collecte` identity has **no other right, anywhere**.
   It cannot create, change or delete anything in `production`, read its
   Secrets, look at another namespace, logs included, or hold any right on
   the cluster.
4. The running Pod of **`tableau`** carries **no token**: nothing is mounted in
   `/var/run/secrets/kubernetes.io/serviceaccount`.
5. The **default account** of `observatoire` keeps **no right**, in the
   namespace or elsewhere, beyond what Kubernetes gives every account: asking
   about its own rights.
6. The Pod of **`collecte`** is **hardened**: it runs **non-root under a numeric
   UID**, cannot **escalate its privileges**, has a **read-only root
   filesystem** and has dropped **all its capabilities**. Hardened, it still
   reads the logs of `production`.

## How you will be graded

Six states, equally weighted. The pass mark is **70 out of 100**, and states
**2 and 3** are **blocking**: reading the logs of `production`, and nothing
more. Passing the others does not make up for missing one of them.

The tests enter the Pod of `collecte` and query the API with its token, then
have the API compute each identity's effective rights: the
application, not the administrator, must hold these rights. The feedback is
limited to the verdict: passed or not, and the score.

```bash
dsoxlab check  k8s-challenge-identite-et-droits-minimaux
dsoxlab submit k8s-challenge-identite-et-droits-minimaux
```
