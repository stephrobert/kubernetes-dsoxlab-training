# Write and validate a manifest

A **manifest** is a YAML file that describes Kubernetes objects. You keep it in
a Git repository, and you replay it as many times as needed. In this course,
you let kubectl generate a skeleton, you see where an object without a
namespace goes, you put three objects in a single file, you have it validated
by the server, you apply it, you look at the difference before a change, then
you fix an existing object without recreating it.

You work in a scratch namespace, `essai-manifeste`, with an `annuaire`
application. The challenge will ask you for another application, in another
namespace: you will do it on your own, at the end.

Related page: [Writing Manifests](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/write-kubernetes-manifests/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-ecrire-un-manifeste
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster `lab` is
running there, and your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026, with Kubernetes 1.37.

## 📚 Exercise 1: generate a skeleton

Create the scratch namespace and a work directory:

```bash
kubectl create namespace essai-manifeste; mkdir -p ~/essai-manifeste
```

```text
namespace/essai-manifeste created
```

Do not start from a blank page. `kubectl create` accepts `--dry-run=client`:
kubectl prepares the object **without sending it** to the cluster, and
`-o yaml` shows it in YAML:

```bash
kubectl create deployment annuaire --image=nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703 --replicas=2 --port=80 --dry-run=client -o yaml
```

```text
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: annuaire
  name: annuaire
spec:
  replicas: 2
  selector:
    matchLabels:
      app: annuaire
  strategy: {}
  template:
    metadata:
      labels:
        app: annuaire
    spec:
      containers:
      - image: nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
        name: nginx
        ports:
        - containerPort: 80
        resources: {}
status: {}
```

Everything is there: the `app: annuaire` label, the selector that repeats it,
the Pod template. The `{}` lines are empty and can be removed. Check that
nothing was created:

```bash
kubectl get deployment -n essai-manifeste
```

```text
No resources found in essai-manifeste namespace.
```

## 📚 Exercise 2: the other skeletons

The same method works for a ConfigMap:

```bash
kubectl create configmap annuaire-config --from-literal=LANGUE=fr --dry-run=client -o yaml
```

```text
apiVersion: v1
data:
  LANGUE: fr
kind: ConfigMap
metadata:
  name: annuaire-config
```

And for a Service. `--tcp=80:80` means "port 80 of the Service to port 80 of
the Pods":

```bash
kubectl create service clusterip annuaire --tcp=80:80 --dry-run=client -o yaml
```

```text
apiVersion: v1
kind: Service
metadata:
  labels:
    app: annuaire
  name: annuaire
spec:
  ports:
  - name: 80-80
    port: 80
    protocol: TCP
    targetPort: 80
  selector:
    app: annuaire
  type: ClusterIP
status:
  loadBalancer: {}
```

The `app: annuaire` selector comes from the name of the Service. So it finds
the Pods of the Deployment from exercise 1, which carry the same label.

## 📚 Exercise 3: without a namespace, the object goes to the current context

None of the skeletons carries a namespace. Look at the one of your current
context (`echo '(fin)'` marks the end of the output; "fin" means "end"):

```bash
kubectl config view --minify -o jsonpath='{..namespace}'; echo '(fin)'
```

```text
(fin)
```

Nothing before `(fin)`: the context sets no namespace, so kubectl uses
`default`. Create an object without giving a namespace, then look for it in the
whole cluster:

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
the context of whoever applies it points, and that is not always the right
place. Delete it:

```bash
kubectl delete configmap essai-perdu
```

```text
configmap "essai-perdu" deleted from default namespace
```

## 📚 Exercise 4: one file, three objects, one namespace

A file can hold several objects, separated by a `---` line. Write the manifest
of the application, from the three skeletons. Each object names its namespace
in `metadata.namespace`. The Deployment also receives the ConfigMap in its
environment variables, with `envFrom`:

```bash
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
    app: annuaire
  ports:
    - port: 80
      targetPort: 80
YAML
grep -c '^---' ~/essai-manifeste/annuaire.yaml
```

```text
2
```

Two separators, so three objects.

## 📚 Exercise 5: validate on the client, then on the server

Make a faulty copy of the file: `sed` adds to the container an
`imagePullPolicy` whose value does not exist (`Parfois`, French for
"sometimes"):

```bash
sed 's/^          ports:/          imagePullPolicy: Parfois\n          ports:/' ~/essai-manifeste/annuaire.yaml > ~/essai-manifeste/faux.yaml; grep -n imagePullPolicy ~/essai-manifeste/faux.yaml
```

```text
27:          imagePullPolicy: Parfois
```

Have it validated by kubectl alone, without the server:

```bash
kubectl apply -f ~/essai-manifeste/faux.yaml --dry-run=client
```

```text
configmap/annuaire-config created (dry run)
deployment.apps/annuaire created (dry run)
service/annuaire created (dry run)
```

kubectl sees nothing. Now ask the **server** to validate, still without
creating anything:

```bash
kubectl apply -f ~/essai-manifeste/faux.yaml --dry-run=server
```

```text
configmap/annuaire-config created (server dry run)
service/annuaire created (server dry run)
The Deployment "annuaire" is invalid: spec.template.spec.containers[0].imagePullPolicy: Unsupported value: "Parfois": supported values: "Always", "IfNotPresent", "Never"
```

The server refuses the Deployment, names the faulty field and gives the
accepted values. Only `--dry-run=server` runs the file through the same checks
as a real `apply`. The correct file passes:

```bash
kubectl apply -f ~/essai-manifeste/annuaire.yaml --dry-run=server
```

```text
configmap/annuaire-config created (server dry run)
deployment.apps/annuaire created (server dry run)
service/annuaire created (server dry run)
```

## 📚 Exercise 6: apply and check

Apply the file for real, then wait until the Pods are ready:

```bash
kubectl apply -f ~/essai-manifeste/annuaire.yaml
kubectl rollout status deployment/annuaire -n essai-manifeste --timeout=180s | tail -1
```

```text
configmap/annuaire-config created
deployment.apps/annuaire created
service/annuaire created
deployment "annuaire" successfully rolled out
```

The three objects are in `essai-manifeste`, without `-n` on the `apply`
command:

```bash
kubectl get deploy,svc,configmap -n essai-manifeste
```

```text
NAME                       READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/annuaire   2/2     2            2           8s

NAME               TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE
service/annuaire   ClusterIP   10.96.205.45   <none>        80/TCP    8s

NAME                         DATA   AGE
configmap/annuaire-config    1      8s
configmap/kube-root-ca.crt   1      9s
```

Does the Service find both Pods? Its addresses are stored in
**EndpointSlices**, which carry the name of the Service in a label:

```bash
kubectl get endpointslices -n essai-manifeste -l kubernetes.io/service-name=annuaire -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]}{"\n"}{end}'
```

```text
10.244.0.7
10.244.0.8
```

Two addresses, one per Pod. Finally, did the container receive the variable
from the ConfigMap?

```bash
kubectl exec -n essai-manifeste deploy/annuaire -- printenv LANGUE
```

```text
fr
```

## 📚 Exercise 7: see the difference before applying

Set the file to 3 replicas, then ask `kubectl diff` what an `apply` would
change. `grep` keeps only the changed lines:

```bash
sed -i 's/^  replicas: 2/  replicas: 3/' ~/essai-manifeste/annuaire.yaml; kubectl diff -f ~/essai-manifeste/annuaire.yaml | grep -E '^[-+] '
```

```text
-  generation: 1
+  generation: 2
-  replicas: 2
+  replicas: 3
```

The `-` shows the current state, the `+` the state after `apply`.
`generation` is a counter the cluster increases on each change. Apply:

```bash
kubectl apply -f ~/essai-manifeste/annuaire.yaml
```

```text
configmap/annuaire-config unchanged
deployment.apps/annuaire configured
service/annuaire unchanged
```

Only the Deployment is changed (`configured`), the two other objects stay as
they are (`unchanged`).

## 📚 Exercise 8: fix an existing object in place

Create a faulty `vitrine` Deployment, with an image that does not exist:

```bash
kubectl create deployment vitrine --image=nginx:1.30.6-introuvable --replicas=1 -n essai-manifeste
sleep 20; kubectl get pods -n essai-manifeste -l app=vitrine
```

```text
deployment.apps/vitrine created
NAME                       READY   STATUS             RESTARTS   AGE
vitrine-5fcdbd9877-8t6ct   0/1     ImagePullBackOff   0          20s
```

`ImagePullBackOff`: the image cannot be found. Note the **uid** of the
Deployment, its unique identifier. An object deleted then recreated gets a new
one:

```bash
kubectl get deployment vitrine -n essai-manifeste -o jsonpath='{.metadata.uid}{"\n"}'
```

```text
1639a99c-7720-49ce-88dd-6533d26237c2
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
1639a99c-7720-49ce-88dd-6533d26237c2
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
vitrine   2/2     2            2           21s
```

Same uid: it is the same object, fixed, and its 2 Pods are ready. `kubectl
edit` or a `kubectl apply` of the corrected manifest would also have kept the
uid. A `kubectl delete` followed by a `create` would not.

## 🧹 Clean up

Delete the scratch namespace and the work directory:

```bash
kubectl delete namespace essai-manifeste; rm -rf ~/essai-manifeste
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

Your turn, on your own this time: write the manifest of another application,
in another namespace, validate it, apply it, and fix in place a Deployment that
does not start.

```bash
dsoxlab run k8s-ecrire-un-manifeste
dsoxlab challenge k8s-ecrire-un-manifeste
```
