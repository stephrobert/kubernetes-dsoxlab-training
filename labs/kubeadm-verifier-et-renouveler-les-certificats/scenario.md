# Check and renew the certificates of a kubeadm cluster

## The situation

kubeadm signs the control plane certificates for one year. A cluster that is
never upgraded ends up refusing its own components the day they expire. The
team wants to check the expiry dates, and renew without waiting for the outage.

You are on **`k8s-cp.lab`**, the control plane of the kubeadm cluster, with
`kubectl` configured and `sudo` rights.

## What you must achieve

1. In **`~/pki/reponses.yaml`**: the **expiry date of the cluster's certificate
   authority** (`ca`), in `YYYY-MM-DD` format.
2. The **control plane** certificates are **renewed**: those of the API server,
   of its clients to the kubelet and to etcd, of the front-proxy, and those of
   etcd.
3. The **API server** and **etcd** **serve** the renewed certificates.
4. Your **`~/.kube/config`** carries the **renewed admin certificate**, and
   `kubectl` answers with it.

## Useful bearings

- `kubeadm certs check-expiration` lists each certificate, its expiry and the
  authority that signed it. `openssl x509 -noout -dates -in <file>` reads a
  certificate by hand.
- `kubeadm certs renew` renews one certificate, or all of them.
- The control plane components are **static Pods**: they only read their
  certificates again when they restart. The manifests live in
  `/etc/kubernetes/manifests`, and the kubelet stops a static Pod whose manifest
  disappears.
- Renewal also rewrites `/etc/kubernetes/admin.conf`, but not the copy you made
  of it.

## How you will know it works

The tests compare each certificate's serial number with the one recorded when
the lab started, then query the API server and etcd to see which certificate
they serve.

```bash
dsoxlab check kubeadm-verifier-et-renouveler-les-certificats
```
