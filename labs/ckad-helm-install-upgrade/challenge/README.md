# Challenge: Install, upgrade and roll back with Helm 4

## 📍 The situation

The team ships its web application as a **Helm chart**, in the
**`~/charts/web`** directory of the control plane. Helm 4 is installed. The
**`lab`** namespace exists, and is empty.

You are asked to run the full cycle of a release, the one operations will go
through every week: install, scale up, then roll back when the scale-up causes
trouble.

## 🎯 What you must obtain

1. A release **`web`** in `lab`, installed from `~/charts/web`, with **one**
   replica.
2. The release **upgraded** to **two** replicas.
3. The release **back on its first revision**: one replica, and a history that
   shows the three revisions: install, upgrade, rollback.
4. The application **runs** and **answers**: the Deployment is ready, and its
   Service serves the nginx page.

## 🧭 Useful landmarks

A Helm release keeps its history in the cluster. Every `install`, `upgrade` or
`rollback` creates a revision, and `helm history` lists them with their
description. A rollback does not delete the revision it undoes: it creates a
new one.

The number of replicas of this chart is a **value**, in its `values.yaml`, and
can be changed on the command line.

## ✅ How you will know it works

The tests read the history of the release, the values of each revision, the
state of the Deployment, and query the Service.

```bash
dsoxlab check ckad-helm-install-upgrade
```
