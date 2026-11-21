# Join a worker node to a kubeadm cluster

The lesson shows `kubeadm join`: a node joins the cluster with a bootstrap
token and the fingerprint of the cluster's certificate authority (CA). The
lab took the worker out of the cluster: that is the challenge. This course
therefore joins nothing. It has you handle what a join needs, and adds cases
the lesson does not show: a short, described token, the Secret that holds it,
the CA fingerprint computed by hand, a join refused before touching the node,
and a deleted token.

You work with scratch tokens described as `essai-cours`, kept in the
`~/jeton-essai` file. The challenge is about the `k8s-w1.lab` worker: you
will do it on your own, at the end.

Related page: [Join a node with kubeadm](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kubeadm-join-a-node/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-joindre-un-noeud-kubeadm
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it. The `kubeadm` commands
need `sudo`.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

## 🎟️ Exercise 1: a token that expires quickly, with a description

Create a token valid for 15 minutes, with a description, then list the
tokens:

```bash
sudo kubeadm token create --ttl 15m --description essai-cours > ~/jeton-essai; cat ~/jeton-essai; sudo kubeadm token list | grep -E 'TOKEN|essai-cours'
```

```text
y559h8.a3h0gktefu10b1d3
TOKEN                     TTL         EXPIRES                USAGES                   DESCRIPTION                                                EXTRA GROUPS
y559h8.a3h0gktefu10b1d3   14m         2026-11-21T04:11:22Z   authentication,signing   essai-cours                                                system:bootstrappers:kubeadm:default-node-token
```

The token has two parts: a public identifier (`y559h8` here) and a secret. It
expires at the time shown, and its description says what it is for. A short
token reduces the risk if someone copies it. Without `--ttl`, kubeadm makes it
valid for 24 hours.

## 🗄️ Exercise 2: the token is a Secret

A bootstrap token is stored in a `kube-system` Secret, named after its
identifier. Read its type, its expiry date and one of its usages:

```bash
ID=$(cut -d. -f1 ~/jeton-essai); kubectl -n kube-system get secret bootstrap-token-$ID -o jsonpath='{.type}{"\n"}{range .data}{end}'; kubectl -n kube-system get secret bootstrap-token-$ID -o jsonpath='{.data.expiration}' | base64 -d; echo; kubectl -n kube-system get secret bootstrap-token-$ID -o jsonpath='{.data.usage-bootstrap-authentication}' | base64 -d; echo
```

```text
bootstrap.kubernetes.io/token
2026-11-21T04:11:22Z
true
```

The `bootstrap.kubernetes.io/token` type, the same expiry, and the
"authentication" usage enabled. Whoever can read `kube-system`'s Secrets can
therefore read the bootstrap tokens, and bring a machine into the cluster.

## 🔏 Exercise 3: compute the CA fingerprint again

The joining node checks it is talking to the right cluster by comparing the
fingerprint (the SHA-256 hash) of the CA's public key. Compute it by hand from
the certificate:

```bash
sudo openssl x509 -pubkey -in /etc/kubernetes/pki/ca.crt -noout | openssl pkey -pubin -outform der | sha256sum | cut -d' ' -f1
```

```text
214a42d520d089d390bbda9c97317185dc1d745e07d565e1fe6b68b952121807
```

Compare with the one given by the ready-to-use join command. It creates a
second token along the way, valid for 5 minutes:

```bash
sudo kubeadm token create --print-join-command --ttl 5m | grep -o 'sha256:[0-9a-f]*'
```

```text
sha256:214a42d520d089d390bbda9c97317185dc1d745e07d565e1fe6b68b952121807
```

Both fingerprints are identical. Knowing how to compute it lets you check a
join command received through another channel, instead of trusting it.

## 🚫 Exercise 4: a wrong fingerprint, refused before touching anything

From the worker, run a dry-run join (`--dry-run`) with a wrong fingerprint,
made of zeros. The command only prints the lines about the fingerprint or an
error:

```bash
IP=$(kubectl get node k8s-cp.lab -o jsonpath='{.status.addresses[0].address}'); ssh -o StrictHostKeyChecking=no k8s-w1.lab "sudo kubeadm join $IP:6443 --token $(cat ~/jeton-essai) --discovery-token-ca-cert-hash sha256:$(printf '0%.0s' $(seq 64)) --dry-run --ignore-preflight-errors=all 2>&1 | grep -i -m2 -E 'hash|error|pin'"
```

```text
error: error execution phase preflight: couldn't validate the identity of the API Server: cluster CA found in cluster-info ConfigMap is invalid: none of the public keys "sha256:214a42d520d089d390bbda9c97317185dc1d745e07d565e1fe6b68b952121807" are pinned
To see the stack trace of this error execute with --v=5 or higher
```

kubeadm fetched the cluster's CA, computed its fingerprint, and found it does
not match the one it was given. It stops at the preflight checks: the worker
was not modified. This is the protection against a fake control plane posing
as the real one.

## 🗑️ Exercise 5: delete a token

Delete the scratch token, then look for it in the list and among the Secrets:

```bash
sudo kubeadm token delete $(cut -d. -f1 ~/jeton-essai); sudo kubeadm token list | grep -c essai-cours; ID=$(cut -d. -f1 ~/jeton-essai); kubectl -n kube-system get secret bootstrap-token-$ID
```

```text
bootstrap token "y559h8" deleted
0
Error from server (NotFound): secrets "bootstrap-token-y559h8" not found
```

No more token, no more Secret: deleting one deletes the other. A token you
suspect has leaked is revoked this way, without waiting for it to expire.

## 🧹 Clean-up

Delete the token file and check that no scratch token is left. The 5-minute
token created in exercise 3 expires on its own:

```bash
rm -f ~/jeton-essai; sudo kubeadm token list | grep -c essai-cours
```

```text
0
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-joindre-un-noeud-kubeadm
dsoxlab check cka-joindre-un-noeud-kubeadm
```

```text
╭─ Result: cka-joindre-un-noeud-kubeadm ─╮
│  0 / 100 pts                           │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests       │
╰────────────────────────────────────────╯
```

0 out of 6: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: prepare the worker and have it join the
cluster, until it runs a Pod.

```bash
dsoxlab run cka-joindre-un-noeud-kubeadm
dsoxlab challenge cka-joindre-un-noeud-kubeadm
```
