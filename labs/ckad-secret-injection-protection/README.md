# Take a password out of a Deployment manifest

An application is already running, and its password is written **in clear** in
its Deployment manifest. That manifest is versioned, reviewed, copied into
backups: anything that reads it also reads the password. In this course, you
measure what a Secret protects and what it does not, then you move a clear
value into a Secret, without recreating the Deployment.

You work in a scratch namespace, `essai-protection`, with a `facture`
application that uses an API token. The challenge will ask you to protect the
password of another application: you will do it on your own, at the end.

Related page: [Kubernetes Secrets](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/secrets/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-secret-injection-protection
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: a clear value in a Deployment

Create the scratch namespace and the `facture` application, then give it its
API token **in clear**, with `kubectl set env`. That is the situation you are
going to fix:

```bash
kubectl create namespace essai-protection
kubectl create deployment facture --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-protection -- sleep 86400
kubectl set env deployment/facture JETON_API=Orage-77 -n essai-protection
kubectl rollout status deployment/facture -n essai-protection --timeout=120s | tail -1
```

```text
namespace/essai-protection created
deployment.apps/facture created
deployment.apps/facture env updated
deployment "facture" successfully rolled out
```

`kubectl set env --list` shows the variables of the Deployment:

```bash
kubectl set env deployment/facture --list -n essai-protection
kubectl get deployment facture -n essai-protection -o yaml | grep -c 'Orage-77'
```

```text
# Deployment facture, container busybox
JETON_API=Orage-77
1
```

The token reads in clear, and it appears once in the Deployment manifest.

## 📚 Exercise 2: encoded is not encrypted

A Secret stores its values base64-encoded. Encode the token yourself (`-n`
avoids adding a line break), then decode the result:

```bash
echo -n 'Orage-77' | base64
echo 'T3JhZ2UtNzc=' | base64 -d; echo
```

```text
T3JhZ2UtNzc=
Orage-77
```

Anyone can decode a base64 value, with no key and no password. A Secret
therefore does not make a value unreadable. What it changes:

- the value leaves the application manifest, which is copied everywhere;
- access to the Secret is set apart, with rights that can be restricted
  (exercise 5).

## 📚 Exercise 3: stringData, with no encoding of your own

In a Secret manifest, the `stringData` field takes the value as it is:
Kubernetes encodes it for you. The key is called `api` here:

```bash
cat <<'YAML' | kubectl apply -n essai-protection -f -
apiVersion: v1
kind: Secret
metadata:
  name: facture-api
type: Opaque
stringData:
  api: Orage-77
YAML
kubectl get secret facture-api -n essai-protection -o jsonpath='{.data}{"\n"}'
```

```text
secret/facture-api created
{"api":"T3JhZ2UtNzc="}
```

The Secret does store the encoded value, in `data`. Be careful: this manifest
itself contains the token in clear. Do not version it. To never write it in a
file, `kubectl create secret generic` does the same job in one command.

## 📚 Exercise 4: wire the variable to the Secret

`kubectl set env --from=secret/<name>` creates one variable per key of the
Secret, which **refers** to the Secret instead of holding the value. The
variable name is the key in upper case, preceded by the given prefix: `JETON_`
plus `API` gives `JETON_API`, the variable that already exists, and which is
replaced.

```bash
kubectl set env deployment/facture --from=secret/facture-api --prefix=JETON_ -n essai-protection
kubectl rollout status deployment/facture -n essai-protection --timeout=120s | tail -1
```

```text
Warning: key api transferred to API
deployment.apps/facture env updated
deployment "facture" successfully rolled out
```

The warning only says that the key `api` was put in upper case to become a
variable name. Read the variables again, then look for the token in the
manifest:

```bash
kubectl set env deployment/facture --list -n essai-protection
kubectl get deployment facture -n essai-protection -o yaml | grep -c 'Orage-77'
```

```text
# Deployment facture, container busybox
# JETON_API from secret facture-api, key api
0
```

`JETON_API` now comes from the Secret, and the token is no longer in the
manifest. The application still receives it:

```bash
sleep 3; kubectl exec deploy/facture -n essai-protection -- sh -c 'echo JETON_API=$JETON_API'
```

```text
JETON_API=Orage-77
```

The Deployment was **changed in place**, not recreated: its history keeps the
three versions.

```bash
kubectl rollout history deployment/facture -n essai-protection
```

```text
deployment.apps/facture
REVISION  CHANGE-CAUSE
1         <none>
2         <none>
3         <none>
```

Revision 1 is the creation, 2 the token in clear, 3 the token wired to the
Secret.

## 📚 Exercise 5: who can read the Secret

A Secret only protects if access is restricted. `kubectl auth can-i` answers
`yes` or `no`: can you, the cluster administrator, read the Secrets of the
namespace?

```bash
kubectl auth can-i get secrets -n essai-protection
```

```text
yes
```

And the `default` service account, under which the Pods of this namespace run?
`--as` asks the question on its behalf:

```bash
kubectl auth can-i get secrets -n essai-protection --as=system:serviceaccount:essai-protection:default
```

```text
no
```

The application Pods cannot read the Secrets through the API. They only receive
what their manifest gives them, by reference.

## 📚 Exercise 6: a Secret that can no longer be changed

A Secret can be made **immutable**: nobody can change its values by mistake any
more.

```bash
kubectl patch secret facture-api -n essai-protection -p '{"immutable":true}'
kubectl patch secret facture-api -n essai-protection -p '{"stringData":{"api":"Grele-12"}}'
kubectl get secret facture-api -n essai-protection -o jsonpath='{.data.api}' | base64 -d; echo
```

```text
secret/facture-api patched
The Secret "facture-api" is invalid: data: Forbidden: field is immutable when `immutable` is set
Orage-77
```

The change is refused, and the value did not move. To change an immutable
token, you create a new Secret, and point the Deployment to it.

## 🧹 Clean up

Delete the scratch namespace, with everything in it:

```bash
kubectl delete namespace essai-protection
```

```text
namespace "essai-protection" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset ckad-secret-injection-protection
dsoxlab check ckad-secret-injection-protection
```

```text
╭─ Result: ckad-secret-injection-protection ─╮
│  0 / 100 pts                               │
│  ░░░░░░░░░░░░░░░░░░░░  0/9 tests           │
╰────────────────────────────────────────────╯
```

0 out of 9: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: the password of an application is written in
clear in its Deployment. Put it in a Secret, without breaking the application.

```bash
dsoxlab run ckad-secret-injection-protection
dsoxlab challenge ckad-secret-injection-protection
```
