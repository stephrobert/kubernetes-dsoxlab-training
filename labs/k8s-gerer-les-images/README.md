# Pin an image by digest and pull from a private registry

An image is named by a **tag** (`nginx:1.29`) or by a **digest**
(`nginx@sha256:…`). A tag can change content from one day to the next, a
digest always names exactly the same image. The lesson shows how to pin an
image and how to give credentials to a ServiceAccount. This course starts from
what goes wrong: a badly copied digest, a registry that refuses a client
without credentials, and a Secret aimed at the wrong server, without the
message changing.

You work in a scratch namespace, `essai-images`, with the `banniere` and
`miniatures` Deployments. The private registry `localhost:30500` is the one
the lab installed. The challenge is about other Deployments, in another
namespace: you will do it on your own, at the end.

Related page: [Images in Kubernetes](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kubernetes-images/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-gerer-les-images
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster `lab`
is running there, and your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 20 November
2026, with Kubernetes v1.37.0.

## 📚 Exercise 1: a tag, and what it names today

Create the scratch namespace and a `banniere` Deployment on the `nginx:1.29`
tag:

```bash
kubectl create namespace essai-images
kubectl create deployment banniere --image=nginx:1.29 -n essai-images && kubectl rollout status deployment/banniere -n essai-images --timeout=180s | tail -1
```

```text
namespace/essai-images created
deployment.apps/banniere created
deployment "banniere" successfully rolled out
```

Compare three fields of the Pod: the **requested** image (in `spec`), the
**started** image and its **digest** (in `status`):

```bash
kubectl get pods -n essai-images -l app=banniere -o jsonpath='{range .items[*]}{.spec.containers[0].image}{"\n"}{.status.containerStatuses[0].image}{"\n"}{.status.containerStatuses[0].imageID}{"\n"}{end}'
```

```text
nginx:1.29
docker.io/library/nginx:1.29
docker.io/library/nginx@sha256:1881968aff6f7cdcc4b888c00a11f4ce241ad7ec957e0cb4a9e19e93a3ff87ea
```

The spec only says `nginx:1.29`. The status says what this tag named **at
start time**: the `sha256:1881…` digest. Your digest may differ: the
`nginx:1.29` tag follows the fixes of version 1.29.

## 📚 Exercise 2: a badly copied digest

A digest is easy to copy wrong: 64 characters, with no mistake visible to the
eye. Simulate the mistake. The command reads the digest of the Pod, changes
its last character, then moves the Deployment to this wrong digest:

```bash
D=$(kubectl get pods -n essai-images -l app=banniere -o jsonpath='{.items[0].status.containerStatuses[0].imageID}' | sed 's/.*@//'); echo "$D"; FAUX=$(echo "$D" | sed 's/.$/0/'); [ "$FAUX" = "$D" ] && FAUX=$(echo "$D" | sed 's/.$/1/'); echo "$FAUX"; kubectl set image deployment/banniere nginx=nginx@$FAUX -n essai-images
sleep 20; kubectl get pods -n essai-images -l app=banniere
```

```text
sha256:1881968aff6f7cdcc4b888c00a11f4ce241ad7ec957e0cb4a9e19e93a3ff87ea
sha256:1881968aff6f7cdcc4b888c00a11f4ce241ad7ec957e0cb4a9e19e93a3ff87e0
deployment.apps/banniere image updated
NAME                        READY   STATUS             RESTARTS   AGE
banniere-57dbb788b5-mlhvr   0/1     ImagePullBackOff   0          20s
banniere-7f66886dd-wsnxw    1/1     Running            0          20s
```

The new Pod does not pull its image, the old one still serves. The why is in
the events of the waiting Pod. `sed` keeps the `Events` section, `grep` the
failure line, and `fold` cuts it into lines of 100 characters:

```bash
P=$(kubectl get pods -n essai-images -l app=banniere --field-selector=status.phase=Pending -o name | head -1); kubectl describe $P -n essai-images | sed -n '/^Events:/,$p' | grep -E 'Failed to pull' | head -1 | fold -w 100
```

```text
  Warning  Failed     5s (x2 over 19s)  kubelet            spec.containers{nginx}: Failed to pull im
age "nginx@sha256:1881968aff6f7cdcc4b888c00a11f4ce241ad7ec957e0cb4a9e19e93a3ff87e0": rpc error: code
 = NotFound desc = failed to pull and unpack image "docker.io/library/nginx@sha256:1881968aff6f7cdcc
4b888c00a11f4ce241ad7ec957e0cb4a9e19e93a3ff87e0": failed to resolve reference "docker.io/library/ngi
nx@sha256:1881968aff6f7cdcc4b888c00a11f4ce241ad7ec957e0cb4a9e19e93a3ff87e0": docker.io/library/nginx
@sha256:1881968aff6f7cdcc4b888c00a11f4ce241ad7ec957e0cb4a9e19e93a3ff87e0: not found
```

`not found`: no image carries this digest. It is the same message as a tag
that does not exist. Go back to the previous version, then pin the right digest
this time, read on a running Pod (`status.phase=Running`):

```bash
kubectl rollout undo deployment/banniere -n essai-images; kubectl rollout status deployment/banniere -n essai-images --timeout=120s | tail -1
D=$(kubectl get pods -n essai-images -l app=banniere --field-selector=status.phase=Running -o jsonpath='{.items[0].status.containerStatuses[0].imageID}' | sed 's/.*@//'); kubectl set image deployment/banniere nginx=nginx@$D -n essai-images && kubectl rollout status deployment/banniere -n essai-images --timeout=180s | tail -1; kubectl get deployment banniere -n essai-images -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

```text
deployment.apps/banniere rolled back
deployment "banniere" successfully rolled out
deployment.apps/banniere image updated
deployment "banniere" successfully rolled out
nginx@sha256:1881968aff6f7cdcc4b888c00a11f4ce241ad7ec957e0cb4a9e19e93a3ff87ea
```

The Deployment is pinned on the digest its Pods were running. Always read
this digest on a `Running` Pod: right after an `undo`, a Pod that has not
started yet has none.

## 📚 Exercise 3: a private registry, without credentials

Create a `miniatures` ServiceAccount, then a `miniatures` Deployment that uses
it and pulls an image from the private registry of the lab. `sed` adds the
`serviceAccountName` line to the generated Pod template:

```bash
kubectl create serviceaccount miniatures -n essai-images
kubectl create deployment miniatures --image=localhost:30500/galerie/vignettes:1.0 -n essai-images --dry-run=client -o yaml | sed 's/^    spec:/    spec:\n      serviceAccountName: miniatures/' | kubectl apply -f -
sleep 20; kubectl get pods -n essai-images -l app=miniatures
```

```text
serviceaccount/miniatures created
deployment.apps/miniatures created
NAME                          READY   STATUS             RESTARTS   AGE
miniatures-6846cd68cb-krkc8   0/1     ImagePullBackOff   0          20s
```

Read the failure message in the events of the namespace:

```bash
kubectl get events -n essai-images --field-selector reason=Failed -o custom-columns=MESSAGE:.message --no-headers | grep -m1 'localhost:30500' | fold -w 100
```

```text
Failed to pull image "localhost:30500/galerie/vignettes:1.0": failed to pull and unpack image "local
host:30500/galerie/vignettes:1.0": failed to resolve reference "localhost:30500/galerie/vignettes:1.
0": pull access denied, repository does not exist or may require authorization: authorization failed
: no basic auth credentials
```

`no basic auth credentials`: the client sent no credentials. Remember this
message: a registry that receives a **wrong** password answers differently.

## 📚 Exercise 4: a Secret aimed at the wrong server

Create a `docker-registry` Secret, but for another server, `localhost:5000`, a
common copy mistake. Attach it to the ServiceAccount, then replace the Pods:

```bash
kubectl create secret docker-registry registre-essai --docker-server=localhost:5000 --docker-username=galerie --docker-password=Vignettes-2026 -n essai-images
kubectl patch serviceaccount miniatures -n essai-images -p '{"imagePullSecrets":[{"name":"registre-essai"}]}'
kubectl rollout restart deployment/miniatures -n essai-images; sleep 25; kubectl get pods -n essai-images -l app=miniatures -o custom-columns='POD:.metadata.name,ETAT:.status.containerStatuses[0].state.waiting.reason,SECRETS:.spec.imagePullSecrets'
```

```text
secret/registre-essai created
serviceaccount/miniatures patched
deployment.apps/miniatures restarted
POD                           ETAT               SECRETS
miniatures-666c6d7978-4nj7t   ImagePullBackOff   [map[name:registre-essai]]
miniatures-6846cd68cb-krkc8   ImagePullBackOff   <none>
```

The new Pod does carry the Secret, and yet it fails. Its message, read on this
Pod alone:

```bash
P=$(kubectl get pods -n essai-images -l app=miniatures -o jsonpath='{range .items[?(@.spec.imagePullSecrets)]}{.metadata.name}{end}'); kubectl get events -n essai-images --field-selector involvedObject.name=$P,reason=Failed -o custom-columns=MESSAGE:.message --no-headers | grep -m1 'localhost:30500' | fold -w 100
```

```text
Failed to pull image "localhost:30500/galerie/vignettes:1.0": failed to pull and unpack image "local
host:30500/galerie/vignettes:1.0": failed to resolve reference "localhost:30500/galerie/vignettes:1.
0": pull access denied, repository does not exist or may require authorization: authorization failed
: no basic auth credentials
```

The same message as in exercise 3: a Secret for another server is of no use,
and the kubelet pulls as if it had none. The cause only shows in the Secret.
Its `.dockerconfigjson` field is base64-encoded:

```bash
kubectl get secret registre-essai -n essai-images -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d; echo
```

```text
{"auths":{"localhost:5000":{"username":"galerie","password":"Vignettes-2026","auth":"Z2FsZXJpZTpWaWduZXR0ZXMtMjAyNg=="}}}
```

`localhost:5000`, instead of `localhost:30500`. Fix the Secret **in place**,
under the same name: `--dry-run=client -o yaml` builds the new Secret, and
`kubectl replace` replaces the old one. Wait a minute, without touching the
Pods:

```bash
kubectl create secret docker-registry registre-essai --docker-server=localhost:30500 --docker-username=galerie --docker-password=Vignettes-2026 -n essai-images --dry-run=client -o yaml | kubectl replace -f -
sleep 60; kubectl get pods -n essai-images -l app=miniatures -o custom-columns='POD:.metadata.name,PRET:.status.containerStatuses[0].ready,ETAT:.status.containerStatuses[0].state.waiting.reason,SECRETS:.spec.imagePullSecrets'
```

```text
secret/registre-essai replaced
POD                           PRET   ETAT     SECRETS
miniatures-666c6d7978-4nj7t   true   <none>   [map[name:registre-essai]]
```

The Pod that already carried the Secret pulled its image on its own, on the
next round of its tries: the kubelet reads the **content** of the Secret again
at each attempt. The old Pod, without a Secret, went away with the end of the
rollout. A Pod born **before** the ServiceAccount got its Secret never receives
it: it must be replaced. The Deployment still cites no Secret:

```bash
kubectl rollout status deployment/miniatures -n essai-images --timeout=120s | tail -1
kubectl get deployment miniatures -n essai-images -o jsonpath='{.spec.template.spec.imagePullSecrets}'; echo '(fin)'
```

```text
deployment "miniatures" successfully rolled out
(fin)
```

Nothing before `(fin)`: it is the ServiceAccount that adds the Secret to the
Pods.

## 🧹 Clean up

Delete the scratch namespace, with its Deployments, its ServiceAccount and its
Secret:

```bash
kubectl delete namespace essai-images
```

```text
namespace "essai-images" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset k8s-gerer-les-images
dsoxlab check k8s-gerer-les-images
```

```text
╭── Result: k8s-gerer-les-images ───╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests  │
╰───────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: pin another application by digest, record
why a second one cannot pull its image, then repair it through its
ServiceAccount.

```bash
dsoxlab run k8s-gerer-les-images
dsoxlab challenge k8s-gerer-les-images
```
