# Get a Pod out of ImagePullBackOff

The lesson shows the `ImagePullBackOff` state: the kubelet cannot fetch a
container's image, and retries less and less often. This course adds cases
the lesson does not show: a missing image you forbid downloading, an image
name refused before it even reaches the cluster, a digest that does not
exist, and the download tried directly from the node.

You work in a scratch namespace, `essai-tirage`. The challenge is about
another Pod: you will do it on your own, at the end.

Related page (in French): [ImagePullBackOff](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/imagepullbackoff-kubernetes/).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cka-troubleshoot-imagepullbackoff
```

You are now connected to `k8s-cp.lab`, the node that runs the kubeadm cluster
(the control plane). Your kubectl already targets it.

The outputs shown in this course were recorded on this machine on 21 November
2026, with Kubernetes v1.37.2.

## 🚫 Exercise 1: forbid downloading a missing image

With `imagePullPolicy: Never`, the kubelet only uses images already present
on the node. Create a Pod with an image that is not there:

```bash
kubectl create namespace essai-tirage; kubectl run jamais --image=nginx:1.29.99-absente -n essai-tirage --image-pull-policy=Never; sleep 8; kubectl get pod jamais -n essai-tirage -o jsonpath='{.status.containerStatuses[0].state.waiting.reason}: {.status.containerStatuses[0].state.waiting.message}{"\n"}' | cut -c1-220
```

```text
namespace/essai-tirage created
pod/jamais created
ErrImageNeverPull: Container image "nginx:1.29.99-absente" is not present with pull policy of Never
```

`ErrImageNeverPull`: this is not a download failure, the kubelet did not try.
This policy is meant for preloaded images. With a missing image, it blocks
the Pod forever.

## ✏️ Exercise 2: an invalid image name

Image names are written in lower case. Try an upper-case letter:

```bash
kubectl run majuscules --image=Nginx:1.30 -n essai-tirage; echo "run : code $?"; kubectl get pods -n essai-tirage -o name
```

```text
error: invalid image name "Nginx:1.30": invalid reference format
run : code 1
pod/jamais
```

kubectl refuses before sending anything (`invalid reference format`), and
only `jamais` exists in the namespace. A format mistake therefore does not
give an `ImagePullBackOff`: it gives an error straight away. An
`ImagePullBackOff` points to a well-formed name that leads nowhere.

## 🔏 Exercise 3: a digest that does not exist

Naming an image by its digest (`@sha256:…`) guarantees you get exactly that
image. Ask for a digest nobody published:

```bash
kubectl run empreinte --image=nginx@sha256:0000000000000000000000000000000000000000000000000000000000000000 -n essai-tirage; sleep 15; kubectl get pod empreinte -n essai-tirage -o jsonpath='{.status.containerStatuses[0].state.waiting.reason}: {.status.containerStatuses[0].state.waiting.message}{"\n"}' | cut -c1-220
```

```text
pod/empreinte created
ImagePullBackOff: Back-off pulling image "nginx@sha256:0000000000000000000000000000000000000000000000000000000000000000": ErrImagePull: rpc error: code = NotFound desc = failed to pull and unpack image "docker.io/library
```

`NotFound`: the registry answers, but has no image with this digest. The
message is cut here, but it names the full image, with its registry
(`docker.io/library/nginx`). That full name is what you must check.

## 🖥️ Exercise 4: try the download from the node

`crictl pull` downloads an image onto a node the way the kubelet would. Try
the same digest from the Pod's node (`nœud` means "node"):

```bash
N=$(kubectl get pod empreinte -n essai-tirage -o jsonpath='{.spec.nodeName}'); echo "nœud : $N"; ssh -o StrictHostKeyChecking=no $N 'sudo crictl pull nginx@sha256:0000000000000000000000000000000000000000000000000000000000000000 2>&1 | tail -1 | cut -c1-200'
```

```text
nœud : k8s-w1.lab
time="2026-11-21T05:47:12Z" level=error msg="pulling image: rpc error: code = NotFound desc = failed to pull and unpack image \"docker.io/library/nginx@sha256:00000000000000000000000000000000000000000
```

Same error as in the Pod's state. Now try an image that exists, and look for
it among the node's images:

```bash
N=$(kubectl get pod empreinte -n essai-tirage -o jsonpath='{.spec.nodeName}'); ssh -o StrictHostKeyChecking=no $N 'sudo crictl pull nginx:1.30.5 2>&1 | tail -1; sudo crictl images --digests | grep -m1 "nginx.*1.30.5"' | cut -c1-140
```

```text
Image is up to date for sha256:3a8edbda21b6357f9d8e8d441c00c44673e89af4c157e76f0f117f2429570e60
docker.io/library/nginx                                                       1.30.5              9bf97bd7714f5       3a8edbda21b63       63
```

The image is there, with its digest (`9bf97bd7714f5`, the start of the one
the courses use). Testing from the node separates two questions: can the node
reach the registry and download, and does the Pod ask for the right image.

## 🧹 Clean-up

Delete the scratch namespace:

```bash
kubectl delete namespace essai-tirage
```

```text
namespace "essai-tirage" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cka-troubleshoot-imagepullbackoff
dsoxlab check cka-troubleshoot-imagepullbackoff
```

```text
╭─ Result: cka-troubleshoot-imagepullbackoff ─╮
│  0 / 100 pts                                │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests            │
╰─────────────────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a Pod stuck on its image, to get running
again with the image the team wanted.

```bash
dsoxlab run cka-troubleshoot-imagepullbackoff
dsoxlab challenge cka-troubleshoot-imagepullbackoff
```
