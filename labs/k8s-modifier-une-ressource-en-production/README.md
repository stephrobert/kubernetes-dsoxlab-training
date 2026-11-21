# Change a live Deployment without losing a container, and resolve the drift

The lesson shows the ways to change an object in place: `kubectl edit`,
`patch` and `replace`. This course adds cases the lesson does not show: the
same patch keeping or deleting a container depending on its type, a JSON
patch that checks a value before changing it, a patch that only touches the
replica count, a refused edit and the copy it leaves, and a `replace --force`
that recreates the object.

You work in a scratch namespace, `essai-modif`, with a two-container
`kiosque` ("kiosk") Deployment: `vitre` ("window", nginx) and `compteur`
("counter", busybox). The challenge is about another Deployment: you will do
it on your own, at the end.

Related page (in French): [kubectl edit, patch et replace](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-edit-patch-replace/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-modifier-une-ressource-en-production
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

Create the namespace and the Deployment. The last command prints each
container and its image, without the digest:

```bash
kubectl create namespace essai-modif; cat <<YAML | kubectl apply -n essai-modif -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kiosque
spec:
  replicas: 2
  selector:
    matchLabels: {app: kiosque}
  template:
    metadata:
      labels: {app: kiosque}
    spec:
      containers:
        - {name: vitre, image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb}
        - {name: compteur, image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4, command: [sleep, "3600"]}
YAML
kubectl rollout status deployment/kiosque -n essai-modif --timeout=120s; kubectl get deployment kiosque -n essai-modif -o jsonpath='{range .spec.template.spec.containers[*]}{.name}={.image} {end}{"\n"}' | sed 's/@sha256:[0-9a-f]*//g'
```

```text
namespace/essai-modif created
deployment.apps/kiosque created
Waiting for deployment "kiosque" rollout to finish: 0 out of 2 new replicas have been updated...
Waiting for deployment "kiosque" rollout to finish: 0 of 2 updated replicas are available...
Waiting for deployment "kiosque" rollout to finish: 1 of 2 updated replicas are available...
deployment "kiosque" successfully rolled out
vitre=nginx:1.30.5 compteur=busybox:1.38.0 
```

## ⚖️ Exercise 1: the same patch, two effects

Change `vitre`'s image with a `strategic` patch, the default type:

```bash
kubectl patch deployment kiosque -n essai-modif --type strategic -p '{"spec":{"template":{"spec":{"containers":[{"name":"vitre","image":"nginx:1.30"}]}}}}'; kubectl get deployment kiosque -n essai-modif -o jsonpath='{range .spec.template.spec.containers[*]}{.name}={.image} {end}{"\n"}' | sed 's/@sha256:[0-9a-f]*//g'
```

```text
deployment.apps/kiosque patched
vitre=nginx:1.30 compteur=busybox:1.38.0 
```

`vitre` changed, `compteur` is still there. The `strategic` patch knows a
Deployment's structure: it finds the container by its name and only changes
that one. Send exactly the same content with a `merge` patch:

```bash
kubectl patch deployment kiosque -n essai-modif --type merge -p '{"spec":{"template":{"spec":{"containers":[{"name":"vitre","image":"nginx:1.30"}]}}}}'; kubectl get deployment kiosque -n essai-modif -o jsonpath='{range .spec.template.spec.containers[*]}{.name}={.image} {end}{"\n"}' | sed 's/@sha256:[0-9a-f]*//g'
```

```text
deployment.apps/kiosque patched
vitre=nginx:1.30 
```

`compteur` is gone. A `merge` patch replaces a list as a whole: the container
list now only holds `vitre`. Go back to the previous revision:

```bash
kubectl rollout undo deployment/kiosque -n essai-modif >/dev/null; kubectl rollout status deployment/kiosque -n essai-modif --timeout=120s >/dev/null; kubectl get deployment kiosque -n essai-modif -o jsonpath='{range .spec.template.spec.containers[*]}{.name}={.image} {end}{"\n"}' | sed 's/@sha256:[0-9a-f]*//g'
```

```text
Warning: resource deployments/kiosque was previously managed with 'kubectl apply'. Rolling back will not update the kubectl.kubernetes.io/last-applied-configuration annotation, which may cause unexpected behavior on future 'kubectl apply' operations. Consider using 'kubectl apply' with your previous configuration file instead.
vitre=nginx:1.30 compteur=busybox:1.38.0 
```

Both containers are back. The warning points out that `kubectl apply`'s
annotation did not follow: a later `apply` of the original file may surprise
you. To change one container in a list, the `strategic` patch is the right
tool.

## 🔒 Exercise 2: a JSON patch that checks before changing

A JSON patch can start with a `test` operation, which checks a value. If it
is wrong, nothing is changed. Ask to go from 5 to 3 replicas, while there
are 2:

```bash
kubectl patch deployment kiosque -n essai-modif --type json -p '[{"op":"test","path":"/spec/replicas","value":5},{"op":"replace","path":"/spec/replicas","value":3}]'
```

```text
The request is invalid: the server rejected our request due to an error in our request
```

Refused: the `test` failed, and the `replace` was not applied. With the right
starting value (`réplicas` means "replicas"):

```bash
kubectl patch deployment kiosque -n essai-modif --type json -p '[{"op":"test","path":"/spec/replicas","value":2},{"op":"replace","path":"/spec/replicas","value":3}]'; kubectl get deployment kiosque -n essai-modif -o jsonpath='réplicas={.spec.replicas}{"\n"}'
```

```text
deployment.apps/kiosque patched
réplicas=3
```

Accepted. The `test` protects against a change made by someone else between
the moment you read the object and the moment you change it.

## 🔢 Exercise 3: only touch the replica count

`--subresource=scale` sends the patch to the Deployment's `scale`
sub-object, which only holds the replica count:

```bash
kubectl patch deployment kiosque -n essai-modif --subresource=scale --type merge -p '{"spec":{"replicas":4}}'; kubectl get deployment kiosque -n essai-modif -o jsonpath='réplicas={.spec.replicas}{"\n"}'
```

```text
scale.autoscaling/kiosque patched
réplicas=4
```

The patch cannot touch anything else. This is also what `kubectl scale` uses,
and an RBAC right on `deployments/scale` is enough to do it.

## ✏️ Exercise 4: a refused edit

`kubectl edit` opens the object in an editor. Here, the editor is replaced by
a `sed` that writes an invalid value: `replicas: quatre` ("four").

```bash
EDITOR='sed -i s/replicas:[[:space:]]4/replicas:\ quatre/' kubectl edit deployment kiosque -n essai-modif 2>&1 | tail -3
```

```text
error: deployments.apps "kiosque" is invalid
A copy of your changes has been stored to "/tmp/kubectl-edit-4194016663.yaml"
error: Edit cancelled, no valid changes were saved.
```

The API refuses, and kubectl keeps your changes in a copy under `/tmp`. Look
at it:

```bash
ls -t /tmp/kubectl-edit-*.yaml 2>/dev/null | head -1 | xargs -r grep -m1 -n 'replicas: quatre'
```

```text
23:  replicas: quatre
```

The copy holds the faulty line. With a real editor, you fix that copy and
apply it, without starting over.

## 💥 Exercise 5: replace --force recreates the object

Export the Deployment, then replace it with `--force`, and compare its UID
before and after:

```bash
kubectl get deployment kiosque -n essai-modif -o jsonpath='uid={.metadata.uid}{"\n"}'; kubectl get deployment kiosque -n essai-modif -o yaml > ~/kiosque.yaml; kubectl replace --force -f ~/kiosque.yaml; kubectl get deployment kiosque -n essai-modif -o jsonpath='uid={.metadata.uid}{"\n"}'
```

```text
uid=39db13d0-f702-4d2d-83e9-113c7882d038
deployment.apps "kiosque" deleted from essai-modif namespace
deployment.apps/kiosque replaced
uid=d4e31f4b-187c-4487-9417-5d96ca373e74
```

Another UID: `--force` deletes the object then recreates it. All its Pods were
replaced, and anything that referred to it by UID is lost. This is the last
resort when an immutable field must change, not a way to change an object in
production.

## 🧹 Clean-up

Delete the scratch namespace, the exported file and the edit's copy:

```bash
kubectl delete namespace essai-modif; rm -f ~/kiosque.yaml /tmp/kubectl-edit-*.yaml
```

```text
namespace "essai-modif" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-modifier-une-ressource-en-production
dsoxlab check k8s-modifier-une-ressource-en-production
```

```text
╭─ Result: k8s-modifier-une-ressource-en-production ─╮
│  0 / 100 pts                                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests                   │
╰────────────────────────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a production Deployment to change without
losing its side container, then a drift to resolve.

```bash
dsoxlab run k8s-modifier-une-ressource-en-production
dsoxlab challenge k8s-modifier-une-ressource-en-production
```
