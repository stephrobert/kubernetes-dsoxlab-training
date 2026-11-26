# Give an application an identity: ServiceAccount, Role, RoleBinding

The lesson shows a ServiceAccount, an application's identity, and the token a
Pod uses to talk to the API. This course focuses on these tokens and adds
cases the lesson does not show: having the API check a token, a token that is
worthless once its ServiceAccount is recreated, a token bound to a Pod that
dies with it, and the old-style token, stored in a Secret, which never
expires.

You work in a scratch namespace, `essai-jetons` ("test-tokens"), with a
ServiceAccount `robot`. The tokens are kept in files in your home directory.
The challenge is about another account and other objects: you will do it on
your own, at the end.

Related page: [ServiceAccounts for developers](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/serviceaccounts-for-developers/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-rbac-serviceaccount
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

To check a token, this course sends the API a `TokenReview` object: the API
answers whether the token is valid, for which user, or why it is refused. Each
check prints `authentifié=` ("authenticated"), `utilisateur=` ("user") and
`erreur=` ("error").

## ✅ Exercise 1: have the API check a token

Create the namespace, the ServiceAccount, and a token valid for 10 minutes
with `kubectl create token`. The command prints the token's size:

```bash
kubectl create namespace essai-jetons; kubectl create serviceaccount robot -n essai-jetons; kubectl create token robot -n essai-jetons --duration=10m > ~/jeton-robot; wc -c < ~/jeton-robot
```

```text
namespace/essai-jetons created
serviceaccount/robot created
938
```

Have it checked:

```bash
J=$(cat ~/jeton-robot); cat <<YAML | kubectl create -o jsonpath='authentifié={.status.authenticated} utilisateur={.status.user.username} erreur={.status.error}{"\n"}' -f -
apiVersion: authentication.k8s.io/v1
kind: TokenReview
spec:
  token: $J
YAML
```

```text
authentifié=true utilisateur=system:serviceaccount:essai-jetons:robot erreur=
```

The token is valid, and the API knows who it belongs to. This token is stored
nowhere in the cluster: the API signed it, and knows how to check it.

## 🔄 Exercise 2: recreating the ServiceAccount invalidates its tokens

Delete then recreate `robot`, under the same name, and check the token right
away:

```bash
kubectl delete serviceaccount robot -n essai-jetons; kubectl create serviceaccount robot -n essai-jetons; J=$(cat ~/jeton-robot); cat <<YAML | kubectl create -o jsonpath='authentifié={.status.authenticated} utilisateur={.status.user.username} erreur={.status.error}{"\n"}' -f -
apiVersion: authentication.k8s.io/v1
kind: TokenReview
spec:
  token: $J
YAML
```

```text
serviceaccount "robot" deleted from essai-jetons namespace
serviceaccount/robot created
authentifié=true utilisateur=system:serviceaccount:essai-jetons:robot erreur=
```

Still valid? The API caches the result of a check for about ten seconds. The
token had just been checked. Wait 15 seconds and try again:

```bash
sleep 15; J=$(cat ~/jeton-robot); cat <<YAML | kubectl create -o jsonpath='authentifié={.status.authenticated} utilisateur={.status.user.username} erreur={.status.error}{"\n"}' -f -
apiVersion: authentication.k8s.io/v1
kind: TokenReview
spec:
  token: $J
YAML
```

```text
authentifié= utilisateur= erreur=[invalid bearer token, service account UID (adb05be1-d9f4-4d91-8e35-f8bf3651446d) does not match claim (f8ea8498-dc9f-4726-b7f5-f144aa424186)]
```

Refused: the token carries the old `robot`'s UID, and the new one has another.
A token is tied to a precise object, not to a name. Recreating a
ServiceAccount therefore cuts off all its tokens, after a few seconds at most.

## 🔗 Exercise 3: a token that dies with its Pod

Create a Pod that uses `robot`, then a token bound to that Pod
(`--bound-object-kind` and `--bound-object-name`), and check it. The Pod must
use the same ServiceAccount, otherwise the API refuses to bind the token:

```bash
kubectl run porteur --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-jetons --overrides='{"spec":{"serviceAccountName":"robot"}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/porteur -n essai-jetons --timeout=120s; kubectl create token robot -n essai-jetons --bound-object-kind=Pod --bound-object-name=porteur > ~/jeton-lie; J=$(cat ~/jeton-lie); cat <<YAML | kubectl create -o jsonpath='authentifié={.status.authenticated} utilisateur={.status.user.username} erreur={.status.error}{"\n"}' -f -
apiVersion: authentication.k8s.io/v1
kind: TokenReview
spec:
  token: $J
YAML
```

```text
pod/porteur created
pod/porteur condition met
authentifié=true utilisateur=system:serviceaccount:essai-jetons:robot erreur=
```

Delete the Pod, wait 15 seconds, and check again:

```bash
kubectl delete pod porteur -n essai-jetons; sleep 15; J=$(cat ~/jeton-lie); cat <<YAML | kubectl create -o jsonpath='authentifié={.status.authenticated} utilisateur={.status.user.username} erreur={.status.error}{"\n"}' -f -
apiVersion: authentication.k8s.io/v1
kind: TokenReview
spec:
  token: $J
YAML
```

```text
pod "porteur" deleted from essai-jetons namespace
authentifié= utilisateur= erreur=[invalid bearer token, service account token has been invalidated]
```

The token died with the Pod. This is the case of the tokens the kubelet mounts
into Pods: a token stolen from a deleted Pod is useless.

## 🗝️ Exercise 4: the old-style token, which never expires

Before Kubernetes 1.24, every ServiceAccount received a token stored in a
Secret. You can still create one, with a Secret of type
`kubernetes.io/service-account-token`. Create it, extract the token, then read
three fields of its content: the expiry date (`exp`), the issue date (`iat`)
and the holder (`sub`):

```bash
cat <<'YAML' | kubectl apply -n essai-jetons -f -
apiVersion: v1
kind: Secret
metadata:
  name: ancien-jeton
  annotations:
    kubernetes.io/service-account.name: robot
type: kubernetes.io/service-account-token
YAML
sleep 3; kubectl get secret ancien-jeton -n essai-jetons -o jsonpath='{.data.token}' | base64 -d > ~/jeton-ancien; cut -d. -f2 ~/jeton-ancien | tr '_-' '/+' | base64 -d 2>/dev/null | tr ',' '\n' | grep -E '"(exp|iat|sub)"'; echo
```

```text
secret/ancien-jeton created
"sub":"system:serviceaccount:essai-jetons:robot"}
```

Only `sub` exists: this token has neither an issue date nor an expiry date.
It is valid as long as its Secret exists:

```bash
J=$(cat ~/jeton-ancien); cat <<YAML | kubectl create -o jsonpath='authentifié={.status.authenticated} utilisateur={.status.user.username} erreur={.status.error}{"\n"}' -f -
apiVersion: authentication.k8s.io/v1
kind: TokenReview
spec:
  token: $J
YAML
```

```text
authentifié=true utilisateur=system:serviceaccount:essai-jetons:robot erreur=
```

Delete the Secret and check right away, then 15 seconds later:

```bash
kubectl delete secret ancien-jeton -n essai-jetons; J=$(cat ~/jeton-ancien); cat <<YAML | kubectl create -o jsonpath='authentifié={.status.authenticated} utilisateur={.status.user.username} erreur={.status.error}{"\n"}' -f -
apiVersion: authentication.k8s.io/v1
kind: TokenReview
spec:
  token: $J
YAML
```

```text
secret "ancien-jeton" deleted from essai-jetons namespace
authentifié=true utilisateur=system:serviceaccount:essai-jetons:robot erreur=
```

```bash
sleep 15; J=$(cat ~/jeton-ancien); cat <<YAML | kubectl create -o jsonpath='authentifié={.status.authenticated} utilisateur={.status.user.username} erreur={.status.error}{"\n"}' -f -
apiVersion: authentication.k8s.io/v1
kind: TokenReview
spec:
  token: $J
YAML
```

```text
authentifié= utilisateur= erreur=[invalid bearer token, Token has been invalidated]
```

First still accepted because of the cache, then refused. Such a token, if it
leaks, stays usable until someone thinks of deleting its Secret. Prefer the
time-limited tokens of `kubectl create token`.

## 🧹 Clean-up

Delete the scratch namespace and the token files:

```bash
kubectl delete namespace essai-jetons; rm -f ~/jeton-robot ~/jeton-lie ~/jeton-ancien
```

```text
namespace "essai-jetons" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-rbac-serviceaccount
dsoxlab check cka-rbac-serviceaccount
```

```text
╭─ Result: cka-rbac-serviceaccount ─╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests  │
╰───────────────────────────────────╯
```

0 out of 6: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: an application that must read the Pods of
its namespace with its own identity, and another that must carry no token at
all.

```bash
dsoxlab run cka-rbac-serviceaccount
dsoxlab challenge cka-rbac-serviceaccount
```
