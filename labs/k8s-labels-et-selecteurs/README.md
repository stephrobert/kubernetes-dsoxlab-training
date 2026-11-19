# Label and select Pods

A **label** is a `key=value` tag set on a Kubernetes object. It is used to
**sort and pick** objects: a Service or a ReplicaSet finds its Pods by their
labels. An **annotation** looks like a label, but it is only used to
**document**: you cannot pick objects with it. In this course, you set, change
and remove labels, you filter Pods with a **selector**, you make a label last,
and you document an object with an annotation.

You work in a scratch namespace, `essai-labels`, with two Deployments, `front`
and `back`. The challenge will ask you for the same work on other objects: you
will do it on your own, at the end.

Related page: [Kubernetes labels and annotations: kubectl label and annotate](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kubectl-label-and-annotate/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-labels-et-selecteurs
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster
`boutique` is running there, and your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026.

## 📚 Exercise 1: create two Deployments and read their labels

Create the scratch namespace, then two Deployments: `front` with three Pods,
`back` with two.

```bash
kubectl create namespace essai-labels
kubectl create deployment front --replicas=3 \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-labels
kubectl create deployment back --replicas=2 \
  --image=nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb \
  -n essai-labels
kubectl rollout status deployment/front -n essai-labels --timeout=120s | tail -1
kubectl rollout status deployment/back -n essai-labels --timeout=120s | tail -1
kubectl get pods -n essai-labels --show-labels
```

```text
namespace/essai-labels created
deployment.apps/front created
deployment.apps/back created
deployment "front" successfully rolled out
deployment "back" successfully rolled out
NAME                     READY   STATUS    RESTARTS   AGE   LABELS
back-77679779f-flc9h     1/1     Running   0          1s    app=back,pod-template-hash=77679779f
back-77679779f-wzlqt     1/1     Running   0          1s    app=back,pod-template-hash=77679779f
front-5f4649c9cf-dk8hj   1/1     Running   0          1s    app=front,pod-template-hash=5f4649c9cf
front-5f4649c9cf-fmszn   1/1     Running   0          1s    app=front,pod-template-hash=5f4649c9cf
front-5f4649c9cf-q6hf8   1/1     Running   0          1s    app=front,pod-template-hash=5f4649c9cf
```

Each Pod already has two labels you did not write: `app`, with the
Deployment's name, and `pod-template-hash`, set by the Deployment.

## 📚 Exercise 2: set, change and remove a label

Store the name of the first `front` Pod in a variable, then give it the
`niveau=bronze` label:

```bash
POD=$(kubectl get pods -n essai-labels -l app=front -o jsonpath='{.items[0].metadata.name}')
echo $POD
kubectl label pod $POD niveau=bronze -n essai-labels
```

```text
front-5f4649c9cf-dk8hj
pod/front-5f4649c9cf-dk8hj labeled
```

Try to change its value, then try again with `--overwrite`:

```bash
kubectl label pod $POD niveau=argent -n essai-labels
kubectl label pod $POD niveau=argent --overwrite -n essai-labels
```

```text
error: 'niveau' already has a value (bronze), and --overwrite is false
pod/front-5f4649c9cf-dk8hj labeled
```

The first command is refused: kubectl does not overwrite a value by accident.
`--overwrite` lifts this protection. To remove a label, stick a dash after the
key:

```bash
kubectl label pod $POD niveau- -n essai-labels
kubectl label pod $POD niveau- -n essai-labels
```

```text
pod/front-5f4649c9cf-dk8hj unlabeled
label "niveau" not found.
pod/front-5f4649c9cf-dk8hj not labeled
```

The second time, the label no longer exists: kubectl says so, without an
error.

## 📚 Exercise 3: label several Pods at once

`kubectl label` accepts a `-l` selector, to touch all the matching Pods. Before
a mass change, `--dry-run=server` shows what would be touched, **without
changing anything**:

```bash
kubectl label pods -l app=front role=vitrine-web --dry-run=server -n essai-labels
kubectl label pods -l app=back role=donnees -n essai-labels
kubectl get pods -n essai-labels -L role
```

```text
pod/front-5f4649c9cf-dk8hj labeled (server dry run)
pod/front-5f4649c9cf-fmszn labeled (server dry run)
pod/front-5f4649c9cf-q6hf8 labeled (server dry run)
pod/back-77679779f-flc9h labeled
pod/back-77679779f-wzlqt labeled
NAME                     READY   STATUS    RESTARTS   AGE   ROLE
back-77679779f-flc9h     1/1     Running   0          2s    donnees
back-77679779f-wzlqt     1/1     Running   0          2s    donnees
front-5f4649c9cf-dk8hj   1/1     Running   0          2s
front-5f4649c9cf-fmszn   1/1     Running   0          2s
front-5f4649c9cf-q6hf8   1/1     Running   0          2s
```

`-L role` shows the `role` label as a column. The `back` Pods got it. The
`front` Pods did not: their command was only a trial (`server dry run`).

## 📚 Exercise 4: filter with a selector

Set a different level on two `front` Pods:

```bash
P1=$(kubectl get pods -n essai-labels -l app=front -o jsonpath='{.items[0].metadata.name}')
P2=$(kubectl get pods -n essai-labels -l app=front -o jsonpath='{.items[1].metadata.name}')
kubectl label pod $P1 niveau=or -n essai-labels
kubectl label pod $P2 niveau=argent -n essai-labels
kubectl get pods -n essai-labels -l app=front,niveau=or
```

```text
pod/front-5f4649c9cf-dk8hj labeled
pod/front-5f4649c9cf-fmszn labeled
NAME                     READY   STATUS    RESTARTS   AGE
front-5f4649c9cf-dk8hj   1/1     Running   0          2s
```

In a selector, the comma means "and": `app=front,niveau=or` keeps only the Pod
that has both. There are other forms. Count the Pods each one keeps (`wc -l`
counts the lines):

```bash
kubectl get pods -n essai-labels -l 'niveau!=argent' --no-headers | wc -l
kubectl get pods -n essai-labels -l 'niveau in (or, argent)' --no-headers | wc -l
kubectl get pods -n essai-labels -l niveau --no-headers | wc -l
kubectl get pods -n essai-labels -l '!niveau' --no-headers | wc -l
kubectl get pods -n essai-labels -l 'niveau,niveau!=argent' --no-headers | wc -l
```

```text
4
2
2
3
1
```

Line by line:

- `niveau!=argent`: **4** Pods. Watch out for the trap: this form also keeps
  the Pods that have **no** `niveau` label at all (the three others);
- `niveau in (or, argent)`: 2 Pods, those with one of the two values;
- `niveau`: 2 Pods, those that have the key, whatever its value;
- `!niveau`: 3 Pods, those without the key;
- `niveau,niveau!=argent`: 1 Pod. You ask for the key **and** a value other
  than `argent`.

Put the selectors that contain `!`, parentheses or spaces between single
quotes: otherwise, the shell changes them before kubectl.

## 📚 Exercise 5: make a label last

A label set on a Pod disappears with it. Delete the Pod that has `niveau=or`,
and look at the one that replaces it:

```bash
P1=$(kubectl get pods -n essai-labels -l niveau=or -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod $P1 -n essai-labels
kubectl rollout status deployment/front -n essai-labels --timeout=120s | tail -1
kubectl get pods -n essai-labels -l app=front -L niveau
```

```text
pod "front-5f4649c9cf-dk8hj" deleted from essai-labels namespace
deployment "front" successfully rolled out
NAME                     READY   STATUS    RESTARTS   AGE   NIVEAU
front-5f4649c9cf-95sjc   1/1     Running   0          2s
front-5f4649c9cf-fmszn   1/1     Running   0          4s    argent
front-5f4649c9cf-q6hf8   1/1     Running   0          4s
```

The new Pod (`95sjc`) does not have the label: the Deployment built it from its
**Pod template**, which does not know `niveau`. A lasting label is therefore
written in that template. `kubectl patch` changes a field of the Deployment:

```bash
kubectl patch deployment front -n essai-labels \
  -p '{"spec":{"template":{"metadata":{"labels":{"equipe":"vente"}}}}}'
kubectl rollout status deployment/front -n essai-labels --timeout=120s | tail -1
kubectl get pods -n essai-labels -l equipe=vente
```

```text
deployment.apps/front patched
deployment "front" successfully rolled out
NAME                     READY   STATUS    RESTARTS   AGE
front-79b5b7cccb-5mplw   1/1     Running   0          0s
front-79b5b7cccb-dsn5b   1/1     Running   0          1s
front-79b5b7cccb-kwg4s   1/1     Running   0          2s
```

All three Pods have `equipe=vente`. Since the template changed, the Deployment
replaced all the Pods. They will keep it, even if they are recreated.

The other way round, a label set on the Deployment itself does not go down to
the Pods:

```bash
kubectl label deployment back equipe=stock -n essai-labels
kubectl get pods -n essai-labels -l equipe=stock
```

```text
deployment.apps/back labeled
No resources found in essai-labels namespace.
```

No Pod has `equipe=stock`: Pods get the labels of the Pod template, not those
of the Deployment.

## 📚 Exercise 6: document an object with an annotation

`kubectl annotate` is used like `kubectl label`. The value, though, is free
text. Add a contact address to the `front` Deployment, then change it:

```bash
kubectl annotate deployment front contact='equipe-vente@exemple.fr' -n essai-labels
kubectl annotate deployment front contact='support@exemple.fr' -n essai-labels
kubectl annotate deployment front contact='support@exemple.fr' --overwrite -n essai-labels
```

```text
deployment.apps/front annotated
error: --overwrite is false but found the following declared annotation(s): 'contact' already has a value (equipe-vente@exemple.fr)
deployment.apps/front annotated
```

As for a label, changing a value needs `--overwrite`. Read the annotation, then
try to use it to pick objects:

```bash
kubectl get deployment front -n essai-labels -o jsonpath='{.metadata.annotations.contact}{"\n"}'
kubectl get deployments -n essai-labels -l contact
```

```text
support@exemple.fr
No resources found in essai-labels namespace.
```

`-l contact` finds nothing: an annotation is not used to select. If you ever
need to pick objects by a piece of information, it is a label. Otherwise, it is
an annotation.

## 📚 Exercise 7: see a label refused

Try to put a sentence in a label:

```bash
kubectl label deployment back 'resume=Stockage des commandes' -n essai-labels
```

```text
error: invalid label value: "resume=Stockage des commandes": a valid label must be an empty string or consist of alphanumeric characters, '-', '_' or '.', and must start and end with an alphanumeric character (e.g. 'MyValue',  or 'my_value',  or '12345', regex used for validation is '(([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9])?')
```

Refused: a label's value accepts no spaces or accents, and is 63 characters at
most. A sentence goes in an annotation.

## 🧹 Clean up

Delete the scratch namespace:

```bash
kubectl delete namespace essai-labels
```

```text
namespace "essai-labels" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-labels-et-selecteurs
dsoxlab check k8s-labels-et-selecteurs
```

```text
╭─ Result: k8s-labels-et-selecteurs ─╮
│  0 / 100 pts                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests   │
╰────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: label an application's Pods for good,
document its Deployment, and write a selector with a negation.

```bash
dsoxlab run k8s-labels-et-selecteurs
dsoxlab challenge k8s-labels-et-selecteurs
```
