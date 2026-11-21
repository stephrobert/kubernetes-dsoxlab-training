# Check etcd health and defragment its database

The lesson shows etcd, the database where Kubernetes stores all its objects,
and the `etcdctl` commands that check its health. This course has you look
inside the database itself, and adds cases the lesson does not show: a key
written without going through the API, a Kubernetes object as etcd stores it,
the revision moving forward at each write, compaction erasing history, and
the member's status read by a script.

You work with scratch keys under the `/essai-cours/` prefix and a scratch
namespace, `essai-etcd`. The challenge is about other questions: you will do
it on your own, at the end.

Related page: [etcd](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/etcd/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-etcd-sante-et-defragmentation
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

`etcdctl` is called inside the node's etcd Pod, with the etcd server's
certificates, as in the lesson. The command is long, but it is always the
same: only the end changes.

## ✍️ Exercise 1: write and read a key outside the API

Write a key directly into etcd, then read it back:

```bash
kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key put /essai-cours/note 'ecrite par etcdctl'; kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /essai-cours/note
```

```text
OK
/essai-cours/note
ecrite par etcdctl
```

List the prefix's keys, then ask the API for the ConfigMaps of `default`:

```bash
kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /essai-cours/ --prefix --keys-only; kubectl get --raw /api/v1/namespaces/default/configmaps | python3 -c 'import json,sys; print(len(json.load(sys.stdin)["items"]), "ConfigMap dans default : la clé ne se voit pas par l API")'
```

```text
/essai-cours/note

1 ConfigMap dans default : la clé ne se voit pas par l API
```

The key exists in etcd, but the API shows it nowhere: it only reads the keys
it stored itself, under `/registry/`. Writing to etcd by hand bypasses every
check the API makes. You only do it to learn, or to repair.

## 🗂️ Exercise 2: a Kubernetes object in etcd

Create a ConfigMap, then look for it in etcd:

```bash
kubectl create namespace essai-etcd; kubectl create configmap fiche -n essai-etcd --from-literal=couleur=bleu; kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /registry/configmaps/essai-etcd/fiche --keys-only
```

```text
namespace/essai-etcd created
configmap/fiche created
/registry/configmaps/essai-etcd/fiche
```

The object is stored under `/registry/<type>/<namespace>/<name>`. Read the
start of its value, character by character:

```bash
kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /registry/configmaps/essai-etcd/fiche --print-value-only | head -c 120 | od -c | head -3
```

```text
0000000   k   8   s  \0  \n 017  \n 002   v   1 022  \t   C   o   n   f
0000020   i   g   M   a   p 022 272 001  \n 246 001  \n 005   f   i   c
0000040   h   e 022  \0 032  \n   e   s   s   a   i   -   e   t   c   d
```

It is neither JSON nor YAML: the `k8s` prefix followed by binary data
(Protobuf). You can spot `v1`, `ConfigMap`, `fiche` and `essai-etcd`. Reading
etcd directly therefore does not replace `kubectl get`: the API is what knows
how to decode.

## 🔢 Exercise 3: every write moves the revision forward

etcd numbers every change to the database: that is the revision. Read the
cluster's revision and the key's version (`révision du cluster` means
"cluster revision", `version de la clé` "key version"):

```bash
kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /essai-cours/note -w json | python3 -c 'import json,sys; d=json.load(sys.stdin); print("révision du cluster", d["header"]["revision"], "| version de la clé", d["kvs"][0]["version"])'
```

```text
révision du cluster 2974 | version de la clé 1
```

Write the key three times, and read again (`créée à` means "created at",
`modifiée à` "modified at"):

```bash
for i in 1 2 3; do kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key put /essai-cours/note "version $i" >/dev/null; done; kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /essai-cours/note -w json | python3 -c 'import json,sys; d=json.load(sys.stdin); print("révision du cluster", d["header"]["revision"], "| version de la clé", d["kvs"][0]["version"], "| créée à", d["kvs"][0]["create_revision"], "| modifiée à", d["kvs"][0]["mod_revision"])'
```

```text
révision du cluster 2977 | version de la clé 4 | créée à 2967 | modifiée à 2977
```

The key is at version 4, and the revision moved forward by 3. The revision
applies to the whole database: any write, of any object, moves it forward.

## 🗜️ Exercise 4: read the past, then compact it

etcd keeps old versions. Read the key as it was at creation (`lecture à la
révision` means "read at revision"):

```bash
CREE=$(kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /essai-cours/note -w json | python3 -c 'import json,sys; print(json.load(sys.stdin)["kvs"][0]["create_revision"])'); echo "lecture à la révision $CREE :"; kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /essai-cours/note --rev=$CREE --print-value-only
```

```text
lecture à la révision 2967 :
ecrite par etcdctl
```

The first value came back. Now compact the history up to the current
revision:

```bash
REV=$(kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /essai-cours/note -w json | python3 -c 'import json,sys; print(json.load(sys.stdin)["header"]["revision"])'); kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key compact $REV
```

```text
compacted revision 2977
```

Read the old version again:

```bash
CREE=$(kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /essai-cours/note -w json | python3 -c 'import json,sys; print(json.load(sys.stdin)["kvs"][0]["create_revision"])'); kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key get /essai-cours/note --rev=$CREE; echo "(code de la relecture)"
```

```text
{"level":"warn","ts":"2026-11-21T04:03:06.587575Z","logger":"etcd-client","caller":"v3/retry_interceptor.go:68","msg":"retrying of unary invoker failed","target":"etcd-endpoints://0xfeb4efeee00/127.0.0.1:2379","peer":"Peer{Addr: '127.0.0.1:2379', LocalAddr: '127.0.0.1:34442', AuthInfo: 'tls'}","method":"/etcdserverpb.KV/Range","attempt":0,"error":"rpc error: code = OutOfRange desc = etcdserver: mvcc: required revision has been compacted"}
Error: etcdserver: mvcc: required revision has been compacted
command terminated with exit code 1
(code de la relecture)
```

`required revision has been compacted`: the earlier history is erased. The
API server asks for this compaction on its own, every 5 minutes by default.
Compaction removes old versions, but does not give the space back to the
disk: that is the job of defragmentation, which the challenge asks for.

## 📊 Exercise 5: the member's status read by a script

`etcdctl endpoint status` can answer in JSON, easier for a script to read than
the table. Extract the database size, the space really in use, and the leader
(`taille` means "size", `en usage` "in use"):

```bash
kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key endpoint status -w json | python3 -c 'import json,sys; s=json.load(sys.stdin)[0]["Status"]; print("taille", s["dbSize"], "en usage", s["dbSizeInUse"], "leader", hex(s["leader"]))'
```

```text
taille 150855680 en usage 2957312 leader 0x2e830b06b400c72b
```

The database takes about 150 MB, but only 3 MB are still in use. The gap is
the space compaction freed without giving it back to the disk.

## 🧹 Clean-up

Delete the scratch keys and the namespace. `etcdctl del` prints the number of
keys deleted:

```bash
kubectl -n kube-system exec etcd-k8s-cp.lab -- etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt --cert /etc/kubernetes/pki/etcd/server.crt --key /etc/kubernetes/pki/etcd/server.key del /essai-cours/ --prefix; kubectl delete namespace essai-etcd
```

```text
1
namespace "essai-etcd" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-etcd-sante-et-defragmentation
dsoxlab check cka-etcd-sante-et-defragmentation
```

```text
╭─ Result: cka-etcd-sante-et-defragmentation ─╮
│  0 / 100 pts                                │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests            │
╰─────────────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: record the etcd member's identity and
health, its quota, and give the lost space back to the disk.

```bash
dsoxlab run cka-etcd-sante-et-defragmentation
dsoxlab challenge cka-etcd-sante-et-defragmentation
```
