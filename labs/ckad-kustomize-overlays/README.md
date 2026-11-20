# One Kustomize base and two overlays

The same application often runs in several environments: test, demo,
production. Copying its manifests for each one always ends in copies that
diverge. **Kustomize**, built into kubectl, starts from a common **base** and
applies **overlays** to it: small files that only describe the differences.
The lesson shows how to write them. This course starts from a ready-made base
and stops on what catches people out: a label added afterwards that the
cluster refuses, a patch that only targets one environment, and a badly named
patch that says nothing.

You work with a `site` application and two scratch environments,
`essai-qualif` and `essai-demo`. The challenge will ask you for another
application, in two other environments: you will do it on your own, at the
end.

Related page: [Kustomize](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kustomize/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run ckad-kustomize-overlays
```

You are now connected to `k8s-cp.lab`, the node that drives the kubeadm
cluster (the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026, with Kubernetes v1.37.2 and the version of Kustomize built into kubectl,
v5.8.1.

## 📚 Exercise 1: a ready-made base

Create both scratch namespaces, the work tree and the base: a Deployment, a
Service and a `kustomization.yaml` that lists them and generates a
`site-config` ConfigMap. The lesson details each of these files:

```bash
kubectl create namespace essai-qualif; kubectl create namespace essai-demo; mkdir -p ~/essai-kustomize/base ~/essai-kustomize/overlays/qualif ~/essai-kustomize/overlays/demo
cat > ~/essai-kustomize/base/deployment.yaml <<'YAML'
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
cat > ~/essai-kustomize/base/service.yaml <<'YAML'
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
cat > ~/essai-kustomize/base/kustomization.yaml <<'YAML'
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
```

```text
namespace/essai-qualif created
namespace/essai-demo created
```

`kubectl kustomize` shows what Kustomize produces, without applying anything.
`grep` only keeps the type and the name of each object:

```bash
kubectl kustomize ~/essai-kustomize/base | grep -E '^kind:|^  name:|name: site-config'
```

```text
kind: ConfigMap
  name: site-config-mgm6hf9htk
kind: Service
  name: site-svc
kind: Deployment
  name: site
            name: site-config-mgm6hf9htk
```

The ConfigMap carries a hash of its content, and Kustomize rewrote this name
in the `envFrom` of the Deployment.

## 📚 Exercise 2: a label added afterwards

Write the `qualif` overlay **without a label**: a namespace, a prefix and 2
replicas. Apply it, and look at the addresses of the Service:

```bash
cat > ~/essai-kustomize/overlays/qualif/kustomization.yaml <<'YAML'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
namespace: essai-qualif
namePrefix: qualif-
replicas:
  - name: site
    count: 2
YAML
kubectl apply -k ~/essai-kustomize/overlays/qualif; kubectl rollout status deployment/qualif-site -n essai-qualif --timeout=120s | tail -1
kubectl get endpointslices -n essai-qualif -l kubernetes.io/service-name=qualif-site-svc
```

```text
configmap/qualif-site-config-mgm6hf9htk created
service/qualif-site-svc created
deployment.apps/qualif-site created
deployment "qualif-site" successfully rolled out
NAME                    ADDRESSTYPE   PORTS   ENDPOINTS                     AGE
qualif-site-svc-dx6kk   IPv4          80      10.244.38.108,10.244.163.46   0s
```

The Service finds both Pods. Now add the `env: qualif` label, with
`includeSelectors: true`, so that it also goes into the selectors. First look
at the selector the overlay would produce:

```bash
cat >> ~/essai-kustomize/overlays/qualif/kustomization.yaml <<'YAML'
labels:
  - pairs:
      env: qualif
    includeSelectors: true
YAML
kubectl kustomize ~/essai-kustomize/overlays/qualif | sed -n '/^kind: Service/,/^---/p' | grep -A3 'selector:'
```

```text
  selector:
    app: site
    env: qualif
---
```

That is what we want. Apply:

```bash
kubectl apply -k ~/essai-kustomize/overlays/qualif; echo "code $?"
```

```text
configmap/qualif-site-config-mgm6hf9htk configured
service/qualif-site-svc configured
The Deployment "qualif-site" is invalid: spec.selector: Invalid value: {"matchLabels":{"app":"site","env":"qualif"}}: field is immutable
code 1
```

The selector of a Deployment can no longer be changed after its creation:
`field is immutable`. The Deployment is refused, but the Service, for its
part, was changed. Look where that leads:

```bash
sleep 3; kubectl get service qualif-site-svc -n essai-qualif -o jsonpath='{.spec.selector}{"\n"}'; kubectl get pods -n essai-qualif --show-labels
kubectl get endpointslices -n essai-qualif -l kubernetes.io/service-name=qualif-site-svc
```

```text
{"app":"site","env":"qualif"}
NAME                           READY   STATUS    RESTARTS   AGE   LABELS
qualif-site-858dd798db-h46rq   1/1     Running   0          4s    app=site,pod-template-hash=858dd798db
qualif-site-858dd798db-l8fps   1/1     Running   0          4s    app=site,pod-template-hash=858dd798db
NAME                    ADDRESSTYPE   PORTS     ENDPOINTS   AGE
qualif-site-svc-dx6kk   IPv4          <unset>   <unset>     4s
```

The Service now looks for `env=qualif`, which the Pods do not have: it no
longer has any address. The Pods run, but the application no longer answers
through its Service. To change the selector, the Deployment must be created
again. Delete it, then apply again:

```bash
kubectl delete deployment qualif-site -n essai-qualif; kubectl apply -k ~/essai-kustomize/overlays/qualif; kubectl rollout status deployment/qualif-site -n essai-qualif --timeout=120s | tail -1
sleep 3; kubectl get endpointslices -n essai-qualif -l kubernetes.io/service-name=qualif-site-svc
```

```text
deployment.apps "qualif-site" deleted from essai-qualif namespace
configmap/qualif-site-config-mgm6hf9htk unchanged
service/qualif-site-svc unchanged
deployment.apps/qualif-site created
deployment "qualif-site" successfully rolled out
NAME                    ADDRESSTYPE   PORTS   ENDPOINTS                     AGE
qualif-site-svc-dx6kk   IPv4          80      10.244.38.114,10.244.163.47   8s
```

The Service finds two Pods again. Between the deletion and the end of the
rollout, the application had no Pod: decide the labels of an environment
**before** its first deployment.

## 📚 Exercise 3: an overlay that changes the image

The `demo` overlay carries its label from the start this time, 2 replicas,
and moves the image to version 1.30.6 through an `images` block. It targets the
images named `nginx` and gives them a new tag and a new digest:

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
kubectl kustomize ~/essai-kustomize/base | grep -E 'image:|replicas:'
```

```text
  replicas: 2
        image: nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
  replicas: 1
        image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

`demo` moves to 1.30.6 with 2 replicas, and the base stays on 1.30.5 with 1
replica.

## 📚 Exercise 4: a patch for a single environment

`namespace`, `replicas` or `images` cover the usual changes. For any other
field, an overlay applies a **patch**: a piece of manifest that only holds what
changes, and that Kustomize merges with the object of the base. Add resource
requests and limits to `demo`, with a patch in the `patches` field. The patch
names the Deployment by its name in the base, `site`, and the container by its
name, `nginx`:

```bash
cat > ~/essai-kustomize/overlays/demo/limites.yaml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: site
spec:
  template:
    spec:
      containers:
        - name: nginx
          resources:
            requests:
              cpu: 50m
              memory: 32Mi
            limits:
              cpu: 200m
              memory: 64Mi
YAML
cat >> ~/essai-kustomize/overlays/demo/kustomization.yaml <<'YAML'
patches:
  - path: limites.yaml
YAML
kubectl kustomize ~/essai-kustomize/overlays/demo | sed -n '/^kind: Deployment/,$p' | grep -A7 'resources:'
kubectl kustomize ~/essai-kustomize/overlays/qualif | grep -c 'resources:'
```

```text
        resources:
          limits:
            cpu: 200m
            memory: 64Mi
          requests:
            cpu: 50m
            memory: 32Mi
0
```

`demo` gets the resources, `qualif` has none: the patch only touches the
overlay that cites it. What happens if the patch gets the name of the
container wrong? Try with a copy that calls it `web`:

```bash
sed 's/name: nginx$/name: web/' ~/essai-kustomize/overlays/demo/limites.yaml > ~/essai-kustomize/overlays/demo/limites-faux.yaml
sed -i 's/path: limites.yaml/path: limites-faux.yaml/' ~/essai-kustomize/overlays/demo/kustomization.yaml; kubectl kustomize ~/essai-kustomize/overlays/demo | sed -n '/^kind: Deployment/,$p' | grep -A12 'containers:'
```

```text
      containers:
      - name: web
        resources:
          limits:
            cpu: 200m
            memory: 64Mi
          requests:
            cpu: 50m
            memory: 32Mi
      - envFrom:
        - configMapRef:
            name: demo-site-config-mgm6hf9htk
        image: nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
```

No error. Kustomize found no `web` container, so it **added** one, without an
image, next to `nginx`, which did not get its resources. A patch merges by
name: a wrong name creates an object instead of changing one. Always read the
output of `kubectl kustomize`. Put the right patch back:

```bash
sed -i 's/path: limites-faux.yaml/path: limites.yaml/' ~/essai-kustomize/overlays/demo/kustomization.yaml; rm ~/essai-kustomize/overlays/demo/limites-faux.yaml
```

## 📚 Exercise 5: apply and compare

Apply `demo`, check the resources of the container, then compare each overlay
with the cluster:

```bash
kubectl apply -k ~/essai-kustomize/overlays/demo; kubectl rollout status deployment/demo-site -n essai-demo --timeout=120s | tail -1
kubectl get deployment demo-site -n essai-demo -o jsonpath='{.spec.template.spec.containers[0].resources}{"\n"}'
kubectl diff -k ~/essai-kustomize/overlays/demo; echo "demo : code $?"; kubectl diff -k ~/essai-kustomize/overlays/qualif; echo "qualif : code $?"
```

```text
configmap/demo-site-config-mgm6hf9htk created
service/demo-site-svc created
deployment.apps/demo-site created
deployment "demo-site" successfully rolled out
{"limits":{"cpu":"200m","memory":"64Mi"},"requests":{"cpu":"50m","memory":"32Mi"}}
demo : code 0
qualif : code 0
```

Code 0 for both: the cluster matches the folder exactly.

## 🧹 Clean up

Delete both scratch namespaces and the work folder:

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
overlays, `recette` and `production`, only one of which moves to version 2, and
a configuration merged in production.

```bash
dsoxlab run ckad-kustomize-overlays
dsoxlab challenge ckad-kustomize-overlays
```
