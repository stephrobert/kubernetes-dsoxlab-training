# Extract precise information with kubectl

`kubectl get` shows a table designed to be read by a human. For a script, or to
keep a single value, kubectl can extract exactly the fields you want:
**JSONPath** follows a path in the object, and **custom-columns** builds a
table with your own columns. In this course, you find the path of a field, you
extract it from an object then from a list, you build your columns, you filter
and sort, then you see why a Deployment and its Pods do not always say the same
thing.

You work in a scratch namespace, `essai-extraction`, with an `inventaire`
application. The challenge will ask you for other fields on another
application: you will do it on your own, at the end.

Related page: [kubectl](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kubectl-cheat-sheet/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-extraire-avec-kubectl
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster
`boutique` is running there, and your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026.

## 📚 Exercise 1: find the path of a field

Create the scratch namespace and the `inventaire` application, with three nginx
Pods:

```bash
kubectl create namespace essai-extraction
kubectl create deployment inventaire --replicas=3 --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb -n essai-extraction
kubectl rollout status deployment/inventaire -n essai-extraction --timeout=180s | tail -1
```

```text
namespace/essai-extraction created
deployment.apps/inventaire created
deployment "inventaire" successfully rolled out
```

To extract a field, you need to know its **path**. You read it in the YAML of
the object, following the indentation. Here, in the YAML of the Deployment, are
the lines leading to the number of Pods and to the image (`grep` keeps only
them):

```bash
kubectl get deployment inventaire -n essai-extraction -o yaml | sed -n '/^spec:/,/^status:/p' | grep -E '^spec:|^  replicas:|^  template:|^    spec:|^      containers:|^      - image:'
```

```text
spec:
  replicas: 3
  template:
    spec:
      containers:
      - image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

The number of Pods is therefore under `spec`, then `replicas`. The image is
under `spec`, then `template`, then `spec`, then `containers`, at the first item
of the list (the dash), then `image`.

## 📚 Exercise 2: JSONPath on an object

In JSONPath, that path is written with dots, starting from the root of the
object. A list item is designated by its rank in square brackets, starting at
0. `{"\n"}` adds a line break:

```bash
kubectl get deployment inventaire -n essai-extraction -o jsonpath='{.spec.replicas}{"\n"}'
kubectl get deployment inventaire -n essai-extraction -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

```text
3
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

The single quotes around the expression stop the shell from interpreting the
brackets and braces.

## 📚 Exercise 3: JSONPath on a list

`kubectl get pods` returns a **list**: the objects are stored under `.items`.
`[*]` takes all of them:

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o jsonpath='{.items[*].metadata.name}{"\n"}'
```

```text
inventaire-869d7bc7cf-8cvtv inventaire-869d7bc7cf-dsws2 inventaire-869d7bc7cf-pq5ck
```

The three names fit on one line. For one line per Pod, `range … end` repeats a
pattern for each object. Here, the name, a tab (`{"\t"}`), the IP address of
the Pod, then a line break:

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.podIP}{"\n"}{end}'
```

```text
inventaire-869d7bc7cf-8cvtv	10.244.0.25
inventaire-869d7bc7cf-dsws2	10.244.0.26
inventaire-869d7bc7cf-pq5ck	10.244.0.24
```

## 📚 Exercise 4: without a line break

JSONPath writes **only** what you ask for. Remove the `{"\n"}` from the
pattern ("fin" means "end"):

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o jsonpath='{range .items[*]}{.metadata.name}{end}'; echo; echo '(fin)'
```

```text
inventaire-869d7bc7cf-8cvtvinventaire-869d7bc7cf-dsws2inventaire-869d7bc7cf-pq5ck
(fin)
```

The three names are glued into a single word, unreadable and unusable by a
script. When a JSONPath output looks odd, first look for the missing line
break.

## 📚 Exercise 5: your own columns

