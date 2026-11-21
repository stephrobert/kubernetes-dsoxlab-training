# Back up etcd, then restore the cluster from a snapshot

The lesson shows how to back up etcd with `etcdctl snapshot save` and restore
the cluster with `etcdutl snapshot restore`. This course adds what the lesson
does not show: checking a backup's content without touching the cluster, by
restoring it into a throwaway directory read by a temporary etcd, and
recognising a damaged backup.

You work in a scratch directory, `/tmp/essai-sauvegarde`, with a scratch
namespace, `essai-sauvegarde` ("test-backup"), and a temporary etcd on ports
32379 and 32380. The challenge is about another backup and the cluster's real
etcd: you will do it on your own, at the end.

Related page: [Backup and restore](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/backup-restore/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-etcd-backup-restore
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it. `etcdctl` and `etcdutl`
are installed on the node. They need `sudo` to read etcd's certificates.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2 and etcd 3.7.0.

## 💾 Exercise 1: back up a state you will recognise

Create a namespace and a witness ConfigMap, then back up etcd. The client uses
the `healthcheck-client` certificate, which kubeadm provides for talking to
etcd:

```bash
kubectl create namespace essai-sauvegarde; kubectl create configmap temoin -n essai-sauvegarde --from-literal=moment=avant-la-sauvegarde; sudo mkdir -p /tmp/essai-sauvegarde; sudo etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt --key=/etc/kubernetes/pki/etcd/healthcheck-client.key snapshot save /tmp/essai-sauvegarde/instantane.db 2>/dev/null; sudo ls -l /tmp/essai-sauvegarde
```

```text
namespace/essai-sauvegarde created
configmap/temoin created
Snapshot saved at /tmp/essai-sauvegarde/instantane.db
Server version 3.7.0
total 3312
-rw------- 1 root root 3387424 Nov 21 04:11 instantane.db
```

Delete the namespace, so that the cluster and the backup no longer say the
same thing, then check the backup:

```bash
kubectl delete namespace essai-sauvegarde; sudo etcdutl snapshot status /tmp/essai-sauvegarde/instantane.db -w table
```

```text
namespace "essai-sauvegarde" deleted
┌──────────┬──────────┬────────────┬────────────┬─────────┐
│   HASH   │ REVISION │ TOTAL KEYS │ TOTAL SIZE │ VERSION │
├──────────┼──────────┼────────────┼────────────┼─────────┤
│ 74e350a3 │     4545 │        682 │     3.4 MB │   3.7.0 │
└──────────┴──────────┴────────────┴────────────┴─────────┘
```

`snapshot status` reads the file without changing it: its hash, the revision
it was taken at, the number of keys. That is the minimum check. It says the
file is readable, but not that it holds what you expect.

## 📂 Exercise 2: restore into a throwaway directory

`etcdutl snapshot restore` builds a data directory from the backup. Target a
scratch directory, with a member name and addresses that are not the real
etcd's:

```bash
sudo etcdutl snapshot restore /tmp/essai-sauvegarde/instantane.db --data-dir /tmp/essai-sauvegarde/donnees --name essai --initial-cluster essai=http://127.0.0.1:32380 --initial-advertise-peer-urls http://127.0.0.1:32380 2>&1 | tail -2; sudo ls /tmp/essai-sauvegarde/donnees/member
```

```text
2026-11-21T04:11:21Z	info	bbolt	bbolt@v1.5.0/db.go:327	Opening bbolt db (/tmp/essai-sauvegarde/donnees/member/snap/db) successfully
2026-11-21T04:11:21Z	info	snapshot/v3_snapshot.go:334	restored snapshot	{"path": "/tmp/essai-sauvegarde/instantane.db", "wal-dir": "/tmp/essai-sauvegarde/donnees/member/wal", "data-dir": "/tmp/essai-sauvegarde/donnees", "snap-dir": "/tmp/essai-sauvegarde/donnees/member/snap", "initial-memory-map-size": 10737418240}
snap
wal
```

The directory holds the two parts of an etcd: `snap` (the database) and `wal`
(the log). The cluster's real etcd was not touched: it still reads
`/var/lib/etcd`.

## 🔎 Exercise 3: query the backup with a temporary etcd

Start a second etcd, with the same image as the cluster's, on this directory
and on ports 32379 and 32380. It runs directly through containerd (`ctr`),
outside Kubernetes:

```bash
IMG=$(kubectl -n kube-system get pod etcd-k8s-cp.lab -o jsonpath='{.spec.containers[0].image}'); sudo ctr -n k8s.io run -d --net-host --mount type=bind,src=/tmp/essai-sauvegarde/donnees,dst=/donnees,options=rbind:rw $IMG etcd-essai etcd --data-dir /donnees --name essai --listen-client-urls http://127.0.0.1:32379 --advertise-client-urls http://127.0.0.1:32379 --listen-peer-urls http://127.0.0.1:32380 --initial-cluster essai=http://127.0.0.1:32380 --initial-advertise-peer-urls "http://127.0.0.1:32380"; sleep 5; sudo etcdctl --endpoints=http://127.0.0.1:32379 endpoint health
```

```text
http://127.0.0.1:32379 is healthy: successfully committed proposal: took = 2.198295ms
```

Look for the witness ConfigMap there, then for the namespace in the real
cluster (the last line reads "the cluster, for its part, no longer has it"):

```bash
sudo etcdctl --endpoints=http://127.0.0.1:32379 get /registry/configmaps/essai-sauvegarde/temoin --print-value-only | tr -cd '[:print:]' | grep -o 'avant-la-sauvegarde'; kubectl get namespace essai-sauvegarde; echo "(le cluster, lui, ne l'a plus)"
```

```text
avant-la-sauvegarde
Error from server (NotFound): namespaces "essai-sauvegarde" not found
(le cluster, lui, ne l'a plus)
```

The backup does hold the witness, which the cluster no longer has. You now
know this backup could bring it back, without having risked the cluster to
check it. Stop and delete the temporary etcd (the last line reads "temporary
etcd stopped"):

```bash
sudo ctr -n k8s.io task kill -s SIGKILL etcd-essai; sleep 2; sudo ctr -n k8s.io task delete etcd-essai; sudo ctr -n k8s.io container delete etcd-essai; sudo etcdctl --endpoints=http://127.0.0.1:32379 --command-timeout=2s endpoint health 2>&1 | tail -2; echo "(etcd temporaire arrêté)"
```

```text
time="2026-11-21T04:11:28Z" level=warning msg="task etcd-essai exit with non-zero exit code 137"
http://127.0.0.1:32379 is unhealthy: failed to commit proposal: context deadline exceeded
Error: unhealthy cluster
(etcd temporaire arrêté)
```

Code 137 is that of a process killed by `SIGKILL`, and the temporary etcd no
longer answers.

## 🩹 Exercise 4: a damaged backup

Copy the backup, cut the copy in half, and have it checked:

```bash
sudo cp /tmp/essai-sauvegarde/instantane.db /tmp/essai-sauvegarde/abimee.db; T=$(sudo stat -c %s /tmp/essai-sauvegarde/abimee.db); sudo truncate -s $((T / 2)) /tmp/essai-sauvegarde/abimee.db; sudo etcdutl snapshot status /tmp/essai-sauvegarde/abimee.db -w table > /tmp/essai-statut.txt 2>&1; echo "status : code $?"; head -2 /tmp/essai-statut.txt; rm -f /tmp/essai-statut.txt
```

```text
status : code 2
unexpected fault address 0x738af5b37000
fatal error: fault
```

`etcdutl` stops with an error (code 2) on a low-level message: it cannot read
the database. A file copied halfway, by an interrupted transfer or a full
disk, looks like a backup from the outside. Always check a backup where it is
stored, not only when you take it.

## 🧹 Clean-up

Delete the scratch directory:

```bash
sudo rm -rf /tmp/essai-sauvegarde
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-etcd-backup-restore
dsoxlab check cka-etcd-backup-restore
```

```text
╭─ Result: cka-etcd-backup-restore ─╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/9 tests  │
╰───────────────────────────────────╯
```

0 out of 9: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: back up the current state, then restore the
real cluster from the previous night's backup.

```bash
dsoxlab run cka-etcd-backup-restore
dsoxlab challenge cka-etcd-backup-restore
```
