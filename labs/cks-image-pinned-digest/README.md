# Pin an image by its digest

The lesson shows why to pin an image by its digest, and how to read the one
the node actually resolved. This course adds three cases it does not show: a
well-formed digest that points to no image, a reference that carries both a
tag and a digest, and the difference between the digest of a multi-platform
image and the image the node keeps for its own architecture.

You work in the `essai-digest` namespace, with the `busybox` image. The
challenge targets another namespace and another image: you will do it on your
own, at the end.

Related page: [Secure the supply chain](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/supply-chain-security/) (in French).

## 🔧 Before you start

Start the lab:

```bash
dsoxlab run cks-image-pinned-digest
```

You are now logged into `k8s-cp.lab`, the node that drives the kubeadm cluster
(the control plane). Your kubectl already targets it, and `ssh` reaches the
workers.

The outputs shown in this course were recorded on this machine on
22 November 2026, with Kubernetes v1.37.2 and containerd.

## 👻 Exercise 1: a digest that points to no image

A digest is recognised by its shape: `sha256:` followed by 64 hexadecimal
characters. Nothing checks that it exists when you write it. Start a Pod on a
tag, and another on a made-up digest:

```bash
kubectl create namespace essai-digest; kubectl run double --image=busybox:1.38.0 -n essai-digest -- sleep 3600; kubectl run fantome --image=busybox@sha256:1111111111111111111111111111111111111111111111111111111111111111 -n essai-digest -- sleep 3600; kubectl wait --for=condition=Ready pod/double -n essai-digest --timeout=120s; sleep 15; kubectl get pods -n essai-digest
```

```text
namespace/essai-digest created
pod/double created
pod/fantome created
pod/double condition met
NAME      READY   STATUS             RESTARTS   AGE
double    1/1     Running            0          16s
fantome   0/1     ImagePullBackOff   0          16s
```

The API server accepts both Pods. The tag one runs, the digest one stays in
`ImagePullBackOff`. Read the reason:

```bash
kubectl get pod fantome -n essai-digest -o jsonpath='{.status.containerStatuses[0].state.waiting.message}{"\n"}' | cut -c1-230
```

```text
Back-off pulling image "busybox@sha256:1111111111111111111111111111111111111111111111111111111111111111": ErrImagePull: rpc error: code = NotFound desc = failed to pull and unpack image "docker.io/library/busybox@sha256:1111111111
```

`NotFound`: the registry knows no content with that fingerprint. A wrong
digest only shows up at pull time, on the node. Remove that Pod:

```bash
kubectl delete pod fantome -n essai-digest
```

```text
pod "fantome" deleted from essai-digest namespace
```

## 🏷️ Exercise 2: with a digest, the tag no longer counts

A reference can carry both: `image:tag@sha256:...`. The tag is then for human
readers, and only the digest decides. To prove it, write a tag that does not
exist, `9.9.9`, in front of a real digest:

```bash
kubectl run faux-tag --image=busybox:9.9.9@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-digest -- sleep 3600; kubectl wait --for=condition=Ready pod/faux-tag -n essai-digest --timeout=120s; kubectl get pod faux-tag -n essai-digest -o jsonpath='{.status.containerStatuses[0].image} -> {.status.containerStatuses[0].imageID}{"\n"}'
```

```text
pod/faux-tag created
pod/faux-tag condition met
docker.io/library/busybox:1.38.0 -> docker.io/library/busybox@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

The Pod starts. containerd shows the image as `busybox:1.38.0`, the local tag
that matches this content, and the digest is the one you wrote. The `9.9.9`
tag was ignored: a wrong tag in front of a digest does not alert you, it only
misleads whoever reads the manifest.

## 🧱 Exercise 3: one index, several platforms

The digest published for `busybox:1.38.0` points to an **index**: a list that
points to one image per architecture (amd64, arm64…). The node pulls the
index, then keeps the image of its own architecture. Look at what containerd
keeps on the node of the `double` Pod:

```bash
N=$(kubectl get pod double -n essai-digest -o jsonpath='{.spec.nodeName}'); ssh -o StrictHostKeyChecking=no $N 'sudo crictl inspecti -o json busybox:1.38.0 | python3 -c "import json,sys; s=json.load(sys.stdin)[\"status\"]; print(\"repoDigests\", s[\"repoDigests\"]); print(\"id local\", s[\"id\"][:19])"'
```

```text
repoDigests ['docker.io/library/busybox@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4']
id local sha256:aaef90e06523
```

`repoDigests` holds the digest of the index, the one you write in a manifest.
The local ID is that of the amd64 image, a different one: that is why you must
never copy into a manifest an ID read with `crictl images`. Start a third Pod,
on the digest alone, and compare:

```bash
kubectl run plateforme --image=busybox@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-digest -- sleep 3600; kubectl wait --for=condition=Ready pod/plateforme -n essai-digest --timeout=120s; kubectl get pods -n essai-digest -o custom-columns=NOM:.metadata.name,IMAGE-ID:.status.containerStatuses[0].imageID
```

```text
pod/plateforme created
pod/plateforme condition met
NOM          IMAGE-ID
double       docker.io/library/busybox@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
faux-tag     docker.io/library/busybox@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
plateforme   docker.io/library/busybox@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
```

The three Pods, declared by tag, by wrong tag plus digest, and by digest
alone, all run the same content: `imageID` holds the same index digest for
all three.

## 🧹 Clean-up

Delete the test namespace, with its three Pods:

```bash
kubectl delete namespace essai-digest
```

```text
namespace "essai-digest" deleted
```

Then leave the machine and reset the lab. `dsoxlab reset` replays the lab's
clean-up then its preparation: you get back exactly the starting state of the
challenge. It asks you to confirm: answer `y`.

```bash
exit
dsoxlab reset cks-image-pinned-digest
dsoxlab check cks-image-pinned-digest
```

```text
╭─ Result: cks-image-pinned-digest ─╮
│  0 / 100 pts                      │
│  ░░░░░░░░░░░░░░░░░░░░  0/3 tests  │
╰───────────────────────────────────╯
```

0 out of 3: that is the expected result. The challenge is waiting for you,
untouched.

## 🎯 The challenge

Your turn, on your own this time: a Deployment running on a tag, to pin to the
digest of the image it actually runs, without stopping it.

```bash
dsoxlab run cks-image-pinned-digest
dsoxlab challenge cks-image-pinned-digest
```
