# Write and validate a manifest

A **manifest** is a YAML file that describes Kubernetes objects. You keep it in
a Git repository, and you replay it as many times as needed. The lesson shows
how to write it, validate it and apply it. This course stops on what goes
wrong next: a Service that finds no Pod, an object that lands in the wrong
namespace, a file applied only halfway, a value only the server refuses, a
cluster that no longer says what the file says, and an object to fix without
recreating it.

You work in a scratch namespace, `essai-manifeste`, with an `annuaire`
application. The challenge will ask you to repair the manifest of another
application: you will do it on your own, at the end.

Related page: [Writing Manifests](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/write-kubernetes-manifests/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-ecrire-un-manifeste
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster `lab`
is running there, and your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026, with Kubernetes 1.37.

## 📚 Exercise 1: a Service that finds no Pod

Create the scratch namespace, then the manifest of the application: a
ConfigMap, a Deployment and a Service, separated by `---` lines. Each object
names its namespace. The selector of the Service holds a typo, `anuaire`:

```bash
kubectl create namespace essai-manifeste; mkdir -p ~/essai-manifeste
cat > ~/essai-manifeste/annuaire.yaml <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: annuaire-config
  namespace: essai-manifeste
data:
  LANGUE: fr
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: annuaire
  namespace: essai-manifeste
spec:
  replicas: 2
  selector:
    matchLabels:
      app: annuaire
  template:
    metadata:
      labels:
        app: annuaire
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
          ports:
            - containerPort: 80
          envFrom:
            - configMapRef:
                name: annuaire-config
---
apiVersion: v1
kind: Service
metadata:
  name: annuaire
  namespace: essai-manifeste
spec:
  selector:
    app: anuaire
  ports:
    - port: 80
      targetPort: 80
YAML
```

```text
namespace/essai-manifeste created
```

Have the server validate the file, then apply it:

```bash
kubectl apply -f ~/essai-manifeste/annuaire.yaml --dry-run=server
kubectl apply -f ~/essai-manifeste/annuaire.yaml; kubectl rollout status deployment/annuaire -n essai-manifeste --timeout=180s | tail -1
```

```text
configmap/annuaire-config created (server dry run)
deployment.apps/annuaire created (server dry run)
service/annuaire created (server dry run)
configmap/annuaire-config created
deployment.apps/annuaire created
service/annuaire created
deployment "annuaire" successfully rolled out
```

The server accepts everything, and the Pods run. Does the Service find the
Pods? Its addresses are stored in **EndpointSlices**, which carry the name of
the Service in a label:

```bash
kubectl get endpointslices -n essai-manifeste -l kubernetes.io/service-name=annuaire
```

```text
NAME             ADDRESSTYPE   PORTS     ENDPOINTS   AGE
annuaire-mwmhx   IPv4          <unset>   <unset>     11s
```

`<unset>`: no address. The server does not check that a selector finds
anything, an empty Service is a valid object. Compare the selector of the
Service with the labels of the Pods:

```bash
kubectl get service annuaire -n essai-manifeste -o jsonpath='{.spec.selector}{"\n"}'; kubectl get pods -n essai-manifeste --show-labels
```

```text
{"app":"anuaire"}
NAME                        READY   STATUS    RESTARTS   AGE   LABELS
annuaire-76c8d45764-jpl5l   1/1     Running   0          11s   app=annuaire,pod-template-hash=76c8d45764
annuaire-76c8d45764-m777c   1/1     Running   0          11s   app=annuaire,pod-template-hash=76c8d45764
```

The Service looks for `app=anuaire`, the Pods carry `app=annuaire`. Fix the
file, then apply it again:

```bash
sed -i 's/app: anuaire/app: annuaire/' ~/essai-manifeste/annuaire.yaml; kubectl apply -f ~/essai-manifeste/annuaire.yaml
sleep 3; kubectl get endpointslices -n essai-manifeste -l kubernetes.io/service-name=annuaire
```

```text
configmap/annuaire-config unchanged
deployment.apps/annuaire unchanged
service/annuaire configured
NAME             ADDRESSTYPE   PORTS   ENDPOINTS                 AGE
annuaire-mwmhx   IPv4          80      10.244.0.65,10.244.0.66   15s
```

Only the Service changes (`configured`), and it now finds both Pods. The
container did receive the variable of the ConfigMap:

```bash
kubectl exec -n essai-manifeste deploy/annuaire -- printenv LANGUE
```

```text
fr
```

## 📚 Exercise 2: without a namespace, the object goes to the current context

Look at the namespace of your current context (`echo '(fin)'` marks the end of
the output):

```bash
kubectl config view --minify -o jsonpath='{..namespace}'; echo '(fin)'
```

```text
(fin)
```

Nothing before `(fin)`: the context sets no namespace, so kubectl uses
`default`. Create an object without giving a namespace, then look for it in
the whole cluster:

```bash
kubectl create configmap essai-perdu --from-literal=a=1
kubectl get configmap -A | grep -E 'NAMESPACE|essai-perdu'
```

```text
configmap/essai-perdu created
NAMESPACE            NAME                                                   DATA   AGE
default              essai-perdu                                            1      0s
```

It is in `default`. A manifest that does not name its namespace lands where
the context of the person applying it points. Delete it:

```bash
kubectl delete configmap essai-perdu
```

```text
configmap "essai-perdu" deleted from default namespace
```

## 📚 Exercise 3: a file applied halfway

Write a file of three ConfigMaps. In the second one, `tarifs`, the `reduit`
line has one space too many at the start:

```bash
cat > ~/essai-manifeste/horaires.yaml <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: horaires
  namespace: essai-manifeste
data:
  ouverture: "8h"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: tarifs
  namespace: essai-manifeste
data:
  ticket: "2 euros"
   reduit: "1 euro"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: contacts
  namespace: essai-manifeste
data:
  accueil: "poste 12"
YAML
kubectl apply -f ~/essai-manifeste/horaires.yaml
```

```text
configmap/horaires created
error: error parsing /home/ansible/essai-manifeste/horaires.yaml: error converting YAML to JSON: yaml: line 7: did not find expected key
```

One creation, then an error. Look at what really exists:

```bash
kubectl get configmaps -n essai-manifeste
```

```text
NAME               DATA   AGE
annuaire-config    1      15s
horaires           1      0s
kube-root-ca.crt   1      16s
```

`horaires` exists, but neither `tarifs`, the faulty document, nor `contacts`,
which was right. kubectl reads the file document by document, applies each one
as soon as it is read, and stops at the first one it cannot read. The cluster
stays in an in-between state: always read again what was created after an
error.

The message says `line 7`, while the mistake is further down in the file: the
number counts from the start of the faulty document. Line 7 of the second
document is line 15 of the file. `cat -A` marks the end of each line with a
`$`, which makes spaces visible:

```bash
sed -n '15,16p' ~/essai-manifeste/horaires.yaml | cat -A
```

```text
  ticket: "2 euros"$
   reduit: "1 euro"$
```

`reduit` has three spaces instead of two. A YAML syntax error also shows
without the server: `--dry-run=client` would have reported it before any
creation.

## 📚 Exercise 4: validate on the client, then on the server

A mistake in a **value**, on the other hand, does not always show without the
server. Build a faulty copy of the manifest: `sed` adds to the container an
`imagePullPolicy` whose value does not exist (`Parfois`):

```bash
sed 's/^          ports:/          imagePullPolicy: Parfois\n          ports:/' ~/essai-manifeste/annuaire.yaml > ~/essai-manifeste/faux.yaml; grep -n imagePullPolicy ~/essai-manifeste/faux.yaml
```

```text
27:          imagePullPolicy: Parfois
```

Have it validated by kubectl alone, then by the server, without creating
anything:

```bash
kubectl apply -f ~/essai-manifeste/faux.yaml --dry-run=client
kubectl apply -f ~/essai-manifeste/faux.yaml --dry-run=server
```

```text
configmap/annuaire-config unchanged (dry run)
deployment.apps/annuaire configured (dry run)
service/annuaire unchanged (dry run)
configmap/annuaire-config unchanged (server dry run)
service/annuaire unchanged (server dry run)
The Deployment "annuaire" is invalid: spec.template.spec.containers[0].imagePullPolicy: Unsupported value: "Parfois": supported values: "Always", "IfNotPresent", "Never"
```

kubectl alone sees nothing. The server refuses the Deployment, names the
faulty field and gives the accepted values. Only `--dry-run=server` puts the
file through the same checks as a real `apply`.

## 📚 Exercise 5: the cluster no longer says what the file says

Someone scales the Deployment to 4 replicas by hand, without touching the
file:

```bash
kubectl scale deployment/annuaire --replicas=4 -n essai-manifeste; kubectl rollout status deployment/annuaire -n essai-manifeste --timeout=120s | tail -1
grep -n 'replicas:' ~/essai-manifeste/annuaire.yaml
```

```text
deployment.apps/annuaire scaled
deployment "annuaire" successfully rolled out
15:  replicas: 2
```

The cluster says 4, the file still says 2. Before applying the file, ask
`kubectl diff` what an `apply` would change. `grep` only keeps the changed
lines:

```bash
kubectl diff -f ~/essai-manifeste/annuaire.yaml | grep -E '^[-+] '
```

```text
-  generation: 2
+  generation: 3
-  replicas: 4
+  replicas: 2
```

The `-` shows the current state, the `+` the state after `apply`: applying the
file would bring the Deployment back to 2 replicas. `generation` is a counter
the cluster increases at each change. Here, that is wanted: the file is the
reference. Apply:

```bash
kubectl apply -f ~/essai-manifeste/annuaire.yaml; sleep 5; kubectl get deployment annuaire -n essai-manifeste
```

```text
configmap/annuaire-config unchanged
deployment.apps/annuaire configured
service/annuaire unchanged
NAME       READY   UP-TO-DATE   AVAILABLE   AGE
annuaire   2/2     2            2           22s
```

If the change by hand was wanted, it is the file that should have been fixed.
`kubectl diff` lets you see it before overwriting a colleague's work.

## 📚 Exercise 6: fix an existing object in place

Create a faulty `vitrine` Deployment, with an image that does not exist:

```bash
kubectl create deployment vitrine --image=nginx:1.30.6-introuvable --replicas=1 -n essai-manifeste
sleep 20; kubectl get pods -n essai-manifeste -l app=vitrine
```

```text
deployment.apps/vitrine created
NAME                       READY   STATUS             RESTARTS   AGE
vitrine-5fcdbd9877-mfxvh   0/1     ImagePullBackOff   0          20s
```

`ImagePullBackOff`: the image cannot be found. Write down the **uid** of the
Deployment, its unique identifier. An object deleted then recreated gets a new
one:

```bash
kubectl get deployment vitrine -n essai-manifeste -o jsonpath='{.metadata.uid}{"\n"}'
```

```text
ff84739a-7956-42b9-b6c0-81c17466cad1
```

Fix the object **in place**: `kubectl set image` changes the image of the
container (named `nginx`), and `kubectl scale` changes the number of replicas:

```bash
kubectl set image deployment/vitrine nginx=nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703 -n essai-manifeste; kubectl scale deployment/vitrine --replicas=2 -n essai-manifeste
kubectl rollout status deployment/vitrine -n essai-manifeste --timeout=180s | tail -1
```

```text
deployment.apps/vitrine image updated
deployment.apps/vitrine scaled
deployment "vitrine" successfully rolled out
```

Read the uid and the state again:

```bash
kubectl get deployment vitrine -n essai-manifeste -o jsonpath='{.metadata.uid}{"\n"}'; kubectl get deployment vitrine -n essai-manifeste
```

```text
ff84739a-7956-42b9-b6c0-81c17466cad1
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
vitrine   2/2     2            2           21s
```

Same uid: it is the same object, fixed, and its 2 Pods are ready.
`kubectl edit` or a `kubectl apply` of the corrected manifest would also have
kept the uid. A `kubectl delete` followed by a `create` would not.

## 🧹 Clean up

Delete the work files and the scratch namespace:

```bash
rm -rf ~/essai-manifeste; kubectl delete namespace essai-manifeste
```

```text
namespace "essai-manifeste" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-ecrire-un-manifeste
dsoxlab check k8s-ecrire-un-manifeste
```

```text
╭─ Result: k8s-ecrire-un-manifeste ─╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests  │
╰───────────────────────────────────╯
```

0 out of 6: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: the manifest of another application is
wrong. Repair it, have the server validate it, then apply it to update in place
the old version that is running.

```bash
dsoxlab run k8s-ecrire-un-manifeste
dsoxlab challenge k8s-ecrire-un-manifeste
```
