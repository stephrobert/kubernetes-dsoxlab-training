# Initialise a control plane with kubeadm

The lesson shows `kubeadm init`, which creates a cluster's control plane from
a configuration file. The lab took the cluster and the node's preparation
apart: that is the challenge. This course therefore initialises nothing. It
uses the kubeadm commands that change nothing, and adds cases the lesson does
not show: validating a file before using it, a configuration that is too old,
the list of images an init will pull, and a dry-run init.

You work in a scratch directory, `~/essai-kubeadm`, with a fictitious
`essai-atelier` cluster and a `10.250.0.0/16` Pod network. The challenge is
about another file and another cluster: you will do it on your own, at the
end.

Related page: [Install Kubernetes with kubeadm](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/install-kubernetes-with-kubeadm/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-initialiser-un-plan-de-controle
```

You are now connected to `k8s-cp.lab`. There is no cluster any more: your
kubectl does not answer, and that is expected.

The outputs shown in this course were recorded on this machine on 21 November
2026, with kubeadm v1.37.2.

## ✔️ Exercise 1: validate a configuration before using it

Write a configuration with a typo, `serviceSubnett`, and have it checked by
`kubeadm config validate`. The command also prints kubeadm's version:

```bash
mkdir -p ~/essai-kubeadm; kubeadm version -o short; cat > ~/essai-kubeadm/atelier.yaml <<'YAML'
apiVersion: kubeadm.k8s.io/v1beta4
kind: ClusterConfiguration
clusterName: essai-atelier
kubernetesVersion: v1.37.2
networking:
  podSubnet: 10.250.0.0/16
  serviceSubnett: 10.96.0.0/12
YAML
kubeadm config validate --config ~/essai-kubeadm/atelier.yaml
```

```text
v1.37.2
error: error unmarshaling configuration schema.GroupVersionKind{Group:"kubeadm.k8s.io", Version:"v1beta4", Kind:"ClusterConfiguration"}: strict decoding error: unknown field "networking.serviceSubnett"
To see the stack trace of this error execute with --v=5 or higher
```

kubeadm refuses the unknown field and names it. Without this check, the typo
would have shown up in the middle of a `kubeadm init`. Fix it and validate
again:

```bash
sed -i 's/serviceSubnett/serviceSubnet/' ~/essai-kubeadm/atelier.yaml; kubeadm config validate --config ~/essai-kubeadm/atelier.yaml
```

```text
ok
```

## 🕰️ Exercise 2: a configuration that is too old

kubeadm files have an API version. Write a configuration in `v1beta3`, the
older version, and validate it:

```bash
cat > ~/essai-kubeadm/ancienne.yaml <<'YAML'
apiVersion: kubeadm.k8s.io/v1beta3
kind: ClusterConfiguration
clusterName: essai-atelier
kubernetesVersion: v1.37.2
networking:
  podSubnet: 10.250.0.0/16
YAML
kubeadm config validate --config ~/essai-kubeadm/ancienne.yaml
```

```text
error: your configuration file uses an old API spec: "kubeadm.k8s.io/v1beta3" (kind: "ClusterConfiguration"). Please use kubeadm v1.36 instead and run 'kubeadm config migrate --old-config old-config-file --new-config new-config-file', which will write the new, similar spec using a newer API version.
To see the stack trace of this error execute with --v=5 or higher
```

kubeadm 1.37 no longer reads `v1beta3`. The message advises migrating the
file, but with kubeadm 1.36. Try anyway with the installed version:

```bash
kubeadm config migrate --old-config ~/essai-kubeadm/ancienne.yaml --new-config ~/essai-kubeadm/migree.yaml; ls ~/essai-kubeadm
```

```text
error: your configuration file uses an old API spec: "kubeadm.k8s.io/v1beta3" (kind: "ClusterConfiguration"). Please use kubeadm v1.36 instead and run 'kubeadm config migrate --old-config old-config-file --new-config new-config-file', which will write the new, similar spec using a newer API version.
To see the stack trace of this error execute with --v=5 or higher
ancienne.yaml
atelier.yaml
```

Same refusal, and no `migree.yaml` file was written. A configuration kept from
an old installation is migrated with the kubeadm version that still
understands it, or rewritten in `v1beta4`.

## 📦 Exercise 3: the images an init will pull

Before an init, especially on a machine with limited Internet access, list
the images it needs:

```bash
kubeadm config images list --config ~/essai-kubeadm/atelier.yaml
```

```text
registry.k8s.io/kube-apiserver:v1.37.2
registry.k8s.io/kube-controller-manager:v1.37.2
registry.k8s.io/kube-scheduler:v1.37.2
registry.k8s.io/kube-proxy:v1.37.2
registry.k8s.io/coredns/coredns:v1.14.6
registry.k8s.io/pause:3.10.2
registry.k8s.io/etcd:3.7.0-0
```

Seven images, with the Kubernetes components at the version the file asks
for. `kubeadm config images pull` downloads them in advance.

## 🧪 Exercise 4: a dry-run init

`kubeadm init --dry-run` goes through every step without installing anything.
Since the node is not prepared (that is the challenge), the preflight checks
are ignored here. The long output is stored in a file, and the command prints
the exit code and three lines (`init à blanc` means "dry-run init"):

```bash
sudo kubeadm init --dry-run --config ~/essai-kubeadm/atelier.yaml --ignore-preflight-errors=all > ~/essai-kubeadm/blanc.txt 2>&1; echo "init à blanc : code $?"; grep -m3 -E 'dry-run|Would|\[dryrun\]' ~/essai-kubeadm/blanc.txt
```

```text
init à blanc : code 0
W1121 03:44:44.121059 1129691 constants.go:627] Using dry-run directory /etc/kubernetes/tmp/kubeadm-init-dryrun2243946114. To override it, set the environment variable KUBEADM_INIT_DRYRUN_DIR
[preflight] Would pull the required images (like 'kubeadm config images pull')
[etcd] Would ensure that "/var/lib/etcd" directory is present
```

Each step says what it would do (`Would`). kubeadm writes the files it would
produce to a temporary directory, under `/etc/kubernetes/tmp`, instead of
their real place. Look for what your configuration changed, then count the
manifests actually written:

```bash
grep -o -m1 -- '--cluster-cidr=[0-9./]*' ~/essai-kubeadm/blanc.txt; grep -o -m1 -- '--cluster-name=[a-z-]*' ~/essai-kubeadm/blanc.txt; sudo ls /etc/kubernetes/manifests 2>/dev/null | wc -l
```

```text
--cluster-cidr=10.250.0.0/16
--cluster-name=essai-atelier
0
```

The Pod network and the cluster name from your file show up in the
components' options. And `/etc/kubernetes/manifests` holds no manifest:
nothing was installed. A dry-run init is the way to read what a configuration
file will produce, before running it for real.

## 🧹 Clean-up

Delete the scratch directory. The dry-run init's temporary directory stays in
`/etc/kubernetes/tmp`, which does not get in the way of a real
`kubeadm init`:

```bash
rm -rf ~/essai-kubeadm
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-initialiser-un-plan-de-controle
dsoxlab check cka-initialiser-un-plan-de-controle
```

```text
╭─ Result: cka-initialiser-un-plan-de-controle ─╮
│  0 / 100 pts                                  │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests              │
╰───────────────────────────────────────────────╯
```

0 out of 6: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: prepare the node, initialise the cluster
from your file, and make it usable.

```bash
dsoxlab run cka-initialiser-un-plan-de-controle
dsoxlab challenge cka-initialiser-un-plan-de-controle
```
