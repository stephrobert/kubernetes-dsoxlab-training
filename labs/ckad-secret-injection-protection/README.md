# Take a password out of a Deployment manifest

An application is already running, and its API token is written **in clear
text** in the manifest of its Deployment. This manifest is versioned,
reviewed, copied into backups: anything that reads it also reads the token.
The lesson moves such a value into a Secret by applying the manifest again.
This course takes another path, `kubectl set env`, and looks at where the
token stays anyway: in an annotation of the Deployment and in its history. It
ends with the step that settles the problem for good: changing the token.

You work in a scratch namespace, `essai-protection`, with a `facture`
application that uses an API token. The challenge will ask you to handle the
password of another application: you will do it on your own, at the end.

Related page: [Kubernetes Secrets](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/secrets/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-secret-injection-protection
```

You are now connected to `k8s-cp.lab`, the node that drives the kubeadm
cluster (the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026, with Kubernetes v1.37.2.

## 📚 Exercise 1: a token in clear text, set by kubectl apply

Create the scratch namespace, then the `facture` Deployment with
`kubectl apply`, as you usually do from a versioned file. Its API token,
`JETON_API`, is written in clear text:

```bash
kubectl create namespace essai-protection
cat > ~/facture.yaml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: facture
spec:
  replicas: 1
  selector:
    matchLabels:
      app: facture
  template:
    metadata:
      labels:
        app: facture
    spec:
      terminationGracePeriodSeconds: 2
      containers:
        - name: facture
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sleep", "86400"]
          env:
            - name: JETON_API
              value: Orage-77
YAML
kubectl apply -n essai-protection -f ~/facture.yaml
kubectl rollout status deployment/facture -n essai-protection --timeout=120s | tail -1
```

```text
namespace/essai-protection created
deployment.apps/facture created
deployment "facture" successfully rolled out
```

Count the lines of the manifest that contain the token, then show them.
`grep -n` gives their number, and `cut` trims lines that are too long:

```bash
kubectl get deployment facture -n essai-protection -o yaml | grep -c 'Orage-77'
kubectl get deployment facture -n essai-protection -o yaml | grep -n 'Orage-77' | cut -c1-120
```

```text
2
7:      {"apiVersion":"apps/v1","kind":"Deployment","metadata":{"annotations":{},"name":"facture","namespace":"essai-pro
37:          value: Orage-77
```

Two lines. Line 37 is the `env` field. Line 7 is the
`kubectl.kubernetes.io/last-applied-configuration` annotation: `kubectl apply`
keeps a full copy of the applied manifest there, token included.

## 📚 Exercise 2: a Secret written with stringData

In a Secret manifest, the `stringData` field accepts the value as is:
Kubernetes encodes it for you. The key is called `api` here:

```bash
cat > ~/facture-api.yaml <<'YAML'
apiVersion: v1
kind: Secret
metadata:
  name: facture-api
type: Opaque
stringData:
  api: Orage-77
YAML
kubectl apply -n essai-protection -f ~/facture-api.yaml
kubectl get secret facture-api -n essai-protection -o jsonpath='{.data}{"\n"}'
```

```text
secret/facture-api created
{"api":"T3JhZ2UtNzc="}
```

The Secret stores the value encoded in base64, in `data`. The
`~/facture-api.yaml` file, however, contains the token in clear text: do not
version it.

## 📚 Exercise 3: set env, then the annotation that stays

`kubectl set env --from=secret/<name>` creates one variable per key of the
Secret, which **refers** to the Secret instead of carrying the value. The
name of the variable is the key in uppercase, preceded by the given prefix:
`JETON_` plus `API` gives `JETON_API`, the variable that already exists, and
which is replaced.

```bash
kubectl set env deployment/facture --from=secret/facture-api --prefix=JETON_ -n essai-protection
kubectl rollout status deployment/facture -n essai-protection --timeout=120s | tail -1
kubectl set env deployment/facture --list -n essai-protection
```

```text
Warning: key api transferred to API
deployment.apps/facture env updated
deployment "facture" successfully rolled out
# Deployment facture, container facture
# JETON_API from secret facture-api, key api
```

The warning only says that the `api` key was turned to uppercase to become a
variable name. `JETON_API` now comes from the Secret. Look for the token in
the manifest again:

```bash
kubectl get deployment facture -n essai-protection -o yaml | grep -c 'Orage-77'
kubectl get deployment facture -n essai-protection -o yaml | grep -n 'Orage-77' | cut -c1-120
```

```text
1
7:      {"apiVersion":"apps/v1","kind":"Deployment","metadata":{"annotations":{},"name":"facture","namespace":"essai-pro
```

The `env` field is clean, but the annotation keeps the token: `kubectl set
env` does not update it (nor does `kubectl edit`). Only `kubectl apply`
rewrites it. Two ways to get rid of it: apply the whole corrected manifest
again, as in the lesson, or remove the annotation. Here, remove it: the final
`-` of `kubectl annotate` deletes an annotation.

```bash
kubectl annotate deployment facture kubectl.kubernetes.io/last-applied-configuration- -n essai-protection
kubectl get deployment facture -n essai-protection -o yaml | grep -c 'Orage-77'
```

```text
deployment.apps/facture annotated
0
```

The manifest no longer contains the token. The application still receives
it:

```bash
sleep 3; kubectl exec deploy/facture -n essai-protection -- sh -c 'echo JETON_API=$JETON_API'
```

```text
JETON_API=Orage-77
```

## 📚 Exercise 4: the history keeps the token

The Deployment was changed in place. Its history has two revisions:

```bash
kubectl rollout history deployment/facture -n essai-protection
```

```text
deployment.apps/facture
REVISION  CHANGE-CAUSE
1         <none>
2         <none>
```

Each revision is a ReplicaSet, kept to allow a rollback. Read revision 1:

```bash
kubectl rollout history deployment/facture -n essai-protection --revision=1 | grep -A1 JETON
kubectl get replicasets -n essai-protection
kubectl get replicasets -n essai-protection -o yaml | grep -c 'Orage-77'
```

```text
      JETON_API:	Orage-77
    Mounts:	<none>
NAME                 DESIRED   CURRENT   READY   AGE
facture-6d5f5b5987   0         0         0       5s
facture-f5945d56f    1         1         1       4s
```

```text title="End of the output"
1
```

The old ReplicaSet, with 0 Pods, still carries the token in clear text. The
Deployment keeps ten of them by default. The token has therefore travelled in
clear text, and can still be read: the only safe fix is to **change** it.
Exercise 6 does it.

## 📚 Exercise 5: who can read the Secret

A Secret only protects if access is restricted. `kubectl auth can-i` answers
`yes` or `no`. You, cluster administrator, can you read the Secrets of the
namespace?

```bash
kubectl auth can-i get secrets -n essai-protection
```

```text
yes
```

The Pods of this namespace run under a service account, `default`, whose full
name is `system:serviceaccount:essai-protection:default`. `--as` asks the
question on its behalf:

```bash
kubectl auth can-i get secrets -n essai-protection --as=system:serviceaccount:essai-protection:default
kubectl auth can-i create pods -n essai-protection --as=system:serviceaccount:essai-protection:default
```

```text
no
no
```

This account can neither read the Secrets through the API, nor create Pods.
The second point matters as much as the first: the Kubernetes documentation
points out that anyone who can create a Pod in a namespace can mount any
Secret of that namespace in it, and therefore read it. Restricting access to
Secrets also means restricting who creates Pods.

## 📚 Exercise 6: change the token through an immutable Secret

Create the new token in a new Secret, `facture-api-v2`, marked
`immutable: true`: nobody can change its value by mistake any more.

```bash
cat > ~/facture-api-v2.yaml <<'YAML'
apiVersion: v1
kind: Secret
metadata:
  name: facture-api-v2
type: Opaque
immutable: true
stringData:
  api: Grele-12
YAML
kubectl apply -n essai-protection -f ~/facture-api-v2.yaml
kubectl patch secret facture-api-v2 -n essai-protection -p '{"stringData":{"api":"Neige-3"}}'
```

```text
secret/facture-api-v2 created
The Secret "facture-api-v2" is invalid: data: Forbidden: field is immutable when `immutable` is set
```

The change is refused. Point the Deployment to the new Secret, check what the
application sees, then delete the old Secret:

```bash
kubectl set env deployment/facture --from=secret/facture-api-v2 --prefix=JETON_ -n essai-protection
kubectl rollout status deployment/facture -n essai-protection --timeout=120s | tail -1
kubectl set env deployment/facture --list -n essai-protection
sleep 3; kubectl exec deploy/facture -n essai-protection -- sh -c 'echo JETON_API=$JETON_API'
kubectl delete secret facture-api -n essai-protection
```

```text
Warning: key api transferred to API
deployment.apps/facture env updated
deployment "facture" successfully rolled out
# Deployment facture, container facture
# JETON_API from secret facture-api-v2, key api
JETON_API=Grele-12
secret "facture-api" deleted from essai-protection namespace
```

The application uses the new token. The old one, `Orage-77`, can still be read
in revision 1, but it is worth nothing once revoked by the service that issued
it. That is what changing a token is for.

## 🧹 Clean up

Delete the work files and the scratch namespace:

```bash
rm -f ~/facture.yaml ~/facture-api.yaml ~/facture-api-v2.yaml
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

Your turn, on your own this time: the password of an application has leaked,
and it is written in clear text in its Deployment. Store the new one in a
Secret, and make the old one disappear from the manifest.

```bash
dsoxlab run ckad-secret-injection-protection
dsoxlab challenge ckad-secret-injection-protection
```
