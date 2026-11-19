# Pin an image by digest and pull from a private registry

An image is named by a **tag** (`nginx:1.30`) or by a **digest**
(`nginx@sha256:…`). A tag can change content from one day to the next, a digest
always names exactly the same image. In this course, you read the image a Pod
really runs, you pin it by its digest, you read why an image cannot be pulled,
then you give a ServiceAccount the credentials of a private registry.

You work in a scratch namespace, `essai-images`, with the `banniere`
("banner"), `faute` ("mistake") and `miniatures` ("thumbnails") Deployments.
The private registry `localhost:30500` is the one the lab installed. The
challenge is about other Deployments, in another namespace: you will do it on
your own, at the end.

Related page: [Images in Kubernetes](https://www.stephane-robert.info/en/docs/conteneurs/orchestrateurs/kubernetes/kubernetes-images/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run k8s-gerer-les-images
```

You are now connected to the `k8s-kind.lab` machine. The kind cluster `lab` is
running there, and your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 19 November
2026, with Kubernetes 1.37.

## 📚 Exercise 1: a tag, and what it points to today

Create the scratch namespace and a `banniere` Deployment on the `nginx:1.30`
tag:

```bash
kubectl create namespace essai-images
kubectl create deployment banniere --image=nginx:1.30 -n essai-images && kubectl rollout status deployment/banniere -n essai-images --timeout=180s | tail -1
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
nginx:1.30
docker.io/library/nginx:1.30
docker.io/library/nginx@sha256:7fad6c0dff97965adbddf28027d934b111fc0221a554315dc274712f3fba24d3
```

The spec only says `nginx:1.30`. The status says what that tag pointed to **at
start time**: the digest `sha256:7fad…`. If the publisher releases a new image
under the same tag tomorrow, the next Pods will no longer run the same thing.

## 📚 Exercise 2: pin the image by its digest

Get the digest from the status (`sed` keeps what follows the `@`), then put it
into the Deployment's image:

```bash
D=$(kubectl get pods -n essai-images -l app=banniere -o jsonpath='{.items[0].status.containerStatuses[0].imageID}' | sed 's/.*@//'); echo "$D"; kubectl set image deployment/banniere nginx=nginx@$D -n essai-images && kubectl rollout status deployment/banniere -n essai-images --timeout=180s | tail -1
```

```text
sha256:7fad6c0dff97965adbddf28027d934b111fc0221a554315dc274712f3fba24d3
deployment.apps/banniere image updated
deployment "banniere" successfully rolled out
```

Read the Deployment's image again, then the digest of its Pods:

```bash
kubectl get deployment banniere -n essai-images -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'; kubectl get pods -n essai-images -l app=banniere -o jsonpath='{range .items[*]}{.status.containerStatuses[0].imageID}{"\n"}{end}'
```

```text
nginx@sha256:7fad6c0dff97965adbddf28027d934b111fc0221a554315dc274712f3fba24d3
docker.io/library/nginx@sha256:7fad6c0dff97965adbddf28027d934b111fc0221a554315dc274712f3fba24d3
docker.io/library/nginx@sha256:7fad6c0dff97965adbddf28027d934b111fc0221a554315dc274712f3fba24d3
```

The Deployment is pinned on the digest its Pods were running. The two Pod
lines are the new Pod and the old one, still stopping: same digest, so exactly
the same image.

## 📚 Exercise 3: an image that does not exist

Create a `faute` Deployment on a tag that does not exist:

```bash
kubectl create deployment faute --image=nginx:1.30-introuvable -n essai-images; sleep 20; kubectl get pods -n essai-images -l app=faute
```

```text
deployment.apps/faute created
NAME                    READY   STATUS             RESTARTS   AGE
faute-b7c5d55d5-fzckt   0/1     ImagePullBackOff   0          20s
```

`ImagePullBackOff` only says that the image cannot be pulled, and that
Kubernetes waits before trying again. The **why** is in the Pod's events.
`kubectl describe` shows them at the end of its output. `sed` keeps the
`Events` section, `grep` the failure line, and `fold` cuts it into lines of
100 characters:

```bash
P=$(kubectl get pods -n essai-images -l app=faute -o name | head -1); kubectl describe $P -n essai-images | sed -n '/^Events:/,$p' | grep -E 'Failed to pull' | head -1 | fold -w 100
```

```text
  Warning  Failed     4s (x2 over 19s)  kubelet            spec.containers{nginx}: Failed to pull im
age "nginx:1.30-introuvable": rpc error: code = NotFound desc = failed to pull and unpack image "doc
ker.io/library/nginx:1.30-introuvable": failed to resolve reference "docker.io/library/nginx:1.30-in
trouvable": docker.io/library/nginx:1.30-introuvable: not found
```

The registry answers `NotFound` then `not found`: this tag does not exist.
Another cause would give another message. Always read this message before
correcting anything.

## 📚 Exercise 4: a private registry, without credentials

Create a `miniatures` ServiceAccount, then a `miniatures` Deployment that uses
it and pulls an image from the lab's private registry. `sed` adds the
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
miniatures-6846cd68cb-b8452   0/1     ImagePullBackOff   0          20s
```

The image cannot be pulled. The exact message is in the Pod's events, as in
exercise 3: the challenge will ask you to read it yourself.

## 📚 Exercise 5: give the credentials to the ServiceAccount

The credentials of a registry are stored in a Secret of type `docker-registry`.
Create it with the registry address and its credentials:

```bash
kubectl create secret docker-registry registre-essai --docker-server=localhost:30500 --docker-username=galerie --docker-password=Vignettes-2026 -n essai-images
```

```text
secret/registre-essai created
```

Rather than writing this Secret into every Pod, attach it to the
ServiceAccount through its `imagePullSecrets` field:

```bash
kubectl patch serviceaccount miniatures -n essai-images -p '{"imagePullSecrets":[{"name":"registre-essai"}]}'; kubectl get serviceaccount miniatures -n essai-images -o jsonpath='{.imagePullSecrets}{"\n"}'
```

```text
serviceaccount/miniatures patched
[{"name":"registre-essai"}]
```

Wait a little, then look at the existing Pod: its state (`ETAT`), and the
Secrets it carries:

```bash
sleep 15; kubectl get pods -n essai-images -l app=miniatures -o custom-columns='POD:.metadata.name,ETAT:.status.containerStatuses[0].state.waiting.reason,SECRETS:.spec.imagePullSecrets'
```

```text
POD                           ETAT           SECRETS
miniatures-6846cd68cb-b8452   ErrImagePull   <none>
```

Still failing, and with no Secret (`<none>`). The ServiceAccount gives its
`imagePullSecrets` to a Pod **when the Pod is created**. This Pod existed
before: it will never receive them.

## 📚 Exercise 6: only new Pods receive the Secret

`kubectl rollout restart` replaces the Deployment's Pods with new ones:

```bash
kubectl rollout restart deployment/miniatures -n essai-images && kubectl rollout status deployment/miniatures -n essai-images --timeout=180s | tail -1; sleep 5
kubectl get pods -n essai-images -l app=miniatures -o custom-columns='POD:.metadata.name,PRET:.status.containerStatuses[0].ready,SECRETS:.spec.imagePullSecrets'
```

```text
deployment.apps/miniatures restarted
deployment "miniatures" successfully rolled out
POD                           PRET   SECRETS
miniatures-646b467959-bq76n   true   [map[name:registre-essai]]
```

The new Pod carries the Secret, pulled its image and runs (`PRET` means
"ready"). Yet the Deployment itself names no Secret (`echo '(fin)'` marks the
end of the output; "fin" means "end"):

```bash
kubectl get deployment miniatures -n essai-images -o jsonpath='{.spec.template.spec.imagePullSecrets}'; echo '(fin)'
```

```text
(fin)
```

Nothing before `(fin)`: the ServiceAccount added the Secret to the Pod. The
credentials thus stay in a single place, and no Pod manifest names them.

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
