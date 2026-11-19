# Organise applications into namespaces

A cluster often hosts several teams or several applications. **Namespaces** put
them in separate spaces: each object belongs to a namespace, and two objects
can have the same name if they are in two different namespaces. But a
namespace does not cut the network: a Pod can reach a Service of another
namespace, if it names it properly. In this course, you create two namespaces,
you put objects with the same name in them, you change the namespace targeted
by default, then you make two Pods talk across them.

You work with two scratch namespaces, `essai-nord` and `essai-sud`. The
challenge will ask you to organise another application: you will do it on your
own, at the end.

Related page: [Kubernetes Namespaces](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/namespaces/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-isoler-par-namespace
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster
`boutique` is running there, and your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026.

## 📚 Exercise 1: the namespaces, and the one targeted without saying so

List the namespaces of the cluster:

```bash
kubectl get namespaces
```

```text
NAME                 STATUS   AGE
acces                Active   25m
configuration        Active   14m
default              Active   25m
kube-node-lease      Active   25m
kube-public          Active   25m
kube-system          Active   25m
local-path-storage   Active   25m
```

`default` is the default namespace. Those starting with `kube-` belong to
Kubernetes itself. Your list may have others, left by the labs you have already
played, like `acces` and `configuration` here.

A command without `-n` targets the namespace of your kubectl **context**. Read
it ("namespace du contexte (vide = default)" means "context namespace (empty =
default)"):

```bash
kubectl config view --minify -o jsonpath='{..namespace}'; echo "<- namespace du contexte (vide = default)"
```

```text
<- namespace du contexte (vide = default)
```

Nothing before the arrow: no namespace is set in the context, so commands
without `-n` target `default`.

## 📚 Exercise 2: the same name in two namespaces

Create the two scratch namespaces, then a ConfigMap `reglages` in each, with a
different value:

```bash
kubectl create namespace essai-nord; kubectl create namespace essai-sud
kubectl create configmap reglages --from-literal=region=nord -n essai-nord; kubectl create configmap reglages --from-literal=region=sud -n essai-sud
kubectl get configmap reglages -n essai-nord -o jsonpath='{.data.region}{"\n"}'; kubectl get configmap reglages -n essai-sud -o jsonpath='{.data.region}{"\n"}'
```

```text
namespace/essai-nord created
namespace/essai-sud created
configmap/reglages created
configmap/reglages created
nord
sud
```

Two `reglages` objects, one per namespace, each with its own value: a namespace
separates **names**. Without `-n`, kubectl looks in `default`, where there is
nothing:

```bash
kubectl get configmap reglages
```

```text
Error from server (NotFound): configmaps "reglages" not found
```

## 📚 Exercise 3: one namespace, or all of them

`-n` targets a given namespace:

```bash
kubectl get configmaps -n essai-nord
```

```text
NAME               DATA   AGE
kube-root-ca.crt   1      0s
reglages           1      0s
```

`kube-root-ca.crt` is put by Kubernetes in every namespace. `-A` (for
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

## 📚 Exercise 4: change the default namespace of the context

Typing `-n essai-nord` on every command quickly gets tiring. You can set the
default namespace of your context:

```bash
kubectl config set-context --current --namespace=essai-nord
kubectl get configmap reglages -o jsonpath='{.data.region}{"\n"}'
```

```text
Context "kind-boutique" modified.
nord
```

Without `-n`, the command targeted `essai-nord`. It is handy, but misleading:
forget this setting, and your next commands will act in the wrong namespace.
Set `default` back right away:

```bash
kubectl config set-context --current --namespace=default
kubectl config view --minify -o jsonpath='{..namespace}{"\n"}'
```

```text
Context "kind-boutique" modified.
default
```

## 📚 Exercise 5: the network crosses namespaces

Create a small `carte` web application in `essai-nord`, with its Service, then a
`visiteur` Pod in `essai-sud`:

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
followed by the namespace answers. The name resolution file of the Pod explains
why:

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
`svc.cluster.local` suffix completes the name, and it is found. The network
itself was never cut.

## 📚 Exercise 6: deleting a namespace deletes everything in it

Look at what `essai-nord` contains, then delete it:

```bash
kubectl get all -n essai-nord
```

```text
NAME                        READY   STATUS    RESTARTS   AGE
pod/carte-5d5c55866-kbgsf   1/1     Running   0          5s

NAME            TYPE        CLUSTER-IP    EXTERNAL-IP   PORT(S)   AGE
service/carte   ClusterIP   10.96.56.18   <none>        80/TCP    5s

NAME                    READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/carte   1/1     1            1           5s

NAME                              DESIRED   CURRENT   READY   AGE
replicaset.apps/carte-5d5c55866   1         1         1       5s
```

```bash
kubectl delete namespace essai-nord
kubectl get all -n essai-nord
```

```text
namespace "essai-nord" deleted
No resources found in essai-nord namespace.
```

The Pod, the Service, the Deployment and the ReplicaSet left with the
namespace. It is handy for cleaning up, and dangerous for the same reason:
always check the name before deleting a namespace.

## 🧹 Clean up

Delete the second scratch namespace:

```bash
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

Your turn, on your own this time: put an application and a client in two
namespaces, then find out which of the two Service names answers.

```bash
dsoxlab run k8s-isoler-par-namespace
dsoxlab challenge k8s-isoler-par-namespace
```
