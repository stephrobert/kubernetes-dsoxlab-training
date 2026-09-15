# Install, upgrade and roll back with Helm 4

## The situation

The team ships its web application as a **Helm chart**, in the
**`~/charts/web`** directory of the control plane. Helm is installed, in
version 4. The **`lab`** namespace exists, empty.

You are asked to run the full release cycle, the one operations will go through
every week: install, scale up, then roll back when the scale-up causes trouble.

## What you must achieve

1. A release **`web`** in `lab`, installed from `~/charts/web`, with **one**
   replica.

2. The release **upgraded** to **two** replicas.

3. The release **back on its first revision**: one replica, and a history
   showing the three revisions, install, upgrade, rollback.

4. The application **running** and **answering**: the Deployment is ready, and
   its Service serves the nginx page.

## Useful bearings

A Helm release keeps its history in the cluster: every `install`, `upgrade` or
`rollback` creates a revision, and `helm history` lists them with their
description. A rollback does not delete the revision it undoes: it creates a
new one.

The replica count of this chart is a **value**, in its `values.yaml`, and can
be changed on the command line.

## How you will know it works

The tests read the release history, the values of each revision, the state of
the Deployment, and query the Service.

```bash
dsoxlab check ckad-helm-install-upgrade
```
