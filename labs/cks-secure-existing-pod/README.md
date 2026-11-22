# Secure an existing Pod without changing what it does

The lesson shows how to set the `securityContext` of a Pod: process identity,
filesystem, capabilities. This course shows **why** these settings matter, by
measuring what a Pod sees of its node and of the API depending on its
definition: the processes of the node, its disks, and the access token mounted
in every container.

You work in the `essai-exposition` namespace. The challenge targets another
namespace and another Pod: you will do it on your own, at the end.

Related page: [Security Context](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/security-context/) (in French).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-secure-existing-pod
```

You are now logged into `k8s-cp.lab`, the node that drives the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on
22 November 2026, with Kubernetes v1.37.2.

## 👁️ Exercise 1: a Pod that sees the processes of the node

Start two identical Pods, except that `voisin` shares the process space of the
node (`hostPID: true`):

```bash
kubectl create namespace essai-exposition; kubectl run voisin --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-exposition --overrides='{"spec":{"hostPID":true}}' -- sleep 3600; kubectl run cloisonne --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-exposition -- sleep 3600; kubectl wait --for=condition=Ready pod --all -n essai-exposition --timeout=60s
```

```text
namespace/essai-exposition created
pod/voisin created
pod/cloisonne created
pod/cloisonne condition met
pod/voisin condition met
```

Count the processes each one sees, and those named `kubelet` or `containerd`:

```bash
for p in cloisonne voisin; do printf '%s : ' $p; kubectl exec $p -n essai-exposition -- sh -c 'ps -o comm | tail -n +2 | wc -l; ps -o comm | grep -c -x -E "kubelet|containerd"; true' | tr '\n' ' '; echo; done
```

```text
cloisonne : 5 0 
voisin : 180 2 
```

`cloisonne` only sees its own processes, and no process of the node.
`voisin` sees all of the node's, including the kubelet and containerd: it can
read their command lines and environment variables, and send them signals if
it runs as root. A single field of the spec is enough to open that door.

## 💽 Exercise 2: a privileged Pod sees the disks

Add a privileged Pod (`privileged: true`) and compare what each one sees in
`/dev`:

```bash
kubectl run tout-voir --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-exposition --overrides='{"spec":{"containers":[{"name":"t","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"securityContext":{"privileged":true}}]}}' -- true; kubectl wait --for=condition=Ready pod/tout-voir -n essai-exposition --timeout=60s; for p in cloisonne tout-voir; do printf '%s : ' $p; kubectl exec $p -n essai-exposition -- sh -c 'ls /dev | wc -l; ls /dev | grep -m2 -E "^(vd|sd)" || echo aucun-disque' | tr '\n' ' '; echo; done
```

```text
pod/tout-voir created
pod/tout-voir condition met
cloisonne : 16 aucun-disque 
tout-voir : 187 vda vda1 
```

`cloisonne` sees 16 entries and no disk. `tout-voir` sees over 180, including
`vda`, the disk of the node: with the root rights it already has, it can mount
it and read or change the whole filesystem of the machine. That is why a
privileged Pod amounts to root access to the node.

## 🔑 Exercise 3: the token mounted by default

Every Pod gets, without asking, the token of its service account:

```bash
kubectl exec cloisonne -n essai-exposition -- ls /var/run/secrets/kubernetes.io/serviceaccount/
```

```text
ca.crt
namespace
token
```

Use that token from the Pod to query the cluster API:

```bash
kubectl exec cloisonne -n essai-exposition -- sh -c 'wget -qO- --no-check-certificate --header "Authorization: Bearer $(cat /var/run/secrets/kubernetes.io/serviceaccount/token)" https://kubernetes.default/api/v1/namespaces/essai-exposition/pods 2>&1 | head -c 120; echo'
```

```text
wget: server returned error: HTTP/1.1 403 Forbidden
```

`403 Forbidden`, not `401`: the API server **recognised** the token (it is the
one of the `default` account of the namespace), but that account has no
rights. The day someone gives it some, every process of the Pod, including an
attacker who got in, gets them too.

## 🚫 Exercise 4: a Pod without a token

A Pod that does not need to talk to the API can refuse the token with
`automountServiceAccountToken: false`:

```bash
kubectl run sans-jeton --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-exposition --overrides='{"spec":{"automountServiceAccountToken":false}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/sans-jeton -n essai-exposition --timeout=60s; kubectl exec sans-jeton -n essai-exposition -- ls /var/run/secrets/kubernetes.io/serviceaccount/; echo "(code de ls)"
```

```text
pod/sans-jeton created
pod/sans-jeton condition met
ls: /var/run/secrets/kubernetes.io/serviceaccount/: No such file or directory
command terminated with exit code 1
(code de ls)
```

The token folder does not exist: there is nothing to steal. The same setting
exists on the service account itself, for all its Pods at once.

## 🧹 Clean-up

Delete the test namespace, with its four Pods:

```bash
kubectl delete namespace essai-exposition
```

```text
namespace "essai-exposition" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-secure-existing-pod
dsoxlab check cks-secure-existing-pod
```

```text
╭─ Result: cks-secure-existing-pod ─╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests  │
╰───────────────────────────────────╯
```

That is the expected result on a fresh lab. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a production Pod that piles up several
defects, to replace with a Pod that does the same job without any of them.

```bash
dsoxlab run cks-secure-existing-pod
dsoxlab challenge cks-secure-existing-pod
```
