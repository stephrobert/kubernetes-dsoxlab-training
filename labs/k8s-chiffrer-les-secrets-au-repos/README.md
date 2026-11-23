# Encrypt Secrets at rest

The lesson shows that a Secret is written to etcd in clear text, how to ask
the API server to encrypt it before writing it, why the Secrets already there
must be rewritten, and how to limit who reads them with RBAC. This course has
you perform these steps on a real kubeadm cluster, with another provider than
the challenge's (`aescbc`), then has you roll back cleanly.

You work in the `essai-secrets` namespace, with a configuration stored in
`/etc/kubernetes/essai-chiffrement`. The challenge uses another namespace,
another provider and other permissions: you will do it on your own, at the
end.

Related page: [Protect Kubernetes Secrets](https://www.stephane-robert.info/en/docs/devsecops/secrets/protect-kubernetes-secrets/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-chiffrer-les-secrets-au-repos
```

You are now connected to `k8s-cp.lab`, the node that runs the API server and
etcd. Your kubectl already targets the cluster. **Keep the same terminal
until the clean-up**: the function and the key defined below only exist in
it.

The outputs shown in this course were captured on this machine on
23 November 2026, with Kubernetes v1.37.2 and etcd 3.7.0.

## 🔍 Exercise 1: read a Secret directly in etcd

Create the scratch namespace and a Secret. Then define an `etcd_get`
function, which saves you from repeating the three certificates etcdctl
needs, and read the Secret in etcd:

```bash
kubectl create namespace essai-secrets
kubectl -n essai-secrets create secret generic essai-ancien --from-literal=mot=Essai-Ancien-1
etcd_get() { sudo etcdctl --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key get "$1" --print-value-only; }
etcd_get /registry/secrets/essai-secrets/essai-ancien | grep -a -o Essai-Ancien-1
etcd_get /registry/secrets/essai-secrets/essai-ancien | head -c 7 | tr -c '[:print:]' '.'; echo
```

```text
namespace/essai-secrets created
secret/essai-ancien created
Essai-Ancien-1
k8s....
```

The value can be read as is in etcd, without going through the API or RBAC.
The stored value starts with `k8s` followed by unreadable bytes (shown here
as dots): that is the mark of an object that is **not encrypted**. The `-a`
option makes grep read the value as text, although it is binary. It replaces
the `strings` command, which is not installed on this node.

## 🔐 Exercise 2: turn on encryption with aescbc

Write an encryption configuration. The **first** provider in the list
encrypts new writes, and all of them are used to read: `aescbc` first, then
`identity` (no encryption) to read what is still in clear text. The key is 32
bytes, encoded in base64.

```bash
CLE=$(head -c 32 /dev/urandom | base64)
sudo mkdir -p /etc/kubernetes/essai-chiffrement
sudo tee /etc/kubernetes/essai-chiffrement/config.yaml >/dev/null <<EOF
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - aescbc:
          keys:
            - name: essai1
              secret: $CLE
      - identity: {}
EOF
sudo chmod 600 /etc/kubernetes/essai-chiffrement/config.yaml
```

The API server runs in a container, described by the manifest
`/etc/kubernetes/manifests/kube-apiserver.yaml`. You must add two flags to it
(the path of the configuration, and its automatic reload), then the volume
that makes this directory visible inside the container. First back up the
manifest **outside** `/etc/kubernetes/manifests`, which the kubelet watches,
then change it with a short Python program:

```bash
sudo cp /etc/kubernetes/manifests/kube-apiserver.yaml /var/backups/kube-apiserver.avant-essai.yaml
sudo python3 - <<'PY'
import yaml
chemin = "/etc/kubernetes/manifests/kube-apiserver.yaml"
m = yaml.safe_load(open(chemin))
c = m["spec"]["containers"][0]
c["command"] += ["--encryption-provider-config=/etc/kubernetes/essai-chiffrement/config.yaml",
                 "--encryption-provider-config-automatic-reload=true"]
c["volumeMounts"].append({"name": "essai-chiffrement", "mountPath": "/etc/kubernetes/essai-chiffrement", "readOnly": True})
m["spec"]["volumes"].append({"name": "essai-chiffrement", "hostPath": {"path": "/etc/kubernetes/essai-chiffrement", "type": "DirectoryOrCreate"}})
open(chemin, "w").write(yaml.safe_dump(m, sort_keys=False))
PY
sleep 20; until kubectl get --raw /healthz >/dev/null 2>&1; do sleep 3; done; echo "API revenue"
```

```text
API revenue
```

The kubelet saw the manifest change and recreated the API server: it
answered again 44 seconds after the change. Create a second Secret and look
at how it is stored:

```bash
kubectl -n essai-secrets create secret generic essai-nouveau --from-literal=mot=Essai-Nouveau-2
etcd_get /registry/secrets/essai-secrets/essai-nouveau | head -c 25; echo
etcd_get /registry/secrets/essai-secrets/essai-nouveau | grep -a -c Essai-Nouveau
```

```text
secret/essai-nouveau created
k8s:enc:aescbc:v1:essai1:
0
```

The prefix `k8s:enc:aescbc:v1:essai1:` names the provider and the key that
encrypted the value, and the value no longer appears even once.

## ♻️ Exercise 3: rewrite the Secrets already there

`essai-ancien` was written before encryption. Count how many times its value
appears in etcd, then rewrite the Secrets of the namespace: `kubectl replace`
sends them back to the API server, which encrypts them as it writes them.

```bash
etcd_get /registry/secrets/essai-secrets/essai-ancien | grep -a -c Essai-Ancien
kubectl -n essai-secrets get secrets -o json | kubectl replace -f -
etcd_get /registry/secrets/essai-secrets/essai-ancien | head -c 25; echo
kubectl -n essai-secrets get secret essai-ancien -o jsonpath='{.data.mot}' | base64 -d; echo
```

```text
1
secret/essai-ancien replaced
secret/essai-nouveau replaced
k8s:enc:aescbc:v1:essai1:
Essai-Ancien-1
```

Before the rewrite, the value was still in clear text: changing the
configuration only affects new writes. After it, `essai-ancien` carries the
prefix. Through the API, nothing changes: the API server decrypts on read and
gives back `Essai-Ancien-1`.

## ↩️ Exercise 4: roll back without losing a Secret

To remove encryption, you cannot just remove the flags: the API server would
lose the key, and could no longer read the encrypted Secrets. You must first
put `identity` **first**, keeping `aescbc` to read. Rewrite the
configuration, then wait for the API server to read it again (it checks the
file once a minute):

```bash
sudo tee /etc/kubernetes/essai-chiffrement/config.yaml >/dev/null <<EOF
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - identity: {}
      - aescbc:
          keys:
            - name: essai1
              secret: $CLE
EOF
sleep 70
kubectl -n essai-secrets create secret generic essai-sonde --from-literal=mot=x
etcd_get /registry/secrets/essai-secrets/essai-sonde | head -c 7 | tr -c '[:print:]' '.'; echo
```

```text
secret/essai-sonde created
k8s....
```

The new Secret is written in clear text again. The Secrets already encrypted
stay so until they are rewritten. Count them across the whole cluster,
rewrite every Secret, then count again:

```bash
chiffres() { for cle in $(sudo etcdctl --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key get /registry/secrets/ --prefix --keys-only); do etcd_get "$cle" | head -c 8 | grep -q 'k8s:enc' && echo "$cle"; done | wc -l; }
chiffres
kubectl get secrets -A -o json | kubectl replace -f - | wc -l
chiffres
```

```text
2
18
0
```

Two Secrets were encrypted, `essai-ancien` and `essai-nouveau`. The rewrite
touches the 18 Secrets of the cluster, and none is left encrypted: restoring
the original manifest will no longer lose anything. While encryption was on,
any Secret created elsewhere in the cluster was encrypted too: that is why
the rewrite covers every namespace.

## 👤 Exercise 5: limit reading down to a single Secret

Create a ServiceAccount that can only read `essai-nouveau`, then ask the API
server what it can do, taking its identity with `--as`:

```bash
kubectl -n essai-secrets create serviceaccount essai-lecteur
kubectl -n essai-secrets create role essai-lecture --verb=get --resource=secrets --resource-name=essai-nouveau
kubectl -n essai-secrets create rolebinding essai-lecture --role=essai-lecture --serviceaccount=essai-secrets:essai-lecteur
S=--as=system:serviceaccount:essai-secrets:essai-lecteur
kubectl auth can-i get secret/essai-nouveau -n essai-secrets $S
kubectl auth can-i get secret/essai-ancien -n essai-secrets $S
kubectl auth can-i list secrets -n essai-secrets $S
```

```text
serviceaccount/essai-lecteur created
role.rbac.authorization.k8s.io/essai-lecture created
rolebinding.rbac.authorization.k8s.io/essai-lecture created
yes
no
no
```

It reads `essai-nouveau`, and nothing else. Now give it only the `list` verb,
which looks harmless, and try:

```bash
kubectl -n essai-secrets create role essai-liste --verb=list --resource=secrets
kubectl -n essai-secrets create rolebinding essai-liste --role=essai-liste --serviceaccount=essai-secrets:essai-lecteur
kubectl -n essai-secrets get secrets $S -o jsonpath='{range .items[*]}{.metadata.name}={.data.mot}{"\n"}{end}'
kubectl -n essai-secrets get secret essai-ancien $S
```

```text
role.rbac.authorization.k8s.io/essai-liste created
rolebinding.rbac.authorization.k8s.io/essai-liste created
essai-ancien=RXNzYWktQW5jaWVuLTE=
essai-nouveau=RXNzYWktTm91dmVhdS0y
essai-sonde=eA==
Error from server (Forbidden): secrets "essai-ancien" is forbidden: User "system:serviceaccount:essai-secrets:essai-lecteur" cannot get resource "secrets" in API group "" in the namespace "essai-secrets"
```

With `list`, the account receives the **value** of every Secret in the
namespace (encoded in base64, not encrypted), while `get` on `essai-ancien`
is still refused. Never grant `list` or `watch` on Secrets to an account
that only needs one Secret.

## 🧹 Clean-up

No Secret has been encrypted since exercise 4: restore the original manifest,
wait for the API server to come back, then delete the configuration, the
backup and the scratch namespace. The last two commands check that the
manifest no longer mentions encryption and that the cluster's Secrets can
still be read:

```bash
sudo cp /var/backups/kube-apiserver.avant-essai.yaml /etc/kubernetes/manifests/kube-apiserver.yaml
sleep 20; until kubectl get --raw /healthz >/dev/null 2>&1; do sleep 3; done; echo "API revenue"
sudo rm -rf /etc/kubernetes/essai-chiffrement /var/backups/kube-apiserver.avant-essai.yaml
kubectl delete namespace essai-secrets --wait=true --timeout=120s
sudo grep -c encryption-provider /etc/kubernetes/manifests/kube-apiserver.yaml
kubectl get secrets -A --no-headers | wc -l
```

```text
API revenue
namespace "essai-secrets" deleted
0
15
```

The manifest is back to its original state, and the 15 remaining Secrets can
be read. Then leave the machine and reset the lab. `dsoxlab reset` replays
the clean-up and then the lab preparation: you get back exactly the starting
state of the challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-chiffrer-les-secrets-au-repos
dsoxlab check k8s-chiffrer-les-secrets-au-repos
```

```text
╭─ Result: k8s-chiffrer-les-secrets-au-repos ─╮
│  0 / 100 pts                                │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests            │
╰─────────────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: encrypt Secrets at rest with secretbox,
rewrite those of a namespace where they are still in clear text, and reduce a
ServiceAccount to the only Secret it needs.

```bash
dsoxlab run k8s-chiffrer-les-secrets-au-repos
dsoxlab challenge k8s-chiffrer-les-secrets-au-repos
```
