# Challenge: Read the state of a failing Pod

## 📍 The situation

In the **`diagnostic`** namespace of the kind cluster `lab`, three
applications were started. **`web`** works. **`api`** and **`batch`** do not
start.

Before fixing anything, the team wants to know **why**, with evidence read in
the cluster. A blind fix would erase the failure you needed to understand.

Your kubectl already targets this cluster. The **`~/diagnostic`** directory
exists and is empty.

## 🎯 What you must obtain

1. A **`~/diagnostic/api.txt`** file that gives the **reason** why the `api`
   container is waiting, and the **image** at fault.

2. A **`~/diagnostic/batch.txt`** file that copies the **error message**
   written by `batch` before it stopped, and the **exit code** of its last
   stop, written as `exit code: N`.

3. A **`~/diagnostic/top.txt`** file that gives the name of the namespace's
   **Pod** that uses the most **memory**.

4. **Nothing is fixed**: `api` and `batch` keep their starting image and
   command.

## 🧭 Useful landmarks

A Pod's status says it is failing, not why. For the reason, read the
container's state and the events with `kubectl describe`. For what the program
wrote, read its logs with `kubectl logs`. If the container restarted, the
useful message is often in the **previous** run (`--previous`).

`kubectl top` measures memory. metrics-server is already installed. A Pod that
does not run has no measurement.

## ✅ How you will know it works

The tests compare your three files with what the cluster says: the reason for
the wait, the real exit code, the memory measured at check time. They also
check that both Deployments were not changed.

```bash
dsoxlab check k8s-lire-l-etat-d-un-pod-en-erreur
```
