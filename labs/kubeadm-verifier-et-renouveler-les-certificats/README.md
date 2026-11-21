# Check and renew the certificates of a kubeadm cluster

The lesson shows a kubeadm cluster's PKI: the control plane's certificates,
their expiry, and `kubeadm certs renew`. This course adds cases the lesson
does not show: the names the API server's certificate covers, the kubelet's
client certificate that renews itself, and a renewal done on a copy of the
PKI, to see what changes in the certificate.

The course renews nothing in `/etc/kubernetes/pki`: it works on a copy,
`/tmp/essai-pki`. The challenge is about the real certificates: you will do it
on your own, at the end.

Related page: [The PKI of a Kubernetes cluster](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/cluster-pki/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run kubeadm-verifier-et-renouveler-les-certificats
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it. The certificates are
readable by root only: the commands use `sudo`.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

## 🏷️ Exercise 1: the names the API server covers

Read the names and addresses in the API server's certificate:

```bash
sudo openssl x509 -in /etc/kubernetes/pki/apiserver.crt -noout -ext subjectAltName
```

```text
X509v3 Subject Alternative Name: 
    DNS:k8s-cp.lab, DNS:kubernetes, DNS:kubernetes.default, DNS:kubernetes.default.svc, DNS:kubernetes.default.svc.cluster.local, IP Address:10.96.0.1, IP Address:10.10.50.11
```

The node's name, Kubernetes' internal names, the `kubernetes` Service's
address (`10.96.0.1`) and the node's address. A client that reaches the API
through another name, another address or a load balancer added later is
refused. This is the first thing to read when `kubectl` complains about a
certificate that does not match.

## 🔁 Exercise 2: the kubelet renews its client certificate itself

Look at the kubelet's certificates, and at the subject of its client
certificate:

```bash
sudo ls -l /var/lib/kubelet/pki/ | cut -c1-140; sudo openssl x509 -in /var/lib/kubelet/pki/kubelet-client-current.pem -noout -subject -enddate
```

```text
total 12
-rw------- 1 root root 2830 Nov 21 03:53 kubelet-client-2026-11-21-03-53-43.pem
lrwxrwxrwx 1 root root   59 Nov 21 03:53 kubelet-client-current.pem -> /var/lib/kubelet/pki/kubelet-client-2026-11-21-03-53-43.pem
-rw-r--r-- 1 root root 2283 Nov 21 03:53 kubelet.crt
-rw------- 1 root root 1679 Nov 21 03:53 kubelet.key
subject=O = system:nodes, CN = system:node:k8s-cp.lab
notAfter=Nov 21 03:53:43 2027 GMT
```

The kubelet keeps dated client certificates, and `kubelet-client-current.pem`
is a link to the most recent one. Its subject places it in the `system:nodes`
group, with the name `system:node:k8s-cp.lab`. Before expiry, the kubelet
itself asks for a new certificate through a CSR, and moves the link. The
cluster's latest CSRs are precisely the kubelets' (`DEMANDEUR` means
"requester", `SIGNATAIRE` "signer", `ETAT` "state"):

```bash
kubectl get csr --sort-by=.metadata.creationTimestamp -o custom-columns=NOM:.metadata.name,DEMANDEUR:.spec.username,SIGNATAIRE:.spec.signerName,ETAT:.status.conditions[0].type | tail -3
```

```text
csr-6km7w   system:bootstrap:67mfev   kubernetes.io/kube-apiserver-client-kubelet   Approved
csr-qx7l5   system:bootstrap:r5onmt   kubernetes.io/kube-apiserver-client-kubelet   Approved
csr-j6mvr   system:bootstrap:lzfpy6   kubernetes.io/kube-apiserver-client-kubelet   Approved
```

Requested during bootstrap (`system:bootstrap:…`), for the kubelet client
signer, and approved automatically. `kubeadm certs renew` does not handle this
certificate.

## 🧪 Exercise 3: renew on a copy

Copy the PKI to `/tmp/essai-pki`, then read the copy's expiry dates (the
first lines only):

```bash
sudo cp -a /etc/kubernetes/pki /tmp/essai-pki; sudo kubeadm certs check-expiration --cert-dir /tmp/essai-pki 2>&1 | sed -n '1,6p'
```

```text
[check-expiration] Reading configuration from the "kubeadm-config" ConfigMap in namespace "kube-system"...
[check-expiration] Use 'kubeadm init phase upload-config kubeadm --config your-config-file' to re-upload it.

CERTIFICATE                EXPIRES                  RESIDUAL TIME   CERTIFICATE AUTHORITY   EXTERNALLY MANAGED
admin.conf                 Nov 21, 2027 03:53 UTC   364d            ca                      no      
apiserver                  Nov 19, 2027 14:18 UTC   363d            ca                      no      
```

Note the serial number, the end date and the public key fingerprint of the
API server's certificate in the copy:

```bash
sudo openssl x509 -in /tmp/essai-pki/apiserver.crt -noout -serial -enddate; sudo openssl x509 -in /tmp/essai-pki/apiserver.crt -noout -pubkey | sha256sum | cut -c1-16
```

```text
serial=3C76ED4D00B086D9
notAfter=Nov 19 14:18:00 2027 GMT
02af5763b250ddb1
```

Renew this certificate in the copy (`--cert-dir`):

```bash
sudo kubeadm certs renew apiserver --cert-dir /tmp/essai-pki 2>&1 | tail -2
```

```text

certificate for serving the Kubernetes API renewed
```

Read the same values again, and check the certificate is still signed by the
same authority:

```bash
sudo openssl x509 -in /tmp/essai-pki/apiserver.crt -noout -serial -enddate; sudo openssl x509 -in /tmp/essai-pki/apiserver.crt -noout -pubkey | sha256sum | cut -c1-16; sudo openssl verify -CAfile /tmp/essai-pki/ca.crt /tmp/essai-pki/apiserver.crt
```

```text
serial=70864233F15CAD27
notAfter=Nov 21 04:25:40 2027 GMT
1dd6692464cb1038
/tmp/essai-pki/apiserver.crt: OK
```

New serial number, new end date, one year later. The public key fingerprint
changed too: kubeadm 1.37 made a new key. The authority did not change: the
check answers `OK`. Clients that trust the CA therefore keep trusting the new
certificate. Finally, check that the real certificate did not move (the last
line reads "the real certificate did not change"):

```bash
sudo openssl x509 -in /etc/kubernetes/pki/apiserver.crt -noout -serial; echo "(le vrai certificat n'a pas changé)"
```

```text
serial=3C76ED4D00B086D9
(le vrai certificat n'a pas changé)
```

Same serial number as before: only the copy's certificate was renewed.

## 🧹 Clean-up

Delete the PKI copy. It holds the cluster's private keys: do not leave it
lying around.

```bash
sudo rm -rf /tmp/essai-pki
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset kubeadm-verifier-et-renouveler-les-certificats
dsoxlab check kubeadm-verifier-et-renouveler-les-certificats
```

```text
╭─ Result: kubeadm-verifier-et-renouveler-les-certificats ─╮
│  0 / 100 pts                                             │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests                         │
╰──────────────────────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: record the authority's expiry, then renew
the control plane's real certificates without breaking the cluster.

```bash
dsoxlab run kubeadm-verifier-et-renouveler-les-certificats
dsoxlab challenge kubeadm-verifier-et-renouveler-les-certificats
```
