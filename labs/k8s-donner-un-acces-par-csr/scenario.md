# Give a person access through a CertificateSigningRequest

## The situation

**camille** joins the web team. She must be able to **read the Pods** of the
**`equipe-web`** namespace, and nothing else. Kubernetes has no "user" object:
a person authenticates with a certificate the cluster signed, and the API
recognizes them by the certificate's **CN**.

The team's rule: the certificate authority's key never leaves the node, and
nobody signs by hand with it. The certificate goes through the
**CertificateSigningRequest** API.

You are on **`k8s-cp.lab`**, with `kubectl` configured. The **`~/acces`**
directory is empty.

## What you must achieve

1. A **CertificateSigningRequest** named **`camille`**, for the CN `camille`,
   addressed to the API server's client signer, for client authentication,
   **approved** and **issued**.
2. **`~/acces/camille.kubeconfig`** carries the **certificate the API issued**
   for that request and camille's key; the API recognizes **camille** in it.
3. With that kubeconfig, camille **reads the Pods** of `equipe-web`.
4. And **nothing more**: no change, no reading Secrets, no looking at another
   namespace or at the nodes.

## Useful bearings

- `openssl genrsa` creates a key, `openssl req -new -subj "/CN=camille"` a
  request signed with that key.
- A CertificateSigningRequest carries the base64-encoded request, a
  `signerName` and `usages`. `kubectl certificate approve` approves it, and the
  issued certificate appears in its `status.certificate`.
- `kubectl config set-cluster`, `set-credentials` and `set-context`, with
  `--kubeconfig`, build a separate kubeconfig.
- `kubectl auth whoami` and `kubectl auth can-i`, run with that kubeconfig, say
  who the API sees and what that identity can do.

## How you will know it works

The tests read the request camille, compare the kubeconfig's certificate with
the one the API issued, then query the API under camille's identity.

```bash
dsoxlab check k8s-donner-un-acces-par-csr
```
