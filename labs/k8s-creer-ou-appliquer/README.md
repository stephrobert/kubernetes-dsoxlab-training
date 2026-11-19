# Create or apply: apply, server-side apply and prune

`kubectl create` creates an object, once. `kubectl apply` brings an object to
the state described in a file, as many times as you replay it. In this course,
you compare the two, you apply a whole folder, you see the trap of a field
removed from the file, you find out who "owns" each field of an object, you
take over a field with server-side apply, then you delete what is no longer in
the folder.

You work in a scratch namespace, `essai-apply`, with a `colis` application and
an `etiquettes` Deployment. The challenge will ask you for the same thing on
other objects: you will do it on your own, at the end.

Related page: [kubectl create and apply](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kubectl-create-apply/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-creer-ou-appliquer
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster `lab` is
running there, and your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026, with Kubernetes 1.37.

Prepare the scratch namespace and an `appli` folder with two files: the
`colis` Deployment at the root, and its ConfigMap in an `extra` subfolder. Both
objects carry the `app: colis` label:

```bash
kubectl create namespace essai-apply; mkdir -p ~/essai-apply/appli/extra
cat > ~/essai-apply/appli/colis.yaml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: colis
  namespace: essai-apply
  labels:
    app: colis
spec:
  replicas: 2
  selector:
    matchLabels:
      app: colis
  template:
    metadata:
      labels:
        app: colis
    spec:
      containers:
        - name: colis
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
YAML
cat > ~/essai-apply/appli/extra/colis-config.yaml <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: colis-config
  namespace: essai-apply
  labels:
    app: colis
data:
  POIDS_MAX: 30kg
YAML
find ~/essai-apply/appli -type f
```

```text
namespace/essai-apply created
/home/ansible/essai-apply/appli/colis.yaml
/home/ansible/essai-apply/appli/extra/colis-config.yaml
```

## 📚 Exercise 1: create, then apply

Create the Deployment with `create`, twice in a row:

```bash
kubectl create -f ~/essai-apply/appli/colis.yaml
kubectl create -f ~/essai-apply/appli/colis.yaml
```

```text
deployment.apps/colis created
Error from server (AlreadyExists): error when creating "/home/ansible/essai-apply/appli/colis.yaml": deployments.apps "colis" already exists
```

`create` refuses an object that already exists. Now do the same with `apply`:

```bash
kubectl apply -f ~/essai-apply/appli/colis.yaml
kubectl apply -f ~/essai-apply/appli/colis.yaml
```

```text
Warning: resource deployments/colis is missing the kubectl.kubernetes.io/last-applied-configuration annotation which is required by kubectl apply. kubectl apply should only be used on resources created declaratively by either kubectl create --save-config or kubectl apply. The missing annotation will be patched automatically.
deployment.apps/colis configured
deployment.apps/colis unchanged
```

The first `apply` warns you: the object was created by `create`, it lacks the
`last-applied-configuration` annotation, and `apply` adds it. The second
`apply` changes nothing (`unchanged`): you can replay it safely.

This annotation keeps a copy of the file applied last time. Here is its
beginning:

```bash
kubectl get deployment colis -n essai-apply -o jsonpath='{.metadata.annotations.kubectl\.kubernetes\.io/last-applied-configuration}' | cut -c1-90
```

```text
{"apiVersion":"apps/v1","kind":"Deployment","metadata":{"annotations":{},"labels":{"app":"
```

## 📚 Exercise 2: a folder and its subfolders

`apply -f` accepts a folder. Apply `appli`:

```bash
kubectl apply -f ~/essai-apply/appli/
```

```text
deployment.apps/colis unchanged
```

Only `colis.yaml` was read: the ConfigMap in the `extra` subfolder is ignored.
`-R` (recursive) goes down into subfolders:

```bash
kubectl apply -f ~/essai-apply/appli/ -R
```

```text
deployment.apps/colis unchanged
configmap/colis-config created
```

## 📚 Exercise 3: remove a field from the file

Imagine that an autoscaler now decides the number of Pods. It sets `colis` to
5 replicas (here, you do it in its place with `kubectl scale`):

```bash
kubectl scale deployment colis --replicas=5 -n essai-apply; kubectl rollout status deployment/colis -n essai-apply --timeout=180s | tail -1
```

```text
deployment.apps/colis scaled
deployment "colis" successfully rolled out
```

So the file must no longer set `replicas`. Remove the line:

```bash
sed -i '/^  replicas:/d' ~/essai-apply/appli/colis.yaml; grep -c replicas ~/essai-apply/appli/colis.yaml
```

```text
0
```

Before applying again, ask the server what `apply` would do, without changing
anything (`--dry-run=server`), showing only the number of replicas:

```bash
kubectl apply -f ~/essai-apply/appli/colis.yaml --dry-run=server -o jsonpath='{.spec.replicas}{"\n"}'
```

```text
1
```

1, not 5. `apply` compares the file with the `last-applied` annotation. The
annotation still holds `replicas: 2`, the file no longer does: for `apply`, it
is a field to **remove**. Without a value, a Deployment goes back to 1 replica.
The autoscaler would lose its work.

`kubectl apply set-last-applied` updates the annotation from the file, without
touching the rest of the object. Do it, then run the simulation again:

```bash
kubectl apply set-last-applied -f ~/essai-apply/appli/colis.yaml
kubectl apply -f ~/essai-apply/appli/colis.yaml --dry-run=server -o jsonpath='{.spec.replicas}{"\n"}'
```

```text
deployment.apps/colis configured
5
```

The annotation no longer mentions `replicas`, so `apply` leaves it alone.
Apply for real:

```bash
kubectl apply -f ~/essai-apply/appli/colis.yaml; kubectl get deployment colis -n essai-apply
```

```text
deployment.apps/colis configured
NAME    READY   UP-TO-DATE   AVAILABLE   AGE
colis   5/5     5            5           2s
```

## 📚 Exercise 4: who owns what

Kubernetes records, for each field of an object, which tool wrote it: that is
the **field manager**. Create an `etiquettes` Deployment with `create`:

```bash
kubectl create deployment etiquettes --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb -n essai-apply; kubectl rollout status deployment/etiquettes -n essai-apply --timeout=180s | tail -1
```

```text
deployment.apps/etiquettes created
deployment "etiquettes" successfully rolled out
```

The list of managers is in `metadata.managedFields`:

```bash
kubectl get deployment etiquettes -n essai-apply -o jsonpath='{range .metadata.managedFields[*]}{.manager}{"\t"}{.operation}{"\n"}{end}'
```

```text
kube-controller-manager	Update
kubectl-create	Update
```

`kubectl-create` wrote the object. `kube-controller-manager` updates its
status. Who owns the `image` field? The JSONPath filter keeps only the fields
of `kubectl-create`, and `grep` looks for `f:image` in them (`aucun` means
"none"):

```bash
kubectl get deployment etiquettes -n essai-apply -o jsonpath='{.metadata.managedFields[?(@.manager=="kubectl-create")].fieldsV1}' | grep -o -w 'f:image' || echo '(aucun)'
```

```text
f:image
```

The image belongs to `kubectl-create`.

## 📚 Exercise 5: server-side apply and conflict

A team now wants to drive the image of `etiquettes`. It writes a file that
describes only what it owns (the selector, the Pod template, the image at
version 1.30.6), and applies it with **server-side apply** under its own
manager name, `equipe-etiquettes`:

```bash
cat > ~/essai-apply/etiquettes.yaml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: etiquettes
  namespace: essai-apply
spec:
  selector:
    matchLabels:
      app: etiquettes
  template:
    metadata:
      labels:
        app: etiquettes
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
YAML
kubectl apply --server-side --field-manager=equipe-etiquettes -f ~/essai-apply/etiquettes.yaml
```

```text
error: Apply failed with 1 conflict: conflict with "kubectl-create" using apps/v1: .spec.template.spec.containers[name="nginx"].image
Please review the fields above--they currently have other managers. Here
are the ways you can resolve this warning:
* If you intend to manage all of these fields, please re-run the apply
  command with the `--force-conflicts` flag.
* If you do not intend to manage all of the fields, please edit your
  manifest to remove references to the fields that should keep their
  current managers.
* You may co-own fields by updating your manifest to match the existing
  value; in this case, you'll become the manager if the other manager(s)
  stop managing the field (remove it from their configuration).
See https://kubernetes.io/docs/reference/using-api/server-side-apply/#conflicts
```

The server refuses: the image belongs to `kubectl-create`, and the team wants
to give it another value. That is a **conflict**. The message gives three ways
out. Here, the team really must take over the image: `--force-conflicts`
transfers the field to it:

```bash
kubectl apply --server-side --field-manager=equipe-etiquettes --force-conflicts -f ~/essai-apply/etiquettes.yaml
```

```text
deployment.apps/etiquettes serverside-applied
```

Read the managers again, then the owner of `image`:

```bash
kubectl get deployment etiquettes -n essai-apply -o jsonpath='{range .metadata.managedFields[*]}{.manager}{"\t"}{.operation}{"\n"}{end}'
kubectl get deployment etiquettes -n essai-apply -o jsonpath='{.metadata.managedFields[?(@.manager=="kubectl-create")].fieldsV1}' | grep -o -w 'f:image' || echo '(aucun)'
kubectl get deployment etiquettes -n essai-apply -o jsonpath='{.metadata.managedFields[?(@.manager=="equipe-etiquettes")].fieldsV1}' | grep -o -w 'f:image' || echo '(aucun)'
```

```text
equipe-etiquettes	Apply
kubectl-create	Update
kube-controller-manager	Update
(aucun)
f:image
```

`equipe-etiquettes` shows up, with the `Apply` operation. The `image` field
left `kubectl-create` for it. `kubectl-create` stays in the list, for the
fields it still owns. The Deployment does run 1.30.6:

```bash
kubectl rollout status deployment/etiquettes -n essai-apply --timeout=180s | tail -1; kubectl get deployment etiquettes -n essai-apply -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

```text
deployment "etiquettes" successfully rolled out
nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
```

## 📚 Exercise 6: prune what is no longer in the folder

Create two ConfigMaps with `apply`, as if they came from old files:
`colis-vieux`, with the `app: colis` label, whose file has left the folder, and
`autre`, with the `app: autre` label, which belongs to another application.
`kubectl label --local` adds the label to the YAML without sending anything to
the cluster:

```bash
kubectl create configmap colis-vieux --from-literal=POIDS_MAX=20kg -n essai-apply --dry-run=client -o yaml | kubectl label --local -f - app=colis -o yaml | kubectl apply -f -
kubectl create configmap autre --from-literal=a=1 -n essai-apply --dry-run=client -o yaml | kubectl label --local -f - app=autre -o yaml | kubectl apply -f -
kubectl get configmap -n essai-apply -L app
```

```text
configmap/colis-vieux created
configmap/autre created
NAME               DATA   AGE   APP
autre              1      0s    autre
colis-config       1      3s    colis
colis-vieux        1      0s    colis
kube-root-ca.crt   1      3s    
```

`-L app` adds a column with the value of the `app` label. `--prune` deletes the
objects created by `apply` that are no longer in the files. Try it without
saying anything more, as a simulation:

```bash
kubectl apply -f ~/essai-apply/appli -R --prune --dry-run=server
```

```text
error: all resources selected for prune without explicitly passing --all. To prune all resources, pass the --all flag. If you did not mean to prune all resources, specify a label selector
```

kubectl refuses: with no limit, it could delete far more than planned. It asks
for a label selector, or `--all`. Limit the pruning to the `app=colis` objects,
still as a simulation:

```bash
kubectl apply -f ~/essai-apply/appli -R --prune -l app=colis --dry-run=server
```

```text
deployment.apps/colis unchanged (server dry run)
configmap/colis-config unchanged (server dry run)
W1119 19:24:06.068201   49079 prune.go:71] Deprecated: kubectl apply will no longer prune non-namespaced resources by default when used with the --namespace flag in a future release. To preserve the current behaviour, list the resources you want to target explicitly in the --prune-allowlist flag.
configmap/colis-vieux pruned (server dry run)
Warning: v1 Endpoints is deprecated in v1.33+; use discovery.k8s.io/v1 EndpointSlice
```

Only `colis-vieux` would go (`pruned`). `autre` is not listed: its label does
not match. The `W1119` and `Warning` lines are kubectl warnings about future
changes, with no effect here. Run the pruning for real, then check:

```bash
kubectl apply -f ~/essai-apply/appli -R --prune -l app=colis
kubectl get configmap -n essai-apply -L app
```

```text
deployment.apps/colis unchanged
configmap/colis-config unchanged
W1119 19:24:07.616119   49090 prune.go:71] Deprecated: kubectl apply will no longer prune non-namespaced resources by default when used with the --namespace flag in a future release. To preserve the current behaviour, list the resources you want to target explicitly in the --prune-allowlist flag.
configmap/colis-vieux pruned
Warning: v1 Endpoints is deprecated in v1.33+; use discovery.k8s.io/v1 EndpointSlice
NAME               DATA   AGE   APP
autre              1      4s    autre
colis-config       1      7s    colis
kube-root-ca.crt   1      7s    
```

`colis-vieux` is gone, `autre` is untouched.

## 🧹 Clean up

Delete the scratch namespace and the work folder:

```bash
kubectl delete namespace essai-apply; rm -rf ~/essai-apply
```

```text
namespace "essai-apply" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-creer-ou-appliquer
dsoxlab check k8s-creer-ou-appliquer
```

```text
╭─ Result: k8s-creer-ou-appliquer ──╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests  │
╰───────────────────────────────────╯
```

0 out of 4: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: apply a whole folder, let an autoscaler
decide the replicas, hand an image over to a team with server-side apply, and
prune without breaking anything.

```bash
dsoxlab run k8s-creer-ou-appliquer
dsoxlab challenge k8s-creer-ou-appliquer
```
