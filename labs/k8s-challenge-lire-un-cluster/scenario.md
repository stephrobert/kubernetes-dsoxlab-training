# Read a cluster: which component does what

## The situation

A kind cluster named **`architecture`** runs four Nodes: one control plane and
three workers. Your `kubectl` already points at it.

In the **`architecture`** namespace, two objects were left for you: a Pod named
**`temoin`**, and a Deployment named **`file-attente`** whose Pods never start.

Everything you find goes into the survey **`~/architecture/releve.txt`**. Its
keys are already there: fill in the value after each colon, one value per
line.

## What you must achieve

1. **`noeud-control-plane`** holds the name of the Node that carries the
   control plane.

2. **`pod-apiserver`**, **`pod-etcd`**, **`pod-scheduler`** and
   **`pod-controller-manager`** hold the names of the Pods of the four control
   plane components, as found in `kube-system`; **`role-apiserver`**,
   **`role-etcd`**, **`role-scheduler`** and **`role-controller-manager`** say,
   in a few words of your own, what each one does.

3. One line **`runtime-<Node name>`** per worker Node, holding the container
   runtime of that Node and its version.

4. **`noeud-du-pod-temoin`** holds the Node that received the `temoin` Pod, and
   **`evenement-scheduled`** quotes the message of the event that proves it.

5. For `file-attente`, **`cree-par`** names the component that created its
   Pods, and **`n-agit-pas`** names the one component that does not act on
   them. Diagnose only: do not repair the Deployment.

## How you are graded

The challenge is graded by comparing your survey with the **live state** of
the cluster, never on the commands typed. Roles are checked on meaning, in
English or French: a role must describe the function of its own component, not
repeat its name. The pass mark is 70 out of 100. No step-by-step instructions:
the lessons of the Architecture module taught everything.

Leave the `temoin` Pod and the `file-attente` Deployment as they are.

Events are kept for **24 hours** on this cluster (one hour is the Kubernetes
default). After a longer break, those of the lab are gone: `dsoxlab reset k8s-challenge-lire-un-cluster`
lays the situation out again.

```bash
dsoxlab check  k8s-challenge-lire-un-cluster
dsoxlab submit k8s-challenge-lire-un-cluster
```
