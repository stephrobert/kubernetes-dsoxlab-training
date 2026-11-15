# Install a kubeadm cluster, join a node and make the control plane highly available

## The situation

Two jobs are waiting for you.

On the kubeadm cluster, the worker **`k8s-w1.lab`** has been removed from the
cluster and reset: it is no longer a node, and its preparation has been
undone. The team wants it back in service, cleanly: a machine joined in a hurry
falls over at its first reboot.

At the same time, the team wants to see a **highly available** control plane
survive the loss of one of its members. With no three spare machines, it hands
you the host **`k8s-kind.lab`**, where Docker and kind are installed. You build
there a kind cluster named **`ha`**, with the catalogue's node image:

```text
kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5
```

You are on **`k8s-cp.lab`**, the control plane of the kubeadm cluster, with
`kubectl` configured and `sudo` rights. `ssh k8s-w1.lab` and
`ssh k8s-kind.lab` open a session on the two other machines, where you also
have `sudo`. No procedure is given: the module taught you what you need.

## What you must achieve

1. **`k8s-w1.lab`** is a node of the kubeadm cluster, **Ready**, and its
   **kubelet** reports a **1.37** version.
2. **Swap** is **off** on the worker, and **nothing will turn it back on** at
   the next boot.
3. **containerd** runs on the worker with the **systemd cgroup driver**.
4. A Pod named **`temoin`**, in the **`installation`** namespace, is **forced
   onto `k8s-w1.lab`** by the `nodeName` field of its spec, and it runs.
5. Cluster **`ha`** has **three control-plane nodes**, all **Ready**, read
   through the **address of the load balancer** that stands in front of their
   API servers.
6. **etcd** there has **three** voting, **healthy** members.
7. The **API** of `ha` still answers, **through the load balancer's address**,
   when one of its control planes is **down**.

## How you are graded

Seven states, equal weight. The threshold is **70 out of 100**, and states
**1 and 7** are **blocking**: the joined worker, and the API that survives the
loss of a control plane. Passing the others does not make up for missing one
of them.

For state 7, the grader **stops a control plane of `ha` itself** (it freezes
its container), queries `/readyz` through the load balancer, then **starts it
again**. Every check therefore acts on cluster `ha` for a good minute. The feedback is limited to the list of unmet criteria, by their label, and the score: no message says why.

```bash
dsoxlab check  k8s-challenge-installer-un-cluster
dsoxlab submit k8s-challenge-installer-un-cluster
```
