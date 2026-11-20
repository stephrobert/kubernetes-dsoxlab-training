# Extract precise information with kubectl

`kubectl get` shows a table designed to be read by a human. For a script, or to
keep a single value, kubectl can extract exactly the fields you want:
**JSONPath** follows a path in the object, and **custom-columns** builds a
table with your own columns. The lesson shows both. This course stops on what
catches people out: a key that contains dots, a case mistake that raises no
error, a forgotten line break, a filter on the state of Pods, and a Deployment
that does not say the same thing as its Pods.

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

The outputs shown in this course were recorded on this machine on 20 November
2026.

## 📚 Exercise 1: find the path of a field

Create the scratch namespace and the `inventaire` application, with three
nginx Pods:

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
the object, following the indentation. Here, in the YAML of the Deployment,
are the lines leading to the number of Pods and to the image (`grep` only keeps
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

The number of Pods is therefore in `spec`, then `replicas`. The image is in
`spec`, then `template`, then `spec`, then `containers`, at the first element
of the list (the dash), then `image`.

## 📚 Exercise 2: a key that contains dots

The Deployment carries an annotation that Kubernetes keeps up to date: the
number of its revision. Show its annotations:

```bash
kubectl get deployment inventaire -n essai-extraction -o yaml | sed -n '/^  annotations:/,/^  [a-z]/p'
```

```text
  annotations:
    deployment.kubernetes.io/revision: "1"
  creationTimestamp: "2026-11-20T14:32:10Z"
```

The key is `deployment.kubernetes.io/revision`. Write it as is in the JSONPath
path:

```bash
kubectl get deployment inventaire -n essai-extraction -o jsonpath='{.metadata.annotations.deployment.kubernetes.io/revision}{"\n"}'; echo "(code $?)"
```

```text

(code 0)
```

An empty line, and code 0: no error. In JSONPath, the dot separates two
levels. kubectl therefore looked for a `deployment` key, then inside it a
`kubernetes` key, then `io/revision`. None of them exists, and kubectl returns
nothing without saying a word. A `\` in front of each dot of the key says that
it is part of the name:

```bash
kubectl get deployment inventaire -n essai-extraction -o jsonpath='{.metadata.annotations.deployment\.kubernetes\.io/revision}{"\n"}'
```

```text
1
```

Kubernetes labels and annotations often contain dots
(`app.kubernetes.io/name`, `kubernetes.io/hostname`): the same `\.` works for
all of them.

## 📚 Exercise 3: a case mistake, without any error

List each Pod with the node that hosts it. `range … end` repeats the pattern
for each Pod, and `{"\t"}` puts a tab. The name of the field is written here
with a mistake, `nodename` instead of `nodeName`:

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.nodename}{"\n"}{end}'; echo "(code $?)"
```

```text
inventaire-869d7bc7cf-4wrrg
inventaire-869d7bc7cf-mrxvn
inventaire-869d7bc7cf-tmqqc
(code 0)
```

The node column is empty, and the code is 0. JSONPath is case sensitive:
`nodename` does not exist, and a missing field returns nothing, not an error.
When a column stays empty, look for the real name of the field in the YAML:

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o yaml | grep -i -m1 'nodename'
```

```text
    nodeName: boutique-control-plane
```

`grep -i` ignores case, and `-m1` stops at the first match. The real name is
`nodeName`, with an uppercase `N`:

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.nodeName}{"\n"}{end}'
```

```text
inventaire-869d7bc7cf-4wrrg	boutique-control-plane
inventaire-869d7bc7cf-mrxvn	boutique-control-plane
inventaire-869d7bc7cf-tmqqc	boutique-control-plane
```

## 📚 Exercise 4: without a line break

JSONPath writes **only** what you ask it to. Remove the `{"\n"}` from the
pattern:

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o jsonpath='{range .items[*]}{.metadata.name}{end}'; echo; echo '(fin)'
```

```text
inventaire-869d7bc7cf-4wrrginventaire-869d7bc7cf-mrxvninventaire-869d7bc7cf-tmqqc
(fin)
```

The three names are glued into a single word, unreadable and useless for a
script. When a JSONPath output looks odd, first look for the missing line
break.

## 📚 Exercise 5: columns of your own

`custom-columns` builds a table: each column has a title, a colon, then the
path of the field. The path starts from each object, without `.items`:

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o custom-columns=POD:.metadata.name,ADRESSE:.status.podIP
```

```text
POD                           ADRESSE
inventaire-869d7bc7cf-4wrrg   10.244.0.118
inventaire-869d7bc7cf-mrxvn   10.244.0.116
inventaire-869d7bc7cf-tmqqc   10.244.0.117
```

`--no-headers` removes the line of titles, for a script:

```bash
kubectl get pods -l app=inventaire -n essai-extraction -o custom-columns=POD:.metadata.name,ADRESSE:.status.podIP --no-headers
```

```text
inventaire-869d7bc7cf-4wrrg   10.244.0.118
inventaire-869d7bc7cf-mrxvn   10.244.0.116
inventaire-869d7bc7cf-tmqqc   10.244.0.117
```

## 📚 Exercise 6: filter and sort

Create a Pod that fails right away: its command exits with an error. Wait for
it to reach the `Failed` phase, then list the Pods of the namespace:

```bash
kubectl run en-panne --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --restart=Never -n essai-extraction -- sh -c 'exit 1'
kubectl wait --for=jsonpath='{.status.phase}'=Failed pod/en-panne -n essai-extraction --timeout=60s
kubectl get pods -n essai-extraction
```

```text
pod/en-panne created
pod/en-panne condition met
NAME                          READY   STATUS    RESTARTS   AGE
en-panne                      0/1     Error     0          2s
inventaire-869d7bc7cf-4wrrg   1/1     Running   0          3s
inventaire-869d7bc7cf-mrxvn   1/1     Running   0          3s
inventaire-869d7bc7cf-tmqqc   1/1     Running   0          3s
```

JSONPath can filter a list with `?(…)`. `@` stands for the object being
examined. Here, keep only the Pods whose phase is not `Running`:

```bash
kubectl get pods -n essai-extraction -o jsonpath='{range .items[?(@.status.phase!="Running")]}{.metadata.name}{"\t"}{.status.phase}{"\n"}{end}'
```

```text
en-panne	Failed
```

In a big namespace, this filter finds in one command the Pods that are not
running. `--sort-by` sorts the output by a field, here the IP address:

```bash
kubectl get pods -l app=inventaire -n essai-extraction --sort-by=.status.podIP -o custom-columns=POD:.metadata.name,ADRESSE:.status.podIP
```

```text
POD                           ADRESSE
inventaire-869d7bc7cf-mrxvn   10.244.0.116
inventaire-869d7bc7cf-tmqqc   10.244.0.117
inventaire-869d7bc7cf-4wrrg   10.244.0.118
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
inventaire-869d7bc7cf-4wrrg   nginx:1.30.5@sha256:9bf97bd771
```

Four lines: the line of titles, then one per Pod.

## 📚 Exercise 8: what the Deployment wants, and what its Pods do

**Pause** the rollout of the Deployment, then change its image:

```bash
kubectl rollout pause deployment/inventaire -n essai-extraction
kubectl set image deployment/inventaire nginx=nginx:1.30.4@sha256:d5792f71a9496b833bc08ea834a758c46e2b6a6306c10f4be926f38a656cdc1c -n essai-extraction
```

```text
deployment.apps/inventaire paused
deployment.apps/inventaire image updated
```

Compare the image asked for by the **Pod template** of the Deployment with the
one of the running Pods:

```bash
kubectl get deployment inventaire -n essai-extraction -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
kubectl get pods -l app=inventaire -n essai-extraction -o jsonpath='{range .items[*]}{.spec.containers[0].image}{"\n"}{end}'
```

```text
nginx:1.30.4@sha256:d5792f71a9496b833bc08ea834a758c46e2b6a6306c10f4be926f38a656cdc1c
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

The Deployment already **wants** 1.30.4, but its Pods still run 1.30.5: the
pause blocked their replacement. To know what a Deployment asks for, read its
template. To know what is running, read its Pods. Resume the rollout:

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
