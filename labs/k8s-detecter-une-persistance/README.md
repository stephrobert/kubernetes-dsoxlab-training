# Find and remove what an attacker left behind

The lesson describes the traces an attacker leaves in a cluster to come back.
This course plants three of them itself, then hunts them down, with cases the
lesson does not show: a DaemonSet posing as a system component, a recent
binding to the `cluster-admin` role found by its date, a Pod that mounts the
node's whole disk, and an old-style token that never expires.

The trial traces have names with `essai` ("trial"). The challenge is about
other objects: you will do it on your own, at the end.

Related page (in French): [Persistance : ce qu'un attaquant laisse derrière lui](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/persistance-attaquant-cluster/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-detecter-une-persistance
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

Plant the three trial traces: a service account bound to `cluster-admin`, a
DaemonSet named like a system component that mounts the root of each node,
and a permanent token for the service account (`chasse` means "hunt"):

```bash
kubectl create namespace essai-chasse; kubectl create serviceaccount essai-maintenance -n essai-chasse; kubectl create clusterrolebinding essai-maintenance-admin --clusterrole=cluster-admin --serviceaccount=essai-chasse:essai-maintenance; cat <<YAML | kubectl apply -f -
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: kube-proxy-essai
  namespace: kube-system
spec:
  selector:
    matchLabels: {app: kube-proxy-essai}
  template:
    metadata:
      labels: {app: kube-proxy-essai}
    spec:
      containers:
        - name: proxy
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: [sleep, "3600"]
          volumeMounts: [{name: hote, mountPath: /hote}]
      volumes:
        - {name: hote, hostPath: {path: /}}
---
apiVersion: v1
kind: Secret
metadata:
  name: essai-jeton-permanent
  namespace: essai-chasse
  annotations: {kubernetes.io/service-account.name: essai-maintenance}
type: kubernetes.io/service-account-token
YAML
sleep 5
```

```text
namespace/essai-chasse created
serviceaccount/essai-maintenance created
clusterrolebinding.rbac.authorization.k8s.io/essai-maintenance-admin created
daemonset.apps/kube-proxy-essai created
secret/essai-jeton-permanent created
```

## 👑 Exercise 1: the bindings to cluster-admin, most recent first

The original bindings date from the cluster's installation. Sort the bindings
to the `cluster-admin` role by creation date, and keep the last ones:

```bash
kubectl get clusterrolebindings --sort-by=.metadata.creationTimestamp -o jsonpath='{range .items[?(@.roleRef.name=="cluster-admin")]}{.metadata.creationTimestamp}{"  "}{.metadata.name}{"\n"}{end}' | tail -3
```

```text
2026-11-21T10:43:44Z  kubeadm:cluster-admins
2026-11-21T10:43:45Z  cluster-admin
2026-11-21T11:04:21Z  essai-maintenance-admin
```

The first two were created by kubeadm at installation, one second apart. The
third one arrived twenty minutes later: that is the one to explain.

## 🎭 Exercise 2: a system component that is not one

A name starting with `kube-` in `kube-system` proves nothing. Compare the
DaemonSets of `kube-system` by date and by image (`NOM` means "name", `CREE`
"created"):

```bash
kubectl get daemonsets -n kube-system -o custom-columns='NOM:.metadata.name,CREE:.metadata.creationTimestamp,IMAGE:.spec.template.spec.containers[0].image'
```

```text
NOM                CREE                   IMAGE
kube-proxy         2026-11-21T10:43:46Z   registry.k8s.io/kube-proxy:v1.37.2
kube-proxy-essai   2026-11-21T11:04:21Z   busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

The real `kube-proxy` comes from `registry.k8s.io` and dates from the
installation. `kube-proxy-essai` runs a busybox image and dates from today: a
fake.

## 💽 Exercise 3: the Pods that mount a node's disk

A Pod that mounts the node's `/` can read and change its whole system. Look
for the Pods with a `hostPath` volume pointing to the root:

```bash
kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name}{" "}{.spec.volumes[*].hostPath.path}{"\n"}{end}' | grep -E ' /( |$)'
```

```text
kube-system/kube-proxy-essai-4jhqv /
kube-system/kube-proxy-essai-5d46m /
kube-system/kube-proxy-essai-7m4z2 /
kube-system/kube-proxy-essai-qdjzg /
```

One Pod per node, those of the fake DaemonSet. The control plane components
also mount node directories, but never the whole root.

## 🔑 Exercise 4: the tokens that never expire

A Secret of type `service-account-token` carries a token that stays valid as
long as the Secret exists, with no expiry date. Normal tokens do expire. List
these Secrets across the cluster (`COMPTE` means "account"):

```bash
kubectl get secrets -A --field-selector type=kubernetes.io/service-account-token -o custom-columns='NS:.metadata.namespace,NOM:.metadata.name,COMPTE:.metadata.annotations.kubernetes\.io/service-account\.name'
```

```text
NS             NOM                     COMPTE
essai-chasse   essai-jeton-permanent   essai-maintenance
```

Only one, for the `essai-maintenance` account, the one bound to
`cluster-admin`: permanent administrator access.

## 🗂️ Exercise 5: record, then remove

Before deleting a trace, keep a copy of it: it will help understand the
attack. Export the DaemonSet and the binding (`constat` means "report"):

```bash
kubectl get daemonset kube-proxy-essai -n kube-system -o yaml > ~/constat-essai.yaml; kubectl get clusterrolebinding essai-maintenance-admin -o yaml >> ~/constat-essai.yaml; grep -c '^kind:' ~/constat-essai.yaml
```

```text
2
```

Two objects recorded. Now remove the three traces:

```bash
kubectl delete daemonset kube-proxy-essai -n kube-system; kubectl delete clusterrolebinding essai-maintenance-admin; kubectl delete namespace essai-chasse; sleep 10; kubectl get pods -n kube-system -l app=kube-proxy-essai
```

```text
daemonset.apps "kube-proxy-essai" deleted from kube-system namespace
clusterrolebinding.rbac.authorization.k8s.io "essai-maintenance-admin" deleted
namespace "essai-chasse" deleted
NAME                     READY   STATUS        RESTARTS   AGE
kube-proxy-essai-4jhqv   1/1     Terminating   0          21s
kube-proxy-essai-7m4z2   1/1     Terminating   0          21s
```

The Pods of the fake DaemonSet are stopping: deleting the DaemonSet also
deletes what it started. Deleting the namespace takes the service account and
its token with it.

## 🧹 Clean-up

Delete the report file:

```bash
rm -f ~/constat-essai.yaml
```

```text

```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-detecter-une-persistance
dsoxlab check k8s-detecter-une-persistance
```

```text
╭─ Result: k8s-detecter-une-persistance ─╮
│  0 / 100 pts                           │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests       │
╰────────────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: an attacker went through the cluster. Find
what gives them access again, record it, then remove it without harming the
legitimate application.

```bash
dsoxlab run k8s-detecter-une-persistance
dsoxlab challenge k8s-detecter-une-persistance
```
