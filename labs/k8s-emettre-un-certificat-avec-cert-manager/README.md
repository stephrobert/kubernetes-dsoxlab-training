# Issue certificates with cert-manager and an internal CA

The lesson shows cert-manager: Issuers that sign, and Certificates that
describe the certificates you want and keep them up to date. This course adds
cases the lesson does not show: the lifetime and the renewal time, a deleted
Secret that cert-manager issues again, the private key replaced or kept when
the request changes, and an Issuer that only serves its own namespace.

You work in two scratch namespaces, `essai-cm` and `essai-ailleurs`, with a
self-signed Issuer `essai-racine` and a Certificate `guichet-tls`. The
challenge is about another namespace: you will do it on your own, at the end.

Related page (in French): [cert-manager](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/cert-manager/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-emettre-un-certificat-avec-cert-manager
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it. The lab installed
cert-manager.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2 and cert-manager v1.21.3.

Create the namespace and a self-signed Issuer, which signs each certificate
with its own key:

```bash
kubectl create namespace essai-cm; cat <<'YAML' | kubectl apply -n essai-cm -f -
apiVersion: cert-manager.io/v1
kind: Issuer
metadata:
  name: essai-racine
spec:
  selfSigned: {}
YAML
kubectl wait --for=condition=Ready issuer/essai-racine -n essai-cm --timeout=60s
```

```text
namespace/essai-cm created
issuer.cert-manager.io/essai-racine created
issuer.cert-manager.io/essai-racine condition met
```

## ⏳ Exercise 1: lifetime and renewal time

Ask for a certificate valid for 2 hours (`duration`), to be renewed 90
minutes before expiry (`renewBefore`), then read its dates (`pas avant` means
"not before", `échéance` "expiry", `renouvellement` "renewal"):

```bash
cat <<'YAML' | kubectl apply -n essai-cm -f -
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: guichet-tls
spec:
  secretName: guichet-tls
  dnsNames: [guichet.essai-cm.svc]
  duration: 2h
  renewBefore: 90m
  issuerRef: {name: essai-racine, kind: Issuer}
YAML
kubectl wait --for=condition=Ready certificate/guichet-tls -n essai-cm --timeout=60s; kubectl get certificate guichet-tls -n essai-cm -o jsonpath='pas avant={.status.notBefore} échéance={.status.notAfter} renouvellement={.status.renewalTime}{"\n"}'
```

```text
certificate.cert-manager.io/guichet-tls created
certificate.cert-manager.io/guichet-tls condition met
pas avant=2026-11-21T05:13:50Z échéance=2026-11-21T07:13:50Z renouvellement=2026-11-21T05:43:50Z
```

Expiry 2 hours after issue, and renewal planned 30 minutes after issue: 2
hours minus 90 minutes. cert-manager will renew on its own at that time,
without waiting for you. A `renewBefore` too close to `duration` renews
constantly, a `renewBefore` too short leaves little margin if issuing fails.

## ♻️ Exercise 2: the deleted Secret comes back

Note the fingerprint of the certificate's public key, delete its Secret, wait
10 seconds, and look:

```bash
kubectl get secret guichet-tls -n essai-cm -o jsonpath='{.data.tls\.key}' | base64 -d | openssl pkey -pubout 2>/dev/null | sha256sum | cut -c1-16; kubectl delete secret guichet-tls -n essai-cm; sleep 10; kubectl get secret guichet-tls -n essai-cm; kubectl get secret guichet-tls -n essai-cm -o jsonpath='{.data.tls\.key}' | base64 -d | openssl pkey -pubout 2>/dev/null | sha256sum | cut -c1-16
```

```text
fd497c14300f5ad9
secret "guichet-tls" deleted from essai-cm namespace
NAME          TYPE                DATA   AGE
guichet-tls   kubernetes.io/tls   3      10s
11f8274fa58427fa
```

The Secret came back, with another key. cert-manager watches the Secret
described by the Certificate, and recreates it as soon as it is missing. Each
issue goes through a CertificateRequest (`PRET` means "ready"):

```bash
kubectl get certificaterequests -n essai-cm -o custom-columns=NOM:.metadata.name,PRET:.status.conditions[0].status
```

```text
NOM             PRET
guichet-tls-2   True
```

`guichet-tls-2`: this is the Certificate's second request. Deleting the
Secret is therefore a way to force a new issue.

## 🔑 Exercise 3: change the request, keep or change the key

Read the key rotation policy, then add a name to the certificate, and compare
the fingerprints before and after:

```bash
kubectl get certificate guichet-tls -n essai-cm -o jsonpath='rotationPolicy={.spec.privateKey.rotationPolicy}{"\n"}'; kubectl get secret guichet-tls -n essai-cm -o jsonpath='{.data.tls\.key}' | base64 -d | openssl pkey -pubout 2>/dev/null | sha256sum | cut -c1-16; kubectl patch certificate guichet-tls -n essai-cm --type merge -p '{"spec":{"dnsNames":["guichet.essai-cm.svc","guichet"]}}'; sleep 10; kubectl get secret guichet-tls -n essai-cm -o jsonpath='{.data.tls\.key}' | base64 -d | openssl pkey -pubout 2>/dev/null | sha256sum | cut -c1-16
```

```text
rotationPolicy=
11f8274fa58427fa
certificate.cert-manager.io/guichet-tls patched
d21b32401ea48a0b
```

The policy is empty, hence the default one, and the key changed: at each new
issue, cert-manager makes a new key. Set the policy to `Never`, then change
the names again, twice:

```bash
kubectl patch certificate guichet-tls -n essai-cm --type merge -p '{"spec":{"privateKey":{"rotationPolicy":"Never"},"dnsNames":["guichet.essai-cm.svc"]}}'; sleep 10; kubectl get secret guichet-tls -n essai-cm -o jsonpath='{.data.tls\.key}' | base64 -d | openssl pkey -pubout 2>/dev/null | sha256sum | cut -c1-16; kubectl patch certificate guichet-tls -n essai-cm --type merge -p '{"spec":{"dnsNames":["guichet.essai-cm.svc","guichet"]}}'; sleep 10; kubectl get secret guichet-tls -n essai-cm -o jsonpath='{.data.tls\.key}' | base64 -d | openssl pkey -pubout 2>/dev/null | sha256sum | cut -c1-16
```

```text
certificate.cert-manager.io/guichet-tls patched
d21b32401ea48a0b
certificate.cert-manager.io/guichet-tls patched
d21b32401ea48a0b
```

The key no longer moves. With `rotationPolicy: Never`, cert-manager keeps the
existing key and only changes the certificate. This is useful when the key is
pinned elsewhere, at the cost of a key that never rotates.

## 🚪 Exercise 4: an Issuer only serves its own namespace

In another namespace, ask `essai-racine` for a certificate:

```bash
kubectl create namespace essai-ailleurs; cat <<'YAML' | kubectl apply -n essai-ailleurs -f -
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: voisin-tls
spec:
  secretName: voisin-tls
  dnsNames: [voisin.essai-ailleurs.svc]
  issuerRef: {name: essai-racine, kind: Issuer}
YAML
sleep 10; kubectl get certificate voisin-tls -n essai-ailleurs; kubectl get certificaterequests -n essai-ailleurs -o jsonpath='{range .items[*].status.conditions[*]}{.type}={.status} {.reason}: {.message}{"\n"}{end}'
```

```text
namespace/essai-ailleurs created
certificate.cert-manager.io/voisin-tls created
NAME         READY   SECRET       AGE
voisin-tls   False   voisin-tls   10s
Approved=True cert-manager.io: Certificate request has been approved by cert-manager.io
Ready=False Pending: Referenced "Issuer" not found: issuer.cert-manager.io "essai-racine" not found
```

The request is approved, but stays pending: `essai-racine` does not exist in
that namespace. An `Issuer` only signs for its own namespace. For an issuer
shared by the whole cluster, you need a `ClusterIssuer`.

## 🧹 Clean-up

Delete the two scratch namespaces:

```bash
kubectl delete namespace essai-cm essai-ailleurs
```

```text
namespace "essai-cm" deleted
namespace "essai-ailleurs" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-emettre-un-certificat-avec-cert-manager
dsoxlab check k8s-emettre-un-certificat-avec-cert-manager
```

```text
╭─ Result: k8s-emettre-un-certificat-avec-cert-manager ─╮
│  0 / 100 pts                                          │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests                      │
╰───────────────────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: an internal CA to build with cert-manager,
certificates to issue, and a broken certificate to repair.

```bash
dsoxlab run k8s-emettre-un-certificat-avec-cert-manager
dsoxlab challenge k8s-emettre-un-certificat-avec-cert-manager
```
