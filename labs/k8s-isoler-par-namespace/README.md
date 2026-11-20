# Organise applications in namespaces

A cluster often hosts several teams or several applications. **Namespaces**
put them in separate spaces: each object belongs to a namespace, and two
objects can bear the same name if they are in two different namespaces. But a
namespace does not cut the network: a Pod can reach a Service of another
namespace, if it names it correctly. The lesson shows these rules. This course
makes you see the cases where people get it wrong: a manifest that lands in
the namespace of the context, a `-n` that contradicts the manifest, a short
name that does not resolve, and a namespace that refuses to go away.

You work with two scratch namespaces, `essai-nord` and `essai-sud`. The
challenge will ask you to put another application back in order: you will do
it on your own, at the end.

Related page: [Kubernetes Namespaces](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/namespaces/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-isoler-par-namespace
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster
`boutique` is running there, and your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026.

## 📚 Exercise 1: the namespaces, and the one you target without saying so

List the namespaces of the cluster:

```bash
kubectl get namespaces
```

```text
NAME                 STATUS   AGE
caisse               Active   1s
default              Active   7h14m
kube-node-lease      Active   7h14m
kube-public          Active   7h14m
kube-system          Active   7h14m
local-path-storage   Active   7h14m
stock                Active   1s
```

`default` is the default namespace. Those starting with `kube-` belong to
Kubernetes itself. `caisse` and `stock` belong to the challenge, set up by the
lab preparation: do not touch them during the course. Your list may hold
others, left by labs you have already played.

A command without `-n` targets the namespace of your kubectl **context**. Read
it:

```bash
kubectl config view --minify -o jsonpath='{..namespace}'; echo "<- namespace du contexte (vide = default)"
```

```text
<- namespace du contexte (vide = default)
```

Nothing before the arrow: no namespace is set in the context, so commands
without `-n` target `default`.

## 📚 Exercise 2: the same name in two namespaces

Create the two scratch namespaces, then a `reglages` ConfigMap in each, with a
different value. Then look for it without `-n`:

```bash
kubectl create namespace essai-nord; kubectl create namespace essai-sud
kubectl create configmap reglages --from-literal=region=nord -n essai-nord; kubectl create configmap reglages --from-literal=region=sud -n essai-sud
kubectl get configmap reglages
```

```text
namespace/essai-nord created
namespace/essai-sud created
configmap/reglages created
configmap/reglages created
Error from server (NotFound): configmaps "reglages" not found
```

Two `reglages` objects live side by side, one per namespace. Without `-n`,
kubectl looks in `default`, where there is nothing.

## 📚 Exercise 3: one namespace, or all of them

`-n` targets a precise namespace:

```bash
kubectl get configmaps -n essai-nord
```

```text
NAME               DATA   AGE
kube-root-ca.crt   1      0s
reglages           1      0s
```

`kube-root-ca.crt` is set by Kubernetes in every namespace. `-A` (for
`--all-namespaces`) looks everywhere, and adds a `NAMESPACE` column. The filter
only keeps the objects named `reglages`:

```bash
kubectl get configmaps -A --field-selector metadata.name=reglages
```

```text
NAMESPACE    NAME       DATA   AGE
essai-nord   reglages   1      0s
essai-sud    reglages   1      0s
```

## 📚 Exercise 4: where a manifest lands

Write two ConfigMap manifests. The first one, `horaires`, gives no namespace.
The second one, `tarifs`, gives one in `metadata.namespace`: `essai-sud`.

```bash
cat > ~/horaires.yaml <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: horaires
data:
  ouverture: "8h"
YAML
cat > ~/tarifs.yaml <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: tarifs
  namespace: essai-sud
data:
  ticket: "2 euros"
YAML
```

Set the default namespace of the context to `essai-nord`, then apply
`horaires` without `-n`, and look where it is created:

```bash
kubectl config set-context --current --namespace=essai-nord
kubectl apply -f ~/horaires.yaml
kubectl get configmaps -A --field-selector metadata.name=horaires
```

```text
Context "kind-boutique" modified.
configmap/horaires created
NAMESPACE    NAME       DATA   AGE
essai-nord   horaires   1      0s
```

A manifest without a namespace lands in the one of the context. The same file,
applied by a colleague whose context targets `default`, would create the
object in `default`. Now apply `tarifs`, still without `-n`:

```bash
kubectl apply -f ~/tarifs.yaml
kubectl get configmaps -A --field-selector metadata.name=tarifs
```

```text
configmap/tarifs created
NAMESPACE   NAME     DATA   AGE
essai-sud   tarifs   1      0s
```

The namespace written in the manifest wins over the one of the context. And
what if `-n` says something else than the manifest?

```bash
kubectl apply -f ~/tarifs.yaml -n essai-nord
```

```text
error: the namespace from the provided object "essai-sud" does not match the namespace "essai-nord". You must pass '--namespace=essai-sud' to perform this operation.
```

kubectl refuses and creates nothing: it does not choose between two namespaces
that contradict each other. Set the context back to `default` right away,
otherwise your next commands will act in `essai-nord`:

```bash
kubectl config set-context --current --namespace=default
kubectl config view --minify -o jsonpath='{..namespace}{"\n"}'
```

```text
Context "kind-boutique" modified.
default
```

## 📚 Exercise 5: the network crosses namespaces

Create a small `carte` web application in `essai-nord`, with its Service, then
a `visiteur` Pod in `essai-sud`:

```bash
kubectl create deployment carte --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-nord -- sh -c 'echo carte-du-nord > /tmp/index.html && httpd -f -p 8080 -h /tmp'
kubectl expose deployment carte --port=80 --target-port=8080 -n essai-nord
kubectl run visiteur --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --restart=Never -n essai-sud -- sleep 3600
kubectl rollout status deployment/carte -n essai-nord --timeout=120s | tail -1; kubectl wait --for=condition=Ready pod/visiteur -n essai-sud --timeout=60s
```

```text
deployment.apps/carte created
service/carte exposed
pod/visiteur created
deployment "carte" successfully rolled out
pod/visiteur condition met
```

From `visiteur`, try the short name of the Service, then its name followed by
the namespace:

```bash
kubectl exec visiteur -n essai-sud -- wget -qO- -T 3 http://carte
kubectl exec visiteur -n essai-sud -- wget -qO- -T 3 http://carte.essai-nord
```

```text
wget: bad address 'carte'
command terminated with exit code 1
carte-du-nord
```

The short name fails (`bad address`: the name does not exist). The name
followed by the namespace answers. The name resolution file of the Pod
explains why:

```bash
kubectl exec visiteur -n essai-sud -- cat /etc/resolv.conf
```

```text
search essai-sud.svc.cluster.local svc.cluster.local cluster.local
nameserver 10.96.0.10
options ndots:5
```

The `search` line lists the suffixes tried for a short name. The first one is
`essai-sud.svc.cluster.local`: the short name `carte` is therefore only looked
up in the namespace **of the Pod**. With `carte.essai-nord`, the
`svc.cluster.local` suffix completes the name, and it is found. The network,
for its part, was never cut.

## 📚 Exercise 6: a namespace that refuses to go away

Deleting a namespace deletes everything it contains. But an object can carry a
**finalizer**: a mark that asks Kubernetes to wait before deleting it, while a
program does its clean-up work. As long as the mark stays, the object stays,
and so does its namespace. Set a made-up finalizer on `reglages` of
`essai-nord`, then delete the namespace without waiting (`--wait=false`):

```bash
kubectl patch configmap reglages -n essai-nord --type=merge -p '{"metadata":{"finalizers":["formation.exemple.fr/retenue"]}}'
kubectl delete namespace essai-nord --wait=false
```

```text
configmap/reglages patched
namespace "essai-nord" deleted
```

Kubernetes empties the namespace, then says what blocks it in the conditions
of the namespace. The loop reads them again every 5 seconds, 2 minutes at
most, until the `NamespaceFinalizersRemaining` condition turns `True`:

```bash
debut=$SECONDS; for i in $(seq 1 24); do kubectl get namespace essai-nord -o jsonpath='{.status.conditions[?(@.type=="NamespaceFinalizersRemaining")].status}' | grep -q True && break; sleep 5; done; echo "attente : $((SECONDS - debut)) s"
kubectl get namespace essai-nord
kubectl get all,configmaps -n essai-nord
```

```text
attente : 45 s
NAME         STATUS        AGE
essai-nord   Terminating   51s
NAME                 DATA   AGE
configmap/reglages   1      51s
```

The namespace stays in `Terminating`, and it only holds `reglages` any more.
The Deployment, the Pod and the Service of `carte` are gone. Read the
conditions of the namespace:

```bash
kubectl get namespace essai-nord -o jsonpath='{range .status.conditions[*]}{.type}={.status}: {.message}{"\n"}{end}'
```

```text
NamespaceDeletionDiscoveryFailure=False: All resources successfully discovered
NamespaceDeletionGroupVersionParsingFailure=False: All legacy kube types successfully parsed
NamespaceDeletionContentFailure=False: All content successfully deleted, may be waiting on finalization
NamespaceContentRemaining=True: Some resources are remaining: configmaps. has 1 resource instances
NamespaceFinalizersRemaining=True: Some content in the namespace has finalizers remaining: formation.exemple.fr/retenue in 1 resource instances
```

The last two lines name the cause: one ConfigMap remains, held by the
`formation.exemple.fr/retenue` finalizer. Do not read these conditions too
early: during the first seconds, they still say that everything is deleted,
while the content is barely leaving.

Here, no program will come and remove this finalizer: you made it up. Remove
it yourself, and the namespace goes away:

```bash
kubectl patch configmap reglages -n essai-nord --type=merge -p '{"metadata":{"finalizers":null}}'
kubectl wait --for=delete namespace/essai-nord --timeout=60s
```

```text
configmap/reglages patched
namespace/essai-nord condition met
```

On a real cluster, a finalizer belongs to a program, often an operator.
Removing it by hand skips the clean-up work this program was supposed to do.
First find out why it did not do it.

## 🧹 Clean up

Delete the work files and the second scratch namespace:

```bash
rm -f ~/horaires.yaml ~/tarifs.yaml
kubectl delete namespace essai-sud
```

```text
namespace "essai-sud" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-isoler-par-namespace
dsoxlab check k8s-isoler-par-namespace
```

```text
╭─ Result: k8s-isoler-par-namespace ─╮
│  0 / 100 pts                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests   │
╰────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: an application was created in the wrong
namespace. Move it to the right one, then reach it from another namespace.

```bash
dsoxlab run k8s-isoler-par-namespace
dsoxlab challenge k8s-isoler-par-namespace
```
