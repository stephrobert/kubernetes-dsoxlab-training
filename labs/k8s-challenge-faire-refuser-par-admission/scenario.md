# Enforce an admission rule and prove the refusal, without guidance

## The situation

The kubeadm cluster admits anything. The security team wants it to **refuse**
what breaks its rules, at creation time, rather than rely on everyone's
discipline. Setup has prepared four namespaces:

- **`vitrine`** applies no security standard. A shop front Pod named
  **`catalogue`** must run there, `busybox:1.37` running `sleep`.
- **`paiement`** runs **`caisse`**, a Pod that nobody reported and that
  accumulates flaws. It must be rebuilt cleanly under the name
  **`caisse-durcie`**, doing the same thing.
- **`production`** accepts any image, including one named by a plain tag. A
  **`conforme`** Pod already runs there, pinned by its digest: leave it alone.
- **`recette`** is a test namespace. Nothing is asked of it, and nothing must
  change for it.

You are on the control plane, with `kubectl` configured. No procedure is
given: the module taught you what you need.

## What you must achieve

1. **`vitrine`** declares the **restricted** standard in all three modes:
   **enforce**, **warn** and **audit**.
2. The Pod **`catalogue`** **runs** in `vitrine`.
3. `catalogue` meets the **four requirements** of the standard: it runs **non
   root**, cannot **escalate its privileges**, has **dropped its
   capabilities**, and declares a **seccomp profile**.
4. Admission in `vitrine` **refuses** a Pod that breaks the standard and
   **accepts** a compliant one.
5. **`caisse-durcie`** **runs** in `paiement`.
6. `caisse-durcie` keeps **none of the flaws** you find in `caisse`.
7. The original **`caisse`** Pod **no longer exists**.
8. The container of `caisse-durcie` **no longer sees the host's processes**
   and does not run as root.
9. A **native** admission policy, evaluated by the API server itself, is bound
   in **deny** mode, not only in warning.
10. In **`production`**, a Pod whose image is named by a **tag** is
    **refused**, a Pod whose image is **pinned by its digest** is **accepted**,
    and the **other namespaces**, `recette` first, are **not affected**.

## How you will be graded

Ten states, equally weighted. The pass mark is **70 out of 100**, and states
**4 and 10** are **blocking**: the two refusals proven by real submissions.
Passing the others does not make up for missing one of them.

The tests read the admitted Pods, enter the new Pod to count what it sees, and
submit real Pods: in `vitrine` without creating anything, in `production` and
`recette` by creating them and removing them at once. The feedback is limited
to the verdict: passed or not, and the score.

```bash
dsoxlab check  k8s-challenge-faire-refuser-par-admission
dsoxlab submit k8s-challenge-faire-refuser-par-admission
```
