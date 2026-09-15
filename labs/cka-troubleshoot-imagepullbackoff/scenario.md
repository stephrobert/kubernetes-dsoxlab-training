# Get a Pod out of ImagePullBackOff

## The situation

In the **`lab`** namespace, the **`broken-pod`** Pod has not started since the
last update. The team wanted to move to the **Alpine variant of nginx 1.27**,
which is lighter, and claims the image exists on Docker Hub. Yet
`kubectl get pods` shows the Pod sometimes in `ErrImagePull`, sometimes in
`ImagePullBackOff`, never in `Running`.

The node has Internet access, and other images download without trouble. The
fault is in what the Pod asks for, not in what the node can do.

## What you must achieve

1. The `broken-pod` Pod is **running**, container ready.

2. Its image is a **public nginx image**, the one the team wanted, and it has
   really been downloaded onto the node.

3. The server **answers over HTTP**: the nginx welcome page is served.

## Useful bearings

`ImagePullBackOff` and `ErrImagePull` are two faces of the same problem: the
runtime tried to download the image, failed, and the kubelet spaces out its
attempts. The runtime's **exact** message, the one that says whether the
registry, the name or the tag is at fault, is not in the Pod's status: it is in
its events.

A bare Pod allows its image to be changed in place; deleting it and recreating
it is just as valid an answer, as long as the result carries the same name.

## How you will know it works

The tests read the state of the Pod, the image the runtime really pulled, and
they query the server from the node.

```bash
dsoxlab check cka-troubleshoot-imagepullbackoff
```
