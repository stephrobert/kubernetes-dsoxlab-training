# One Kustomize base and two overlays

The same application often runs in several environments: test, demo,
production. Copying its manifests for each one always ends in copies that drift
apart. **Kustomize**, built into kubectl, starts from a common **base** and
applies **overlays** to it: small files that describe only the differences. In
this course, you write a base, you see the name of a generated ConfigMap change
with its content, you write an overlay, you check that a label does reach the
Service's selector, you change the image in a second overlay, you apply both,
then you change the configuration.

You work with a `site` application and two trial environments, `essai-qualif`
and `essai-demo`. The challenge will ask you for another application, in `dev`
and `prod`: you will do it on your own, at the end.

Related page: [Kustomize](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kustomize/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-kustomize-overlays
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026, with Kubernetes v1.37.2 and the Kustomize version built into kubectl,
v5.8.1.

## 📚 Exercise 1: a base

Create the two trial namespaces and the work tree: one base, and one folder
per overlay:

```bash
kubectl create namespace essai-qualif; kubectl create namespace essai-demo; mkdir -p ~/essai-kustomize/base ~/essai-kustomize/overlays/qualif ~/essai-kustomize/overlays/demo
```

```text
namespace/essai-qualif created
namespace/essai-demo created
```

The base holds the ordinary manifests, **without a namespace**, and a
`kustomization.yaml` file. That file lists the manifests under `resources`, and
asks Kustomize to **generate** a `site-config` ConfigMap
(`configMapGenerator`). The Deployment reads this ConfigMap through `envFrom`
(`COULEUR=bleu` means "COLOUR=blue"):

```bash
cd ~/essai-kustomize/base
cat > deployment.yaml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: site
spec:
  replicas: 1
  selector:
    matchLabels:
      app: site
  template:
    metadata:
      labels:
        app: site
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
          ports:
            - containerPort: 80
          envFrom:
            - configMapRef:
                name: site-config
YAML
cat > service.yaml <<'YAML'
apiVersion: v1
kind: Service
metadata:
  name: site-svc
spec:
  selector:
    app: site
  ports:
    - port: 80
      targetPort: 80
YAML
cat > kustomization.yaml <<'YAML'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml
configMapGenerator:
  - name: site-config
    literals:
      - COULEUR=bleu
YAML
ls
```

```text
deployment.yaml
kustomization.yaml
service.yaml
```

`kubectl kustomize` shows what Kustomize produces, **without applying
anything**:

```bash
kubectl kustomize ~/essai-kustomize/base
```

```text
apiVersion: v1
data:
  COULEUR: bleu
kind: ConfigMap
metadata:
  name: site-config-mgm6hf9htk
---
apiVersion: v1
kind: Service
metadata:
  name: site-svc
spec:
  ports:
  - port: 80
    targetPort: 80
  selector:
    app: site
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: site
spec:
  replicas: 1
  selector:
    matchLabels:
      app: site
  template:
    metadata:
      labels:
        app: site
    spec:
      containers:
      - envFrom:
        - configMapRef:
            name: site-config-mgm6hf9htk
        image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
        name: nginx
        ports:
        - containerPort: 80
```

Three objects separated by `---`. The ConfigMap is called
`site-config-mgm6hf9htk`: Kustomize added a **hash** of its content. It also
rewrote the name in the Deployment's `envFrom`.

## 📚 Exercise 2: the name changes with the content

Note the name of the generated ConfigMap, change the colour, then note it
again (`vert` means "green"):

```bash
kubectl kustomize ~/essai-kustomize/base | grep -E '^  name: site-config|^                name: site-config'
sed -i 's/COULEUR=bleu/COULEUR=vert/' ~/essai-kustomize/base/kustomization.yaml; kubectl kustomize ~/essai-kustomize/base | grep -E '^  name: site-config'
```

```text
  name: site-config-mgm6hf9htk
  name: site-config-g7gd24m975
```

Another content gives another name. Since the Deployment names it, its Pod
template changes too: applying the new configuration restarts its Pods, which
then read the new value. Put the original colour back, and the hash comes back:

```bash
sed -i 's/COULEUR=vert/COULEUR=bleu/' ~/essai-kustomize/base/kustomization.yaml; kubectl kustomize ~/essai-kustomize/base | grep -E '^  name: site-config'
```

```text
  name: site-config-mgm6hf9htk
```

## 📚 Exercise 3: an overlay that holds only the differences

The `qualif` overlay takes the base (`resources: ../../base`), then only says
what changes: the namespace, a prefix added to the names (`namePrefix`), an
`env: qualif` label, and the number of replicas. `grep` keeps only the lines
that carry these changes:

```bash
cat > ~/essai-kustomize/overlays/qualif/kustomization.yaml <<'YAML'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
namespace: essai-qualif
namePrefix: qualif-
labels:
  - pairs:
      env: qualif
    includeSelectors: true
replicas:
  - name: site
    count: 1
YAML
kubectl kustomize ~/essai-kustomize/overlays/qualif | grep -E '^kind:|^  name:|^  namespace:|^    env:|^      env:|^        env:|name: qualif-site-config'
```

```text
kind: ConfigMap
    env: qualif
  name: qualif-site-config-mgm6hf9htk
  namespace: essai-qualif
kind: Service
    env: qualif
  name: qualif-site-svc
  namespace: essai-qualif
    env: qualif
kind: Deployment
    env: qualif
  name: qualif-site
  namespace: essai-qualif
      env: qualif
        env: qualif
            name: qualif-site-config-mgm6hf9htk
```

Every object got the `qualif-` prefix, the `essai-qualif` namespace and the
`env: qualif` label. The Service carries the label twice: on itself, and in its
selector. The Deployment carries it three times: on itself, in its selector,
and on its Pod template. The name of the ConfigMap is rewritten everywhere,
prefix included. The base, for its part, has not changed.

## 📚 Exercise 4: the label must reach the selector

`includeSelectors: true` asks Kustomize to put the label in the selectors too.
See what happens without it. Create a `sans-selecteur` overlay ("without
selector"), a copy of `qualif` with `includeSelectors: false`, and look at the
selector of its Service:

```bash
mkdir -p ~/essai-kustomize/overlays/sans-selecteur; sed 's/includeSelectors: true/includeSelectors: false/' ~/essai-kustomize/overlays/qualif/kustomization.yaml > ~/essai-kustomize/overlays/sans-selecteur/kustomization.yaml; kubectl kustomize ~/essai-kustomize/overlays/sans-selecteur | sed -n '/^kind: Service/,/^---/p' | grep -A3 'selector:'
```

```text
  selector:
    app: site
---
```

The selector only names `app: site`. If two environments shared a namespace,
this Service would find the Pods of both. With `qualif`:

```bash
kubectl kustomize ~/essai-kustomize/overlays/qualif | sed -n '/^kind: Service/,/^---/p' | grep -A3 'selector:'
```

```text
  selector:
    app: site
    env: qualif
---
```

The Service only finds the Pods of its own environment.

## 📚 Exercise 5: a second overlay that changes the image

The `demo` overlay does the same with 2 replicas, and moves the image to
version 1.30.6 with an `images` block. That block targets the images named
`nginx` and gives them a new tag and a new digest:

```bash
cat > ~/essai-kustomize/overlays/demo/kustomization.yaml <<'YAML'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
namespace: essai-demo
namePrefix: demo-
labels:
  - pairs:
      env: demo
    includeSelectors: true
replicas:
  - name: site
    count: 2
images:
  - name: nginx
    newTag: 1.30.6
    digest: sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
YAML
kubectl kustomize ~/essai-kustomize/overlays/demo | grep -E 'image:|replicas:'
```

```text
  replicas: 2
        image: nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
```

The base still describes version 1.30.5 and 1 replica:

```bash
kubectl kustomize ~/essai-kustomize/base | grep -E 'image:|replicas:'
```

```text
  replicas: 1
        image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

A change that belongs to one environment goes into its overlay, never into the
base.

## 📚 Exercise 6: apply and check

`kubectl apply -k` applies a Kustomize folder. Apply both overlays, then wait
for both rollouts:

```bash
kubectl apply -k ~/essai-kustomize/overlays/qualif; kubectl apply -k ~/essai-kustomize/overlays/demo
kubectl rollout status deployment/qualif-site -n essai-qualif --timeout=180s | tail -1; kubectl rollout status deployment/demo-site -n essai-demo --timeout=180s | tail -1
```

```text
configmap/qualif-site-config-mgm6hf9htk created
service/qualif-site-svc created
deployment.apps/qualif-site created
configmap/demo-site-config-mgm6hf9htk created
service/demo-site-svc created
deployment.apps/demo-site created
deployment "qualif-site" successfully rolled out
deployment "demo-site" successfully rolled out
```

Look at what `essai-demo` holds:

```bash
kubectl get deploy,svc,configmap -n essai-demo
```

```text
NAME                        READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/demo-site   2/2     2            2           1s

NAME                    TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE
service/demo-site-svc   ClusterIP   10.99.212.73   <none>        80/TCP    1s

NAME                                    DATA   AGE
configmap/demo-site-config-mgm6hf9htk   1      1s
configmap/kube-root-ca.crt              1      2s
```

The Pods carry their environment label (`-L env` adds the column, and `awk`
keeps only five columns):

```bash
kubectl get pods -n essai-demo -L env -o wide | awk '{print $1, $2, $3, $6, $NF}' | column -t
```

```text
NAME                       READY  STATUS   IP             ENV
demo-site-b668c76c4-22529  1/1    Running  10.244.163.42  demo
demo-site-b668c76c4-g5q5q  1/1    Running  10.244.38.124  demo
```

The Service finds both Pods, and the container received its configuration:

```bash
kubectl get endpointslices -n essai-demo -l kubernetes.io/service-name=demo-site-svc -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]}{"\n"}{end}'
kubectl exec -n essai-demo deploy/demo-site -- printenv COULEUR
```

```text
10.244.38.124
10.244.163.42
bleu
```

Finally, `kubectl diff -k` compares each overlay with the cluster:

```bash
kubectl diff -k ~/essai-kustomize/overlays/qualif > /dev/null; echo "qualif : code $?"; kubectl diff -k ~/essai-kustomize/overlays/demo > /dev/null; echo "demo : code $?"
```

```text
qualif : code 0
demo : code 0
```

Code 0: the cluster matches the folder.

## 📚 Exercise 7: changing the configuration restarts the Pods

Change the colour in the base, then apply the `demo` overlay again:

```bash
sed -i 's/COULEUR=bleu/COULEUR=vert/' ~/essai-kustomize/base/kustomization.yaml; kubectl apply -k ~/essai-kustomize/overlays/demo
```

```text
configmap/demo-site-config-g7gd24m975 created
service/demo-site-svc unchanged
deployment.apps/demo-site configured
```

A **new** ConfigMap is created, and the Deployment is changed to name it. So
its Pods are replaced:

```bash
kubectl rollout status deployment/demo-site -n essai-demo --timeout=180s | tail -1; kubectl exec -n essai-demo deploy/demo-site -- printenv COULEUR
```

```text
deployment "demo-site" successfully rolled out
vert
```

The new Pods read `vert`. The old ConfigMap is still there:

```bash
kubectl get configmap -n essai-demo
```

```text
NAME                          DATA   AGE
demo-site-config-g7gd24m975   1      2s
demo-site-config-mgm6hf9htk   1      3s
kube-root-ca.crt              1      4s
```

`apply` deletes nothing on its own. That is rather useful: a rollback finds the
old configuration untouched.

## 🧹 Clean up

Delete both trial namespaces and the work tree:

```bash
kubectl delete namespace essai-qualif essai-demo; rm -rf ~/essai-kustomize
```

```text
namespace "essai-qualif" deleted
namespace "essai-demo" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset ckad-kustomize-overlays
dsoxlab check ckad-kustomize-overlays
```

```text
╭─ Result: ckad-kustomize-overlays ─╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/9 tests  │
╰───────────────────────────────────╯
```

0 out of 9: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: another application, one base and two
overlays, `dev` and `prod`, only one of which moves to version 2.

```bash
dsoxlab run ckad-kustomize-overlays
dsoxlab challenge ckad-kustomize-overlays
```