`custom-columns` builds a table: each column has a title, a colon, then the
path of the field. The path starts from each object, without `.items`:

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o custom-columns=POD:.metadata.name,ADRESSE:.status.podIP
```

```text
POD                           ADRESSE
inventaire-869d7bc7cf-8cvtv   10.244.0.25
inventaire-869d7bc7cf-dsws2   10.244.0.26
inventaire-869d7bc7cf-pq5ck   10.244.0.24
```

`--no-headers` removes the title line, for a script:

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o custom-columns=POD:.metadata.name,ADRESSE:.status.podIP --no-headers
```

```text
inventaire-869d7bc7cf-8cvtv   10.244.0.25
inventaire-869d7bc7cf-dsws2   10.244.0.26
inventaire-869d7bc7cf-pq5ck   10.244.0.24
```

## 📚 Exercise 6: filter and sort

JSONPath can filter a list with `?(…)`. `@` stands for the object being
examined. Here, among the Pods of **all** namespaces (`-A`), keep only those of
`essai-extraction`:

```bash
kubectl get pods -A -o jsonpath='{range .items[?(@.metadata.namespace=="essai-extraction")]}{.metadata.name}{"\n"}{end}'
```

```text
inventaire-869d7bc7cf-8cvtv
inventaire-869d7bc7cf-dsws2
inventaire-869d7bc7cf-pq5ck
```

`--sort-by` sorts the output by a field, here the IP address:

```bash
kubectl get pods -l app=inventaire -n essai-extraction --sort-by=.status.podIP -o custom-columns=POD:.metadata.name,ADRESSE:.status.podIP
```

```text
POD                           ADRESSE
inventaire-869d7bc7cf-pq5ck   10.244.0.24
inventaire-869d7bc7cf-8cvtv   10.244.0.25
inventaire-869d7bc7cf-dsws2   10.244.0.26
```

## 📚 Exercise 7: keep an output in a file

A kubectl output is redirected to a file like any other (`>`). `wc -l` counts
its lines, and `cut` shortens the display:

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o 'custom-columns=POD:.metadata.name,IMAGE:.spec.containers[0].image' > ~/inventaire.txt; wc -l ~/inventaire.txt; head -2 ~/inventaire.txt | cut -c1-60
```

```text
4 /home/ansible/inventaire.txt
POD                           IMAGE
inventaire-869d7bc7cf-8cvtv   nginx:1.30.5@sha256:9bf97bd771
```

Four lines: the title line, then one per Pod.

## 📚 Exercise 8: what the Deployment wants, and what its Pods do

**Pause** the Deployment update, then change its image:

```bash
kubectl rollout pause deployment/inventaire -n essai-extraction
kubectl set image deployment/inventaire nginx=nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703 -n essai-extraction
```

```text
deployment.apps/inventaire paused
deployment.apps/inventaire image updated
```

Compare the image asked by the **Pod template** of the Deployment with the one
of the running Pods:

```bash
kubectl get deployment inventaire -n essai-extraction -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
kubectl get pods -l app=inventaire -n essai-extraction -o jsonpath='{range .items[*]}{.spec.containers[0].image}{"\n"}{end}'
```

```text
nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

The Deployment already **wants** 1.30.6, but its Pods still run 1.30.5: the
pause blocked their replacement. To know what a Deployment asks for, read its
template. To know what runs, read its Pods. Resume the update:

```bash
kubectl rollout resume deployment/inventaire -n essai-extraction && kubectl rollout status deployment/inventaire -n essai-extraction --timeout=180s | tail -1
```

```text
deployment.apps/inventaire resumed
deployment "inventaire" successfully rolled out
```

## 🧹 Clean up

Delete the work file and the scratch namespace:

```bash
rm -f ~/inventaire.txt; kubectl delete namespace essai-extraction
```

```text
namespace "essai-extraction" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-extraire-avec-kubectl
dsoxlab check k8s-extraire-avec-kubectl
```

```text
╭─ Result: k8s-extraire-avec-kubectl ─╮
│  0 / 100 pts                        │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests    │
╰─────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: extract the image a Deployment asks for, then
list its Pods and their node, with JSONPath and with custom-columns.

```bash
dsoxlab run k8s-extraire-avec-kubectl
dsoxlab challenge k8s-extraire-avec-kubectl
```
