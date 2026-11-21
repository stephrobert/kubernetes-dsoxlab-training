# Upgrade a cluster one minor version, without interrupting what runs on it

The lesson shows how to upgrade a kubeadm cluster, node by node. Here, the
upgrade is the challenge: this course upgrades nothing. It prepares the
upgrade and measures what it would do, with cases the lesson does not show:
the versions the repository offers, what the plan says when kubeadm lags
behind, what would change in the manifests, and a dry-run upgrade.

Related page: [Upgrade a Kubernetes cluster without downtime](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/upgrade-a-kubernetes-cluster/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-kubeadm-upgrade
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it. The lab's preparation
set up a v1.36 cluster: that is the one you will upgrade in the challenge.

The outputs shown in this course were recorded on this machine on 21 November
2026.

## 🔢 Exercise 1: the versions in place

Read the API server's version, each kubelet's, then the ones the package
repository offers (`NOEUD` means "node"):

```bash
kubectl version 2>/dev/null | grep -E 'Server|Client'; kubectl get nodes -o custom-columns=NOEUD:.metadata.name,KUBELET:.status.nodeInfo.kubeletVersion
```

```text
Client Version: v1.36.4
Server Version: v1.36.6
NOEUD        KUBELET
k8s-cp.lab   v1.36.4
k8s-w1.lab   v1.36.4
```

The API server is at v1.36.6, the kubelets at v1.36.4: a kubelet may lag a few
versions behind the API server, never be ahead of it.

```bash
apt-cache madison kubeadm | head -4; apt-mark showhold
```

```text
   kubeadm | 1.37.2-1.1 | https://pkgs.k8s.io/core:/stable:/v1.37/deb  Packages
   kubeadm | 1.37.1-1.1 | https://pkgs.k8s.io/core:/stable:/v1.37/deb  Packages
   kubeadm | 1.37.0-1.1 | https://pkgs.k8s.io/core:/stable:/v1.37/deb  Packages
   kubeadm | 1.36.6-1.1 | https://pkgs.k8s.io/core:/stable:/v1.36/deb  Packages
kubeadm
kubectl
kubelet
```

The repository offers several versions of the v1.37 series. The three packages
are **held** (`apt-mark hold`): an ordinary `apt upgrade` will not upgrade them
by accident. They have to be released, one by one, when the time comes.

## 🗺️ Exercise 2: what the plan says

`kubeadm upgrade plan` tells which version the cluster can move to:

```bash
sudo kubeadm upgrade plan 2>&1 | grep -E 'upgrade/versions|falling back'
```

```text
[upgrade/versions] Cluster version: 1.36.6
[upgrade/versions] kubeadm version: v1.36.4
I1121 10:38:54.539512   23758 version.go:260] remote version is much newer: v1.37.2; falling back to: stable-1.36
[upgrade/versions] Target version: v1.36.6
[upgrade/versions] Latest version in the v1.36 series: v1.36.6
```

The plan does see v1.37.2, but it "falls back" to the v1.36 series: a kubeadm
only ever offers the latest version of its own series. For it to offer v1.37,
kubeadm itself must first be at v1.37.

## 🔍 Exercise 3: what the upgrade would change in the manifests

`kubeadm upgrade diff` shows, without applying anything, the changes the
upgrade would make to the control plane's static manifests (`version visée`
means "target version"):

```bash
V=$(apt-cache madison kubeadm | awk '{print $3}' | sort -V | tail -1 | cut -d- -f1); echo "version visée : v$V"; sudo kubeadm upgrade diff v$V 2>&1 | grep -E '^[-+] .*image:' | head -6
```

```text
version visée : v1.37.2
-    image: registry.k8s.io/kube-controller-manager:v1.36.6
+    image: registry.k8s.io/kube-controller-manager:v1.37.2
-    image: registry.k8s.io/kube-scheduler:v1.36.6
+    image: registry.k8s.io/kube-scheduler:v1.37.2
-    image: registry.k8s.io/kube-apiserver:v1.36.6
+    image: registry.k8s.io/kube-apiserver:v1.37.2
```

Every control plane component would change image. Nothing is written to disk.

## 🧪 Exercise 4: a dry-run upgrade

`--dry-run` goes through the upgrade without applying anything. Try it towards
the same version:

```bash
V=$(apt-cache madison kubeadm | awk '{print $3}' | sort -V | tail -1 | cut -d- -f1); sudo kubeadm upgrade apply v$V --dry-run --yes 2>&1 | grep -E 'Specified version|^error'
```

```text
error: error execution phase preflight: the version argument is invalid due to these fatal errors:
	- Specified version to upgrade to "v1.37.2" is at least one minor release higher than the kubeadm minor release (37 > 36). Such an upgrade is not supported
```

The preflight check refuses: kubeadm v1.36 cannot upgrade a cluster to v1.37.
It is the same rule as the plan, this time stated by an error. Check that
nothing moved (`rien n'a bougé` means "nothing moved"):

```bash
kubectl version 2>/dev/null | grep Server; echo "(rien n'a bougé)"
```

```text
Server Version: v1.36.6
(rien n'a bougé)
```

Still at v1.36.6. Each dry-run does leave a work directory under
`/etc/kubernetes/tmp/`, which kubeadm does not remove.

## 🧹 Clean-up

The course created no object. Leave the machine and reset the lab.
`dsoxlab reset` replays the lab's clean-up then its preparation: you get back
exactly the starting state of the challenge. It asks you to confirm: answer
`y`.

```bash
exit
dsoxlab reset cka-kubeadm-upgrade
dsoxlab check cka-kubeadm-upgrade
```

```text
╭─── Result: cka-kubeadm-upgrade ───╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/2 tests  │
╰───────────────────────────────────╯
```

0 out of 2: that is the expected result. The challenge is waiting for you, untouched.

## 🎯 The challenge

Your turn, on your own this time: upgrade the cluster one minor version, node
by node, without interrupting the application running on it.

```bash
dsoxlab run cka-kubeadm-upgrade
dsoxlab challenge cka-kubeadm-upgrade
```
