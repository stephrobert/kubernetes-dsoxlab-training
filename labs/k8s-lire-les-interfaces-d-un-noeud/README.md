# Read the CRI, CNI and CSI interfaces of a node

The lesson presents the three interfaces through which the kubelet hands off
its work: CRI for the container runtime, CNI for the Pod network, CSI for
storage. This course has you touch what lies behind these interfaces, on the
node, and adds cases the lesson does not show: a container stopped without
going through the API, the same container seen by containerd, the network
namespace the CNI prepared, and the agreement between the kubelet and
containerd on cgroups.

You work in a scratch namespace, `essai-cri`, with a `cobaye` ("guinea pig")
Pod placed on the control plane. The challenge is about other questions: you
will do it on your own, at the end.

Related page: [CNI, CSI and CRI](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/cni-csi-cri/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-lire-les-interfaces-d-un-noeud
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it. The runtime tools,
`crictl` and `ctr`, need `sudo`.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

Create the namespace and an nginx Pod on this node, so you can watch it up
close:

```bash
kubectl create namespace essai-cri; kubectl run cobaye --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb -n essai-cri --overrides='{"spec":{"nodeName":"k8s-cp.lab"}}'; kubectl wait --for=condition=Ready pod/cobaye -n essai-cri --timeout=120s
```

```text
namespace/essai-cri created
pod/cobaye created
pod/cobaye condition met
```

## 🛑 Exercise 1: stop a container without going through the API

`crictl` talks to the runtime through the CRI interface, like the kubelet.
Find the Pod's container:

```bash
sudo crictl ps --name cobaye -o json | python3 -c 'import json,sys; c=json.load(sys.stdin)["containers"][0]; print(c["id"][:13], c["state"])'
```

```text
1a5f03e39416f CONTAINER_RUNNING
```

Stop it directly, without asking the API anything, wait 15 seconds, and look
at the Pod (`redémarrages` means "restarts", `dernier arrêt` "last stop"):

```bash
C=$(sudo crictl ps --name cobaye -q | head -1); sudo crictl stop $C >/dev/null; sleep 15; kubectl get pod cobaye -n essai-cri -o jsonpath='redémarrages={.status.containerStatuses[0].restartCount} dernier arrêt={.status.containerStatuses[0].lastState.terminated.reason}{"\n"}'
```

```text
redémarrages=1 dernier arrêt=Error
```

The kubelet saw the stopped container and restarted it: one restart, with
`Error` as the reason for the last stop. The API remains the source of truth.
Whatever you change by hand on the node, the kubelet brings back to what the
API asks for.

## 📦 Exercise 2: the same container seen by containerd

`ctr` is containerd's own tool, below the CRI interface. containerd stores its
objects in namespaces, which have nothing to do with Kubernetes ones:

```bash
sudo ctr namespaces list
```

```text
NAME   LABELS 
k8s.io        
```

Kubernetes uses the `k8s.io` namespace. Look for `cobaye`'s container there,
then look at the `default` namespace (`espace default` means "default
namespace"):

```bash
C=$(sudo crictl ps --name cobaye -q | head -1); sudo ctr -n k8s.io containers list | grep ${C:0:12} | cut -c1-120; echo "--- espace default :"; sudo ctr -n default containers list
```

```text
aa6998223b7e400850d6898929ea2bf767100345905b31e9d2492ae6ef4ffe62    docker.io/library/nginx@sha256:9bf97bd7714f5e24c1ccd
--- espace default :
CONTAINER    IMAGE    RUNTIME    
```

The container is in `k8s.io`, with its full identifier and the pinned image.
`default` is empty. A `ctr containers list` without `-n k8s.io` therefore
shows none of Kubernetes' containers, and wrongly suggests the node is empty.

## 🌐 Exercise 3: enter the Pod's network namespace

The CNI prepares a kernel network namespace for each Pod. Read its path in the
runtime's description of the Pod:

```bash
P=$(sudo crictl pods --name cobaye -q | head -1); sudo crictl inspectp $P | python3 -c 'import json,sys; d=json.load(sys.stdin); print([n["path"] for n in d["info"]["runtimeSpec"]["linux"]["namespaces"] if n["type"]=="network"])'
```

```text
['/var/run/netns/cni-d4842914-f343-e68d-eb7d-683afeb59948']
```

Enter that namespace with `nsenter`, list its interfaces, and compare with the
address the API announces (`IP annoncée` means "announced IP"):

```bash
P=$(sudo crictl pods --name cobaye -q | head -1); NS=$(sudo crictl inspectp $P | python3 -c 'import json,sys; d=json.load(sys.stdin); print([n["path"] for n in d["info"]["runtimeSpec"]["linux"]["namespaces"] if n["type"]=="network"][0])'); sudo nsenter --net=$NS ip -br addr; kubectl get pod cobaye -n essai-cri -o jsonpath='IP annoncée : {.status.podIP}{"\n"}'
```

```text
lo               UNKNOWN        127.0.0.1/8 ::1/128 
eth0@if242       UP             10.244.163.39/32 fe80::681f:deff:fe64:5e8a/64 
IP annoncée : 10.244.163.39
```

The `eth0` interface carries the address announced by the API, and its other
end is the node's interface number 242 (`@if242`). The CNI (here Calico)
created this pair and set the address. `nsenter` lets you troubleshoot a Pod's
network even when its image has no tools at all.

## ⚙️ Exercise 4: kubelet and containerd agree on cgroups

The kubelet and the runtime must manage cgroups (the kernel's resource limits)
the same way. Read each one's setting:

```bash
sudo grep -E '^cgroupDriver' /var/lib/kubelet/config.yaml; sudo grep -n 'SystemdCgroup' /etc/containerd/config.toml
```

```text
cgroupDriver: systemd
109:            SystemdCgroup = true
```

Both use systemd. A disagreement between the two brings the kubelet down or
restarts Pods for no visible reason. It is one of the first checks on a node
that does not become Ready.

## 🧹 Clean-up

Delete the scratch namespace:

```bash
kubectl delete namespace essai-cri
```

```text
namespace "essai-cri" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-lire-les-interfaces-d-un-noeud
dsoxlab check k8s-lire-les-interfaces-d-un-noeud
```

```text
╭─ Result: k8s-lire-les-interfaces-d-un-noeud ─╮
│  0 / 100 pts                                 │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests             │
╰──────────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: record what the node uses for each of the
three interfaces, and write it to an answers file.

```bash
dsoxlab run k8s-lire-les-interfaces-d-un-noeud
dsoxlab challenge k8s-lire-les-interfaces-d-un-noeud
```
