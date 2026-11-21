# Give a person access through a CertificateSigningRequest

The lesson shows how to give a person access: they make a key and a
certificate request, the cluster signs it through a CertificateSigningRequest
(CSR), and RBAC grants the rights. This course adds cases the lesson does not
show: a refused request, a request sent to the wrong signer, a short-lived
certificate, and a group carried by the certificate's O field.

You work in a scratch directory, `~/essai-csr`, with `essai-*` requests and
an `essai-csr` namespace. The challenge is about another person and another
namespace: you will do it on your own, at the end.

Related page: [The PKI of a Kubernetes cluster](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/cluster-pki/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-donner-un-acces-par-csr
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it, with administrator
rights.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

Every request follows the same pattern: `openssl req` makes a key and a
request, base64-encoded, which the command puts into a CSR.

## ⛔ Exercise 1: a refused request

Create a request for the API server's client signer, then deny it
(`certificat délivré` means "certificate issued"):

```bash
mkdir -p ~/essai-csr; openssl req -new -newkey rsa:2048 -nodes -keyout ~/essai-csr/essai-refus.key -subj '/CN=essai-refus' 2>/dev/null | base64 -w0 > ~/essai-csr/essai-refus.b64; cat <<YAML | kubectl apply -f -
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: essai-refus
spec:
  request: $(cat ~/essai-csr/essai-refus.b64)
  signerName: kubernetes.io/kube-apiserver-client
  usages: [client auth]
  
YAML
kubectl certificate deny essai-refus; kubectl get csr essai-refus; kubectl get csr essai-refus -o jsonpath='certificat délivré : [{.status.certificate}]{"\n"}'
```

```text
certificatesigningrequest.certificates.k8s.io/essai-refus created
certificatesigningrequest.certificates.k8s.io/essai-refus denied
NAME          AGE   SIGNERNAME                            REQUESTOR          REQUESTEDDURATION   CONDITION
essai-refus   1s    kubernetes.io/kube-apiserver-client   kubernetes-admin   <none>              Denied
certificat délivré : []
```

The request is `Denied`, and the certificate field is empty: nothing was
signed. A denial is final. To go back on it, you need a new request.

## ✍️ Exercise 2: the wrong signer

Create a request sent to `kubernetes.io/kubelet-serving`, the signer of the
kubelets' serving certificates, for a plain client:

```bash
openssl req -new -newkey rsa:2048 -nodes -keyout ~/essai-csr/essai-mauvais-signataire.key -subj '/CN=essai-mauvais' 2>/dev/null | base64 -w0 > ~/essai-csr/essai-mauvais-signataire.b64; cat <<YAML | kubectl apply -f -
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: essai-mauvais-signataire
spec:
  request: $(cat ~/essai-csr/essai-mauvais-signataire.b64)
  signerName: kubernetes.io/kubelet-serving
  usages: [client auth]
  
YAML
```

```text
certificatesigningrequest.certificates.k8s.io/essai-mauvais-signataire created
```

Approve it, wait, and read its state:

```bash
kubectl certificate approve essai-mauvais-signataire 2>&1; sleep 5; kubectl get csr essai-mauvais-signataire; kubectl get csr essai-mauvais-signataire -o jsonpath='{range .status.conditions[*]}{.type}: {.message}{"\n"}{end}'
```

```text
certificatesigningrequest.certificates.k8s.io/essai-mauvais-signataire approved
NAME                       AGE   SIGNERNAME                      REQUESTOR          REQUESTEDDURATION   CONDITION
essai-mauvais-signataire   5s    kubernetes.io/kubelet-serving   kubernetes-admin   <none>              Approved,Failed
Approved: This CSR was approved by kubectl certificate approve.
Failed: subject organization is not system:nodes
```

`Approved,Failed`: you approved, but the signer refused to sign. This signer
only issues for nodes (organisation `system:nodes`). Approving is not enough:
the signer also checks what it is asked for. For a person, the signer is
`kubernetes.io/kube-apiserver-client`.

## ⏳ Exercise 3: a certificate that only lives ten minutes

Create a request with `expirationSeconds: 600` and an `essai-lecteurs`
organisation, approve it, then read the issued certificate's subject and
dates:

```bash
openssl req -new -newkey rsa:2048 -nodes -keyout ~/essai-csr/essai-dominique.key -subj '/CN=essai-dominique/O=essai-lecteurs' 2>/dev/null | base64 -w0 > ~/essai-csr/essai-dominique.b64; cat <<YAML | kubectl apply -f -
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: essai-dominique
spec:
  request: $(cat ~/essai-csr/essai-dominique.b64)
  signerName: kubernetes.io/kube-apiserver-client
  usages: [client auth]
  expirationSeconds: 600
YAML
kubectl certificate approve essai-dominique; sleep 3; kubectl get csr essai-dominique -o jsonpath='{.status.certificate}' | base64 -d > ~/essai-csr/essai-dominique.crt; openssl x509 -in ~/essai-csr/essai-dominique.crt -noout -subject -dates
```

```text
certificatesigningrequest.certificates.k8s.io/essai-dominique created
certificatesigningrequest.certificates.k8s.io/essai-dominique approved
subject=O = essai-lecteurs, CN = essai-dominique
notBefore=Nov 21 04:15:50 2026 GMT
notAfter=Nov 21 04:30:50 2026 GMT
```

The certificate carries the requested CN and organisation. Its start
(`notBefore`) is moved back a few minutes, to tolerate a clock that runs a
little ahead: the gap shown is therefore more than ten minutes, but the
certificate does expire ten minutes after it was issued. Temporary access is
granted this way, without having to revoke it later: Kubernetes cannot revoke
a certificate.

## 👥 Exercise 4: the group carried by the O field

Build a kubeconfig with this certificate and its key, then ask the API who
you are:

```bash
SERVEUR=$(kubectl config view --raw -o jsonpath='{.clusters[0].cluster.server}'); kubectl config view --raw -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' | base64 -d > ~/essai-csr/ca.crt; K=~/essai-csr/dominique.kubeconfig; kubectl config set-cluster essai --server=$SERVEUR --certificate-authority=$HOME/essai-csr/ca.crt --embed-certs --kubeconfig=$K >/dev/null; kubectl config set-credentials essai-dominique --client-certificate=$HOME/essai-csr/essai-dominique.crt --client-key=$HOME/essai-csr/essai-dominique.key --embed-certs --kubeconfig=$K >/dev/null; kubectl config set-context essai --cluster=essai --user=essai-dominique --kubeconfig=$K >/dev/null; kubectl config use-context essai --kubeconfig=$K >/dev/null; kubectl auth whoami --kubeconfig=$K
```

```text
ATTRIBUTE                                           VALUE
Username                                            essai-dominique
Groups                                              [essai-lecteurs system:authenticated]
Extra: authentication.kubernetes.io/credential-id   [X509SHA256=116ccd97ee7343173c3244d62fab5daf086c380c8ceb9a6e14ab2eae77467972]
```

The CN becomes the user name, and the organisation (O field) becomes a group:
`essai-lecteurs`. Give rights to this group in a scratch namespace, and try to
read Pods, in that namespace then in `default`:

```bash
kubectl create namespace essai-csr; kubectl create rolebinding lecteurs-du-groupe -n essai-csr --clusterrole=view --group=essai-lecteurs; kubectl get pods -n essai-csr --kubeconfig=$HOME/essai-csr/dominique.kubeconfig; kubectl get pods -n default --kubeconfig=$HOME/essai-csr/dominique.kubeconfig 2>&1 | cut -c1-140
```

```text
namespace/essai-csr created
rolebinding.rbac.authorization.k8s.io/lecteurs-du-groupe created
No resources found in essai-csr namespace.
Error from server (Forbidden): pods is forbidden: User "essai-dominique" cannot list resource "pods" in API group "" in the namespace "defau
```

Reading works in `essai-csr` (no Pod, but no error), and is refused in
`default`. The right comes from the group written in the certificate: any
certificate signed with `O=essai-lecteurs` gets these rights. Choosing a
request's O field therefore means choosing rights, which you check before
approving.

## 🧹 Clean-up

Delete the three requests, the namespace and the scratch directory:

```bash
kubectl delete csr essai-refus essai-mauvais-signataire essai-dominique; kubectl delete namespace essai-csr; rm -rf ~/essai-csr
```

```text
certificatesigningrequest.certificates.k8s.io "essai-refus" deleted
certificatesigningrequest.certificates.k8s.io "essai-mauvais-signataire" deleted
certificatesigningrequest.certificates.k8s.io "essai-dominique" deleted
namespace "essai-csr" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-donner-un-acces-par-csr
dsoxlab check k8s-donner-un-acces-par-csr
```

```text
╭─ Result: k8s-donner-un-acces-par-csr ─╮
│  0 / 100 pts                          │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests      │
╰───────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: read access to a namespace's Pods for a new
person, through a certificate request, and nothing more.

```bash
dsoxlab run k8s-donner-un-acces-par-csr
dsoxlab challenge k8s-donner-un-acces-par-csr
```
