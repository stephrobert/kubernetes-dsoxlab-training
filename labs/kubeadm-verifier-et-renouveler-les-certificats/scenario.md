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
3. **kube-controller-manager** and **kube-scheduler** run with the **renewed
   client certificate** of their kubeconfig.
4. Your **`~/.kube/config`** carries the **renewed admin certificate**, and
   `kubectl` answers with it.

## Useful bearings

- `kubeadm certs check-expiration` lists each certificate, its expiry and the
  authority that signed it. `openssl x509 -noout -dates -in <file>` reads a
  certificate by hand.
- `kubeadm certs renew` renews one certificate, or all of them.
- The control plane components are **static Pods**. The API server and etcd
  reload their serving certificate on their own when the file changes; the
  controller manager and the scheduler only read the client certificate of
  their kubeconfig when they start. The manifests live in
  `/etc/kubernetes/manifests`, and the kubelet stops a static Pod whose manifest
  disappears.
- Renewal also rewrites `/etc/kubernetes/admin.conf`, but not the copy you made
  of it.

## How you will know it works

The tests read the state of the node, not the commands you typed:

- the date written in `~/pki/reponses.yaml` is the expiry date of the
  cluster's certificate authority;
- the serial number of each control plane certificate has changed since the
  lab started;
- the controller manager and the scheduler started after their kubeconfig was
  rewritten;
- your `~/.kube/config` carries the same certificate as the new
  `admin.conf`, and `kubectl` answers with it.

```bash
dsoxlab check kubeadm-verifier-et-renouveler-les-certificats
```
