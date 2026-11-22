# Serve a Gateway over HTTPS

The lesson asks cert-manager for a certificate, declares an Istio Gateway
with an HTTPS listener that uses it, attaches a route to it, then reads the
certificate the listener presents. That is the challenge of this lab: this
course creates no Gateway. It works on the certificate itself, which the
lesson does not show: a certificate that never comes out, what an issued
certificate contains, the name the client checks, trust limited to the
internal CA, and renewal when the Secret disappears.

You work in the `essai-tls` namespace, for the name `essai.formation.test`,
and in a scratch directory, `~/essai-tls`. The challenge uses another name,
another namespace and the Gateway: you will do it on your own, at the end.

Related page: [Serve a Gateway over HTTPS with cert-manager](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/gateway-api-https-cert-manager/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-servir-une-gateway-en-https
```

You are now connected to `k8s-cp.lab`, the control plane of the kubeadm
cluster. cert-manager runs there, with two cluster-wide issuers:
`amorce-auto-signee`, used to create the CA, and `ca-formation`, the internal
CA. Create the scratch namespace:

```bash
kubectl get clusterissuer
kubectl create namespace essai-tls
```

```text
NAME                 READY   AGE
amorce-auto-signee   True    3s
ca-formation         True    3s
namespace/essai-tls created
```

The outputs shown in this course were captured on this machine on
22 November 2026 (Kubernetes v1.37.2, cert-manager v1.21.3).

## 🚫 Exercise 1: a certificate that never comes out

Ask for a certificate from an issuer that does not exist, `ca-absente`, as
after a typo:

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: essai-orphelin
  namespace: essai-tls
spec:
  secretName: essai-orphelin-tls
  dnsNames:
    - orphelin.formation.test
  issuerRef:
    kind: ClusterIssuer
    name: ca-absente
YAML
sleep 10
kubectl -n essai-tls get certificate essai-orphelin
kubectl -n essai-tls get certificaterequest -o jsonpath='{range .items[*]}{.metadata.name}: {range .status.conditions[*]}{.type}={.status} {.reason}: {.message}{"\n"}{end}{end}'
kubectl -n essai-tls delete certificate essai-orphelin
```

```text
certificate.cert-manager.io/essai-orphelin created
NAME             READY   SECRET               AGE
essai-orphelin   False   essai-orphelin-tls   10s
essai-orphelin-1: Approved=True cert-manager.io: Certificate request has been approved by cert-manager.io
Ready=False Pending: Referenced "ClusterIssuer" not found: clusterissuer.cert-manager.io "ca-absente" not found
certificate.cert-manager.io "essai-orphelin" deleted from essai-tls namespace
```

The Certificate stays `READY False`, without saying why. The cause is one
level down: cert-manager creates a **CertificateRequest**, `essai-orphelin-1`,
and that is where the message is, `Referenced "ClusterIssuer" not found`, with
the faulty name. A Gateway waiting for this Secret would never have a
certificate to present.

## 📜 Exercise 2: what an issued certificate contains

Now ask the internal CA for a certificate valid for two hours, and read it.
The cert-manager Secret holds the certificate (`tls.crt`) and the CA that
issued it (`ca.crt`):

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: essai
  namespace: essai-tls
spec:
  secretName: essai-tls
  duration: 2h
  renewBefore: 1h
  dnsNames:
    - essai.formation.test
  issuerRef:
    kind: ClusterIssuer
    name: ca-formation
YAML
kubectl -n essai-tls wait --for=condition=Ready certificate/essai --timeout=60s
mkdir -p ~/essai-tls && cd ~/essai-tls
kubectl -n essai-tls get secret essai-tls -o jsonpath='{.data.tls\.crt}' | base64 -d > essai.crt
kubectl -n essai-tls get secret essai-tls -o jsonpath='{.data.ca\.crt}' | base64 -d > ca.crt
openssl x509 -in essai.crt -noout -subject -issuer -ext subjectAltName -startdate -enddate
```

```text
certificate.cert-manager.io/essai created
certificate.cert-manager.io/essai condition met
subject=
issuer=O = Formation Kubernetes, CN = CA de la formation
X509v3 Subject Alternative Name: critical
    DNS:essai.formation.test
notBefore=Nov 22 23:17:39 2026 GMT
notAfter=Nov 23 01:17:39 2026 GMT
```

The subject is **empty**: cert-manager puts the name in the *Subject
Alternative Name* (SAN) extension, marked `critical`, and that is where
modern clients look for it. The issuer is the course CA, and the validity
lasts exactly the two hours of `duration`. With `renewBefore: 1h`,
cert-manager will renew the certificate one hour before it expires.

## 🏷️ Exercise 3: the name the client checks

An HTTPS client is not satisfied with a valid signature: it also checks that
the certificate carries the name it asked for. `openssl verify` can do both,
with `-verify_hostname`. Check the certificate for its name, then for another
one:

```bash
openssl verify -CAfile ca.crt -verify_hostname essai.formation.test essai.crt
openssl verify -CAfile ca.crt -verify_hostname autre.formation.test essai.crt
echo "code=$?"
```

```text
essai.crt: OK

error 62 at 0 depth lookup: hostname mismatch
error essai.crt: verification failed
code=2
```

Same certificate, same CA, but the second name fails with `hostname
mismatch`. This is the error a browser would see when it comes through a name
the listener does not have in its certificate: the signature is right, the
name is not.

## 🔐 Exercise 4: trust limited to the internal CA

Without `-CAfile`, `openssl` only trusts the public authorities installed on
the machine:

```bash
openssl verify essai.crt
echo "code=$?"
```

```text

error 20 at 0 depth lookup: unable to get local issuer certificate
error essai.crt: verification failed
code=2
```

`unable to get local issuer certificate`: no authority known to the machine
signed this certificate. This is the intended behaviour of an internal CA. A
client will only trust the listener if it is given the course CA, as the
challenge check does.

## 🔄 Exercise 5: renewal when the Secret disappears

cert-manager watches the Secret of each Certificate. Note the serial number
of the certificate and the revision of the Certificate, delete the Secret,
then read both again:

```bash
openssl x509 -in essai.crt -noout -serial
kubectl -n essai-tls get certificate essai -o jsonpath='revision={.status.revision}{"\n"}'
kubectl -n essai-tls delete secret essai-tls
sleep 10
kubectl -n essai-tls get certificate essai -o jsonpath='revision={.status.revision}{"\n"}'
kubectl -n essai-tls get secret essai-tls -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -serial
```

```text
serial=3F3E8F2AB4FF19E8AE22B565C60B329B2D28BD68
revision=1
secret "essai-tls" deleted from essai-tls namespace
revision=2
serial=381729420D73547BCBE37EA8450E6512B5E76834
```

In less than ten seconds, cert-manager recreated the Secret with a **new**
certificate: the revision goes to 2 and the serial number changes. The Secret
keeps its name: whatever references it, such as a listener, has nothing to
change. The `essai.crt` file in the scratch directory stayed the old one: a
copy taken by hand does not follow renewals.

## 🧹 Clean-up

Delete the scratch directory and the namespace, which takes the Certificate
and its Secret with it:

```bash
cd ~ && rm -rf ~/essai-tls
kubectl delete namespace essai-tls --wait=true --timeout=120s
```

```text
namespace "essai-tls" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the
clean-up and then the lab preparation: you get back exactly the starting state
of the challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-servir-une-gateway-en-https
dsoxlab check k8s-servir-une-gateway-en-https
```

```text
╭─ Result: k8s-servir-une-gateway-en-https ─╮
│  0 / 100 pts                              │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests          │
╰───────────────────────────────────────────╯
```

0 out of 5: that is the expected result. The challenge is waiting for
you, untouched.

## 🎯 The challenge

Your turn, on your own this time: ask for the certificate of an application,
hand it to the HTTPS listener of an Istio Gateway, and prove that a client
that only trusts the internal CA reaches it.

```bash
dsoxlab run k8s-servir-une-gateway-en-https
dsoxlab challenge k8s-servir-une-gateway-en-https
```
