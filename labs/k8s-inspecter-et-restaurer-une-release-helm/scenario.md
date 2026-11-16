# Inspect a failed Helm release and restore it

## The situation

In the namespace **`helm-demo`**, the release **`vitrine`** deploys the
**podinfo** chart. It ran fine until its last upgrade, which failed. The
`podinfo` chart repository is already declared for you (`helm repo list`).

You are on the control plane, with `kubectl` and `helm` 4.3.2. Your answers
go into **`~/vitrine`**.

## What you must achieve

1. **`~/vitrine/derniere-version.txt`** holds, on one line, the **latest
   version of the podinfo chart** published in the repository.
2. **`~/vitrine/revision-en-echec.txt`** holds the **number of the revision**
   of `vitrine` that failed.
3. The release is **back on the last healthy revision**: its last revision is
   a deployed rollback, and the application is available.
4. The **chart's tests** succeeded on the current revision.

## Landmarks

`helm search repo` searches the declared repositories. `helm status` and
`helm get` describe a release; `helm history` lists its revisions with their
status. A rollback deletes no revision: it creates a new one, a copy of the
target revision. `helm test` runs the tests a chart ships, and their result
stays attached to the revision.

## How you will know it works

The tests run `helm search repo` and `helm history` themselves, compare with
your files, then read the history and the status of the release.

```bash
dsoxlab check k8s-inspecter-et-restaurer-une-release-helm
```
