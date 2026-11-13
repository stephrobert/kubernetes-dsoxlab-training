# Issue certificates with cert-manager and an internal CA

## The situation

The team wants TLS certificates for its internal services, issued and renewed
without manual work. **cert-manager** is installed in the cluster. No public
ACME here: the cluster cannot be reached from the Internet. The certificates
will come from an **internal CA**, which you must build first.

A colleague already declared the certificate **`api-tls`**, in the
**`atelier-tls`** namespace: it stays "not ready".

You are on **`k8s-cp.lab`**, with `kubectl` configured.

## What you must achieve

In the **`atelier-tls`** namespace:

1. A **self-signed** Issuer named **`auto-signe`**, ready.
2. An **internal CA**: a Certificate **`ca-interne`**, a certificate
   authority, issued by `auto-signe`, in the Secret `ca-interne`; and an Issuer
   **`ca-interne`** that signs with that Secret, ready.
3. A Certificate **`vitrine-tls`** for the name **`vitrine.atelier-tls.svc`**,
   issued by the internal CA, ready.
4. The Certificate **`api-tls`** **repaired**: ready, and issued by the
   internal CA.

## Useful bearings

- An `Issuer` lives in a namespace, a `ClusterIssuer` in the whole cluster. A
  `selfSigned` Issuer signs each certificate with its own key.
- A Certificate with `isCA: true` produces a certificate authority. An Issuer of
  type `ca` then signs with the Secret that holds it.
- A "not ready" Certificate is diagnosed top-down: `kubectl describe
  certificate`, then the `CertificateRequest` it created, then the namespace
  events.
- `kubectl get secret <name> -o jsonpath='{.data.tls\.crt}' | base64 -d |
  openssl x509 -noout -subject -issuer -dates` reads the issued certificate.

## How you will know it works

The tests read the issuers and certificates, then check each chain with
`openssl verify` against the internal CA: a ready certificate signed by the
wrong issuer does not pass.

```bash
dsoxlab check k8s-emettre-un-certificat-avec-cert-manager
```
