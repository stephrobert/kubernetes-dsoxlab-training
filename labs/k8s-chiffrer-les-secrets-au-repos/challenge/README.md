# Challenge: encrypt Secrets at rest in etcd and limit who reads them

## 🧭 The situation

An audit has just found two problems on the cluster.

First, the API server writes Secrets to etcd **in clear text**. The two
Secrets of the **`tresorerie`** namespace, `cle-banque` and `cle-paie`, can be
read as is in etcd, and so in every etcd backup.

Second, the **`facturation`** ServiceAccount of `tresorerie` can read **all**
the Secrets of the namespace. It only needs `cle-banque`.

## 🎯 What you must achieve

1. Every Secret written from now on is **encrypted** in etcd by the
   **secretbox** provider.
2. `cle-banque` and `cle-paie`, which existed before, are **encrypted** in
   etcd too. Through the API, they still give back their value.
3. `facturation` can read `cle-banque`, and **nothing else**: neither
   `cle-paie`, nor the list of Secrets, nor following them continuously
   (`watch`).

## 🔎 Useful pointers

You are on `k8s-cp.lab`, the node that runs the API server. Its manifest is
`/etc/kubernetes/manifests/kube-apiserver.yaml`. The kubelet watches it: as
soon as you save it, it restarts the API server, which answers again after
about a minute. Copy it to another directory before changing it, **never**
into `/etc/kubernetes/manifests`.

The API server runs in a container: a file you put on the node is only
visible inside it if the manifest mounts it.

etcdctl is installed on the node. It needs the three etcd certificates,
stored in `/etc/kubernetes/pki/etcd/`, and `sudo` to read them.

The lesson shows how to check that a Secret is encrypted, and why changing
the configuration is not enough for the Secrets already there.

## ✅ How you will know it works

The tests read etcd: they create a test Secret and look at how it is stored,
then look at `cle-banque` and `cle-paie`. They then ask the API server what
`facturation` is allowed to do (`kubectl auth can-i`).

```bash
dsoxlab check k8s-chiffrer-les-secrets-au-repos
```
