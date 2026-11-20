# Challenge: Inspect a failed Helm release and restore it

## 📍 The situation

In the **`helm-demo`** namespace, the **`vitrine`** release deploys the
**podinfo** chart. It went through several upgrades, and the last ones
failed. The `podinfo` chart repository is already declared for you
(`helm repo list`).

You are on the control plane, with `kubectl` and `helm` 4.3.2. Your answers
go into **`~/vitrine`**.

## 🎯 What you must obtain

1. **`~/vitrine/derniere-version.txt`** holds, on one line, the **latest
   version of the 6.14 series** of the podinfo chart published in the
   repository.
2. **`~/vitrine/revisions-en-echec.txt`** holds the **numbers of every
   revision** of `vitrine` that failed, separated by spaces.
3. The release is **back on the last healthy revision**: its last revision is
   a deployed rollback to it, and the application is available.
4. The **chart tests** succeeded on the current, deployed revision.

## 🧭 Useful landmarks

`helm search repo` searches the declared repositories, and gives by default
the latest version of all. `helm status` and `helm get` describe a release.
`helm history` lists its revisions, with their status. A rollback deletes no
revision: it creates a new one, a copy of the target revision, and without a
number it targets the previous revision. `helm test` runs the tests a chart
holds, and their result stays attached to the revision.

## ✅ How you will know it is right

The tests run `helm search repo` and `helm history` themselves, compare them
with your files, then read the history and the status of the release.

```bash
dsoxlab check k8s-inspecter-et-restaurer-une-release-helm
```
