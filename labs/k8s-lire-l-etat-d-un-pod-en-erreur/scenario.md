# Read the state of a failing Pod

## The situation

In the **`diagnostic`** namespace of the `lab` kind cluster, three applications
were started. **`web`** answers. **`api`** and **`batch`** do not start.
Before fixing anything, the team wants to know **why**, with evidence read
from the cluster: a blind fix erases the failure you had to understand.

Your `kubectl` already points at this cluster. The **`~/diagnostic`**
directory exists and is empty.

## What you must achieve

1. A file **`~/diagnostic/api.txt`** that names the **reason** the `api`
   container is waiting, and the faulty **image**.

2. A file **`~/diagnostic/batch.txt`** that quotes the **error** `batch` wrote
   before stopping, and the **exit code** of its last terminated container,
   written as `exit code: N`.

3. A file **`~/diagnostic/top.txt`** that names the **Pod** of the namespace
   that uses the most **memory**.

4. **Nothing is repaired**: `api` and `batch` keep their original image and
   command.

## Useful landmarks

A status is not enough: it says a Pod is unwell, not why. The detailed state
of a container, its reason and the Pod events say what blocks; the logs say
what the program wrote before stopping. When a container has been restarted,
the useful logs are often those of the **previous** run.

Resource usage comes from metrics-server, already installed. A Pod that is not
running has no measurement.

## How you will know it works

The tests compare your three files with what the cluster says itself: waiting
reason, actual exit code, memory measured at check time. They also check that
the two Deployments were not modified.

```bash
dsoxlab check k8s-lire-l-etat-d-un-pod-en-erreur
```
