# Challenge: Ship an application with Helm and GitOps, from a built image

## 📍 The situation

The shop team hands you two deliveries on the kind cluster `lab`.

The first one is the **vitrine** (the storefront). Its code is in
**`~/livraison/app`**, with its Dockerfile, and its Helm chart in
**`~/livraison/chart-vitrine`**. Read the `values.yaml` of the chart: it says
everything that can be set.

The second one is the **catalogue**. Its manifests live in a Git repository,
and the team wants the cluster to follow that repository on its own. Argo CD
is installed in the `argocd` namespace, and it already has access to the
repository. Your working clone is in **`~/livraison/catalogue`**.

What the environment provides:

- an **image registry** in the cluster, the `registre` Service of the
  `registre` namespace. The cluster pulls its images from
  **`localhost:30500`**. From the VM, you push to it after opening a tunnel:
  `kubectl -n registre port-forward svc/registre 30500:5000`;
- the **Git repository** of the catalogue, which the cluster reaches at
  **`ssh://git@172.18.0.1/srv/git/catalogue.git`**;
- `docker`, `helm` and `kubectl` on the VM. Argo CD has no CLI there:
  `kubectl` is enough to drive it.

## 🎯 What you must achieve

1. The vitrine image is built from `~/livraison/app` and pushed to the
   registry as **`localhost:30500/vitrine:1.0`**.

2. The Helm release **`vitrine`** of the chart `~/livraison/chart-vitrine` is
   installed in the **`vitrine`** namespace, from a values file you write in
   **`~/livraison/values-vitrine.yaml`**. This file asks for **2 copies** and
   the image you built. It stays as it was when it served the installation.

3. The vitrine runs the built image, **pinned by its digest**, and both copies
   are ready. **Blocking requirement.**

4. The release is then **upgraded to 3 copies** (revision 2), then **brought
   back to revision 1**.

5. An Argo CD Application **`catalogue`**, in the `argocd` namespace, follows
   the catalogue repository (folder **`catalogue`**) and deploys into the
   **`catalogue`** namespace, with **automated sync**. It is **Synced** and
   **Healthy** on the **last commit** of the repository. **Blocking
   requirement.**

6. The catalogue goes to **2 copies**, through a commit **pushed** to the
   repository, never through a command on the cluster. Argo CD has applied it.
   It reads the repository again about every three minutes.

## ✅ How you will know it works

The tests query the registry and the page served by the vitrine, read the
release history and its values revision by revision, and read the state of the
Argo CD Application to compare it with the last commit of the repository. The
content of `~/livraison/app` carries a mark drawn at random during the
preparation: the running image must come from it.

Six requirements, equal weight. The pass mark is 70%, and both blocking
requirements must hold. The feedback is limited to the list of unmet criteria
and the score.

```bash
dsoxlab check k8s-challenge-livrer-avec-helm-et-gitops
```
