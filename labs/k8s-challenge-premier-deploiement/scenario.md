# Ship the storefront and bring the stock service back

## The situation

The shop runs on a kind cluster named **`boutique`**. You were handed its
kubeconfig, copied to **`~/.kube/boutique.yaml`**, and your `kubectl` already
knows it. But someone left it pointing at an old cluster.

In the **`catalogue`** namespace, the **`stock`** service does not start. Its
manifest is in **`~/boutique/stock.yaml`**. The storefront still has to be
shipped.

The shop's reference image is:

```text
nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

## What you must achieve

1. Your active `kubectl` context points at the shop cluster, and its default
   namespace is **`vitrine`**.

2. A **`vitrine`** Deployment, in the `vitrine` namespace, with **three
   available replicas** on the reference image.

3. A **`vitrine`** Service that selects those three Pods.

4. The storefront **answers** HTTP at `http://vitrine.vitrine` from a Pod of
   the cluster. *Blocking requirement.*

5. A file **`~/boutique/cause-stock.txt`** that names why `stock` does not
   start and the faulty image, **written before any repair**.

6. `stock` runs on the reference image, **fixed in `~/boutique/stock.yaml`**
   and applied from that file.

7. **`~/.kube/boutique.yaml`** is readable by you only. *Blocking
   requirement.*

## How you are graded

The challenge is graded on the **final state** of the cluster and of the
files, never on the commands typed. The pass mark is 70 out of 100, and both
blocking requirements must succeed whatever the total. No step-by-step
instructions: the lessons of the Fundamentals module taught everything.

`dsoxlab check` shows the requirements still failing; `dsoxlab submit` gives the verdict of the challenge, and it is the one that applies the pass mark and the blocking requirements.

```bash
dsoxlab check  k8s-challenge-premier-deploiement
dsoxlab submit k8s-challenge-premier-deploiement
```
