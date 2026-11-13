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
3. **That is all**: with that same token, `collecte` can neither **delete** a
   Pod of `production`, nor **read its Secrets**, nor look at **another
   namespace**, logs included.
4. The running Pod of **`tableau`** carries **no token**: nothing is mounted in
   `/var/run/secrets/kubernetes.io/serviceaccount`.
5. The **default account** of `observatoire` keeps **no right** to create,
   change or delete anything, nor to read the namespace's Secrets.
6. The Pod of **`collecte`** is **hardened**: it runs **non-root under a numeric
   UID**, cannot **escalate its privileges**, has a **read-only root
   filesystem** and has dropped **all its capabilities**. Hardened, it still
   reads the logs of `production`.

## How you will be graded

Six states, equally weighted. The pass mark is **70 out of 100**, and states
**2 and 3** are **blocking**: reading the logs of `production`, and nothing
more. Passing the others does not make up for missing one of them.

The tests enter the Pod of `collecte` and query the API with its token: the
application, not the administrator, must hold these rights. The feedback is
limited to the verdict: passed or not, and the score.

```bash
dsoxlab check  k8s-challenge-identite-et-droits-minimaux
dsoxlab submit k8s-challenge-identite-et-droits-minimaux
```
